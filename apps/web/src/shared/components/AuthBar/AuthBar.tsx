import { useEffect, useState, type FormEvent } from 'react'
import { apiClient } from '@/core/api-client'
import { getAccessToken, getSessionUsername, subscribeAuth } from '@/core/auth-token'

/**
 * Minimal login so the SPA can attach Bearer tokens to protected API routes.
 * Token is stored in localStorage (see core/auth-token.ts).
 */
export default function AuthBar() {
    const [authed, setAuthed] = useState(() => !!getAccessToken())
    const [sessionName, setSessionName] = useState<string | null>(() => getSessionUsername())
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [busy, setBusy] = useState(false)

    useEffect(() => {
        const sync = () => {
            setAuthed(!!getAccessToken())
            setSessionName(getSessionUsername())
        }
        sync()
        return subscribeAuth(sync)
    }, [])

    const onSubmit = async (e: FormEvent) => {
        e.preventDefault()
        setError('')
        setBusy(true)
        try {
            await apiClient.login(username, password)
            setPassword('')
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Login failed')
        } finally {
            setBusy(false)
        }
    }

    if (authed) {
        const label =
            sessionName && sessionName.length > 0
                ? `Signed in as ${sessionName}`
                : 'Signed in'
        return (
            <div className="auth-bar auth-bar--session">
                <span className="auth-bar-label" title={sessionName ?? undefined}>
                    {label}
                </span>
                <button type="button" onClick={() => apiClient.logout()}>
                    Log out
                </button>
            </div>
        )
    }

    return (
        <form className="auth-bar" onSubmit={onSubmit} aria-label="Sign in">
            <label className="sr-only" htmlFor="auth-username">Username</label>
            <input
                id="auth-username"
                name="username"
                autoComplete="username"
                placeholder="User"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={busy}
            />
            <label className="sr-only" htmlFor="auth-password">Password</label>
            <input
                id="auth-password"
                name="password"
                type="password"
                autoComplete="current-password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={busy}
            />
            <button type="submit" disabled={busy || !username || !password}>
                {busy ? 'Signing in…' : 'Sign in'}
            </button>
            {error ? (
                <span className="auth-bar-error" role="alert">
                    {error}
                </span>
            ) : null}
        </form>
    )
}
