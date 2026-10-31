import { useRef, useState } from 'react'
import { type Plan, type PlanRequest, planTrip } from './api'
import { RouteList } from './RouteList'
import { RouteMap } from './RouteMap'
import { TripForm } from './TripForm'

export default function App() {
  const [plan, setPlan] = useState<Plan | null>(null)
  const [selectedRouteId, setSelectedRouteId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inFlight = useRef<AbortController | null>(null)

  async function handleSubmit(request: PlanRequest) {
    inFlight.current?.abort()
    const controller = new AbortController()
    inFlight.current = controller
    setLoading(true)
    setError(null)
    try {
      const result = await planTrip(request, controller.signal)
      setPlan(result)
      setSelectedRouteId(result.recommended_route_id)
    } catch (e) {
      if (!controller.signal.aborted) setError(e instanceof Error ? e.message : String(e))
    } finally {
      if (inFlight.current === controller) setLoading(false)
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>Weather-Aware Truck Routing</h1>
        <TripForm loading={loading} onSubmit={handleSubmit} />
        {error && <div className="error">{error}</div>}
        {plan && <RouteList plan={plan} selectedRouteId={selectedRouteId} onSelect={setSelectedRouteId} />}
      </aside>
      <main className="map-wrap">
        <RouteMap plan={plan} selectedRouteId={selectedRouteId} onSelectRoute={setSelectedRouteId} />
      </main>
    </div>
  )
}
