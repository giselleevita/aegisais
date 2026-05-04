export type TimelineMode = 'live' | 'replay'
export type FocusPresetId = 'global' | 'atlantic' | 'indo-pacific' | 'europe-med'

export type CameraCommand =
  | { sequence: number; type: 'preset'; presetId: FocusPresetId }
  | { sequence: number; type: 'fit-visible' }

export const FOCUS_PRESETS: Record<
  FocusPresetId,
  { label: string; lon: number; lat: number; height: number; range: number }
> = {
  global: {
    label: 'Global',
    lon: 8,
    lat: 18,
    height: 23_000_000,
    range: 11_000_000,
  },
  atlantic: {
    label: 'Atlantic',
    lon: -35,
    lat: 36,
    height: 9_000_000,
    range: 5_500_000,
  },
  'indo-pacific': {
    label: 'Indo-Pacific',
    lon: 112,
    lat: 9,
    height: 12_000_000,
    range: 6_500_000,
  },
  'europe-med': {
    label: 'Europe / Med',
    lon: 17,
    lat: 42,
    height: 7_500_000,
    range: 4_200_000,
  },
}