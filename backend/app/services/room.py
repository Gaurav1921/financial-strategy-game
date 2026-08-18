"""Room lifecycle: lobby membership, connections, and the live round loop.

A `Room` owns one game's authoritative `GameState`, its seeded RNG, every
connected player's WebSocket, and the background task that drives the round
timer (GAMEPLAY.md Section 2). `RoomStore` is the process-wide registry of
every live room, keyed by room code. Both are in-memory only: a game lives
and dies inside one room's session (GDD.md Section 11), so there is nothing
here that needs a database.
"""

import asyncio
import contextlib
import random
import secrets
import string
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket

from app.core.constants import MAX_PLAYERS, RESULT_DISPLAY_SECONDS, ROUND_TIMER_SECONDS
from app.models.game import (
    Alliance,
    AllocationRequest,
    GameState,
    Industry,
    Phase,
    Player,
    PublicPlayerView,
    RoundSummary,
)
from app.services import conflict_engine, endgame_engine, round_engine

PROPOSAL_ID_BYTES = 4
ACTIVE_PHASES = (Phase.BUILDING, Phase.CONFLICT, Phase.FINAL)  # a round loop is actually running


@dataclass
class AllianceProposal:
    """A pending, not-yet-accepted alliance invite from one player to another."""

    id: str
    from_id: str
    to_id: str
    jv_industry: Industry | None
    pact_declared: bool | None


@dataclass
class KickVote:
    """An in-progress vote to remove a player who's missed at least one round."""

    target_id: str
    voters: set[str]


ROOM_CODE_ALPHABET = string.ascii_uppercase
ROOM_CODE_LENGTH = 4
PLAYER_ID_BYTES = 4
RECONNECT_TOKEN_BYTES = 24


