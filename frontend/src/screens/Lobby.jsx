/**
 * The waiting room: shows the shareable room code/link, everyone who has
 * joined so far, and, for the host only, the Start Game control.
 */

import { useState } from 'react'
import { startGame } from '../api/client'
import { MAX_PLAYERS, MIN_PLAYERS } from '../constants'

export function Lobby({ session, roomState, connectionStatus }) {
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState(null)

  const players = roomState?.players ?? []
  const playerCount = players.length
  const canStart = session.isHost && playerCount >= MIN_PLAYERS && playerCount <= MAX_PLAYERS

  const inviteLink =
    typeof window !== 'undefined'
      ? `${window.location.origin}${window.location.pathname}?room=${session.roomCode}`
      : ''

  async function handleStart() {
    setStarting(true)
    setError(null)
    try {
      await startGame(session.roomCode, {
        playerId: session.playerId,
        reconnectToken: session.reconnectToken,
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setStarting(false)
    }
  }

  async function copyInviteLink() {
    try {
      await navigator.clipboard.writeText(inviteLink)
    } catch {
      // Clipboard access can be denied by the browser; the code is still
      // shown on screen either way, so this failing silently is fine.
    }
  }

  return (
    <div className="panel lobby">
      <h1>Waiting for players</h1>

      <div className="room-code-block">
        <span className="room-code-label">Room code</span>
        <span className="room-code">{session.roomCode}</span>
        <button type="button" onClick={copyInviteLink}>
          Copy invite link
        </button>
      </div>

      {connectionStatus !== 'open' && <p className="status-text">Connecting...</p>}

      <ul className="player-list">
        {players.map((player) => (
          <li key={player.id}>
            <span className="badge" style={{ backgroundColor: player.icon || '#555' }}>
              {player.name.slice(0, 1).toUpperCase()}
            </span>
            <span>{player.name}</span>
            <span className="leaderboard-industry">{player.industry}</span>
            {player.is_host && <span className="tag">host</span>}
            {player.id === session.playerId && <span className="tag">you</span>}
          </li>
        ))}
      </ul>

      {session.isHost ? (
        <>
          <button type="button" className="primary" disabled={!canStart || starting} onClick={handleStart}>
            {starting
              ? 'Starting...'
              : playerCount < MIN_PLAYERS
                ? `Need at least ${MIN_PLAYERS} players`
                : 'Start game'}
          </button>
          {error && <p className="error-text">{error}</p>}
        </>
      ) : (
        <p className="status-text">Waiting for the host to start the game.</p>
      )}
    </div>
  )
}
