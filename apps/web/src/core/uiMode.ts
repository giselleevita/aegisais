const STORAGE_KEY = 'aegisais_ui_mode'

export type UiMode = 'aml' | 'legacy'

/** How the SPA chooses between the AML console and the legacy tabbed app. */
export function getUiMode(): UiMode {
  if (import.meta.env.VITE_USE_LEGACY_UI === 'true') {
    return 'legacy'
  }
  try {
    const stored = localStorage.getItem(STORAGE_KEY) as UiMode | null
    if (stored === 'legacy' || stored === 'aml') {
      return stored
    }
  } catch {
    // ignore
  }
  return 'aml'
}

export function setUiMode(mode: UiMode): void {
  try {
    localStorage.setItem(STORAGE_KEY, mode)
  } catch {
    // ignore
  }
}

export function switchToLegacyUi(): void {
  setUiMode('legacy')
  window.location.reload()
}

export function switchToAmlUi(): void {
  setUiMode('aml')
  window.location.reload()
}
