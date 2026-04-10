import { useCallback, useEffect, useState } from 'react'
import { getAccessToken, subscribeAuth } from '@/core/auth-token'
import { apiClient } from '@/core/api-client'
import type { AuthContextResponse, ClassificationLevel } from '@/shared/types/common'

export type PolicyRequirements = {
  minClearance?: ClassificationLevel
  requiredReleasability?: string[]
  requiredLicenses?: string[]
}

export type PolicyDecision = {
  allowed: boolean
  pending: boolean
  reason: string | null
}

type AuthContextState = {
  context: AuthContextResponse | null
  loading: boolean
  error: string | null
}

const AUTH_CONTEXT_TTL_MS = 60_000

const CLASSIFICATION_ORDER: Record<ClassificationLevel, number> = {
  UNCLASSIFIED: 0,
  RESTRICTED: 1,
  CONFIDENTIAL: 2,
  SECRET: 3,
  TOP_SECRET: 4,
}

let cachedContext: AuthContextResponse | null = null
let cachedFetchedAt = 0
let inFlightRequest: Promise<AuthContextResponse | null> | null = null

function hasFreshCache(): boolean {
  return cachedContext !== null && Date.now() - cachedFetchedAt < AUTH_CONTEXT_TTL_MS
}

function clearCachedContext(): void {
  cachedContext = null
  cachedFetchedAt = 0
  inFlightRequest = null
}

function getHighestClearance(context: AuthContextResponse | null): ClassificationLevel {
  const clearances = context?.claims.clearances ?? []
  return clearances[0] ?? 'UNCLASSIFIED'
}

export function hasRequiredClearance(
  context: AuthContextResponse | null,
  minimum: ClassificationLevel | undefined
): boolean {
  if (!minimum) return true
  return CLASSIFICATION_ORDER[getHighestClearance(context)] >= CLASSIFICATION_ORDER[minimum]
}

export function hasRequiredReleasability(
  context: AuthContextResponse | null,
  tags: string[] | undefined
): boolean {
  if (!tags || tags.length === 0) return true
  const available = new Set((context?.claims.releasability ?? []).map((tag) => tag.toUpperCase()))
  return tags.every((tag) => available.has(tag.toUpperCase()))
}

export function hasRequiredLicenses(
  context: AuthContextResponse | null,
  licenses: string[] | undefined
): boolean {
  if (!licenses || licenses.length === 0) return true
  const available = new Set(context?.claims.licenses ?? [])
  return licenses.every((license) => available.has(license))
}

export function evaluatePolicyRequirements(
  context: AuthContextResponse | null,
  requirements: PolicyRequirements,
  options: {
    loading?: boolean
    hasSession?: boolean
    fallbackLabel?: string
  } = {}
): PolicyDecision {
  const { loading = false, hasSession = false, fallbackLabel = 'this workspace' } = options

  if (!requirements.minClearance && !requirements.requiredReleasability?.length && !requirements.requiredLicenses?.length) {
    return { allowed: true, pending: false, reason: null }
  }

  if (loading) {
    return { allowed: false, pending: true, reason: null }
  }

  if (!context) {
    return {
      allowed: false,
      pending: false,
      reason: hasSession
        ? `Cannot verify access to ${fallbackLabel} until your policy context loads.`
        : `Sign in to access ${fallbackLabel}.`,
    }
  }

  if (!hasRequiredClearance(context, requirements.minClearance)) {
    return {
      allowed: false,
      pending: false,
      reason: `${fallbackLabel} requires ${requirements.minClearance} clearance.`,
    }
  }

  if (!hasRequiredReleasability(context, requirements.requiredReleasability)) {
    const needed = requirements.requiredReleasability?.join(', ')
    return {
      allowed: false,
      pending: false,
      reason: `${fallbackLabel} requires ${needed} releasability.`,
    }
  }

  if (!hasRequiredLicenses(context, requirements.requiredLicenses)) {
    const needed = requirements.requiredLicenses?.join(', ')
    return {
      allowed: false,
      pending: false,
      reason: `${fallbackLabel} requires ${needed} entitlement.`,
    }
  }

  return { allowed: true, pending: false, reason: null }
}

export async function loadAuthoritativeAuthContext(force = false): Promise<AuthContextResponse | null> {
  if (!getAccessToken()) {
    clearCachedContext()
    return null
  }

  if (!force && hasFreshCache()) {
    return cachedContext
  }

  if (inFlightRequest) {
    return inFlightRequest
  }

  inFlightRequest = apiClient
    .getAuthContext()
    .then((context) => {
      cachedContext = context
      cachedFetchedAt = Date.now()
      return context
    })
    .finally(() => {
      inFlightRequest = null
    })

  return inFlightRequest
}

export function useAuthoritativeAuthContext(): AuthContextState & { refresh: () => Promise<void> } {
  const [state, setState] = useState<AuthContextState>({
    context: hasFreshCache() ? cachedContext : null,
    loading: !!getAccessToken() && !hasFreshCache(),
    error: null,
  })

  const refresh = useCallback(async () => {
    if (!getAccessToken()) {
      clearCachedContext()
      setState({ context: null, loading: false, error: null })
      return
    }

    setState((prev) => ({ ...prev, loading: true, error: null }))

    try {
      const context = await loadAuthoritativeAuthContext(true)
      setState({ context, loading: false, error: null })
    } catch (error) {
      setState({
        context: null,
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to load access context.',
      })
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    if (state.loading) {
      void loadAuthoritativeAuthContext()
        .then((context) => {
          if (cancelled) return
          setState({ context, loading: false, error: null })
        })
        .catch((error) => {
          if (cancelled) return
          setState({
            context: null,
            loading: false,
            error: error instanceof Error ? error.message : 'Failed to load access context.',
          })
        })
    }

    const unsubscribe = subscribeAuth(() => {
      clearCachedContext()
      void refresh()
    })

    return () => {
      cancelled = true
      unsubscribe()
    }
  }, [refresh, state.loading])

  return { ...state, refresh }
}