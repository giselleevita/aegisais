import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import type { NavLinkProps } from 'react-router-dom'
import type { WebSocketMessage } from '@/shared/types/common'
import type { AmlOutletContext } from '@/aml/amlOutletContext'
import { apiClient } from '@/core/api-client'
import AuthBar from '@/shared/components/AuthBar/AuthBar'
import { switchToLegacyUi } from '@/core/uiMode'
import './aml-shell.css'

const navLinkClass: NavLinkProps['className'] = ({ isActive }) =>
  isActive ? 'aml-shell__nav-link--active' : undefined

type AmlShellProps = {
  streamConnected: boolean
  lastMessage: WebSocketMessage | null
}

export default function AmlShell({ streamConnected, lastMessage }: AmlShellProps) {
  const { pathname } = useLocation()
  const operationsActive = pathname === '/triage' || pathname === '/'
  const [replayRunning, setReplayRunning] = useState(false)
  const [replayProcessed, setReplayProcessed] = useState(0)

  useEffect(() => {
    let mounted = true
    const loadReplayStatus = async () => {
      try {
        const next = await apiClient.getReplayStatus()
        if (!mounted) return
        setReplayRunning(next.running)
        setReplayProcessed(next.processed)
      } catch {
        // Keep shell resilient when replay endpoint is unavailable.
      }
    }
    void loadReplayStatus()
    const timer = window.setInterval(loadReplayStatus, 3000)
    return () => {
      mounted = false
      window.clearInterval(timer)
    }
  }, [])

  return (
    <div className="aml-app">
      <header className="aml-shell__header">
        <div className="aml-shell__brand">
          <h1>
            AEGIS<span>AIS</span>
          </h1>
          <span className="aml-shell__brand-sub">Analyst</span>
        </div>
        <AuthBar />
        {replayRunning ? (
          <div className="aml-shell__demo-banner" aria-live="polite">
            Demo run active: {replayProcessed.toLocaleString()} points processed
          </div>
        ) : null}
        <span className={`status-indicator ${streamConnected ? 'connected' : 'disconnected'}`}>
          {streamConnected ? 'Live' : 'Offline'}
        </span>
      </header>

      <nav className="aml-shell__nav" role="navigation" aria-label="Main navigation">
        <div className="aml-shell__nav-group" aria-label="Primary views">
          <NavLink
            to="/triage"
            className={operationsActive ? 'aml-shell__nav-link--active' : undefined}
            aria-current={operationsActive ? 'page' : undefined}
          >
            Operations
          </NavLink>
          <NavLink to="/map" className={navLinkClass}>
            Map
          </NavLink>
          <NavLink to="/incidents" className={navLinkClass}>
            Incidents
          </NavLink>
          <NavLink to="/watchlist" className={navLinkClass}>
            Watchlist
          </NavLink>
        </div>
        <span className="aml-shell__nav-separator" aria-hidden="true" />
        <div className="aml-shell__nav-group" aria-label="Secondary views">
          <NavLink to="/globe" className={navLinkClass}>
            Globe
          </NavLink>
          <NavLink to="/itdae" className={navLinkClass}>
            ITDAE
          </NavLink>
          <NavLink to="/lab" className={navLinkClass}>
            Lab
          </NavLink>
          <NavLink to="/audit" className={navLinkClass}>
            Audit
          </NavLink>
          <NavLink to="/admin" className={navLinkClass}>
            Admin
          </NavLink>
        </div>
      </nav>

      <main className="aml-shell__main">
        <Outlet context={{ lastMessage } satisfies AmlOutletContext} />
      </main>

      <footer className="aml-shell__footer">
        <span>Deep links: /triage, /alerts/:id, /map?mmsi=</span>
        <button type="button" onClick={() => switchToLegacyUi()}>
          Classic tabbed UI
        </button>
      </footer>
    </div>
  )
}
