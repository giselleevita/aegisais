import type { LayerDefinition } from '@/shared/types/common'
import { API_BASE_URL } from '@/core/config'
import { apiClient } from '@/core/api-client'

export type FlightPoint = {
  id: string
  label: string
  lat: number
  lon: number
  altitudeM: number
}

export type PortPoint = {
  id: string
  name: string
  lat: number
  lon: number
}

export type CableSegment = {
  id: string
  label: string
  path: Array<[number, number]>
  placeholder?: boolean
}

const FALLBACK_LAYERS: LayerDefinition[] = [
  {
    id: 'flights-live',
    name: 'Flights Live',
    category: 'live',
    description: 'BFF-backed airborne tracks for analyst correlation.',
    enabledByDefault: true,
    metadata: {
      provenance: 'BFF fusion stream',
      confidence: 0.84,
      source: 'ADS-B feed bundle',
      access: 'analyst',
      licence: 'internal-use',
    },
  },
  {
    id: 'ports-reference',
    name: 'Ports',
    category: 'reference',
    description: 'Reference points for major ports and terminals.',
    enabledByDefault: true,
    metadata: {
      provenance: 'Aegis static gazetteer',
      confidence: 0.96,
      source: 'UN/LOCODE + curated edits',
      access: 'viewer',
      licence: 'open-database',
    },
  },
  {
    id: 'subsea-cables',
    name: 'Subsea Cables',
    category: 'infrastructure',
    description: 'Cable route overlays. Shows placeholders when no feed is connected.',
    restricted: true,
    nonCommercial: true,
    enabledByDefault: false,
    metadata: {
      provenance: 'Infrastructure partner exports',
      confidence: 0.61,
      source: 'Telecom consortium handoff',
      access: 'restricted',
      licence: 'non-commercial',
    },
  },
]

const FALLBACK_PORTS: PortPoint[] = [
  { id: 'sgp', name: 'Port of Singapore', lat: 1.264, lon: 103.84 },
  { id: 'rtm', name: 'Port of Rotterdam', lat: 51.94, lon: 4.14 },
  { id: 'dub', name: 'Port of Dubai', lat: 25.246, lon: 55.281 },
  { id: 'ham', name: 'Port of Hamburg', lat: 53.547, lon: 9.966 },
]

const FALLBACK_CABLES: CableSegment[] = [
  {
    id: 'placeholder-atlantic',
    label: 'Atlantic trunk (placeholder)',
    placeholder: true,
    path: [
      [51.5, -0.12],
      [45.2, -28.2],
      [40.7, -74.0],
    ],
  },
]

function flightSeed(): FlightPoint[] {
  return [
    { id: 'flt-101', label: 'FLT101', lat: 53.2, lon: 5.1, altitudeM: 9400 },
    { id: 'flt-224', label: 'FLT224', lat: 41.5, lon: 2.1, altitudeM: 10100 },
    { id: 'flt-390', label: 'FLT390', lat: 25.8, lon: 55.2, altitudeM: 10800 },
  ]
}

export async function getLayerCatalogue(): Promise<LayerDefinition[]> {
  try {
    return await apiClient.getLayers()
  } catch {
    return FALLBACK_LAYERS
  }
}

export async function getPortsReference(): Promise<PortPoint[]> {
  return FALLBACK_PORTS
}

export async function getSubseaCables(): Promise<CableSegment[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/bff/subsea-cables`)
    if (!res.ok) throw new Error('no cable feed')
    const rows = (await res.json()) as CableSegment[]
    return rows.length ? rows : FALLBACK_CABLES
  } catch {
    return FALLBACK_CABLES
  }
}

export async function getFlightsLiveSnapshot(): Promise<FlightPoint[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/bff/flights/live`)
    if (!res.ok) throw new Error('live flight endpoint unavailable')
    return (await res.json()) as FlightPoint[]
  } catch {
    return flightSeed()
  }
}

export function subscribeFlightsLive(onFrame: (next: FlightPoint[]) => void): () => void {
  const timer = window.setInterval(() => {
    const jittered = flightSeed().map((flight, index) => ({
      ...flight,
      lat: flight.lat + Math.sin(Date.now() / 8000 + index) * 0.12,
      lon: flight.lon + Math.cos(Date.now() / 7000 + index) * 0.16,
    }))
    onFrame(jittered)
  }, 2500)

  return () => window.clearInterval(timer)
}
