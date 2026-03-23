import { NavLink, Outlet, useLocation } from 'react-router-dom'
import type { NavLinkProps } from 'react-router-dom'
import type { WebSocketMessage } from '@/shared/types/common'
import type { AmlOutletContext } from '@/aml/amlOutletContext'
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
        <span className={`status-indicator ${streamConnected ? 'connected' : 'disconnected'}`}>
          {streamConnected ? 'Live' : 'Offline'}
        </span>
      </header>

      <nav className="aml-shell__nav" role="navigation" aria-label="Main navigation">
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
        <NavLink to="/lab" className={navLinkClass}>
          Lab
        </NavLink>
        <NavLink to="/itdae" className={navLinkClass}>
          ITDAE
        </NavLink>
        <NavLink to="/globe" className={navLinkClass}>
          Globe
        </NavLink>
        <NavLink to="/watchlist" className={navLinkClass}>
          Watchlist
        </NavLink>
        <NavLink to="/incidents" className={navLinkClass}>
          Incidents
        </NavLink>
        <NavLink to="/audit" className={navLinkClass}>
          Audit
        </NavLink>
        <NavLink to="/admin" className={navLinkClass}>
          Admin
        </NavLink>
        <NavLink to="/about" className={navLinkClass}>
          About
        </NavLink>
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
