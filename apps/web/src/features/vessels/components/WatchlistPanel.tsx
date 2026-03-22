import { useCallback, useEffect, useState } from 'react'
import { apiClient } from '@/core/api-client'
import { getAccessToken } from '@/core/auth-token'
import type { WatchlistEntry } from '@/shared/types/common'
import './WatchlistPanel.css'

export default function WatchlistPanel() {
    const [entries, setEntries] = useState<WatchlistEntry[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [mmsiInput, setMmsiInput] = useState('')
    const [labelInput, setLabelInput] = useState('')
    const [priority, setPriority] = useState<'low' | 'medium' | 'high'>('medium')

    const load = useCallback(async () => {
        if (!getAccessToken()) {
            setEntries([])
            setLoading(false)
            setError('Sign in to view the watchlist.')
            return
        }
        try {
            setLoading(true)
            setError(null)
            const data = await apiClient.getWatchlist()
            setEntries(data)
        } catch (e) {
            const msg = e instanceof Error ? e.message : 'Failed to load watchlist'
            setError(msg)
            setEntries([])
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        void load()
    }, [load])

    const handleAdd = async () => {
        const m = mmsiInput.trim()
        if (!/^\d{9}$/.test(m)) {
            alert('MMSI must be exactly 9 digits.')
            return
        }
        try {
            await apiClient.addWatchlistEntry({ mmsi: m, label: labelInput.trim(), priority })
            setMmsiInput('')
            setLabelInput('')
            await load()
        } catch (e) {
            alert(e instanceof Error ? e.message : 'Could not add to watchlist')
        }
    }

    const handleRemove = async (mmsi: string) => {
        if (!confirm(`Remove MMSI ${mmsi} from the watchlist?`)) return
        try {
            await apiClient.removeWatchlistEntry(mmsi)
            await load()
        } catch (e) {
            alert(e instanceof Error ? e.message : 'Could not remove')
        }
    }

    return (
        <div className="watchlist-panel">
            <div className="watchlist-header">
                <h2>Watchlist</h2>
                <p className="watchlist-subtitle">
                    Analyst-prioritised MMSIs. Alerts for these vessels are ordered first and tagged with
                    watchlist priority. Map markers use a purple dot for watchlisted vessels.
                </p>
            </div>

            {!getAccessToken() ? (
                <div className="watchlist-empty">Sign in to manage the watchlist.</div>
            ) : (
                <>
                    <div className="watchlist-add">
                        <input
                            type="text"
                            inputMode="numeric"
                            placeholder="MMSI (9 digits)"
                            value={mmsiInput}
                            maxLength={9}
                            onChange={(e) => setMmsiInput(e.target.value.replace(/\D/g, ''))}
                            className="watchlist-input"
                        />
                        <input
                            type="text"
                            placeholder="Label (optional)"
                            value={labelInput}
                            onChange={(e) => setLabelInput(e.target.value)}
                            className="watchlist-input"
                        />
                        <select
                            value={priority}
                            onChange={(e) => setPriority(e.target.value as 'low' | 'medium' | 'high')}
                            className="watchlist-select"
                        >
                            <option value="low">Low</option>
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                        </select>
                        <button type="button" onClick={() => void handleAdd()} className="watchlist-btn-add">
                            Add
                        </button>
                        <button type="button" onClick={() => void load()} className="watchlist-btn-refresh">
                            Refresh
                        </button>
                    </div>

                    {loading ? (
                        <div className="watchlist-loading">Loading…</div>
                    ) : error ? (
                        <div className="watchlist-error">{error}</div>
                    ) : entries.length === 0 ? (
                        <div className="watchlist-empty">No vessels on the watchlist.</div>
                    ) : (
                        <table className="watchlist-table">
                            <thead>
                                <tr>
                                    <th>MMSI</th>
                                    <th>Label</th>
                                    <th>Priority</th>
                                    <th />
                                </tr>
                            </thead>
                            <tbody>
                                {entries.map((row) => (
                                    <tr key={row.id}>
                                        <td>{row.mmsi}</td>
                                        <td>{row.label || '—'}</td>
                                        <td>
                                            <span className={`watchlist-prio watchlist-prio-${row.priority}`}>
                                                {row.priority}
                                            </span>
                                        </td>
                                        <td>
                                            <button
                                                type="button"
                                                className="watchlist-btn-remove"
                                                onClick={() => void handleRemove(row.mmsi)}
                                            >
                                                Remove
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </>
            )}
        </div>
    )
}
