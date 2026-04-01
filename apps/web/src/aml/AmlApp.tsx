import { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import '@/App.css'
import { useWebSocket } from '@/shared/hooks/useWebSocket'
import { getStreamWebSocketUrl } from '@/core/ws-url'
import { subscribeAuth } from '@/core/auth-token'
import AmlShell from '@/aml/AmlShell'
import OperationsPage from '@/aml/pages/OperationsPage'
import AlertInvestigationPage from '@/aml/pages/AlertInvestigationPage'
import MapPage from '@/aml/pages/MapPage'
import ItdaePage from '@/aml/pages/ItdaePage'
import WatchlistPage from '@/aml/pages/WatchlistPage'
import AdminPage from '@/aml/pages/AdminPage'
import GlobeWorkbenchPage from '@/aml/pages/GlobeWorkbenchPage'
import IncidentsPage from '@/aml/pages/IncidentsPage'
import IncidentDetailPage from '@/aml/pages/IncidentDetailPage'
import AuditPage from '@/aml/pages/AuditPage'
import SanctionsPage from '@/aml/pages/SanctionsPage'
import OnboardingTourPage from '@/aml/pages/OnboardingTourPage'
import { AML_OPERATIONS_PATH } from '@/aml/amlRoutes'

export default function AmlApp() {
  const [streamUrl, setStreamUrl] = useState(() => getStreamWebSocketUrl())
  useEffect(() => subscribeAuth(() => setStreamUrl(getStreamWebSocketUrl())), [])
  const { connected, lastMessage } = useWebSocket(streamUrl)

  return (
    <Routes>
      <Route element={<AmlShell streamConnected={connected} lastMessage={lastMessage} />}>
        <Route path="/" element={<Navigate to={AML_OPERATIONS_PATH} replace />} />
        <Route path={AML_OPERATIONS_PATH} element={<OperationsPage />} />
        <Route path="/alerts/:alertId" element={<AlertInvestigationPage />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/lab" element={<Navigate to={AML_OPERATIONS_PATH} replace />} />
        <Route path="/itdae" element={<ItdaePage />} />
        <Route path="/globe" element={<GlobeWorkbenchPage />} />
        <Route path="/watchlist" element={<WatchlistPage />} />
        <Route path="/sanctions" element={<SanctionsPage />} />
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/incidents/:incidentId" element={<IncidentDetailPage />} />
        <Route path="/audit" element={<AuditPage />} />
        <Route path="/onboarding" element={<OnboardingTourPage />} />
        <Route path="/about" element={<Navigate to={AML_OPERATIONS_PATH} replace />} />
        <Route path="/admin" element={<AdminPage />} />
      </Route>
    </Routes>
  )
}
