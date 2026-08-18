/**
 * The live per-round screen: this round's scenario, the countdown, the
 * Allocate form (or a waiting/result view once submitted), and the
 * always-visible Power leaderboard (GDD.md Section 6/13).
 */

import { useEffect, useState } from 'react'
import { AllocationForm } from '../components/AllocationForm'
import { ConflictPanel } from '../components/ConflictPanel'
import { Leaderboard } from '../components/Leaderboard'

function formatPercent(delta) {
  const pct = (delta * 100).toFixed(1)
  return delta >= 0 ? `+${pct}%` : `${pct}%`
}

function ScenarioCard({ scenario }) {
  if (!scenario) {
    return null
  }
  const effects = Object.entries(scenario.industry_deltas || {})
  return (
    <div className="scenario-card">
      <span className="scenario-label">This round's scenario</span>
      <p className="scenario-text">{scenario.text}</p>
      {effects.length > 0 ? (
        <ul className="scenario-effects">
          {effects.map(([industry, delta]) => (
            <li key={industry} className={delta >= 0 ? 'is-up' : 'is-down'}>
              {industry} {formatPercent(delta)}
            </li>
          ))}
        </ul>
      ) : (
        <p className="hint-text">Every Industry stays flat this round.</p>
      )}
    </div>
  )
}

function useCountdown(deadline) {
  const [secondsLeft, setSecondsLeft] = useState(null)

  useEffect(() => {
    if (!deadline) {
      setSecondsLeft(null)
      return undefined
    }
    const tick = () => setSecondsLeft(Math.max(0, Math.round(deadline - Date.now() / 1000)))
    tick()
    const interval = setInterval(tick, 1000)
    return () => clearInterval(interval)
  }, [deadline])

  return secondsLeft
}

function formatClock(seconds) {
  if (seconds === null) {
    return '--:--'
  }
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return `${minutes}:${String(rest).padStart(2, '0')}`
}

function RoundWaitOrResult({ playerId, currentRound, roundResult }) {
  if (!roundResult || roundResult.round_number !== currentRound) {
    return <p className="status-text">Submitted. Waiting on the rest of the table...</p>
  }

  const income = roundResult.income[playerId] ?? 0
  const eroded = roundResult.eroded_idle_cash[playerId] ?? 0

  return (
    <div className="round-result">
      <p>Round {roundResult.round_number} result</p>
      <p className={income >= 0 ? 'is-up' : 'is-down'}>Income: {income >= 0 ? '+' : ''}{income.toFixed(1)}</p>
      {eroded > 0 && <p className="is-down">Idle cash eroded: -{eroded.toFixed(1)}</p>}
      {roundResult.held.includes(playerId) && (
        <p className="hint-text">You held this round; your last split was replayed automatically.</p>
      )}
      <p className="status-text">Next round starting soon...</p>
    </div>
  )
}

export function GameRoom({ session, socket }) {
  const { roomState, roundStarted, roundResult, submitAllocation } = socket
  const [submitted, setSubmitted] = useState(false)
  const secondsLeft = useCountdown(roundStarted?.deadline)

  useEffect(() => {
    setSubmitted(false)
  }, [roundStarted?.round_number])

  const me = roomState?.me
  const players = roomState?.players ?? []
  const phase = roomState?.phase

  if (phase === 'ended') {
    return (
      <div className="panel game-room">
        <h1>Game over</h1>
        <p className="subtitle">Final standings</p>
        <Leaderboard players={players} selfId={session.playerId} />
      </div>
    )
  }

  if (!me || !roundStarted) {
    return (
      <div className="panel game-room">
        <p className="status-text">Waiting for the round to begin...</p>
      </div>
    )
  }

  function handleSubmit(allocation) {
    submitAllocation(allocation)
    setSubmitted(true)
  }

  return (
    <div className="game-room-layout">
      <div className="panel game-room">
        <div className="round-header">
          <span className="round-label">
            Round {roundStarted.round_number} - {phase === 'conflict' ? 'Conflict Phase' : 'Building Phase'}
          </span>
          <span className={`countdown${secondsLeft !== null && secondsLeft <= 30 ? ' is-urgent' : ''}`}>
            {formatClock(secondsLeft)}
          </span>
        </div>

        <ScenarioCard scenario={roundStarted.scenario} />

        {submitted ? (
          <RoundWaitOrResult
            playerId={session.playerId}
            currentRound={roundStarted.round_number}
            roundResult={roundResult}
          />
        ) : (
          <AllocationForm me={me} onSubmit={handleSubmit} submitting={submitted} />
        )}
      </div>

      <div className="game-room-sidebar">
        <div className="panel">
          <h2>Power</h2>
          <Leaderboard players={players} selfId={session.playerId} />
        </div>
        <ConflictPanel socket={socket} session={session} roomState={roomState} />
      </div>
    </div>
  )
}
