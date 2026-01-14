import { useState } from 'react'
import './App.css'
import WelcomePage from './components/WelcomePage'
import Dashboard from './components/Dashboard'
import VesselsPanel from './components/VesselsPanel'
import AlertsPanel from './components/AlertsPanel'
import MapView from './components/MapView'
import VesselDetails from './components/VesselDetails'
import ReplayControls from './components/ReplayControls'
import AboutAegisAIS from './components/AboutAegisAIS'
import ErrorBoundary from './components/ErrorBoundary'
import { useWebSocket } from './hooks/useWebSocket'
import { API_BASE_URL } from './config'

function App() {
  const [activeTab, setActiveTab] = useState<'home' | 'dashboard' | 'vessels' | 'alerts' | 'map' | 'vessel-details'>('home')
  const [selectedVessel, setSelectedVessel] = useState<string | null>(null)
  const { connected, lastMessage } = useWebSocket(`${API_BASE_URL.replace('http', 'ws')}/v1/stream`)

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>🛡️ AegisAIS</h1>
          <div className="header-status">
            <span className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}>
              {connected ? '● Connected' : '○ Disconnected'}
            </span>
          </div>
        </div>
      </header>

      <nav className="app-nav">
        <button
          className={activeTab === 'home' ? 'active' : ''}
          onClick={() => setActiveTab('home')}
        >
          Home
        </button>
        <button
          className={activeTab === 'dashboard' ? 'active' : ''}
          onClick={() => setActiveTab('dashboard')}
        >
          Dashboard
        </button>
        <button
          className={activeTab === 'vessels' ? 'active' : ''}
          onClick={() => setActiveTab('vessels')}
        >
          Vessels
        </button>
        <button
          className={activeTab === 'alerts' ? 'active' : ''}
          onClick={() => setActiveTab('alerts')}
        >
          Alerts
        </button>
        <button
          className={activeTab === 'map' ? 'active' : ''}
          onClick={() => setActiveTab('map')}
        >
          Map
        </button>
      </nav>

      <main className="app-main">
        <div className="main-content">
          <ErrorBoundary>
            {activeTab === 'home' && <WelcomePage />}
            {activeTab === 'dashboard' && <Dashboard lastMessage={lastMessage} />}
            {activeTab === 'vessels' && <VesselsPanel onVesselClick={(mmsi) => { setSelectedVessel(mmsi); setActiveTab('vessel-details'); }} />}
            {activeTab === 'alerts' && <AlertsPanel />}
            {activeTab === 'map' && <MapView selectedVessel={selectedVessel} onVesselClick={(mmsi) => { setSelectedVessel(mmsi); setActiveTab('vessel-details'); }} />}
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

export default App
