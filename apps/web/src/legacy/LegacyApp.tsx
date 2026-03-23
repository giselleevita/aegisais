import { useState, useEffect } from 'react'
import '../App.css'
import WelcomePage from '@/shared/components/WelcomePage/WelcomePage'
import Dashboard from '@/shared/components/Dashboard/Dashboard'
import VesselsPanel from '@/features/vessels/components/VesselsPanel'
import AlertsPanel from '@/features/alerts/components/AlertsPanel'
import MapView from '@/features/map/components/MapView'
import VesselDetails from '@/features/vessels/components/VesselDetails'
import ReplayControls from '@/shared/components/ReplayControls/ReplayControls'
import AboutAegisAIS from '@/shared/components/AboutAegisAIS/AboutAegisAIS'
import Onboarding from '@/shared/components/Onboarding/Onboarding'
import ErrorBoundary from '@/shared/components/ErrorBoundary'
import ITDAEPanel from '@/features/itdae/components/ITDAEPanel'
import { useWebSocket } from '@/shared/hooks/useWebSocket'
import { getStreamWebSocketUrl } from '@/core/ws-url'
import { subscribeAuth } from '@/core/auth-token'
import AuthBar from '@/shared/components/AuthBar/AuthBar'
import WatchlistPanel from '@/features/vessels/components/WatchlistPanel'
import { switchToAmlUi } from '@/core/uiMode'

export default function LegacyApp() {
  const [activeTab, setActiveTab] = useState<'home' | 'dashboard' | 'vessels' | 'alerts' | 'map' | 'itdae' | 'watchlist' | 'vessel-details'>('home')
  const [selectedVessel, setSelectedVessel] = useState<string | null>(null)
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [streamUrl, setStreamUrl] = useState(() => getStreamWebSocketUrl())

  useEffect(() => subscribeAuth(() => setStreamUrl(getStreamWebSocketUrl())), [])

  const { connected, lastMessage } = useWebSocket(streamUrl)

  useEffect(() => {
    const hasCompletedOnboarding = localStorage.getItem('aegisais_onboarding_completed')
    if (!hasCompletedOnboarding) {
      const timer = setTimeout(() => {
        setShowOnboarding(true)
      }, 1000)
      return () => clearTimeout(timer)
    }
  }, [])

  const handleOnboardingComplete = () => {
    localStorage.setItem('aegisais_onboarding_completed', 'true')
    setShowOnboarding(false)
  }

  const handleOnboardingSkip = () => {
    localStorage.setItem('aegisais_onboarding_completed', 'true')
    setShowOnboarding(false)
  }

  return (
    <div className="app">
      {showOnboarding && (
        <Onboarding
          onComplete={handleOnboardingComplete}
          onSkip={handleOnboardingSkip}
        />
      )}
      <header className="app-header">
        <div className="header-content">
          <h1>AEGIS<span>AIS</span></h1>
          <AuthBar />
          <div className="header-status">
            <span className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}>
              {connected ? 'Live' : 'Offline'}
            </span>
            <button
              type="button"
              onClick={() => {
                localStorage.removeItem('aegisais_onboarding_completed')
                setShowOnboarding(true)
              }}
              className="onboarding-trigger"
              title="Show onboarding tour"
            >
              Tour
            </button>
            <button
              type="button"
              className="onboarding-trigger"
              title="Open the AML analyst console"
              onClick={() => switchToAmlUi()}
            >
              Analyst console
            </button>
          </div>
        </div>
      </header>

      <nav className="app-nav" role="navigation" aria-label="Main navigation">
        <button
          className={activeTab === 'home' ? 'active' : ''}
          onClick={() => setActiveTab('home')}
          aria-label="Home page"
          aria-current={activeTab === 'home' ? 'page' : undefined}
        >
          Home
        </button>
        <button
          className={activeTab === 'dashboard' ? 'active' : ''}
          onClick={() => setActiveTab('dashboard')}
          aria-label="Dashboard"
          aria-current={activeTab === 'dashboard' ? 'page' : undefined}
        >
          Dashboard
        </button>
        <button
          className={activeTab === 'vessels' ? 'active' : ''}
          onClick={() => setActiveTab('vessels')}
          aria-label="Vessels"
          aria-current={activeTab === 'vessels' ? 'page' : undefined}
        >
          Vessels
        </button>
        <button
          className={activeTab === 'alerts' ? 'active' : ''}
          onClick={() => setActiveTab('alerts')}
          aria-label="Alerts"
          aria-current={activeTab === 'alerts' ? 'page' : undefined}
        >
          Alerts
        </button>
        <button
          className={activeTab === 'map' ? 'active' : ''}
          onClick={() => setActiveTab('map')}
          aria-label="Map view"
          aria-current={activeTab === 'map' ? 'page' : undefined}
        >
          Map
        </button>
        <button
          className={activeTab === 'itdae' ? 'active' : ''}
          onClick={() => setActiveTab('itdae')}
          aria-label="Infrastructure threats"
          aria-current={activeTab === 'itdae' ? 'page' : undefined}
        >
          ITDAE
        </button>
        <button
          className={activeTab === 'watchlist' ? 'active' : ''}
          onClick={() => setActiveTab('watchlist')}
          aria-label="Watchlist"
          aria-current={activeTab === 'watchlist' ? 'page' : undefined}
        >
          Watchlist
        </button>
      </nav>

      <main className="app-main">
        <div className="main-content">
          <ErrorBoundary>
            {activeTab === 'home' && (
              <WelcomePage
                onStartOnboarding={() => {
                  localStorage.removeItem('aegisais_onboarding_completed')
                  setShowOnboarding(true)
                }}
              />
            )}
            {activeTab === 'dashboard' && <Dashboard lastMessage={lastMessage} />}
            {activeTab === 'vessels' && <VesselsPanel onVesselClick={(mmsi) => { setSelectedVessel(mmsi); setActiveTab('vessel-details'); }} />}
            {activeTab === 'alerts' && <AlertsPanel streamMessage={lastMessage} />}
            {activeTab === 'itdae' && (
              <ErrorBoundary>
                <ITDAEPanel />
              </ErrorBoundary>
            )}
            {activeTab === 'watchlist' && (
              <ErrorBoundary>
                <WatchlistPanel />
              </ErrorBoundary>
            )}
            {activeTab === 'map' && <MapView selectedVessel={selectedVessel} onVesselClick={(mmsi) => { setSelectedVessel(mmsi); setActiveTab('vessel-details'); }} showInfrastructure={activeTab === 'map'} />}
            {activeTab === 'vessel-details' && selectedVessel && (
              <VesselDetails
                mmsi={selectedVessel}
                onClose={() => { setSelectedVessel(null); setActiveTab('vessels'); }}
              />
            )}
          </ErrorBoundary>
        </div>

        <aside className="app-sidebar">
          <ErrorBoundary>
            <ReplayControls lastMessage={lastMessage} />
          </ErrorBoundary>
          <ErrorBoundary>
            <AboutAegisAIS />
          </ErrorBoundary>
        </aside>
      </main>
    </div>
  )
}
