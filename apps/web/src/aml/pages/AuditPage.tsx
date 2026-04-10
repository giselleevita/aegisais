import { useCallback, useEffect, useState } from 'react'
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
  const [userId, setUserId] = useState('')
  const [resourceType, setResourceType] = useState('')
  const [resourceId, setResourceId] = useState('')
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 50
  const [hasMore, setHasMore] = useState(false)
  const [exporting, setExporting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiClient.getAuditLogs({
        action: action || undefined,
        user_id: userId || undefined,
        resource_type: resourceType || undefined,
        resource_id: resourceId || undefined,
        start_time: startTime ? new Date(startTime).toISOString() : undefined,
        end_time: endTime ? new Date(endTime).toISOString() : undefined,
        limit,
        offset,
      })
      setRows(data)
      setHasMore(data.length === limit)
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
  }, [action, endTime, offset, resourceId, resourceType, startTime, userId])

  useEffect(() => {
    void load()
  }, [load])

  const handleExport = async () => {
    setExporting(true)
    try {
      await apiClient.downloadAuditLogsCsv({
        action: action || undefined,
        user_id: userId || undefined,
        resource_type: resourceType || undefined,
        resource_id: resourceId || undefined,
        start_time: startTime ? new Date(startTime).toISOString() : undefined,
        end_time: endTime ? new Date(endTime).toISOString() : undefined,
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
          <select
            value={action}
            onChange={(e) => {
              setOffset(0)
              setAction(e.target.value)
            }}
            aria-label="Filter audit action"
          >
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

      <div
        style={{
          display: 'grid',
          gap: '0.5rem',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          marginBottom: '0.75rem',
        }}
      >
        <input
          placeholder="user_id"
          value={userId}
          onChange={(e) => {
            setOffset(0)
            setUserId(e.target.value)
          }}
        />
        <input
          placeholder="resource_type"
          value={resourceType}
          onChange={(e) => {
            setOffset(0)
            setResourceType(e.target.value)
          }}
        />
        <input
          placeholder="resource_id"
          value={resourceId}
          onChange={(e) => {
            setOffset(0)
            setResourceId(e.target.value)
          }}
        />
        <input
          type="datetime-local"
          value={startTime}
          onChange={(e) => {
            setOffset(0)
            setStartTime(e.target.value)
          }}
          aria-label="Start time"
        />
        <input
          type="datetime-local"
          value={endTime}
          onChange={(e) => {
            setOffset(0)
            setEndTime(e.target.value)
          }}
          aria-label="End time"
        />
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
          {rows.length > 0 ? (
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem' }}>
              <button
                type="button"
                onClick={() => setOffset((prev) => Math.max(0, prev - limit))}
                disabled={offset === 0}
              >
                Previous
              </button>
              <span>Offset: {offset}</span>
              <button type="button" onClick={() => setOffset((prev) => prev + limit)} disabled={!hasMore}>
                Next
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

