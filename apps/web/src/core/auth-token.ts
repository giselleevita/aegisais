/** localStorage key for JWT from POST /v1/auth/login */
const STORAGE_KEY = 'aegisais_access_token'

export const AUTH_CHANGED_EVENT = 'aegisais-auth-changed'

export function getAccessToken(): string | null {
    return localStorage.getItem(STORAGE_KEY)
}

export function setAccessToken(token: string | null): void {
    if (token) {
        localStorage.setItem(STORAGE_KEY, token)
    } else {
        localStorage.removeItem(STORAGE_KEY)
    }
    window.dispatchEvent(new CustomEvent(AUTH_CHANGED_EVENT))
}

export function subscribeAuth(onChange: () => void): () => void {
    const handler = () => onChange()
    window.addEventListener(AUTH_CHANGED_EVENT, handler)
    return () => window.removeEventListener(AUTH_CHANGED_EVENT, handler)
}
