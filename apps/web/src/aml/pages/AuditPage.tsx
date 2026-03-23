import { useEffect, useState } from 'react'
import { apiClient } from '@/core/api-client'
import type { AuditLogEntry } from '@/shared/types/common'

const ACTION_PRESETS = [
  '',
  'incident.update',
  'alert.export.csv',
  'alert.export.json',
  'alert.status.update',
]

export default function AuditPage() {
  const [rows, setRows] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [action, setAction] = useState('')
  const [exporting, setExporting] = useState(false)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiClient.getAuditLogs({ action: action || undefined, limit: 200 })
      setRows(data)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load audit logs'
      if (
        msg.includes('403') ||
        msg.toLowerCase().includes('admin') ||
        msg.toLowerCase().includes('not authenticated') ||
        msg.toLowerCase().includes('unauthorized')
      ) {
        setError('Sign in as admin to view audit logs.')
      } else {
        setError(msg)
      }
      setRows([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [action])

  const handleExport = async () => {
    setExporting(true)
    try {
      await apiClient.downloadAuditLogsCsv({
        action: action || undefined,
        max_rows: 10000,
      })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to export audit logs'
      setError(msg)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="aml-page-pad aml-audit">
      <div className="aml-incidents__header">
        <h2 className="aml-page-title">Audit</h2>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <select value={action} onChange={(e) => setAction(e.target.value)} aria-label="Filter audit action">
            {ACTION_PRESETS.map((preset) => (
              <option key={preset || 'all'} value={preset}>
                {preset || 'All actions'}
              </option>
            ))}
          </select>
          <button type="button" onClick={() => void handleExport()} disabled={exporting}>
            {exporting ? 'Exporting…' : 'Export CSV'}
          </button>
        </div>
      </div>

      {loading ? <p>Loading audit logs...</p> : null}
      {error ? <p>{error}</p> : null}

      {!loading && !error ? (
        <div className="aml-audit__table-wrap">
          <table className="aml-audit__table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Action</th>
                <th>User</th>
                <th>Resource</th>
                <th>Summary</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>{new Date(row.timestamp).toLocaleString()}</td>
                  <td>{row.action}</td>
                  <td>{row.user_id || 'system'}</td>
                  <td>
                    {row.resource_type || '-'}
                    {row.resource_id ? `:${row.resource_id}` : ''}
                  </td>
                  <td>{row.change_summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 ? <p>No audit rows for current filter.</p> : null}
        </div>
      ) : null}
    </div>
  )
}

