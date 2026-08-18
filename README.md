# Hostile Ledger

A web-based financial strategy game for a small group of friends (3 to 10)
playing together in one sitting - start to finish in under an hour, like a
board game night. Everyone builds a company and grows a **Power** score
built from cash, real estate, stock positions, loans, and captured rivals -
not just a single net-worth number. The biggest plays (a Hostile Bid on a
rival's company) usually need allies to pull off, some of your allies might
secretly want you to fail, and every claim anyone makes can be bluffed.
See [`docs/GDD.md`](docs/GDD.md) for the full design.

## Repository structure

- **`docs/`** - all project documentation.
  - [`GDD.md`](docs/GDD.md) - the full game design: the Power system, the
    Building/Conflict phase structure, all six ways to make money, combat
    rules, Power Cards, and the MVP scope for the first playable version.
  - [`GAMEPLAY.md`](docs/GAMEPLAY.md) - the practical companion to the GDD:
    what a player actually sees and does, round by round.
  - [`TABLE_REFERENCE.html`](docs/TABLE_REFERENCE.html) - a print-and-play
    reference card for running a live game: the round loop, rates, combat
    math, and all 7 Power Cards laid out to cut apart and deal privately.
  - [`MARKET_RESEARCH.md`](docs/MARKET_RESEARCH.md) - research into
    competing games (mobile 4X strategy titles, social-deduction/
    negotiation games, and economic-negotiation board games like 18xx and
    Chinatown) that shaped the design decisions in the GDD.
  - [`BALANCE_TESTING.md`](docs/BALANCE_TESTING.md) - results from the
    simulations used to test and tune the game's numbers before building
    anything, including bugs and exploits that were found and fixed along
    the way (loan interest, Hostile Bid math, alliance betrayal payouts).
  - [`ENVIRONMENT_SETUP.md`](docs/ENVIRONMENT_SETUP.md) - how the Python
    dev environment is created and auto-initialized when opening this
    project in VS Code.
- **`sim/`** - the Python simulations behind every finding in
  `BALANCE_TESTING.md`: `power_simulation.py` (the original 6-archetype
  bot pod) and `human_sim.py` (the human-shaped extension, mistakes,
  Power Cards, Hidden Raiders, and everything else validated since).
- **`backend/`** - Python + FastAPI backend, structured as an `app/`
  package per `CLAUDE.md`'s conventions. `app/core/` holds every game
  constant and the scenario table (ported from `sim/`), `app/models/`
  holds the Pydantic game state, `app/services/round_engine.py` resolves
  the Building Phase's Income/Allocate/Market/Taxes loop, `app/services/room.py`
  drives a live room's WebSocket connections and round timer, and `app/api/`
  exposes it all (`POST /rooms`, `/rooms/{code}/join`, `/rooms/{code}/start`,
  `WS /ws/rooms/{code}`). `backend/tests/` covers the engine and room layer.
  Hostile Bids, Joint Ventures, Defense Pacts, Declare/Audit, Power Cards,
  and the Hidden Raider are not built yet.
- **`CLAUDE.md`** - coding standards for this project: writing style, code
  quality, docstrings, security practices, folder structure, and the
  linting/pre-commit tooling that enforces them.
- **`frontend/`** - React + Vite frontend. `src/screens/` holds the three
  live screens (Landing, Lobby, GameRoom), `src/components/` the shared
  Allocate form and Power leaderboard, `src/hooks/useRoomSocket.js` owns
  the live WebSocket connection, and `src/api/client.js` wraps the REST
  calls. `VITE_API_BASE` (see `.env.example`) points it at the backend.
- **`.vscode/`** - editor settings that auto-select the project's Python
  environment and auto-run its setup task whenever this folder is opened
  in VS Code (see `docs/ENVIRONMENT_SETUP.md` for details).

## Status

Design and balance-testing are done (see `docs/GDD.md` Section 9). A first
playable slice is built and running: create a room, join over a link,
play the full Building Phase economy (Company, Real Estate, Gold, the
Market, Bank loans/deposits) round by round with a live, Power-only
leaderboard, for as many rounds as the game runs (the backend still
transitions into the Conflict Phase and to game-end on schedule, it just
doesn't yet have combat to run there). Not yet built: Hostile Bids, Joint
Ventures, Defense Pacts, Declare/Audit, Power Cards, the Hidden Raider,
the Final Round, and disconnection handling beyond a basic connected/away
flag - see `docs/GDD.md` Section 10 for the full v1 scope this is working
toward.
