import { getAccessToken } from '@/core/auth-token'
import type { AuthContextResponse } from '@/shared/types/common'

const ROLE_STORAGE_KEY = 'aegisais_ui_role'

export type UiRole = 'guest' | 'analyst' | 'supervisor' | 'admin'

const ROLE_WEIGHT: Record<UiRole, number> = {
  guest: 0,
  analyst: 1,
  supervisor: 2,
  admin: 3,
}

function normalizeRole(value: string | null | undefined): UiRole | null {
  if (!value) return null
  const v = value.toLowerCase().trim()
  if (v === 'guest' || v === 'analyst' || v === 'supervisor' || v === 'admin') {
    return v
  }
  return null
}

function normalizeRoleAlias(value: string): UiRole | null {
  const v = value.toLowerCase().trim()
  if (v === 'guest' || v === 'anonymous' || v === 'unauthenticated') return 'guest'
  if (v === 'analyst' || v === 'operator' || v === 'viewer' || v === 'user') return 'analyst'
  if (v === 'supervisor' || v === 'lead' || v === 'manager') return 'supervisor'
  if (v === 'admin' || v === 'administrator' || v === 'owner') return 'admin'
  return null
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.')
    if (parts.length < 2) return null
    const payload = parts[1]
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4)
    const json = atob(padded)
    return JSON.parse(json) as Record<string, unknown>
  } catch {
    return null
  }
}

function rolesFromTokenClaims(payload: Record<string, unknown>): string[] {
  const out: string[] = []
  const pushValue = (v: unknown) => {
    if (typeof v === 'string' && v.trim()) out.push(v)
  }
  const pushList = (v: unknown) => {
    if (Array.isArray(v)) {
      v.forEach(pushValue)
    }
  }

  pushValue(payload.role)
  pushList(payload.roles)
  pushList(payload.groups)
  pushList(payload.permissions)
  if (typeof payload.scope === 'string') {
    payload.scope
      .split(/\s+/)
      .map((x) => x.trim())
      .filter(Boolean)
      .forEach((x) => out.push(x))
  }

  const realmAccess = payload.realm_access
  if (realmAccess && typeof realmAccess === 'object') {
    const maybeRoles = (realmAccess as { roles?: unknown }).roles
    pushList(maybeRoles)
  }
  return out
}

function roleFromTokenClaims(token: string | null): UiRole | null {
  if (!token) return null
  const payload = decodeJwtPayload(token)
  if (!payload) return null
  const claims = rolesFromTokenClaims(payload)
  if (claims.length === 0) return null

  const mapped = claims
    .map((claim) => normalizeRoleAlias(claim))
    .filter((r): r is UiRole => !!r)

  if (mapped.includes('admin')) return 'admin'
  if (mapped.includes('supervisor')) return 'supervisor'
  if (mapped.includes('analyst')) return 'analyst'

  // Fallbacks for scope/permission-style claims that are not literal roles.
  const lowered = claims.map((c) => c.toLowerCase())
  if (lowered.some((c) => c.includes('admin'))) return 'admin'
  if (lowered.some((c) => c.includes('incidents:write') || c.includes('audit:read') || c.includes('manager'))) {
    return 'supervisor'
  }
  return 'analyst'
}

function inferRoleFromSession(): UiRole {
  const token = getAccessToken()
  if (!token) return 'guest'
  return roleFromTokenClaims(token) ?? 'analyst'
}

function roleFromAuthContext(authContext: AuthContextResponse | null | undefined): UiRole | null {
  return normalizeRole(authContext?.claims.role ?? authContext?.viewer.role)
}

export function getUiRole(authContext?: AuthContextResponse | null): UiRole {
  const envRole = normalizeRole(import.meta.env.VITE_UI_ROLE)
  if (envRole) return envRole
  const authoritativeRole = roleFromAuthContext(authContext)
  if (authoritativeRole) return authoritativeRole
  const storedRole = normalizeRole(localStorage.getItem(ROLE_STORAGE_KEY))
  if (storedRole) return storedRole
  return inferRoleFromSession()
}

export function setUiRole(role: UiRole | null): void {
  if (!role) {
    localStorage.removeItem(ROLE_STORAGE_KEY)
    return
  }
  localStorage.setItem(ROLE_STORAGE_KEY, role)
}

export function roleAtLeast(current: UiRole, required: UiRole): boolean {
  return ROLE_WEIGHT[current] >= ROLE_WEIGHT[required]
}
