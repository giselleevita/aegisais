import { useEffect, useState, type FormEvent } from 'react'
import { apiClient } from '@/core/api-client'
import { getAccessToken, subscribeAuth } from '@/core/auth-token'

/**
 * Minimal login so the SPA can attach Bearer tokens to protected API routes.
 * Token is stored in localStorage (see core/auth-token.ts).
 */
export default function AuthBar() {
    const [authed, setAuthed] = useState(() => !!getAccessToken())
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [busy, setBusy] = useState(false)

    useEffect(() => subscribeAuth(() => setAuthed(!!getAccessToken())), [])

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
        return (
            <div className="auth-bar">
                <span className="auth-bar-label">Signed in</span>
                <button type="button" onClick={() => apiClient.logout()}>
                    Log out
                </button>
            </div>
        )
    }

    return (
        <form className="auth-bar" onSubmit={onSubmit} aria-label="Sign in">
            <input
                name="username"
                autoComplete="username"
                placeholder="User"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={busy}
            />
            <input
                name="password"
                type="password"
                autoComplete="current-password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={busy}
            />
            <button type="submit" disabled={busy || !username || !password}>
                {busy ? '…' : 'Sign in'}
            </button>
            {error ? <span className="auth-bar-error">{error}</span> : null}
        </form>
    )
}
