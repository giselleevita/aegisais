import type { LayerDefinition, LayerManifestItem } from '@/shared/types/common'
import { API_BASE_URL } from '@/core/config'
import { ApiClientError, apiClient } from '@/core/api-client'

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
  { id: 'sue', name: 'Suez Port', lat: 29.966, lon: 32.549 },
  { id: 'la', name: 'Port of Los Angeles', lat: 33.736, lon: -118.263 },
  { id: 'cpt', name: 'Port of Cape Town', lat: -33.907, lon: 18.435 },
  { id: 'tok', name: 'Port of Tokyo', lat: 35.614, lon: 139.795 },
  { id: 'syd', name: 'Port Botany', lat: -33.966, lon: 151.228 },
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
  {
    id: 'placeholder-med-indian',
    label: 'Mediterranean - Indian Ocean (placeholder)',
    placeholder: true,
    path: [
      [36.1, -5.3],
      [31.0, 32.3],
      [15.6, 54.0],
      [1.3, 103.8],
    ],
  },
  {
    id: 'placeholder-pacific',
    label: 'Trans-Pacific trunk (placeholder)',
    placeholder: true,
    path: [
      [35.7, 139.8],
      [33.3, 179.0],
      [37.7, -122.2],
    ],
  },
]

function flightSeed(): FlightPoint[] {
  return [
    { id: 'flt-101', label: 'FLT101', lat: 53.2, lon: 5.1, altitudeM: 9400 },
    { id: 'flt-224', label: 'FLT224', lat: 41.5, lon: 2.1, altitudeM: 10100 },
    { id: 'flt-390', label: 'FLT390', lat: 25.8, lon: 55.2, altitudeM: 10800 },
    { id: 'flt-557', label: 'FLT557', lat: 1.3, lon: 104.1, altitudeM: 11200 },
    { id: 'flt-612', label: 'FLT612', lat: 35.7, lon: 139.8, altitudeM: 9700 },
    { id: 'flt-731', label: 'FLT731', lat: 59.2, lon: 18.3, altitudeM: 8900 },
    { id: 'flt-844', label: 'FLT844', lat: -33.9, lon: 18.4, altitudeM: 10300 },
    { id: 'flt-905', label: 'FLT905', lat: 37.7, lon: -122.2, altitudeM: 9200 },
  ]
}

function manifestItemToLayerDefinition(item: LayerManifestItem): LayerDefinition {
  const category =
    item.domain === 'ports'
      ? 'reference'
      : item.domain === 'subsea'
        ? 'infrastructure'
        : 'live'

  const descriptions: Record<LayerManifestItem['domain'], string> = {
    aviation: 'Airspace and aviation overlays from the BFF policy surface.',
    ports: 'Port and terminal reference overlays from the BFF policy surface.',
    subsea: 'Subsea cable overlays from the BFF policy surface.',
  }

  return {
    id: item.id,
    name: item.name,
    category,
    description: descriptions[item.domain],
    enabledByDefault: item.domain !== 'subsea',
    restricted: item.domain === 'subsea',
    nonCommercial: item.domain === 'subsea',
    licensedFeature: item.licensedFeature,
    updatedAt: item.updatedAt,
    metadata: {
      provenance: `BFF ${item.domain} manifest`,
      confidence: item.domain === 'ports' ? 0.96 : 0.84,
      source: item.source,
      access: item.licensedFeature,
      licence: item.licensedFeature,
    },
  }
}

export async function getLayerCatalogue(): Promise<LayerDefinition[]> {
  try {
    const manifest = await apiClient.getLayersManifest()
    return manifest.layers.map(manifestItemToLayerDefinition)
  } catch (error) {
    if (error instanceof ApiClientError && (error.status === 401 || error.status === 403)) {
      throw error
    }
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
