/**
 * Top-level screen router: Landing (create/join) -> Lobby -> GameRoom,
 * driven by the room's own phase rather than local navigation state.
 * Session credentials persist to `sessionStorage` so a page refresh
 * resumes the same seat instead of losing it.
 */

import { useEffect, useState } from 'react'
import './App.css'
import { Landing } from './screens/Landing'
import { Lobby } from './screens/Lobby'
import { GameRoom } from './screens/GameRoom'
import { useRoomSocket } from './hooks/useRoomSocket'
import { SESSION_STORAGE_KEY } from './constants'

function loadStoredSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function App() {
  const [session, setSession] = useState(loadStoredSession)
  const [initialRoomCode] = useState(
    () => new URLSearchParams(window.location.search).get('room') || '',
  )
  const socket = useRoomSocket(session?.roomCode, session)

  useEffect(() => {
    if (session) {
      sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session))
    }
  }, [session])

  if (!session) {
    return <Landing initialRoomCode={initialRoomCode} onJoined={setSession} />
  }

  const phase = socket.roomState?.phase
  const screen =
    phase && phase !== 'lobby' ? (
      <GameRoom session={session} socket={socket} />
    ) : (
      <Lobby session={session} roomState={socket.roomState} connectionStatus={socket.status} />
    )

  return (
    <>
      {socket.status === 'closed' && <div className="banner banner-warn">Disconnected. Try refreshing.</div>}
      {socket.errorMessage && (
        <button type="button" className="banner banner-error" onClick={socket.clearError}>
          {socket.errorMessage} (tap to dismiss)
        </button>
      )}
      {screen}
    </>
  )
}

export default App
