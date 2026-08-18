/**
 * REST client for the Hostile Ledger backend: creating, joining, and
 * starting a room. The live per-round connection is a WebSocket, handled
 * separately by `src/hooks/useRoomSocket.js`.
 */

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const WS_BASE = API_BASE.replace(/^http/, 'ws')

async function postJson(path, body) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body ?? {}),
    })
  } catch {
    // fetch() throws the same generic error for "server unreachable" and
    // "blocked by CORS" - the browser deliberately doesn't expose which,
    // so this can't be more specific than that.
    throw new Error(`could not reach the server at ${API_BASE} (or the request was blocked)`)
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || `request to ${path} failed (${response.status})`)
  }
  return data
}

export function createRoom() {
  return postJson('/rooms', {})
}

export function joinRoom(roomCode, { name, icon, industry }) {
  return postJson(`/rooms/${roomCode}/join`, { name, icon, industry })
}

export function startGame(roomCode, { playerId, reconnectToken }) {
  return postJson(`/rooms/${roomCode}/start`, {
    player_id: playerId,
    reconnect_token: reconnectToken,
  })
}

export function roomSocketUrl(roomCode, { playerId, reconnectToken }) {
  const params = new URLSearchParams({ player_id: playerId, token: reconnectToken })
  return `${WS_BASE}/ws/rooms/${roomCode}?${params.toString()}`
}
