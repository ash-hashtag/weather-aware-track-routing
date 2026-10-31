import type { Plan, Route } from './api'
import { RISK_COLORS, RISK_LEVELS, RISK_NAMES, formatDuration, formatMiles, formatTime } from './format'

interface Props {
  plan: Plan
  selectedRouteId: number | null
  onSelect: (id: number) => void
}

export function RouteList({ plan, selectedRouteId, onSelect }: Props) {
  const routes = [...plan.routes].sort((a, b) => a.rank - b.rank)
  return (
    <div className="routes">
      <p className="reason">{plan.recommendation_reason}</p>
      {routes.map((route) => (
        <RouteCard
          key={route.id}
          route={route}
          selected={route.id === selectedRouteId}
          onSelect={() => onSelect(route.id)}
        />
      ))}
      <Legend />
    </div>
  )
}

function RouteCard({ route, selected, onSelect }: { route: Route; selected: boolean; onSelect: () => void }) {
  return (
    <button type="button" className={`route-card${selected ? ' selected' : ''}`} onClick={onSelect}>
      <div className="route-head">
        <span className="route-name">Route {route.rank}</span>
        {route.recommended && <span className="badge">Recommended</span>}
        <span className="route-max" style={{ color: RISK_COLORS[route.max_risk] }}>
          Worst: {RISK_NAMES[route.max_risk]}
        </span>
      </div>
      <div className="route-stats">
        <span>{formatMiles(route.distance_miles)}</span>
        <span>{formatDuration(route.duration_s)}</span>
        <span>Arrive {formatTime(route.arrival)}</span>
      </div>
      <RiskBar route={route} />
      <div className="route-risk">
        {RISK_LEVELS.filter((l) => l !== 'low' && route.miles_by_risk[l] > 0).map((l) => (
          <span key={l}>
            {RISK_NAMES[l]}: {formatMiles(route.miles_by_risk[l])}
          </span>
        ))}
        <span>Avg risk {route.average_risk.toFixed(2)} / 4</span>
      </div>
      {route.notices.length > 0 && <div className="notices">{route.notices.join(' · ')}</div>}
    </button>
  )
}

function RiskBar({ route }: { route: Route }) {
  const total = RISK_LEVELS.reduce((sum, l) => sum + route.miles_by_risk[l], 0) || 1
  return (
    <div className="risk-bar" aria-label="Miles by risk level">
      {RISK_LEVELS.map((l) =>
        route.miles_by_risk[l] > 0 ? (
          <span
            key={l}
            style={{ width: `${(route.miles_by_risk[l] / total) * 100}%`, background: RISK_COLORS[l] }}
            title={`${RISK_NAMES[l]}: ${formatMiles(route.miles_by_risk[l])}`}
          />
        ) : null,
      )}
    </div>
  )
}

function Legend() {
  return (
    <div className="legend">
      {RISK_LEVELS.map((l) => (
        <span key={l}>
          <span className="dot" style={{ background: RISK_COLORS[l] }} />
          {RISK_NAMES[l]}
        </span>
      ))}
    </div>
  )
}
