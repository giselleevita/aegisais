import { ApiClientError } from '@/core/api-client'

type ApiFailureCopy = {
  fallback: string
  unauthorized?: string
  forbidden?: string
  offline?: string
}

function isNetworkFailureMessage(message: string): boolean {
  return [
    'failed to fetch',
    'load failed',
    'networkerror',
    'network request failed',
    'connection refused',
  ].some((hint) => message.includes(hint))
}

export function describeApiFailure(error: unknown, copy: ApiFailureCopy): string {
  const unauthorized = copy.unauthorized ?? 'Sign in to continue.'
  const forbidden = copy.forbidden ?? copy.fallback
  const offline = copy.offline ?? 'Command link to the API is unavailable. Restore the backend and try again.'

  if (error instanceof ApiClientError) {
    if (error.status === 401) return unauthorized
    if (error.status === 403) return forbidden
    return error.message || copy.fallback
  }

  if (error instanceof TypeError && isNetworkFailureMessage(error.message.toLowerCase())) {
    return offline
  }

  if (error instanceof Error) {
    const message = error.message.trim()
    const normalized = message.toLowerCase()

    if (
      normalized.includes('401') ||
      normalized.includes('not authenticated') ||
      normalized.includes('unauthorized')
    ) {
      return unauthorized
    }

    if (
      normalized.includes('403') ||
      normalized.includes('forbidden') ||
      normalized.includes('access denied')
    ) {
      return forbidden
    }

    if (isNetworkFailureMessage(normalized)) {
      return offline
    }

    return message || copy.fallback
  }

  return copy.fallback
}