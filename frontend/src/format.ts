import type { RiskLabel } from './api'

export const RISK_LEVELS: RiskLabel[] = ['low', 'moderate', 'high', 'severe', 'no_travel']

export const RISK_COLORS: Record<RiskLabel, string> = {
  low: '#2e9e5b',
  moderate: '#e3b505',
  high: '#f07c1b',
  severe: '#d62839',
  no_travel: '#6a1b9a',
}

export const RISK_NAMES: Record<RiskLabel, string> = {
  low: 'Low',
  moderate: 'Moderate',
  high: 'High',
  severe: 'Severe',
  no_travel: 'No Travel',
}

export function formatDuration(seconds: number): string {
  const totalMinutes = Math.round(seconds / 60)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return hours ? `${hours} h ${minutes} min` : `${minutes} min`
}

const dateTime = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  hour: 'numeric',
  minute: '2-digit',
})

export function formatTime(iso: string): string {
  return dateTime.format(new Date(iso))
}

export function formatMiles(miles: number): string {
  return `${Math.round(miles).toLocaleString()} mi`
}
