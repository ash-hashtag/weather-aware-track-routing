import type { FeatureCollection } from 'geojson'
import * as maplibregl from 'maplibre-gl'
import type { GeoJSONSource, MapLayerMouseEvent } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useEffect, useRef, useState } from 'react'
import type { Checkpoint, Plan } from './api'
import { RISK_COLORS, RISK_NAMES, formatTime } from './format'

// maplibre builds its worker URL at runtime, which bundlers can't see; importing it with
// `?url` makes Vite emit the file and gives us its hashed production URL.
maplibregl.setWorkerUrl(workerUrl)

const STYLE_URL = 'https://tiles.openfreemap.org/styles/positron'
const US_CENTER: [number, number] = [-98.6, 39.8]

interface Props {
  plan: Plan | null
  selectedRouteId: number | null
  onSelectRoute: (id: number) => void
}

export function RouteMap({ plan, selectedRouteId, onSelectRoute }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const onSelectRef = useRef(onSelectRoute)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    onSelectRef.current = onSelectRoute
  }, [onSelectRoute])

  useEffect(() => {
    if (!container.current) return
    const map = new maplibregl.Map({
      container: container.current,
      style: STYLE_URL,
      center: US_CENTER,
      zoom: 3.5,
      attributionControl: { compact: true, customAttribution: 'Weather: Open-Meteo.com (CC BY 4.0)' },
    })
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    map.on('load', () => {
      addLayers(map)
      setReady(true)
    })
    map.on('click', 'route-lines', (e: MapLayerMouseEvent) => {
      const id = e.features?.[0]?.properties.id
      if (typeof id === 'number') onSelectRef.current(id)
    })
    map.on('click', 'checkpoints', (e: MapLayerMouseEvent) => {
      const feature = e.features?.[0]
      if (!feature || feature.geometry.type !== 'Point') return
      const cp = JSON.parse(String(feature.properties.data)) as Checkpoint
      new maplibregl.Popup({ maxWidth: '260px' })
        .setLngLat(feature.geometry.coordinates as [number, number])
        .setHTML(checkpointHtml(cp))
        .addTo(map)
    })
    for (const layer of ['route-lines', 'checkpoints']) {
      map.on('mouseenter', layer, () => (map.getCanvas().style.cursor = 'pointer'))
      map.on('mouseleave', layer, () => (map.getCanvas().style.cursor = ''))
    }
    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
      setReady(false)
    }
  }, [])

  // New plan: replace data and fit the view to all routes.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const routes = map.getSource<GeoJSONSource>('routes')
    const riskSegments = map.getSource<GeoJSONSource>('risk-segments')
    const checkpoints = map.getSource<GeoJSONSource>('checkpoints')
    const endpoints = map.getSource<GeoJSONSource>('endpoints')
    if (!plan) {
      for (const source of [routes, riskSegments, checkpoints, endpoints]) source?.setData(EMPTY)
      return
    }
    routes?.setData({
      type: 'FeatureCollection',
      features: plan.routes.map((r) => ({
        type: 'Feature',
        properties: { id: r.id },
        geometry: { type: 'LineString', coordinates: r.geometry },
      })),
    })
    riskSegments?.setData({
      type: 'FeatureCollection',
      features: plan.routes.flatMap((r) =>
        r.risk_segments.map((seg) => ({
          type: 'Feature' as const,
          properties: { routeId: r.id, risk: seg.risk },
          geometry: { type: 'LineString' as const, coordinates: seg.coordinates },
        })),
      ),
    })
    checkpoints?.setData({
      type: 'FeatureCollection',
      features: plan.routes.flatMap((r) =>
        r.checkpoints.map((cp) => ({
          type: 'Feature' as const,
          properties: { routeId: r.id, risk: cp.risk, score: cp.risk_score, data: JSON.stringify(cp) },
          geometry: { type: 'Point' as const, coordinates: [cp.lng, cp.lat] },
        })),
      ),
    })
    endpoints?.setData({
      type: 'FeatureCollection',
      features: [plan.origin, plan.destination].map((p, i) => ({
        type: 'Feature',
        properties: { label: i === 0 ? 'A' : 'B' },
        geometry: { type: 'Point', coordinates: [p.lng, p.lat] },
      })),
    })
    const bounds = new maplibregl.LngLatBounds()
    for (const r of plan.routes) for (const c of r.geometry) bounds.extend(c)
    map.fitBounds(bounds, { padding: 60, duration: 800 })
  }, [plan, ready])

  // Selection only restyles; no data upload.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const selected = selectedRouteId ?? -1
    const isSelected: maplibregl.ExpressionSpecification = ['==', ['get', 'id'], selected]
    const cpSelected: maplibregl.ExpressionSpecification = ['==', ['get', 'routeId'], selected]
    // The selected route is drawn by the risk layers on top; these restyle the others.
    map.setPaintProperty('route-lines', 'line-color', ['case', isSelected, '#1e293b', '#94a3b8'])
    map.setPaintProperty('route-lines', 'line-width', ['case', isSelected, 6, 4])
    map.setLayoutProperty('route-lines', 'line-sort-key', ['case', isSelected, 1, 0])
    map.setFilter('risk-casing', cpSelected)
    map.setFilter('risk-segments', cpSelected)
    map.setPaintProperty('checkpoints', 'circle-radius', ['case', cpSelected, 4.5, 3])
    map.setPaintProperty('checkpoints', 'circle-opacity', ['case', cpSelected, 1, 0.55])
    map.setLayoutProperty('checkpoints', 'circle-sort-key', [
      '+',
      ['case', cpSelected, 10, 0],
      ['get', 'score'],
    ])
  }, [selectedRouteId, plan, ready])

  return <div ref={container} className="map" />
}

