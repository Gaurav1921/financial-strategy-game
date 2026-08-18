/**
 * Alliances and combat: propose/respond to Joint Ventures and Defense
 * Pacts, manage existing ones, and - once the Conflict Phase opens -
 * Hostile Bids, gang-up counter-attacks, and Audit. Everything here is
 * either a private action between two players or a public event the whole
 * table sees resolve (GDD.md Section 6/7); see each section for which.
 */

import { useState } from 'react'
import { INDUSTRIES } from '../constants'

function ProposalInbox({ proposals, players, onRespond }) {
  if (proposals.length === 0) {
    return null
  }
  return (
    <div className="conflict-section">
      <h3>Alliance offers</h3>
      {proposals.map((proposal) => {
        const from = players.find((p) => p.id === proposal.from_id)
        return (
          <div key={proposal.proposal_id} className="proposal-row">
            <span>
              {from?.name ?? 'Someone'} offers{' '}
              {proposal.jv_industry && `a Joint Venture in ${proposal.jv_industry}`}
              {proposal.jv_industry && proposal.pact_declared !== null && ' + '}
              {proposal.pact_declared === true && 'a declared Defense Pact'}
              {proposal.pact_declared === false && 'a covert Defense Pact'}
            </span>
            <div className="proposal-actions">
              <button type="button" onClick={() => onRespond(proposal.proposal_id, true)}>
                Accept
              </button>
              <button type="button" onClick={() => onRespond(proposal.proposal_id, false)}>
                Decline
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function ProposeForm({ target, onCancel, onPropose }) {
  const [wantJv, setWantJv] = useState(true)
  const [jvIndustry, setJvIndustry] = useState(INDUSTRIES[0])
  const [pactMode, setPactMode] = useState('declared')

  function submit(event) {
    event.preventDefault()
    onPropose(
      target.id,
      wantJv ? jvIndustry : null,
      pactMode === 'none' ? null : pactMode === 'declared',
    )
    onCancel()
  }

  return (
    <form className="propose-form" onSubmit={submit}>
      <p>Propose an alliance with {target.name}</p>
      <label>
        <input type="checkbox" checked={wantJv} onChange={(e) => setWantJv(e.target.checked)} />
        Joint Venture
      </label>
      {wantJv && (
        <select value={jvIndustry} onChange={(e) => setJvIndustry(e.target.value)}>
          {INDUSTRIES.map((industry) => (
            <option key={industry} value={industry}>
              {industry}
            </option>
          ))}
        </select>
      )}
      <label>
        Defense Pact
        <select value={pactMode} onChange={(e) => setPactMode(e.target.value)}>
          <option value="none">None</option>
          <option value="declared">Declared (public)</option>
          <option value="covert">Covert (secret)</option>
        </select>
      </label>
      <div className="proposal-actions">
        <button type="submit" disabled={!wantJv && pactMode === 'none'}>
          Send offer
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  )
}

function MyAlliances({ alliances, players, onTopUp, onDrain, onBreak }) {
  if (alliances.length === 0) {
    return null
  }
  return (
    <div className="conflict-section">
      <h3>Your alliances</h3>
      {alliances.map((alliance) => {
        const partner = players.find((p) => p.id === alliance.ally_id)
        return (
          <div key={alliance.ally_id} className="alliance-row">
            <span>
              {partner?.name ?? alliance.ally_id}
              {alliance.jv_industry && ` - JV in ${alliance.jv_industry} (${alliance.jv_value.toFixed(1)})`}
              {alliance.pact_declared === true && ' - declared pact'}
              {alliance.pact_declared === false && ' - covert pact'}
              {alliance.pending_break && ' (breaking next round)'}
            </span>
            <div className="proposal-actions">
              {alliance.jv_industry && (
                <>
                  <button type="button" onClick={() => onTopUp(alliance.ally_id)}>
                    Top up
                  </button>
                  <button type="button" onClick={() => onDrain(alliance.ally_id)}>
                    Drain
                  </button>
                </>
              )}
              {alliance.pact_declared !== null && !alliance.pending_break && (
                <button type="button" onClick={() => onBreak(alliance.ally_id)}>
                  Break pact
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function RivalList({ players, selfId, alliances, phase, onProposeTarget, onHostileBid, onAudit }) {
  const allyIds = new Set(alliances.map((a) => a.ally_id))
  const rivals = players.filter((p) => p.id !== selfId)

  return (
    <div className="conflict-section">
      <h3>The table</h3>
      {rivals.map((player) => (
        <div key={player.id} className="rival-row">
          <span>
            {player.name} - {player.power.toFixed(1)} Power
            {player.shielded && ' (shielded)'}
            {allyIds.has(player.id) && ' (ally)'}
          </span>
          <div className="proposal-actions">
            {!allyIds.has(player.id) && (
              <button type="button" onClick={() => onProposeTarget(player)}>
                Propose alliance
              </button>
            )}
            <button type="button" onClick={() => onAudit(player.id)}>
              Audit (5 cash)
            </button>
            {phase === 'conflict' && !player.shielded && (
              <button type="button" className="danger" onClick={() => onHostileBid(player.id)}>
                Hostile Bid
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function EventLog({ events, players }) {
  if (events.length === 0) {
    return null
  }
  const nameOf = (id) => players.find((p) => p.id === id)?.name ?? id
  return (
    <div className="conflict-section">
      <h3>Recent events</h3>
      <ul className="event-log">
        {events.map((event, index) => (
          // eslint-disable-next-line react/no-array-index-key -- a rolling log has no stable id
          <li key={index}>
            {event.type === 'jv_drained' &&
              `${nameOf(event.drainer_id)} drained a Joint Venture with ${nameOf(event.partner_id)} for ${event.amount.toFixed(1)}`}
            {event.type === 'hostile_bid_result' &&
              (event.success
                ? `${nameOf(event.attacker_id)} took over ${event.amount.toFixed(1)} from ${nameOf(event.target_id)}!`
                : `${nameOf(event.attacker_id)}'s Hostile Bid on ${nameOf(event.target_id)} failed.`)}
            {event.type === 'counter_attack_result' &&
              (event.success
                ? `${nameOf(event.attacker_id)} and allies brought down leader ${nameOf(event.target_id)} for ${event.amount.toFixed(1)}!`
                : `${nameOf(event.attacker_id)}'s counter-attack on ${nameOf(event.target_id)} failed.`)}
          </li>
        ))}
      </ul>
    </div>
  )
}

export function ConflictPanel({ socket, session, roomState }) {
  const [proposeTarget, setProposeTarget] = useState(null)
  const players = roomState?.players ?? []
  const alliances = roomState?.my_alliances ?? []
  const phase = roomState?.phase

  return (
    <div className="panel conflict-panel">
      <h2>Alliances &amp; Combat</h2>

      {socket.auditResult && (
        <div className="conflict-section audit-result">
          <h3>Audit: {players.find((p) => p.id === socket.auditResult.target_id)?.name}</h3>
          <p>Cash {socket.auditResult.cash.toFixed(1)}</p>
          <p>Company {socket.auditResult.company.toFixed(1)}</p>
          <p>Real Estate {socket.auditResult.real_estate.toFixed(1)}</p>
          <p>Gold {socket.auditResult.gold.toFixed(1)}</p>
          <p>Debt {socket.auditResult.debt.toFixed(1)}</p>
          <button type="button" onClick={socket.clearAuditResult}>
            Dismiss
          </button>
        </div>
      )}

      {socket.proposalResponse && (
        <div className="conflict-section proposal-response">
          <p>
            {players.find((p) => p.id === socket.proposalResponse.to_id)?.name ?? 'They'}{' '}
            {socket.proposalResponse.accepted ? 'accepted' : 'declined'} your alliance offer.
          </p>
          <button type="button" onClick={socket.clearProposalResponse}>
            Dismiss
          </button>
        </div>
      )}

      <ProposalInbox proposals={socket.proposals} players={players} onRespond={socket.respondAlliance} />

      {proposeTarget && (
        <ProposeForm
          target={proposeTarget}
          onCancel={() => setProposeTarget(null)}
          onPropose={socket.proposeAlliance}
        />
      )}

      <MyAlliances
        alliances={alliances}
        players={players}
        onTopUp={socket.topUpJv}
        onDrain={socket.drainJv}
        onBreak={socket.breakPact}
      />

      {phase === 'conflict' && (
        <div className="conflict-section">
          <button type="button" className="danger" onClick={socket.counterAttack}>
            Gang up on the leader
          </button>
        </div>
      )}

      <RivalList
        players={players}
        selfId={session.playerId}
        alliances={alliances}
        phase={phase}
        onProposeTarget={setProposeTarget}
        onHostileBid={socket.hostileBid}
        onAudit={socket.audit}
      />

      <EventLog events={socket.eventLog} players={players} />
    </div>
  )
}
