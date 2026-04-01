import { useEffect, useMemo, useState } from 'react'
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

const DOC_TITLE_BY_PATH: Array<{ match: (p: string) => boolean; title: string }> = [
  { match: (p) => p === '/triage' || p === '/', title: 'Triage' },
  { match: (p) => p === '/map', title: 'Map' },
  { match: (p) => p.startsWith('/alerts/'), title: 'Alert' },
  { match: (p) => p === '/incidents' || p.startsWith('/incidents/'), title: 'Incidents' },
  { match: (p) => p === '/watchlist', title: 'Watchlist' },
  { match: (p) => p === '/sanctions', title: 'Sanctions' },
  { match: (p) => p === '/globe', title: 'Globe' },
  { match: (p) => p === '/itdae', title: 'ITDAE' },
  { match: (p) => p === '/onboarding', title: 'Onboarding' },
  { match: (p) => p === '/audit', title: 'Audit' },
  { match: (p) => p === '/admin', title: 'Admin' },
]

export default function AmlShell({ streamConnected, lastMessage }: AmlShellProps) {
  const { pathname } = useLocation()
  const triageActive = pathname === '/triage' || pathname === '/'
  const [replayRunning, setReplayRunning] = useState(false)
  const [replayProcessed, setReplayProcessed] = useState(0)

  const pageTitle = useMemo(() => {
    const row = DOC_TITLE_BY_PATH.find((x) => x.match(pathname))
    return row?.title ?? 'Analyst'
  }, [pathname])

  useEffect(() => {
    document.title = `${pageTitle} · AegisAIS`
  }, [pageTitle])

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
      <a href="#main-content" className="aml-shell__skip">
        Skip to main content
      </a>
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
        <span
          className={`status-indicator ${streamConnected ? 'connected' : 'disconnected'}`}
          title={streamConnected ? 'Stream connected' : 'Stream disconnected — data may be stale'}
        >
          {streamConnected ? 'Live' : 'Offline'}
        </span>
      </header>

      <nav className="aml-shell__nav" role="navigation" aria-label="Main navigation">
        <div className="aml-shell__nav-section">
          <span className="aml-shell__nav-section-label" id="aml-nav-work">
            Work
          </span>
          <div className="aml-shell__nav-group" role="group" aria-labelledby="aml-nav-work">
            <NavLink
              to="/triage"
              className={triageActive ? 'aml-shell__nav-link--active' : undefined}
              aria-current={triageActive ? 'page' : undefined}
              title="Alert queue and map — primary workflow"
            >
              Triage
            </NavLink>
            <NavLink to="/map" className={navLinkClass} title="Vessel positions and alerts on the map">
              Map
            </NavLink>
            <NavLink to="/incidents" className={navLinkClass} title="Incident records linked to alerts">
              Incidents
            </NavLink>
            <NavLink to="/watchlist" className={navLinkClass} title="Vessels under active watch">
              Watchlist
            </NavLink>
            <NavLink to="/sanctions" className={navLinkClass} title="Sanctions list sync and management">
              Sanctions
            </NavLink>
          </div>
        </div>
        <div className="aml-shell__nav-section">
          <span className="aml-shell__nav-section-label" id="aml-nav-tools">
            Tools
          </span>
          <div className="aml-shell__nav-group" role="group" aria-labelledby="aml-nav-tools">
            <NavLink to="/globe" className={navLinkClass} title="3D globe and layer overlays">
              Globe
            </NavLink>
            <NavLink to="/itdae" className={navLinkClass} title="Infrastructure threat detection">
              ITDAE
            </NavLink>
            <NavLink to="/onboarding" className={navLinkClass} title="Guided setup for analysts">
              Onboarding
            </NavLink>
          </div>
        </div>
        <div className="aml-shell__nav-section">
          <span className="aml-shell__nav-section-label" id="aml-nav-system">
            System
          </span>
          <div className="aml-shell__nav-group" role="group" aria-labelledby="aml-nav-system">
            <NavLink to="/audit" className={navLinkClass} title="Audit log of analyst actions">
              Audit
            </NavLink>
            <NavLink to="/admin" className={navLinkClass} title="Integrations and control plane">
              Admin
            </NavLink>
          </div>
        </div>
      </nav>

      <main id="main-content" className="aml-shell__main" tabIndex={-1}>
        <Outlet context={{ lastMessage } satisfies AmlOutletContext} />
      </main>

      <footer className="aml-shell__footer">
        <details className="aml-shell__footer-shortcuts">
          <summary>Shortcuts &amp; deep links</summary>
          <ul className="aml-shell__footer-shortcuts-list">
            <li>
              <span>Triage (queue + map)</span> <code>/triage</code>
            </li>
            <li>
              <span>Alert investigation</span> <code>/alerts/:id</code>
            </li>
            <li>
              <span>Map with vessel</span> <code>/map?mmsi=</code>
            </li>
            <li>
              <span>Incident detail</span> <code>/incidents/:id</code>
            </li>
          </ul>
        </details>
        <button type="button" className="aml-shell__footer-legacy" onClick={() => switchToLegacyUi()}>
          Classic UI
        </button>
      </footer>
    </div>
  )
}
