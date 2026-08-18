/**
 * Live Power-only leaderboard. GDD.md Section 6: only Power is ever shown
 * for another player, exactly, always - this component must never be
 * handed anything beyond the `PublicPlayerView` shape (id/name/icon/
 * industry/power/is_host/connected), so there is nothing here it could
 * leak even by accident.
 */

function Badge({ color, label }) {
  return (
    <span className="badge" style={{ backgroundColor: color || '#555' }}>
      {label.slice(0, 1).toUpperCase()}
    </span>
  )
}

export function Leaderboard({ players, selfId }) {
  const ranked = [...players].sort((a, b) => b.power - a.power)

  return (
    <ol className="leaderboard">
      {ranked.map((player) => (
        <li
          key={player.id}
          className={`leaderboard-row${player.id === selfId ? ' is-self' : ''}${
            player.connected ? '' : ' is-disconnected'
          }`}
        >
          <Badge color={player.icon} label={player.name} />
          <span className="leaderboard-name">
            <span className="leaderboard-name-text">{player.name}</span>
            {player.is_host && <span className="tag">host</span>}
            {player.id === selfId && <span className="tag">you</span>}
            {!player.connected && <span className="tag tag-warn">away</span>}
          </span>
          <span className="leaderboard-industry">{player.industry}</span>
          <span className="leaderboard-power">{player.power.toFixed(1)}</span>
        </li>
      ))}
    </ol>
  )
}
