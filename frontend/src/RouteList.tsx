import type { Hazard, Plan, RiskLabel, Route, WeatherStats } from './api'
import { RISK_COLORS, RISK_LEVELS, RISK_NAMES, formatDuration, formatMiles, formatTime } from './format'

interface Props {
  plan: Plan
  selectedRouteId: number | null
  onSelect: (id: number) => void
}

const ELEVATED: RiskLabel[] = ['no_travel', 'severe', 'high', 'moderate']
const MAX_HAZARDS_SHOWN = 3

export function RouteList({ plan, selectedRouteId, onSelect }: Props) {
  const routes = [...plan.routes].sort((a, b) => a.rank - b.rank)
  const fastest = plan.routes.reduce((a, b) => (b.duration_s < a.duration_s ? b : a))
  return (
    <div className="routes">
      <p className="reason">{plan.recommendation_reason}</p>
      {routes.map((route) => (
        <RouteCard
          key={route.id}
          route={route}
          fastest={fastest}
          selected={route.id === selectedRouteId}
          onSelect={() => onSelect(route.id)}
        />
      ))}
      <Legend />
    </div>
  )
}

interface CardProps {
  route: Route
  fastest: Route
  selected: boolean
  onSelect: () => void
}

function RouteCard({ route, fastest, selected, onSelect }: CardProps) {
  const tradeOff = compareWithFastest(route, fastest)
  return (
    <button type="button" className={`route-card${selected ? ' selected' : ''}`} onClick={onSelect}>
      <div className="route-head">
        <span className="route-name">Route {route.rank}</span>
        {route.recommended && <span className="badge">Recommended</span>}
        {route.id === fastest.id && <span className="badge badge-muted">Fastest</span>}
        <span className="route-max" style={{ color: RISK_COLORS[route.max_risk] }}>
          Worst: {RISK_NAMES[route.max_risk]}
        </span>
      </div>
      <div className="route-stats">
        <span>{formatMiles(route.distance_miles)}</span>
        <span>{formatDuration(route.duration_s)}</span>
        <span>Arrive {formatTime(route.arrival)}</span>
      </div>
      {tradeOff && <div className="trade-off">{tradeOff}</div>}
      <RiskBar route={route} />
      <div className="route-risk">
        {RISK_LEVELS.filter((l) => l !== 'low' && route.miles_by_risk[l] > 0).map((l) => (
          <span key={l}>
            {RISK_NAMES[l]}: {formatMiles(route.miles_by_risk[l])}
          </span>
        ))}
        <span>Avg risk {route.average_risk.toFixed(2)} / 4</span>
      </div>
      <WeatherMetrics stats={route.weather} />
      <Hazards hazards={route.hazards} />
      {route.notices.length > 0 && <div className="notices">{route.notices.join(' · ')}</div>}
    </button>
  )
}

// e.g. "+2 h 31 min vs fastest · avoids 50 mi Moderate · adds 20 mi High"
function compareWithFastest(route: Route, fastest: Route): string | null {
  if (route.id === fastest.id) return null
  const extra = route.duration_s - fastest.duration_s
  const parts = [`${extra >= 0 ? '+' : '−'}${formatDuration(Math.abs(extra))} vs fastest`]
  const avoided = riskMilesDiff(fastest, route)
  const added = riskMilesDiff(route, fastest)
  if (avoided.length) parts.push(`avoids ${avoided.join(', ')}`)
  if (added.length) parts.push(`adds ${added.join(', ')}`)
  return parts.join(' · ')
}

// Elevated-risk miles `a` has beyond `b`, worst level first.
function riskMilesDiff(a: Route, b: Route): string[] {
  return ELEVATED.filter((l) => a.miles_by_risk[l] - b.miles_by_risk[l] >= 1).map(
    (l) => `${formatMiles(a.miles_by_risk[l] - b.miles_by_risk[l])} ${RISK_NAMES[l]}`,
  )
}

function WeatherMetrics({ stats }: { stats: WeatherStats }) {
  return (
    <dl className="weather-metrics">
      <div>
        <dt>Wind</dt>
        <dd>
          {stats.max_wind_mph.toFixed(0)} mph <small>gust {stats.max_gust_mph.toFixed(0)}</small>
        </dd>
      </div>
      <div>
        <dt>Rain peak</dt>
        <dd>{stats.max_rain_in_hr.toFixed(2)} in/hr</dd>
      </div>
      <div>
        <dt>Snow peak</dt>
        <dd>{stats.max_snow_in_hr.toFixed(2)} in/hr</dd>
      </div>
      <div>
        <dt>Temp</dt>
        <dd>
          {stats.min_temperature_f.toFixed(0)}–{stats.max_temperature_f.toFixed(0)}°F
        </dd>
      </div>
      <div>
        <dt>Wet roads</dt>
        <dd>{formatMiles(stats.wet_miles)}</dd>
      </div>
      <div>
        <dt>Snowy roads</dt>
        <dd>{formatMiles(stats.snow_miles)}</dd>
      </div>
    </dl>
  )
}

function Hazards({ hazards }: { hazards: Hazard[] }) {
  if (hazards.length === 0) {
    return <div className="hazards-none">No weather hazards at your ETAs along this route.</div>
  }
  const shown = [...hazards]
    .sort((a, b) => RISK_LEVELS.indexOf(b.risk) - RISK_LEVELS.indexOf(a.risk))
    .slice(0, MAX_HAZARDS_SHOWN)
    .sort((a, b) => a.from_mile - b.from_mile)
  return (
    <ul className="hazards">
      {shown.map((h) => (
        <li key={h.from_mile}>
          <span className="dot" style={{ background: RISK_COLORS[h.risk] }} />
          <span>
            <strong>
              Mile {Math.round(h.from_mile)}–{Math.round(h.to_mile)} · {RISK_NAMES[h.risk]}
            </strong>{' '}
            {formatTime(h.from_eta)}–{formatTime(h.to_eta)}
            {h.reasons.length > 0 && <span className="hazard-reasons"> · {h.reasons.join(', ')}</span>}
          </span>
        </li>
      ))}
      {hazards.length > shown.length && <li className="hazards-more">+{hazards.length - shown.length} more</li>}
    </ul>
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
