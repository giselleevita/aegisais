import { useState, useEffect } from 'react'
import { apiClient } from '@/core/api-client'
import './SanctionsPage.css'

interface SyncResult {
    status: string
    source: string
    mmsi_count: number
    imo_count: number
    name_count: number
}

export default function SanctionsPage() {
    const [syncing, setSyncing] = useState(false)
    const [lastSync, setLastSync] = useState<SyncResult | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [watchlistCount, setWatchlistCount] = useState<number | null>(null)

    useEffect(() => {
        apiClient
            .getWatchlist()
            .then((entries) => setWatchlistCount(entries.length))
            .catch(() => setWatchlistCount(null))
    }, [lastSync])

    const handleSync = async () => {
        setSyncing(true)
        setError(null)
        try {
            const result = await apiClient.syncSanctionsWatchlist()
            setLastSync(result)
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Sync failed')
        } finally {
            setSyncing(false)
        }
    }

    return (
        <div className="sanctions-page">
            <header className="sanctions-page__header">
                <h2>Sanctions &amp; Watchlist</h2>
                <p className="sanctions-page__subtitle">
                    Download and merge official OFAC SDN and EU consolidated sanctions lists
                    into the local vessel watchlist.
                </p>
            </header>

            <section className="sanctions-page__status">
                <h3>Current Status</h3>
                <div className="sanctions-page__stat-row">
                    <span className="sanctions-page__stat-label">Local watchlist entries:</span>
                    <span className="sanctions-page__stat-value">
                        {watchlistCount !== null ? watchlistCount : '—'}
                    </span>
                </div>
            </section>

            <section className="sanctions-page__actions">
                <h3>Sync Official Lists</h3>
                <p>
                    Downloads sanctioned vessel entries from:
                </p>
                <ul className="sanctions-page__source-list">
                    <li>
                        <strong>OFAC SDN</strong> — U.S. Treasury Specially Designated Nationals
                    </li>
                    <li>
                        <strong>EU Consolidated</strong> — European Union sanctions list
                    </li>
                </ul>
                <button
                    className="sanctions-page__sync-btn"
                    onClick={handleSync}
                    disabled={syncing}
                >
                    {syncing ? 'Syncing…' : 'Sync Now'}
                </button>

                {error && (
                    <div className="sanctions-page__error" role="alert">
                        {error}
                    </div>
                )}

                {lastSync && (
                    <div className="sanctions-page__result">
                        <h4>Sync Complete</h4>
                        <table className="sanctions-page__result-table">
                            <tbody>
                                <tr>
                                    <td>Source</td>
                                    <td>{lastSync.source}</td>
                                </tr>
                                <tr>
                                    <td>MMSI entries</td>
                                    <td>{lastSync.mmsi_count}</td>
                                </tr>
                                <tr>
                                    <td>IMO entries</td>
                                    <td>{lastSync.imo_count}</td>
                                </tr>
                                <tr>
                                    <td>Named vessels</td>
                                    <td><strong>{lastSync.name_count}</strong></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                )}
            </section>

            <section className="sanctions-page__info">
                <h3>How It Works</h3>
                <ol>
                    <li>Downloads the latest OFAC SDN CSV from treasury.gov</li>
                    <li>Downloads the EU consolidated sanctions CSV</li>
                    <li>Filters for vessel-related entries (MMSI, IMO, vessel names)</li>
                    <li>Merges and deduplicates against the existing local watchlist</li>
                    <li>Saves to the local JSON watchlist and reloads the sanctions service</li>
                </ol>
            </section>
        </div>
    )
}
