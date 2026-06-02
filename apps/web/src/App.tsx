import { Suspense, lazy } from 'react'
import { BrowserRouter } from 'react-router-dom'
import { getUiMode } from '@/core/uiMode'
import { ErrorBoundary } from '@/core/ErrorBoundary'

const LegacyApp = lazy(() => import('@/legacy/LegacyApp'))
const AmlApp = lazy(() => import('@/aml/AmlApp'))

function AppBootFallback() {
    return <div className="app-loading-shell">Loading workspace...</div>
}

export default function App() {
    const mode = getUiMode()
    if (mode === 'legacy') {
        return (
            <ErrorBoundary label="LegacyApp">
                <Suspense fallback={<AppBootFallback />}>
                    <LegacyApp />
                </Suspense>
            </ErrorBoundary>
        )
    }
    return (
        <ErrorBoundary label="AmlApp">
            <Suspense fallback={<AppBootFallback />}>
                <BrowserRouter>
                    <AmlApp />
                </BrowserRouter>
            </Suspense>
        </ErrorBoundary>
    )
}
