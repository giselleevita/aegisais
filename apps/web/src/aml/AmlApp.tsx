import { lazy, Suspense, useMemo } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import '@/App.css'
import { useWebSocket } from '@/shared/hooks/useWebSocket'
import { getStreamWebSocketUrl } from '@/core/ws-url'
import { evaluatePolicyRequirements, useAuthoritativeAuthContext } from '@/core/auth-context'
import { getAccessToken } from '@/core/auth-token'
import AmlShell from '@/aml/AmlShell'
import OperationsPage from '@/aml/pages/OperationsPage'
import AlertInvestigationPage from '@/aml/pages/AlertInvestigationPage'
import WatchlistPage from '@/aml/pages/WatchlistPage'
import AdminPage from '@/aml/pages/AdminPage'
import IncidentsPage from '@/aml/pages/IncidentsPage'
import IncidentDetailPage from '@/aml/pages/IncidentDetailPage'
import AuditPage from '@/aml/pages/AuditPage'
import SanctionsPage from '@/aml/pages/SanctionsPage'
import OnboardingTourPage from '@/aml/pages/OnboardingTourPage'
import { AML_OPERATIONS_PATH, AML_PATHS } from '@/aml/amlRoutes'

const MapPage = lazy(() => import('@/aml/pages/MapPage'))
const ItdaePage = lazy(() => import('@/aml/pages/ItdaePage'))
const GlobeWorkbenchPage = lazy(() => import('@/aml/pages/GlobeWorkbenchPage'))

function RouteLoader() {
  return <div className="aml-page-pad aml-route-loading">Loading workspace…</div>
}

export default function AmlApp() {
  const {
    context: authContext,
    loading: authContextLoading,
    error: authContextError,
  } = useAuthoritativeAuthContext()
  const hasSession = !!getAccessToken()
  const streamAccess = useMemo(
    () =>
      evaluatePolicyRequirements(
        authContext,
        {
          minClearance: 'CONFIDENTIAL',
          requiredReleasability: ['NATO'],
          requiredLicenses: ['ports:read'],
        },
        {
          loading: authContextLoading,
          hasSession,
          fallbackLabel: 'live stream',
        }
      ),
    [authContext, authContextLoading, hasSession]
  )
  const streamUrl = streamAccess.allowed ? getStreamWebSocketUrl() : null
  const { connected, lastMessage } = useWebSocket(streamUrl)

  return (
    <Routes>
      <Route
        element={
          <AmlShell
            streamConnected={connected}
            lastMessage={lastMessage}
            authContext={authContext}
            authContextLoading={authContextLoading}
            authContextError={authContextError}
            streamAccessBlocked={!streamAccess.allowed && !streamAccess.pending}
            streamAccessPending={streamAccess.pending}
            streamAccessNotice={streamAccess.reason}
          />
        }
      >
        <Route path="/" element={<Navigate to={AML_OPERATIONS_PATH} replace />} />
        <Route path={AML_OPERATIONS_PATH} element={<OperationsPage />} />
        <Route path={AML_PATHS.alertDetailPattern} element={<AlertInvestigationPage />} />
        <Route
          path={AML_PATHS.map}
          element={
            <Suspense fallback={<RouteLoader />}>
              <MapPage />
            </Suspense>
          }
        />
        <Route path="/lab" element={<Navigate to={AML_OPERATIONS_PATH} replace />} />
        <Route
          path={AML_PATHS.itdae}
          element={
            <Suspense fallback={<RouteLoader />}>
              <ItdaePage />
            </Suspense>
          }
        />
        <Route
          path={AML_PATHS.globe}
          element={
            <Suspense fallback={<RouteLoader />}>
              <GlobeWorkbenchPage />
            </Suspense>
          }
        />
        <Route path={AML_PATHS.watchlist} element={<WatchlistPage />} />
        <Route path={AML_PATHS.sanctions} element={<SanctionsPage />} />
        <Route path={AML_PATHS.incidents} element={<IncidentsPage />} />
        <Route path={AML_PATHS.incidentDetailPattern} element={<IncidentDetailPage />} />
        <Route path={AML_PATHS.audit} element={<AuditPage />} />
        <Route path={AML_PATHS.onboarding} element={<OnboardingTourPage />} />
        <Route path="/about" element={<Navigate to={AML_OPERATIONS_PATH} replace />} />
        <Route path={AML_PATHS.admin} element={<AdminPage />} />
      </Route>
    </Routes>
  )
}