class Room:
    """One room's live session: game state, connections, and the round loop."""

    def __init__(self, code: str, on_ended: Callable[[], None] | None = None) -> None:
        """Creates an empty lobby with the given room code.

        Args:
            code: This room's unique, player-facing join code.
            on_ended: Called once, when this room's game loop exits for any
                reason (the game reached `Phase.ENDED`, or a round failed).
                `RoomStore` uses this to evict the room once nobody can join
                or reconnect to it anymore, so a long-running process
                doesn't accumulate one `Room` per game ever started.
        """
        self.state = GameState(room_code=code)
        self.rng = random.Random()  # noqa: S311 - scenario/timing rolls, not a security use
        self.connections: dict[str, WebSocket] = {}
        self.reconnect_tokens: dict[str, str] = {}
        self.pending_allocations: dict[str, AllocationRequest] = {}
        self.pending_proposals: dict[str, AllianceProposal] = {}
        self.kick_votes: dict[str, KickVote] = {}
        self.round_deadline: float | None = None
        self._round_ready = asyncio.Event()
        self._game_task: asyncio.Task[None] | None = None
        self._on_ended = on_ended

    def join(self, name: str, icon: str, industry: Industry) -> tuple[Player, str]:
        """Adds a new player to this room's lobby.

        Args:
            name: The player's display name, unique within this room.
            icon: A short icon identifier the frontend renders.
            industry: The Industry this player's company belongs to.

        Returns:
            The new player, plus a reconnect token their client must store
            and present on every future WebSocket connection.

        Raises:
            ValueError: If the game already started, the room is full, or
                the name is already taken.
        """
        if self.state.phase != Phase.LOBBY:
            raise ValueError("this game has already started")
        if len(self.state.players) >= MAX_PLAYERS:
            raise ValueError("this room is full")
        if any(p.name == name for p in self.state.players.values()):
            raise ValueError("that name is already taken in this room")

        player_id = secrets.token_hex(PLAYER_ID_BYTES)
        while player_id in self.state.players:
            player_id = secrets.token_hex(PLAYER_ID_BYTES)
        is_host = not self.state.players
        player = Player(id=player_id, name=name, icon=icon, industry=industry, is_host=is_host)
        self.state.players[player_id] = player

        token = secrets.token_urlsafe(RECONNECT_TOKEN_BYTES)
        self.reconnect_tokens[player_id] = token
        return player, token

    def authenticate(self, player_id: str, token: str) -> Player:
        """Verifies a reconnect token and returns the player it belongs to.

        Args:
            player_id: The player id presented by the client.
            token: The reconnect token presented by the client.

        Returns:
            The authenticated player.

        Raises:
            ValueError: If the id/token pair doesn't match a player here.
        """
        expected = self.reconnect_tokens.get(player_id)
        if expected is None or not secrets.compare_digest(expected, token):
            raise ValueError("invalid room code, player id, or reconnect token")
        return self.state.players[player_id]

    def start(self, player_id: str, token: str) -> None:
        """Authenticates the requester as this room's host and starts the game.

        Args:
            player_id: The player requesting the start.
            token: Their reconnect token, proving they are that player.

        Raises:
            ValueError: If the id/token pair is invalid, the requester isn't
                this room's host, or `round_engine.start_game` itself rejects
                the start (wrong phase, too few/many players).
        """
        host = self.authenticate(player_id, token)
        if not host.is_host:
            raise ValueError("only the host can start the game")

        round_engine.start_game(self.state, self.rng)
        self._game_task = asyncio.create_task(self._run_game_loop())

    def submit_allocation(self, player_id: str, allocation: AllocationRequest) -> None:
        """Records a player's allocation for the round currently in progress.

        Marks the round ready to resolve early once every connected player
        has submitted (GAMEPLAY.md Section 2's "ends the moment every active
        player signals ready").

        Args:
            player_id: The submitting player.
            allocation: Their chosen split for this round's cash.

        Raises:
            ValueError: If no round is currently accepting allocations.
        """
        if self.state.phase not in ACTIVE_PHASES:
            raise ValueError("no round is currently accepting allocations")
        self.pending_allocations[player_id] = allocation

        active_ids = {pid for pid, p in self.state.players.items() if p.connected}
        if active_ids and active_ids.issubset(self.pending_allocations.keys()):
            self._round_ready.set()

    def _require_started(self) -> None:
        if self.state.phase not in ACTIVE_PHASES:
            raise ValueError("the game hasn't started yet")

    def propose_alliance(
        self,
        from_id: str,
        to_id: str,
        jv_industry: Industry | None,
        pact_declared: bool | None,
    ) -> AllianceProposal:
        """Records a pending alliance invite for `to_id` to accept or decline.

        Args:
            from_id: The proposing player.
            to_id: The invited player.
            jv_industry: The Industry to seed a Joint Venture in, or None.
            pact_declared: True/False for a declared/covert Defense Pact, or
                None for a pure Joint Venture.

        Returns:
            The pending proposal, including its id for `respond_alliance`.

        Raises:
            ValueError: If the game hasn't started, the invited player
                doesn't exist, or a player is proposing to themselves.
        """
        self._require_started()
        if to_id not in self.state.players:
            raise ValueError("no such player")
        if from_id == to_id:
            raise ValueError("a player cannot ally with themselves")
        proposal_id = secrets.token_hex(PROPOSAL_ID_BYTES)
        proposal = AllianceProposal(proposal_id, from_id, to_id, jv_industry, pact_declared)
        self.pending_proposals[proposal_id] = proposal
        return proposal

    def respond_alliance(self, player_id: str, proposal_id: str, accept: bool) -> Alliance | None:
        """Accepts or declines a pending alliance proposal addressed to this player.

        Args:
            player_id: The player responding; must be the invited partner.
            proposal_id: Which pending proposal this responds to.
            accept: Whether to form the alliance.

        Returns:
            The newly formed alliance, or None if declined.

        Raises:
            ValueError: If no such pending proposal is addressed to this
                player, or `conflict_engine.propose_alliance` itself rejects
                it (an ally cap already full, etc).
        """
        proposal = self.pending_proposals.get(proposal_id)
        if proposal is None or proposal.to_id != player_id:
            raise ValueError("no such pending proposal")
        del self.pending_proposals[proposal_id]
        if not accept:
            return None
        return conflict_engine.propose_alliance(
            self.state,
            proposal.from_id,
            proposal.to_id,
            proposal.jv_industry,
            proposal.pact_declared,
        )

    def top_up_jv(self, player_id: str, ally_id: str) -> None:
        """Adds a top-up to a Joint Venture the requesting player is part of."""
        self._require_started()
        conflict_engine.top_up_jv(self.state, player_id, ally_id)

    def drain_jv(self, player_id: str, ally_id: str) -> float:
        """Drains a Joint Venture the requesting player is part of."""
        self._require_started()
        return conflict_engine.drain_jv(self.state, player_id, ally_id)

    def break_pact(self, player_id: str, ally_id: str) -> bool:
        """Breaks a Defense Pact the requesting player is part of."""
        self._require_started()
        return conflict_engine.initiate_pact_break(self.state, player_id, ally_id)

    def hostile_bid(self, attacker_id: str, target_id: str) -> conflict_engine.HostileBidResult:
        """Resolves a Hostile Bid. Conflict Phase (or the Final Round) only."""
        if self.state.phase not in (Phase.CONFLICT, Phase.FINAL):
            raise ValueError("Hostile Bids only open once the Conflict Phase starts")
        return conflict_engine.resolve_hostile_bid(
            self.state, attacker_id, target_id, self.state.round_number
        )

    def counter_attack(self, challenger_id: str) -> conflict_engine.HostileBidResult:
        """Resolves a counter-attack against the current runaway leader, if any."""
        if self.state.phase not in (Phase.CONFLICT, Phase.FINAL):
            raise ValueError("counter-attacks only open once the Conflict Phase starts")
        return conflict_engine.resolve_counter_attack(
            self.state, challenger_id, self.state.round_number
        )

    def audit(self, auditor_id: str, target_id: str) -> conflict_engine.AuditResult:
        """Pays to reveal a target's true financial breakdown to the auditor."""
        self._require_started()
        return conflict_engine.audit_player(self.state, auditor_id, target_id)

    def recruit_co_founder(self, host_id: str, broke_player_id: str) -> None:
        """A living player recruits a Board Observer as their co-founder."""
        self._require_started()
        endgame_engine.recruit_co_founder(self.state, host_id, broke_player_id)

    def buy_out_co_founder(self, host_id: str, co_founder_id: str) -> float:
        """A host buys their co-founder out entirely, once they can afford it."""
        self._require_started()
        return endgame_engine.buy_out_co_founder(self.state, host_id, co_founder_id)

    def back_player(self, backer_id: str, target_id: str) -> None:
        """A Board Observer picks a living player to root for (Final Round tiebreak)."""
        self._require_started()
        endgame_engine.back_player(self.state, backer_id, target_id)

    def initiate_kick_vote(self, initiator_id: str, target_id: str) -> KickVote:
        """Starts (or joins) a vote to remove a player who's missed at least one round.

        Args:
            initiator_id: The player starting or joining the vote.
            target_id: The player the vote is against.

        Returns:
            The vote's current state.

        Raises:
            ValueError: If the target isn't eligible (already voted out,
                hasn't missed a round, or is the initiator themselves).
        """
        self._require_started()
        self._validate_kick_target(initiator_id, target_id)
        vote = self.kick_votes.setdefault(target_id, KickVote(target_id=target_id, voters=set()))
        vote.voters.add(initiator_id)
        self._tally_kick_vote(target_id)
        return vote

    def cast_kick_vote(self, voter_id: str, target_id: str) -> KickVote:
        """Adds a vote to an already-open vote to remove a player.

        Args:
            voter_id: The player casting a vote.
            target_id: The player the vote is against.

        Returns:
            The vote's current state.

        Raises:
            ValueError: If no vote is currently open against that player.
        """
        vote = self.kick_votes.get(target_id)
        if vote is None:
            raise ValueError("no vote is currently open against that player")
        vote.voters.add(voter_id)
        self._tally_kick_vote(target_id)
        return vote

    def _validate_kick_target(self, initiator_id: str, target_id: str) -> None:
        if target_id == initiator_id:
            raise ValueError("cannot start a vote against yourself")
        target = self.state.players.get(target_id)
        if target is None:
            raise ValueError("no such player")
        if target.afk_kicked:
            raise ValueError("that player has already been voted out")
        if target.missed_rounds < 1:
            raise ValueError("that player hasn't missed a round yet")

    def _tally_kick_vote(self, target_id: str) -> bool:
        """Applies the vote once a strict majority of other active players back it."""
        vote = self.kick_votes[target_id]
        eligible = {
            pid for pid, p in self.state.players.items() if pid != target_id and not p.afk_kicked
        }
        majority = len(eligible) // 2 + 1
        if len(vote.voters & eligible) < majority:
            return False
        self.state.players[target_id].afk_kicked = True
        del self.kick_votes[target_id]
        return True

    async def register_connection(self, player_id: str, websocket: WebSocket) -> None:
        """Attaches a live WebSocket to a player and marks them connected.

        A player previously voted out for being disconnected simply resumes
        playing normally the moment they reconnect (GDD.md Section 4.1);
        that vote isn't a permanent removal.

        Args:
            player_id: The player this socket belongs to.
            websocket: The already-accepted WebSocket connection.
        """
        self.connections[player_id] = websocket
        self.state.players[player_id].connected = True
        self.state.players[player_id].afk_kicked = False
        await self.broadcast_state()

    async def unregister_connection(self, player_id: str, websocket: WebSocket) -> None:
        """Detaches a player's WebSocket and marks them disconnected.

        Only acts if `websocket` is still the connection actually registered
        for this player. A reconnect (new tab, refresh) can register a fresh
        socket for the same player before the old one notices it's dead;
        when that stale socket's own cleanup finally runs, it must not evict
        the newer, live connection that already replaced it, this check is
        what tells the two apart.

        Args:
            player_id: The player whose socket just closed.
            websocket: The specific connection that closed.
        """
        if self.connections.get(player_id) is not websocket:
            return
        self.connections.pop(player_id, None)
        if player_id in self.state.players:
            self.state.players[player_id].connected = False
            await self.broadcast_state()

    def _declared_allies_of(self, player_id: str) -> list[str]:
        """Player ids of a player's *declared* Defense Pact partners only.

        A declared pact is automatically public (GDD.md Section 6/7); a
        covert one stays invisible here even to the pact's own partner's
        other observers, until a fight actually reveals it.
        """
        return [
            a.other(player_id)
            for a in self.state.alliances_of(player_id)
            if a.pact_declared is True
        ]

    async def broadcast_state(self) -> None:
        """Sends every connected player a personalized state snapshot.

        Every player sees everyone's name/icon/Power (GDD.md Section 6's
        "only Power is shown, always"), plus their own full financial
        detail, and nobody else's.
        """
        public_players = [
            PublicPlayerView.of(
                p, self.state.round_number, self._declared_allies_of(p.id)
            ).model_dump()
            for p in self.state.players.values()
        ]
        # Public: anyone deciding whether to join a kick vote needs to see
        # one is already open and how close it is to passing.
        kick_votes = [
            {"target_id": vote.target_id, "voters": sorted(vote.voters)}
            for vote in self.kick_votes.values()
        ]
        for player_id, websocket in list(self.connections.items()):
            payload = {
                "type": "state",
                "phase": self.state.phase.value,
                "round_number": self.state.round_number,
                "players": public_players,
                "me": self.state.players[player_id].model_dump(),
                "my_alliances": self._alliances_view(player_id),
                "kick_votes": kick_votes,
                "winner_id": self.state.winner_id,
            }
            await self._send(player_id, websocket, payload)

    def _alliances_view(self, player_id: str) -> list[dict[str, Any]]:
        """A player's own alliances, private detail included (their own eyes only)."""
        return [
            {
                "ally_id": a.other(player_id),
                "jv_industry": a.jv.industry if a.jv else None,
                "jv_value": a.jv.value if a.jv else None,
                "pact_declared": a.pact_declared,
                "pending_break": a.pending_pact_break_by is not None,
            }
            for a in self.state.alliances_of(player_id)
        ]

    async def _broadcast_round_result(self, summary: RoundSummary) -> None:
        """Sends every connected player their own view of one round's result."""
        base = summary.model_dump()
        for player_id, websocket in list(self.connections.items()):
            payload = {
                "type": "round_result",
                **base,
                "income": {player_id: base["income"].get(player_id, 0.0)},
                "eroded_idle_cash": {player_id: base["eroded_idle_cash"].get(player_id, 0.0)},
            }
            await self._send(player_id, websocket, payload)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """Sends one message to every currently connected player.

        Args:
            payload: The message to send.
        """
        for player_id, websocket in list(self.connections.items()):
            await self._send(player_id, websocket, payload)

    async def send_to(self, player_id: str, payload: dict[str, Any]) -> None:
        """Sends one message to a single connected player, if they're online.

        Args:
            player_id: The recipient. Silently does nothing if they're not
                currently connected (an alliance invite or Audit result
                that arrives to a closed socket has nowhere useful to go).
            payload: The message to send.
        """
        websocket = self.connections.get(player_id)
        if websocket is not None:
            await self._send(player_id, websocket, payload)

    async def _send(self, player_id: str, websocket: WebSocket, payload: dict[str, Any]) -> None:
        try:
            await websocket.send_json(payload)
        except Exception:  # noqa: BLE001 - a dead socket shouldn't crash the room loop
            await self.unregister_connection(player_id, websocket)

    async def _run_game_loop(self) -> None:
        """Drives every round from just after start until the game ends.

        A round-resolution failure (a bug, or a genuinely invalid state)
        is broadcast as an error and ends this room's loop rather than
        silently vanishing: an unhandled exception in a detached
        `asyncio.create_task` would otherwise just be swallowed, leaving
        every connected player stuck on a round that will never resolve.
        `on_ended` (passed to `__init__`) fires exactly once no matter
        which of those two ways this loop actually ends, so `RoomStore`
        can evict a finished room either way.
        """
        try:
            await self._run_game_loop_body()
        finally:
            if self._on_ended is not None:
                self._on_ended()

    async def _run_game_loop_body(self) -> None:
        # Without this, clients only learn the game has left the lobby once
        # round 1 fully resolves and the next `state` broadcast goes out -
        # the phase actually changed the instant `start()` ran, so say so
        # immediately instead of leaving everyone on the lobby screen for
        # up to a full round timer.
        await self.broadcast_state()

        while self.state.phase in ACTIVE_PHASES:
            self.pending_allocations = {}
            self._round_ready = asyncio.Event()
            self.round_deadline = time.time() + ROUND_TIMER_SECONDS

            # Drawn and revealed *before* allocation, not resolved silently
            # at the end: players read this to decide where new cash goes
            # (GAMEPLAY.md Section 3), the same scenario is reused below
            # once the collection window closes.
            scenario = round_engine.draw_scenario(self.rng)

            await self.broadcast(
                {
                    "type": "round_started",
                    "round_number": self.state.round_number + 1,
                    "phase": self.state.phase.value,
                    "deadline": self.round_deadline,
                    "scenario": scenario.model_dump(),
                }
            )

            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._round_ready.wait(), timeout=ROUND_TIMER_SECONDS)

            try:
                summary = round_engine.advance_round(self.state, self.pending_allocations, scenario)
            except ValueError as exc:
                await self.broadcast({"type": "error", "message": f"round failed: {exc}"})
                return

            await self._broadcast_round_result(summary)
            await self.broadcast_state()

            # A round that resolves the instant everyone submits would
            # otherwise flash the result screen for a few milliseconds
            # before the next round's scenario replaces it - give the
            # table a real, guaranteed moment to read what just happened.
            if self.state.phase in ACTIVE_PHASES:
                await asyncio.sleep(RESULT_DISPLAY_SECONDS)


class RoomStore:
    """Process-wide registry of every live room, keyed by room code."""

    def __init__(self) -> None:
        """Creates an empty store, holding no rooms yet."""
        self._rooms: dict[str, Room] = {}

    def create_room(self) -> Room:
        """Creates a new, empty room with a fresh, unique room code.

        The room removes itself from this store once its game loop ends
        (`Room.__init__`'s `on_ended`), so a long-running process doesn't
        keep every game ever started in memory for the life of the server.

        Returns:
            The new room.
        """
        code = self._generate_unique_code()
        room = Room(code, on_ended=lambda: self._rooms.pop(code, None))
        self._rooms[code] = room
        return room

    def get(self, code: str) -> Room | None:
        """Looks up a room by code.

        Args:
            code: The room code, case-insensitive.

        Returns:
            The room, or None if no such room exists.
        """
        return self._rooms.get(code.upper())

    def _generate_unique_code(self) -> str:
        while True:
            code = "".join(secrets.choice(ROOM_CODE_ALPHABET) for _ in range(ROOM_CODE_LENGTH))
            if code not in self._rooms:
                return code


room_store = RoomStore()
