import { useState } from 'react'
import './App.css'
import Dashboard from './components/Dashboard'
import VesselsPanel from './components/VesselsPanel'
import AlertsPanel from './components/AlertsPanel'
import ReplayControls from './components/ReplayControls'
import AboutAegisAIS from './components/AboutAegisAIS'
import { useWebSocket } from './hooks/useWebSocket'
import { API_BASE_URL } from './config'

function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'vessels' | 'alerts'>('dashboard')
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
      </nav>

      <main className="app-main">
        <div className="main-content">
          {activeTab === 'dashboard' && <Dashboard lastMessage={lastMessage} />}
          {activeTab === 'vessels' && <VesselsPanel />}
          {activeTab === 'alerts' && <AlertsPanel />}
        </div>

        <aside className="app-sidebar">
          <ReplayControls lastMessage={lastMessage} />
          <AboutAegisAIS />
        </aside>
      </main>
    </div>
  )
}

export default App
