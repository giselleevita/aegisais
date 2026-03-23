/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  /** When `true`, load the legacy tabbed UI instead of the AML analyst console. */
  readonly VITE_USE_LEGACY_UI?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
