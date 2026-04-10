import { useEffect, useMemo, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import type { NavLinkProps } from 'react-router-dom'
import type { AuthContextResponse, WebSocketMessage } from '@/shared/types/common'
import type { AmlOutletContext } from '@/aml/amlOutletContext'
import {
  AML_ROUTE_META,
  canAccessPath,
  canAccessMatchedPath,
  getRouteAccessDecision,
  getActiveRouteMeta,
  getSectionLandingPath,
  getSectionNav,
  PRODUCT_SECTIONS,
} from '@/aml/amlRouteMeta'
import { getUiRole } from '@/core/uiRole'
import { apiClient } from '@/core/api-client'
import AuthBar from '@/shared/components/AuthBar/AuthBar'
import { switchToLegacyUi } from '@/core/uiMode'
import { getAccessToken } from '@/core/auth-token'
import { AML_OPERATIONS_PATH, AML_PATHS, AML_QUERY, getMapForMmsiPath } from '@/aml/amlRoutes'
import './aml-shell.css'

const navLinkClass: NavLinkProps['className'] = ({ isActive }) =>
  isActive ? 'aml-shell__nav-link--active' : undefined

const topNavLinkClass: NavLinkProps['className'] = ({ isActive }) =>
  isActive ? 'aml-shell__top-nav-link aml-shell__top-nav-link--active' : 'aml-shell__top-nav-link'

type AmlShellProps = {
  streamConnected: boolean
  lastMessage: WebSocketMessage | null
  authContext: AuthContextResponse | null
  authContextLoading: boolean
  authContextError: string | null
  streamAccessBlocked: boolean
  streamAccessPending: boolean
  streamAccessNotice: string | null
}

type AmlLocationState = {
  accessNotice?: string
}

type PaletteItem = {
  id: string
  label: string
  hint?: string
  aliases?: string[]
  run: () => void
}

const COMPACT_MODE_STORAGE_KEY = 'aegisais_compact_mode'
const HIGH_CONTRAST_STORAGE_KEY = 'aegisais_high_contrast_mode'
const PALETTE_USAGE_STORAGE_KEY = 'aegisais_palette_usage'

const NAV_SHORTCUTS: Array<{ key: string; label: string; path: string }> = [
  { key: 'Alt+1', label: 'Triage', path: AML_OPERATIONS_PATH },
  { key: 'Alt+2', label: 'Map', path: AML_PATHS.map },
  { key: 'Alt+3', label: 'Incidents', path: AML_PATHS.incidents },
  { key: 'Alt+4', label: 'Watchlist', path: AML_PATHS.watchlist },
  { key: 'Alt+5', label: 'Audit', path: AML_PATHS.audit },
  { key: 'Alt+6', label: 'Admin', path: AML_PATHS.admin },
]

const ROUTE_PRIORITY: Record<string, number> = {
  [AML_OPERATIONS_PATH]: 30,
  [AML_PATHS.map]: 28,
  [AML_PATHS.incidents]: 25,
  [AML_PATHS.watchlist]: 24,
  [AML_PATHS.audit]: 20,
  [AML_PATHS.admin]: 18,
}

const ROUTE_ALIASES: Record<string, string[]> = {
  [AML_OPERATIONS_PATH]: ['go triage', 'open triage', 'queue', 'alerts queue'],
  [AML_PATHS.map]: ['go map', 'open map', 'map view'],
  [AML_PATHS.incidents]: ['go incidents', 'open incidents', 'case list'],
  [AML_PATHS.watchlist]: ['go watchlist', 'open watchlist'],
  [AML_PATHS.audit]: ['go audit', 'open audit', 'audit log'],
  [AML_PATHS.admin]: ['go admin', 'open admin', 'control plane'],
  [AML_PATHS.globe]: ['go globe', 'open globe', '3d globe'],
  [AML_PATHS.itdae]: ['go itdae', 'open itdae', 'infrastructure threat'],
}

function getInitialCompactMode(): boolean {
  try {
    const stored = localStorage.getItem(COMPACT_MODE_STORAGE_KEY)
    if (stored === 'true') return true
    if (stored === 'false') return false
  } catch {
    // ignore
  }
  if (typeof window === 'undefined') return false
  return window.matchMedia('(max-width: 1366px)').matches
}

function getInitialHighContrastMode(): boolean {
  try {
    return localStorage.getItem(HIGH_CONTRAST_STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

function editableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName.toLowerCase()
  return target.isContentEditable || tag === 'input' || tag === 'textarea' || tag === 'select'
}

function getPaletteUsageMap(): Record<string, number> {
  try {
    const raw = localStorage.getItem(PALETTE_USAGE_STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object') return {}
    const out: Record<string, number> = {}
    Object.entries(parsed as Record<string, unknown>).forEach(([k, v]) => {
      if (typeof v === 'number' && Number.isFinite(v) && v > 0) out[k] = v
    })
    return out
  } catch {
    return {}
  }
}

function trackPaletteUsage(id: string): void {
  try {
    const usage = getPaletteUsageMap()
    usage[id] = (usage[id] ?? 0) + 1
    localStorage.setItem(PALETTE_USAGE_STORAGE_KEY, JSON.stringify(usage))
  } catch {
    // ignore local storage failures
  }
}

export default function AmlShell({
  streamConnected,
  lastMessage,
  authContext,
  authContextLoading,
  authContextError,
  streamAccessBlocked,
  streamAccessPending,
  streamAccessNotice,
}: AmlShellProps) {
  const location = useLocation()
  const { pathname, search } = location
  const navigate = useNavigate()
  const hasSession = !!getAccessToken()
  const [replayRunning, setReplayRunning] = useState(false)
  const [replayProcessed, setReplayProcessed] = useState(0)
  const [compactMode, setCompactMode] = useState(() => getInitialCompactMode())
  const [highContrastMode, setHighContrastMode] = useState(() => getInitialHighContrastMode())
  const [shortcutsOpen, setShortcutsOpen] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [paletteQuery, setPaletteQuery] = useState('')
  const [paletteIndex, setPaletteIndex] = useState(0)
  const paletteInputRef = useRef<HTMLInputElement | null>(null)
  const [paletteUsage, setPaletteUsage] = useState<Record<string, number>>(() => getPaletteUsageMap())
  const selectedMmsi = useMemo(() => new URLSearchParams(search).get(AML_QUERY.mmsi), [search])
  const selectedAlertId = useMemo(() => (pathname.startsWith('/alerts/') ? pathname.split('/')[2] ?? null : null), [pathname])
  const selectedIncidentId = useMemo(
    () => (pathname.startsWith('/incidents/') ? pathname.split('/')[2] ?? null : null),
    [pathname]
  )

  const uiRole = useMemo(() => getUiRole(authContext), [authContext])
  const activeRoute = useMemo(() => getActiveRouteMeta(pathname), [pathname])
  const activeSectionId = activeRoute?.sectionId ?? 'operations'
  const pageTitle = activeRoute?.title ?? 'Analyst'
  const activeRouteAccess = useMemo(
    () =>
      activeRoute
        ? getRouteAccessDecision(activeRoute, uiRole, authContext, {
            authLoading: authContextLoading,
            hasSession,
          })
        : { allowed: true, pending: false, reason: null },
    [activeRoute, authContext, authContextLoading, hasSession, uiRole]
  )
  const canAccessActiveRoute = useMemo(
    () => canAccessMatchedPath(pathname, uiRole, authContext, { authLoading: authContextLoading, hasSession }),
    [authContext, authContextLoading, hasSession, pathname, uiRole]
  )
  const accessNotice = useMemo(() => {
    const state = (location.state ?? null) as AmlLocationState | null
    return typeof state?.accessNotice === 'string' ? state.accessNotice : null
  }, [location.state])
  const visibleSections = useMemo(
    () =>
      PRODUCT_SECTIONS.filter(
        (section) =>
          getSectionNav(section.id, uiRole, authContext, {
            authLoading: authContextLoading,
            hasSession,
          }).length > 0
      ),
    [authContext, authContextLoading, hasSession, uiRole]
  )
  const sectionNav = useMemo(
    () => getSectionNav(activeSectionId, uiRole, authContext, { authLoading: authContextLoading, hasSession }),
    [activeSectionId, authContext, authContextLoading, hasSession, uiRole]
  )
  const paletteItems = useMemo<PaletteItem[]>(() => {
    const routeItems = AML_ROUTE_META.filter(
      (route) =>
        route.navLabel &&
        canAccessPath(route.path, uiRole, authContext, { authLoading: authContextLoading, hasSession })
    ).map((route) => ({
      id: `route:${route.path}`,
      label: route.navLabel!,
      hint: route.sectionId,
      aliases: ROUTE_ALIASES[route.path] ?? [],
      run: () => navigate(route.path),
    }))

    const actionItems: PaletteItem[] = [
      {
        id: 'action:compact',
        label: compactMode ? 'Disable compact mode' : 'Enable compact mode',
        hint: 'display',
        aliases: compactMode ? ['compact off', 'disable compact'] : ['compact on', 'enable compact'],
        run: () => setCompactMode((prev) => !prev),
      },
      {
        id: 'action:contrast',
        label: highContrastMode ? 'Disable high contrast mode' : 'Enable high contrast mode',
        hint: 'display',
        aliases: highContrastMode
          ? ['contrast off', 'normal contrast', 'high contrast off']
          : ['contrast on', 'high contrast on'],
        run: () => setHighContrastMode((prev) => !prev),
      },
      {
        id: 'action:shortcuts',
        label: shortcutsOpen ? 'Hide shortcuts panel' : 'Show shortcuts panel',
        hint: 'help',
        aliases: shortcutsOpen ? ['hide shortcuts'] : ['show shortcuts', 'open shortcuts'],
        run: () => setShortcutsOpen((prev) => !prev),
      },
    ]
    return [...routeItems, ...actionItems]
  }, [authContext, authContextLoading, compactMode, hasSession, highContrastMode, navigate, shortcutsOpen, uiRole])
  const paletteResults = useMemo(() => {
    const q = paletteQuery.trim().toLowerCase()
    const scoreItem = (item: PaletteItem): number => {
      const label = item.label.toLowerCase()
      const hint = (item.hint ?? '').toLowerCase()
      const aliases = (item.aliases ?? []).map((x) => x.toLowerCase())
      let score = paletteUsage[item.id] ?? 0

      if (item.id.startsWith('route:')) {
        const routePath = item.id.replace('route:', '')
        score += ROUTE_PRIORITY[routePath] ?? 0
      }

      if (!q) return score

      if (label === q) score += 120
      else if (label.startsWith(q)) score += 90
      else if (label.includes(q)) score += 50

      if (aliases.some((a) => a === q)) score += 100
      else if (aliases.some((a) => a.startsWith(q))) score += 70
      else if (aliases.some((a) => a.includes(q))) score += 40

      if (hint.includes(q)) score += 12
      return score
    }

    const scored = paletteItems
      .map((item) => ({ item, score: scoreItem(item) }))
      .filter((row) => (q ? row.score > 0 : true))
      .sort((a, b) => b.score - a.score)

    return scored.map((row) => row.item)
  }, [paletteItems, paletteQuery, paletteUsage])
  const breadcrumbs = useMemo(() => {
    const section = PRODUCT_SECTIONS.find((x) => x.id === activeSectionId)
    const rows: Array<{ label: string; to?: string }> = []
    const sectionLanding = section
      ? getSectionNav(section.id, uiRole, authContext, {
          authLoading: authContextLoading,
          hasSession,
        })[0]?.path
      : undefined
    if (section) {
      rows.push({
        label: section.label,
        to: sectionLanding,
      })
    }

    if (pathname.startsWith('/alerts/')) {
      rows.push({ label: 'Investigation' })
      const id = pathname.split('/')[2]
      if (id) rows.push({ label: `Alert #${id}` })
      return rows
    }

    if (pathname.startsWith('/incidents/')) {
      rows.push({ label: 'Incidents', to: AML_PATHS.incidents })
      const id = pathname.split('/')[2]
      if (id) rows.push({ label: `Incident #${id}` })
      return rows
    }

    if ((pathname === AML_OPERATIONS_PATH || pathname === AML_PATHS.map) && selectedMmsi) {
      rows.push({ label: pageTitle })
      rows.push({ label: `Vessel ${selectedMmsi}`, to: getMapForMmsiPath(selectedMmsi) })
      return rows
    }

    rows.push({ label: pageTitle })
    return rows
  }, [activeSectionId, authContext, authContextLoading, hasSession, pageTitle, pathname, selectedMmsi, uiRole])

  const openPalette = () => {
    setPaletteUsage(getPaletteUsageMap())
    setPaletteQuery('')
    setPaletteIndex(0)
    setPaletteOpen(true)
    window.requestAnimationFrame(() => {
      paletteInputRef.current?.focus()
    })
  }

  const closePalette = () => {
    setPaletteOpen(false)
  }

  const runPaletteItem = (item: PaletteItem) => {
    trackPaletteUsage(item.id)
    setPaletteUsage(getPaletteUsageMap())
    item.run()
    closePalette()
  }

  useEffect(() => {
    try {
      localStorage.setItem(COMPACT_MODE_STORAGE_KEY, compactMode ? 'true' : 'false')
    } catch {
      // ignore
    }
  }, [compactMode])

  useEffect(() => {
    try {
      localStorage.setItem(HIGH_CONTRAST_STORAGE_KEY, highContrastMode ? 'true' : 'false')
    } catch {
      // ignore
    }
  }, [highContrastMode])

  useEffect(() => {
    if (activeRouteAccess.pending || canAccessActiveRoute) {
      return
    }
    const deniedTitle = activeRoute?.title ?? 'Requested page'
    navigate(getSectionLandingPath('operations', uiRole, authContext, { authLoading: false, hasSession }), {
      replace: true,
      state: {
        accessNotice: activeRouteAccess.reason ?? `${deniedTitle} requires higher privileges for your role.`,
      } satisfies AmlLocationState,
    })
  }, [activeRoute, activeRouteAccess.pending, activeRouteAccess.reason, authContext, canAccessActiveRoute, hasSession, navigate, uiRole])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (editableTarget(event.target)) return

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        openPalette()
        return
      }

      if (event.key === '?') {
        event.preventDefault()
        setShortcutsOpen((prev) => !prev)
        return
      }

      if (event.key === 'Escape') {
        if (paletteOpen) {
          closePalette()
          return
        }
        setShortcutsOpen(false)
        return
      }

      if (event.altKey && !event.metaKey && !event.ctrlKey) {
        if (event.key.toLowerCase() === 'h') {
          event.preventDefault()
          setHighContrastMode((prev) => !prev)
          return
        }
        const target = NAV_SHORTCUTS.find((x) => x.key === `Alt+${event.key}`)
        if (!target) return
        if (!canAccessPath(target.path, uiRole, authContext, { authLoading: authContextLoading, hasSession })) return
        event.preventDefault()
        navigate(target.path)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [authContext, authContextLoading, hasSession, navigate, paletteOpen, uiRole])

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

  const clearanceLabel = authContextLoading && hasSession ? 'Syncing' : authContext?.claims.clearances[0] ?? 'UNCLASSIFIED'
  const releasabilityLabel = authContext?.claims.releasability.slice(0, 2).join(', ') || 'none'
  const streamStatusText = streamAccessPending ? 'Syncing' : streamAccessBlocked ? 'Blocked' : streamConnected ? 'Live' : 'Offline'
  const streamStatusTitle = streamAccessPending
    ? 'Verifying live stream policy.'
    : streamAccessBlocked
      ? streamAccessNotice ?? 'Live stream unavailable for this session.'
      : streamConnected
        ? 'Stream connected'
        : 'Stream disconnected — data may be stale'
  const currentTargetLabel = selectedIncidentId
    ? `Incident #${selectedIncidentId}`
    : selectedAlertId
      ? `Alert #${selectedAlertId}`
      : selectedMmsi
        ? `Vessel ${selectedMmsi}`
        : 'No active mission target'
  const routeStatusLabel = activeRouteAccess.pending
    ? 'Access posture syncing'
    : activeRouteAccess.allowed
      ? 'Route cleared'
      : 'Route constrained'

  return (
    <div
      className={[
        'aml-app',
        compactMode ? 'aml-app--compact' : '',
        highContrastMode ? 'aml-app--high-contrast' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <a href="#main-content" className="aml-shell__skip">
        Skip to main content
      </a>
      <header className="aml-shell__header">
        <div className="aml-shell__brand-block">
          <div className="aml-shell__brand">
            <h1>
              AEGIS<span>AIS</span>
            </h1>
            <span className="aml-shell__brand-sub">Analyst Command Deck</span>
          </div>
          <p className="aml-shell__header-copy">
            Policy-aware maritime surveillance, intelligence routing, and incident coordination.
          </p>
        </div>
        <div className="aml-shell__header-side">
          <AuthBar />
          {replayRunning ? (
            <div className="aml-shell__demo-banner" aria-live="polite">
              Demo run active: {replayProcessed.toLocaleString()} points processed
            </div>
          ) : null}
          <span
            className={`status-indicator ${streamConnected && !streamAccessBlocked && !streamAccessPending ? 'connected' : 'disconnected'}`}
            title={streamStatusTitle}
          >
            {streamStatusText}
          </span>
        </div>
      </header>

      <section className="aml-shell__mission-deck" aria-label="Mission context">
        <article className="aml-shell__mission-card aml-shell__mission-card--hero">
          <span className="aml-shell__card-eyebrow">{PRODUCT_SECTIONS.find((x) => x.id === activeSectionId)?.label}</span>
          <h2>{pageTitle}</h2>
          <p>
            {activeRouteAccess.reason ?? accessNotice ?? 'Operational view aligned to role, clearance, releasability, and active entitlements.'}
          </p>
          <div className="aml-shell__card-tags">
            <span className="aml-shell__mission-chip">NATO AOI</span>
            <span className="aml-shell__mission-chip">{routeStatusLabel}</span>
            <span className="aml-shell__mission-chip">Target: {currentTargetLabel}</span>
          </div>
        </article>

        <article className="aml-shell__mission-card">
          <span className="aml-shell__card-eyebrow">Access Posture</span>
          <dl className="aml-shell__posture-list">
            <div>
              <dt>Role</dt>
              <dd>{uiRole}</dd>
            </div>
            <div>
              <dt>Clearance</dt>
              <dd>{clearanceLabel}</dd>
            </div>
            <div>
              <dt>Release</dt>
              <dd>{releasabilityLabel}</dd>
            </div>
            <div>
              <dt>Licenses</dt>
              <dd>{authContext?.claims.licenses.length ?? 0}</dd>
            </div>
          </dl>
        </article>

        <article className="aml-shell__mission-card">
          <span className="aml-shell__card-eyebrow">System State</span>
          <dl className="aml-shell__posture-list">
            <div>
              <dt>Stream</dt>
              <dd>{streamStatusText}</dd>
            </div>
            <div>
              <dt>Replay</dt>
              <dd>{replayRunning ? 'Running' : 'Idle'}</dd>
            </div>
            <div>
              <dt>Policy</dt>
              <dd>{authContextLoading ? 'Syncing' : authContextError ? 'Degraded' : 'Current'}</dd>
            </div>
            <div>
              <dt>Notice</dt>
              <dd>{streamAccessNotice ?? 'No active stream constraints'}</dd>
            </div>
          </dl>
        </article>

        <article className="aml-shell__mission-card aml-shell__mission-card--actions">
          <span className="aml-shell__card-eyebrow">Deck Controls</span>
          <div className="aml-shell__deck-actions">
            <button
              type="button"
              className="aml-shell__compact-toggle"
              onClick={() => setCompactMode((prev) => !prev)}
              aria-pressed={compactMode}
              title="Toggle compact field mode"
            >
              {compactMode ? 'Compact on' : 'Compact off'}
            </button>
            <button
              type="button"
              className="aml-shell__compact-toggle"
              onClick={() => setHighContrastMode((prev) => !prev)}
              aria-pressed={highContrastMode}
              title="Toggle high contrast mode"
            >
              {highContrastMode ? 'High contrast' : 'Normal contrast'}
            </button>
            <button
              type="button"
              className="aml-shell__compact-toggle"
              onClick={() => setShortcutsOpen((prev) => !prev)}
              aria-pressed={shortcutsOpen}
              title="Show keyboard shortcuts"
            >
              Shortcuts
            </button>
            <button
              type="button"
              className="aml-shell__compact-toggle"
              onClick={openPalette}
              aria-pressed={paletteOpen}
              title="Open command palette"
            >
              Command
            </button>
          </div>
          {authContextError ? <p className="aml-shell__mission-note">{authContextError}</p> : null}
        </article>
      </section>

      <div className="aml-shell__workspace-shell">
        <nav className="aml-shell__rail" role="navigation" aria-label="Main navigation">
          <div className="aml-shell__rail-section">
            <span className="aml-shell__rail-title">Product sections</span>
            <div className="aml-shell__top-nav" role="navigation" aria-label="Product sections">
              {visibleSections.map((section) => {
                const landingPath = getSectionLandingPath(section.id, uiRole, authContext, {
                  authLoading: authContextLoading,
                  hasSession,
                })
                return (
                  <NavLink
                    key={section.id}
                    to={landingPath}
                    className={topNavLinkClass}
                  >
                    {section.label}
                  </NavLink>
                )
              })}
            </div>
          </div>

          <div className="aml-shell__rail-section">
            <span className="aml-shell__rail-title">{PRODUCT_SECTIONS.find((x) => x.id === activeSectionId)?.label}</span>
            <div className="aml-shell__nav-group" role="group" aria-label="Section pages">
              {sectionNav.map((route) => (
                <NavLink key={route.path} to={route.path} className={navLinkClass}>
                  {route.navLabel}
                </NavLink>
              ))}
            </div>
          </div>

          <div className="aml-shell__rail-section aml-shell__rail-section--support">
            <span className="aml-shell__rail-title">Deep links</span>
            <div className="aml-shell__footer-shortcuts-list">
              <div><span>Triage</span><code>/triage</code></div>
              <div><span>Investigation</span><code>/alerts/:id</code></div>
              <div><span>Map</span><code>/map?mmsi=</code></div>
              <div><span>Incident</span><code>/incidents/:id</code></div>
            </div>
            <button type="button" className="aml-shell__footer-legacy" onClick={() => switchToLegacyUi()}>
              Classic UI
            </button>
          </div>
        </nav>

        <section className="aml-shell__workspace">
          <div className="aml-shell__workspace-bar">
            <nav className="aml-shell__breadcrumbs" aria-label="Breadcrumb">
              <ol>
                {breadcrumbs.map((crumb, idx) => (
                  <li key={`${crumb.label}-${idx}`}>
                    {crumb.to && idx < breadcrumbs.length - 1 ? <NavLink to={crumb.to}>{crumb.label}</NavLink> : <span>{crumb.label}</span>}
                  </li>
                ))}
              </ol>
            </nav>
            <div className="aml-shell__workspace-notice">
              <span>{routeStatusLabel}</span>
              <strong>{currentTargetLabel}</strong>
            </div>
          </div>

          <main id="main-content" className="aml-shell__main" tabIndex={-1}>
            <Outlet context={{ lastMessage, authContext } satisfies AmlOutletContext} />
          </main>

          {shortcutsOpen ? (
            <section className="aml-shell__shortcuts" role="dialog" aria-label="Keyboard shortcuts">
              <h2>Keyboard shortcuts</h2>
              <ul>
                {NAV_SHORTCUTS.filter((x) => canAccessPath(x.path, uiRole, authContext, { authLoading: authContextLoading, hasSession })).map((x) => (
                  <li key={x.key}>
                    <span>{x.label}</span>
                    <code>{x.key}</code>
                  </li>
                ))}
                <li>
                  <span>Toggle high contrast</span>
                  <code>Alt+H</code>
                </li>
                <li>
                  <span>Toggle shortcuts help</span>
                  <code>?</code>
                </li>
              </ul>
            </section>
          ) : null}
        </section>
      </div>

      {paletteOpen ? (
        <div className="aml-shell__palette-backdrop" onClick={closePalette} role="presentation">
          <section
            className="aml-shell__palette"
            role="dialog"
            aria-label="Command palette"
            onClick={(e) => e.stopPropagation()}
          >
            <form
              onSubmit={(e) => {
                e.preventDefault()
                const target = paletteResults[paletteIndex]
                if (!target) return
                runPaletteItem(target)
              }}
            >
              <input
                ref={paletteInputRef}
                className="aml-shell__palette-input"
                value={paletteQuery}
                onChange={(e) => {
                  setPaletteQuery(e.target.value)
                  setPaletteIndex(0)
                }}
                onKeyDown={(e) => {
                  if (e.key === 'ArrowDown') {
                    e.preventDefault()
                    setPaletteIndex((idx) => Math.min(idx + 1, Math.max(0, paletteResults.length - 1)))
                  }
                  if (e.key === 'ArrowUp') {
                    e.preventDefault()
                    setPaletteIndex((idx) => Math.max(0, idx - 1))
                  }
                }}
                placeholder="Type a command or page..."
              />
            </form>
            <ul className="aml-shell__palette-results">
              {paletteResults.length === 0 ? (
                <li className="aml-shell__palette-empty">No matches</li>
              ) : (
                paletteResults.map((item, idx) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      className={idx === paletteIndex ? 'is-active' : undefined}
                      onClick={() => {
                        runPaletteItem(item)
                      }}
                    >
                      <span>{item.label}</span>
                      <small>{item.hint}</small>
                    </button>
                  </li>
                ))
              )}
            </ul>
            <p className="aml-shell__palette-help">Use Ctrl/Cmd+K to open, arrows to navigate, Enter to run.</p>
          </section>
        </div>
      ) : null}

    </div>
  )
}