const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] }

const RISK_COLOR_EXPRESSION = [
  'match',
  ['get', 'risk'],
  ...Object.entries(RISK_COLORS).flat(),
  '#888888',
] as unknown as maplibregl.ExpressionSpecification

function addLayers(map: maplibregl.Map) {
  map.addSource('routes', { type: 'geojson', data: EMPTY })
  map.addSource('risk-segments', { type: 'geojson', data: EMPTY })
  map.addSource('checkpoints', { type: 'geojson', data: EMPTY })
  map.addSource('endpoints', { type: 'geojson', data: EMPTY })

  map.addLayer({
    id: 'route-casing',
    type: 'line',
    source: 'routes',
    layout: { 'line-join': 'round', 'line-cap': 'round' },
    paint: { 'line-color': '#ffffff', 'line-width': 9 },
  })
  map.addLayer({
    id: 'route-lines',
    type: 'line',
    source: 'routes',
    layout: { 'line-join': 'round', 'line-cap': 'round' },
    paint: { 'line-color': '#94a3b8', 'line-width': 4 },
  })
  // Selected route only (filtered on selection): risk-coloured line with a dark outline.
  map.addLayer({
    id: 'risk-casing',
    type: 'line',
    source: 'risk-segments',
    filter: ['==', ['get', 'routeId'], -1],
    layout: { 'line-join': 'round', 'line-cap': 'round' },
    paint: { 'line-color': '#1e293b', 'line-width': 10 },
  })
  map.addLayer({
    id: 'risk-segments',
    type: 'line',
    source: 'risk-segments',
    filter: ['==', ['get', 'routeId'], -1],
    layout: { 'line-join': 'round', 'line-cap': 'round' },
    paint: { 'line-color': RISK_COLOR_EXPRESSION, 'line-width': 6 },
  })
  map.addLayer({
    id: 'checkpoints',
    type: 'circle',
    source: 'checkpoints',
    paint: {
      'circle-color': RISK_COLOR_EXPRESSION,
      'circle-radius': 4,
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': 1.5,
    },
  })
  map.addLayer({
    id: 'endpoints',
    type: 'circle',
    source: 'endpoints',
    paint: {
      'circle-color': '#0f172a',
      'circle-radius': 10,
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': 2,
    },
  })
  map.addLayer({
    id: 'endpoint-labels',
    type: 'symbol',
    source: 'endpoints',
    layout: {
      'text-field': ['get', 'label'],
      'text-font': ['Noto Sans Bold'],
      'text-size': 12,
      'text-allow-overlap': true,
    },
    paint: { 'text-color': '#ffffff' },
  })
}

function checkpointHtml(cp: Checkpoint): string {
  const w = cp.weather
  const reasons = cp.reasons.length ? `<ul>${cp.reasons.map((r) => `<li>${escapeHtml(r)}</li>`).join('')}</ul>` : ''
  return `
    <div class="popup">
      <div class="popup-title">
        <span class="dot" style="background:${RISK_COLORS[cp.risk]}"></span>
        ${RISK_NAMES[cp.risk]} · mile ${Math.round(cp.mile)}
      </div>
      <div>ETA ${formatTime(cp.eta)}</div>
      <div>Wind ${w.wind_mph.toFixed(0)} mph (gusts ${w.gust_mph.toFixed(0)})</div>
      <div>Rain ${w.rain_in_hr.toFixed(2)} in/hr · Snow ${w.snow_in_hr.toFixed(2)} in/hr</div>
      <div>${w.temperature_f.toFixed(0)}°F</div>
      ${reasons}
    </div>`
}

function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`)
}
