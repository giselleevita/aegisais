import { Suspense, lazy } from 'react'
import { BrowserRouter } from 'react-router-dom'
import { getUiMode } from '@/core/uiMode'

const LegacyApp = lazy(() => import('@/legacy/LegacyApp'))
const AmlApp = lazy(() => import('@/aml/AmlApp'))

function AppBootFallback() {
  return <div className="app-loading-shell">Loading workspace...</div>
}

/**
 * Default: AML analyst console (fusion-to-risk workflow). Legacy tabbed UI when
 * `VITE_USE_LEGACY_UI=true` or when the user chooses “Classic tabbed UI” (stored in localStorage).
 */
export default function App() {
  const mode = getUiMode()
  if (mode === 'legacy') {
    return (
      <Suspense fallback={<AppBootFallback />}>
        <LegacyApp />
      </Suspense>
    )
  }
  return (
    <Suspense fallback={<AppBootFallback />}>
      <BrowserRouter>
        <AmlApp />
      </BrowserRouter>
    </Suspense>
  )
}
