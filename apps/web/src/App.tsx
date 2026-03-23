import { BrowserRouter } from 'react-router-dom'
import LegacyApp from '@/legacy/LegacyApp'
import AmlApp from '@/aml/AmlApp'
import { getUiMode } from '@/core/uiMode'

/**
 * Default: AML analyst console (fusion-to-risk workflow). Legacy tabbed UI when
 * `VITE_USE_LEGACY_UI=true` or when the user chooses “Classic tabbed UI” (stored in localStorage).
 */
export default function App() {
  const mode = getUiMode()
  if (mode === 'legacy') {
    return <LegacyApp />
  }
  return (
    <BrowserRouter>
      <AmlApp />
    </BrowserRouter>
  )
}
