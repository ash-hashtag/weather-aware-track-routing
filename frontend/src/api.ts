// Mirrors the TypedDicts in backend/routing/planner.py.

export type RiskLabel = 'low' | 'moderate' | 'high' | 'severe' | 'no_travel'

export interface Place {
  label: string
  lat: number
  lng: number
}

export interface CheckpointWeather {
  wind_mph: number
  gust_mph: number
  rain_in_hr: number
  snow_in_hr: number
  temperature_f: number
}

export interface Checkpoint {
  mile: number
  lat: number
  lng: number
  eta: string
  weather: CheckpointWeather
  risk: RiskLabel
  risk_score: number
  reasons: string[]
}

export interface WeatherStats {
  max_wind_mph: number
  max_gust_mph: number
  max_rain_in_hr: number
  max_snow_in_hr: number
  min_temperature_f: number
  max_temperature_f: number
  wet_miles: number
  snow_miles: number
}

export interface Hazard {
  from_mile: number
  to_mile: number
  from_eta: string
  to_eta: string
  risk: RiskLabel
  reasons: string[]
}

export interface RiskSegment {
  risk: RiskLabel
  coordinates: [number, number][]
}

export interface Route {
  id: number
  rank: number
  recommended: boolean
  distance_miles: number
  duration_s: number
  departure: string
  arrival: string
  miles_by_risk: Record<RiskLabel, number>
  average_risk: number
  max_risk: RiskLabel
  geometry: [number, number][]
  risk_segments: RiskSegment[]
  weather: WeatherStats
  hazards: Hazard[]
  checkpoints: Checkpoint[]
  notices: string[]
}

export interface Plan {
  origin: Place
  destination: Place
  departure: string
  load_lbs: number
  interval_miles: number
  recommended_route_id: number
  recommendation_reason: string
  routes: Route[]
}

export interface PlanRequest {
  origin: string
  destination: string
  departure: string
  load_lbs: number
  interval_miles: 10 | 25 | 50
}

export class ApiError extends Error {}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(formatError(body) ?? `Request failed (${response.status})`)
  }
  return body as T
}

// DRF errors are either {detail: "..."} or {field: ["msg", ...], ...}.
function formatError(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null
  if ('detail' in body && typeof body.detail === 'string') return body.detail
  return Object.entries(body)
    .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(' ') : String(messages)}`)
    .join('\n')
}

export function planTrip(body: PlanRequest, signal?: AbortSignal): Promise<Plan> {
  return request<Plan>('/api/plan/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
}

export function suggestPlaces(q: string, signal?: AbortSignal): Promise<Place[]> {
  return request<Place[]>(`/api/places/?${new URLSearchParams({ q })}`, { signal })
}
