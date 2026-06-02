import { AML_OPERATIONS_PATH, AML_PATHS } from '@/aml/amlRoutes'
import {
  evaluatePolicyRequirements,
  type PolicyDecision,
} from '@/core/auth-context'
import type { UiRole } from '@/core/uiRole'
import { roleAtLeast } from '@/core/uiRole'
import type { AuthContextResponse, ClassificationLevel } from '@/shared/types/common'

export type ProductSectionId = 'operations' | 'intelligence' | 'governance'

export type ProductSection = {
  id: ProductSectionId
  label: string
}

export type ProductRouteMeta = {
  path: string
  title: string
  sectionId: ProductSectionId
  navLabel?: string
  minRole?: UiRole
  minClearance?: ClassificationLevel
  requiredReleasability?: string[]
  requiredLicenses?: string[]
  matches: (pathname: string) => boolean
}

export const PRODUCT_SECTIONS: ProductSection[] = [
  { id: 'operations', label: 'Operations' },
  { id: 'intelligence', label: 'Intelligence' },
  { id: 'governance', label: 'Governance' },
]

export const AML_ROUTE_META: ProductRouteMeta[] = [
  {
    path: AML_PATHS.home,
    title: 'Triage',
    sectionId: 'operations',
    navLabel: 'Triage',
    matches: (pathname) => pathname === AML_OPERATIONS_PATH || pathname === '/',
  },
  {
    path: AML_PATHS.map,
    title: 'Map',
    sectionId: 'operations',
    navLabel: 'Map',
    matches: (pathname) => pathname === AML_PATHS.map,
  },
  {
    path: AML_PATHS.incidents,
    title: 'Incidents',
    sectionId: 'operations',
    navLabel: 'Incidents',
    minRole: 'analyst',
    matches: (pathname) => pathname === AML_PATHS.incidents || pathname.startsWith(`${AML_PATHS.incidents}/`),
  },
  {
    path: AML_PATHS.watchlist,
    title: 'Watchlist',
    sectionId: 'operations',
    navLabel: 'Watchlist',
    minRole: 'analyst',
    matches: (pathname) => pathname === AML_PATHS.watchlist,
  },
  {
    path: AML_PATHS.sanctions,
    title: 'Sanctions',
    sectionId: 'operations',
    navLabel: 'Sanctions',
    minRole: 'supervisor',
    matches: (pathname) => pathname === AML_PATHS.sanctions,
  },
  {
    path: AML_PATHS.alertDetailPattern,
    title: 'Investigation',
    sectionId: 'operations',
    matches: (pathname) => pathname.startsWith('/alerts/'),
  },
  {
    path: AML_PATHS.itdae,
    title: 'ITDAE',
    sectionId: 'intelligence',
    navLabel: 'ITDAE',
    matches: (pathname) => pathname === AML_PATHS.itdae,
  },
  {
    path: AML_PATHS.onboarding,
    title: 'Onboarding',
    sectionId: 'intelligence',
    navLabel: 'Onboarding',
    matches: (pathname) => pathname === AML_PATHS.onboarding,
  },
  {
    path: AML_PATHS.audit,
    title: 'Audit',
    sectionId: 'governance',
    navLabel: 'Audit',
    minRole: 'admin',
    matches: (pathname) => pathname === AML_PATHS.audit,
  },
  {
    path: AML_PATHS.admin,
    title: 'Admin',
    sectionId: 'governance',
    navLabel: 'Admin',
    minRole: 'admin',
    matches: (pathname) => pathname === AML_PATHS.admin,
  },
]

export function getActiveRouteMeta(pathname: string): ProductRouteMeta | null {
  return AML_ROUTE_META.find((route) => route.matches(pathname)) ?? null
}

export function getRouteAccessDecision(
  route: ProductRouteMeta,
  role: UiRole,
  authContext: AuthContextResponse | null,
  options: { authLoading?: boolean; hasSession?: boolean } = {}
): PolicyDecision {
  if (!roleAtLeast(role, route.minRole ?? 'guest')) {
    return {
      allowed: false,
      pending: false,
      reason: `${route.title} requires ${route.minRole ?? 'guest'} role.`,
    }
  }

  return evaluatePolicyRequirements(
    authContext,
    {
      minClearance: route.minClearance,
      requiredReleasability: route.requiredReleasability,
      requiredLicenses: route.requiredLicenses,
    },
    {
      loading: options.authLoading,
      hasSession: options.hasSession,
      fallbackLabel: route.title,
    }
  )
}

export function getSectionNav(
  sectionId: ProductSectionId,
  role: UiRole,
  authContext: AuthContextResponse | null,
  options: { authLoading?: boolean; hasSession?: boolean } = {}
): ProductRouteMeta[] {
  return AML_ROUTE_META.filter(
    (route) =>
      route.sectionId === sectionId &&
      route.navLabel &&
      getRouteAccessDecision(route, role, authContext, options).allowed
  )
}

export function getSectionLandingPath(
  sectionId: ProductSectionId,
  role: UiRole,
  authContext: AuthContextResponse | null,
  options: { authLoading?: boolean; hasSession?: boolean } = {}
): string {
  const first = getSectionNav(sectionId, role, authContext, options)[0]
  return first?.path ?? AML_OPERATIONS_PATH
}

export function canAccessRoute(
  route: ProductRouteMeta,
  role: UiRole,
  authContext: AuthContextResponse | null,
  options: { authLoading?: boolean; hasSession?: boolean } = {}
): boolean {
  return getRouteAccessDecision(route, role, authContext, options).allowed
}

export function canAccessPath(
  pathname: string,
  role: UiRole,
  authContext: AuthContextResponse | null,
  options: { authLoading?: boolean; hasSession?: boolean } = {}
): boolean {
  const route = AML_ROUTE_META.find((row) => row.path === pathname)
  if (!route) return true
  return canAccessRoute(route, role, authContext, options)
}

export function canAccessMatchedPath(
  pathname: string,
  role: UiRole,
  authContext: AuthContextResponse | null,
  options: { authLoading?: boolean; hasSession?: boolean } = {}
): boolean {
  const route = getActiveRouteMeta(pathname)
  if (!route) return true
  const decision = getRouteAccessDecision(route, role, authContext, options)
  return decision.allowed || decision.pending
}
