/**
 * React hook owning one room's live WebSocket connection.
 *
 * Tracks the latest lobby/game `state` snapshot (including the caller's own
 * alliances), the current round's `round_started` announcement (including
 * its scenario, revealed up front so players can read it before
 * allocating), the most recent `round_result`, incoming alliance proposals,
 * a rolling combat/alliance event log (everything the room broadcasts
 * publicly: Hostile Bids, counter-attacks, Joint Venture drains), the most
 * recent private Audit result, the most recent response to a proposal this
 * player sent, and any server-side error. `roundResult` is cleared the
 * moment a new round starts, not when `state` updates, so the result stays
 * on screen for the full gap between one round ending and the next
 * beginning.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { roomSocketUrl } from '../api/client'

const LOG_TYPES = new Set(['hostile_bid_result', 'counter_attack_result', 'jv_drained'])
const MAX_LOG_ENTRIES = 20

export function useRoomSocket(roomCode, credentials) {
  const [status, setStatus] = useState('connecting')
  const [roomState, setRoomState] = useState(null)
  const [roundStarted, setRoundStarted] = useState(null)
  const [roundResult, setRoundResult] = useState(null)
  const [errorMessage, setErrorMessage] = useState(null)
  const [proposals, setProposals] = useState([])
  const [eventLog, setEventLog] = useState([])
  const [auditResult, setAuditResult] = useState(null)
  const [proposalResponse, setProposalResponse] = useState(null)
  const socketRef = useRef(null)

  const playerId = credentials?.playerId
  const reconnectToken = credentials?.reconnectToken

  useEffect(() => {
    if (!roomCode || !playerId || !reconnectToken) {
      return undefined
    }

    const socket = new WebSocket(roomSocketUrl(roomCode, { playerId, reconnectToken }))
    socketRef.current = socket
    setStatus('connecting')

    socket.onopen = () => setStatus('open')
    socket.onclose = () => setStatus('closed')
    socket.onerror = () => setStatus('closed')
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data)
      if (LOG_TYPES.has(message.type)) {
        setEventLog((prev) => [message, ...prev].slice(0, MAX_LOG_ENTRIES))
      }
      switch (message.type) {
        case 'state':
          setRoomState(message)
          break
        case 'round_started':
          setRoundStarted(message)
          setRoundResult(null)
          break
        case 'round_result':
          setRoundResult(message)
          break
        case 'alliance_proposal':
          setProposals((prev) => [...prev, message])
          break
        case 'alliance_response':
          // Sent only to the original proposer (see backend/app/api/ws.py); the
          // responder's own client already dropped the offer locally in
          // respondAlliance below.
          setProposalResponse(message)
          break
        case 'audit_result':
          setAuditResult(message)
          break
        case 'error':
          setErrorMessage(message.message)
          break
        default:
          break
      }
    }

    return () => {
      socket.close()
      socketRef.current = null
    }
  }, [roomCode, playerId, reconnectToken])

  const send = useCallback((payload) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(payload))
    }
  }, [])

  const submitAllocation = useCallback(
    (allocation) => send({ type: 'submit_allocation', allocation }),
    [send],
  )
  const proposeAlliance = useCallback(
    (toId, jvIndustry, pactDeclared) =>
      send({ type: 'propose_alliance', to_id: toId, jv_industry: jvIndustry, pact_declared: pactDeclared }),
    [send],
  )
  const respondAlliance = useCallback(
    (proposalId, accept) => {
      send({ type: 'respond_alliance', proposal_id: proposalId, accept })
      setProposals((prev) => prev.filter((p) => p.proposal_id !== proposalId))
    },
    [send],
  )
  const topUpJv = useCallback((allyId) => send({ type: 'top_up_jv', ally_id: allyId }), [send])
  const drainJv = useCallback((allyId) => send({ type: 'drain_jv', ally_id: allyId }), [send])
  const breakPact = useCallback((allyId) => send({ type: 'break_pact', ally_id: allyId }), [send])
  const hostileBid = useCallback(
    (targetId) => send({ type: 'hostile_bid', target_id: targetId }),
    [send],
  )
  const counterAttack = useCallback(() => send({ type: 'counter_attack' }), [send])
  const audit = useCallback((targetId) => send({ type: 'audit', target_id: targetId }), [send])

  const clearError = useCallback(() => setErrorMessage(null), [])
  const clearAuditResult = useCallback(() => setAuditResult(null), [])
  const clearProposalResponse = useCallback(() => setProposalResponse(null), [])

  return {
    status,
    roomState,
    roundStarted,
    roundResult,
    errorMessage,
    proposals,
    eventLog,
    auditResult,
    proposalResponse,
    submitAllocation,
    proposeAlliance,
    respondAlliance,
    topUpJv,
    drainJv,
    breakPact,
    hostileBid,
    counterAttack,
    audit,
    clearError,
    clearAuditResult,
    clearProposalResponse,
  }
}
