/**
 * The entry screen: host a new room or join one by code, picking a company
 * name, color, and Industry (GAMEPLAY.md Section 1's setup step) either way.
 */

import { useState } from 'react'
import { createRoom, joinRoom } from '../api/client'
import { COMPANY_COLORS, INDUSTRIES } from '../constants'

export function Landing({ initialRoomCode, onJoined }) {
  const [mode, setMode] = useState(initialRoomCode ? 'join' : 'host')
  const [roomCodeInput, setRoomCodeInput] = useState(initialRoomCode || '')
  const [name, setName] = useState('')
  const [color, setColor] = useState(COMPANY_COLORS[0])
  const [industry, setIndustry] = useState(INDUSTRIES[0])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(event) {
    event.preventDefault()
    if (!name.trim()) {
      setError('Pick a company name.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const roomCode = mode === 'host' ? (await createRoom()).room_code : roomCodeInput.trim().toUpperCase()
      if (!roomCode) {
        throw new Error('Enter the room code your host shared with you.')
      }
      const joined = await joinRoom(roomCode, { name: name.trim(), icon: color, industry })
      onJoined({
        roomCode: joined.room_code,
        playerId: joined.player_id,
        reconnectToken: joined.reconnect_token,
        isHost: joined.is_host,
        name: name.trim(),
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="panel landing">
      <h1>Hostile Ledger</h1>
      <p className="subtitle">Grow your Power. Don't get caught undefended.</p>

      <div className="mode-toggle">
        <button
          type="button"
          className={mode === 'host' ? 'active' : ''}
          onClick={() => setMode('host')}
        >
          Host a game
        </button>
        <button
          type="button"
          className={mode === 'join' ? 'active' : ''}
          onClick={() => setMode('join')}
        >
          Join a game
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        {mode === 'join' && (
          <label>
            Room code
            <input
              value={roomCodeInput}
              onChange={(event) => setRoomCodeInput(event.target.value)}
              placeholder="e.g. ABCD"
              maxLength={8}
              autoCapitalize="characters"
            />
          </label>
        )}

        <label>
          Company name
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Your company"
            maxLength={24}
          />
        </label>

        <label>
          Company color
          <div className="color-picker">
            {COMPANY_COLORS.map((swatch) => (
              <button
                type="button"
                key={swatch}
                className={`swatch${swatch === color ? ' selected' : ''}`}
                style={{ backgroundColor: swatch }}
                aria-label={`Choose ${swatch}`}
                onClick={() => setColor(swatch)}
              />
            ))}
          </div>
        </label>

        <label>
          Industry
          <select value={industry} onChange={(event) => setIndustry(event.target.value)}>
            {INDUSTRIES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        {error && <p className="error-text">{error}</p>}

        <button type="submit" className="primary" disabled={busy}>
          {busy ? 'Please wait...' : mode === 'host' ? 'Create room' : 'Join room'}
        </button>
      </form>
    </div>
  )
}
