import { type FormEvent, useEffect, useId, useState } from 'react'
import { type PlanRequest, suggestPlaces } from './api'

interface Props {
  loading: boolean
  onSubmit: (request: PlanRequest) => void
}

const INTERVALS = [10, 25, 50] as const

export function TripForm({ loading, onSubmit }: Props) {
  const [origin, setOrigin] = useState('Chicago, IL')
  const [destination, setDestination] = useState('Denver, CO')
  const [departure, setDeparture] = useState(defaultDeparture)
  const [loadLbs, setLoadLbs] = useState(35000)
  const [intervalMiles, setIntervalMiles] = useState<PlanRequest['interval_miles']>(25)

  function submit(e: FormEvent) {
    e.preventDefault()
    onSubmit({
      origin,
      destination,
      departure: new Date(departure).toISOString(),
      load_lbs: loadLbs,
      interval_miles: intervalMiles,
    })
  }

  return (
    <form className="trip-form" onSubmit={submit}>
      <PlaceInput label="Origin" value={origin} onChange={setOrigin} />
      <PlaceInput label="Destination" value={destination} onChange={setDestination} />
      <label>
        Departure
        <input
          type="datetime-local"
          value={departure}
          onChange={(e) => setDeparture(e.target.value)}
          required
        />
      </label>
      <div className="row">
        <label>
          Load (lb)
          <input
            type="number"
            min={1}
            max={200000}
            step={1}
            value={loadLbs}
            onChange={(e) => setLoadLbs(e.target.valueAsNumber)}
            required
          />
        </label>
        <label>
          Weather every
          <select
            value={intervalMiles}
            onChange={(e) => setIntervalMiles(Number(e.target.value) as PlanRequest['interval_miles'])}
          >
            {INTERVALS.map((mi) => (
              <option key={mi} value={mi}>
                {mi} mi
              </option>
            ))}
          </select>
        </label>
      </div>
      <button type="submit" disabled={loading}>
        {loading ? 'Planning…' : 'Plan routes'}
      </button>
    </form>
  )
}

function PlaceInput({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  const listId = useId()
  const [options, setOptions] = useState<string[]>([])

  // Debounced so typing doesn't spend one HERE request per keystroke.
  useEffect(() => {
    if (value.trim().length < 3) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      suggestPlaces(value, controller.signal)
        .then((places) => setOptions(places.map((p) => p.label)))
        .catch(() => {})
    }, 350)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [value])

  return (
    <label>
      {label}
      <input list={listId} value={value} onChange={(e) => onChange(e.target.value)} required />
      <datalist id={listId}>
        {options.map((o) => (
          <option key={o} value={o} />
        ))}
      </datalist>
    </label>
  )
}

// Next full hour, in the browser's local time, formatted for <input type="datetime-local">.
function defaultDeparture(): string {
  const d = new Date()
  d.setHours(d.getHours() + 1, 0, 0, 0)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
