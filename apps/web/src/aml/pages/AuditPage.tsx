import { useCallback, useEffect, useState } from 'react'
import { apiClient } from '@/core/api-client'
import { describeApiFailure } from '@/core/api-errors'
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
      setError(
        describeApiFailure(err, {
          fallback: 'Unable to load audit logs.',
          unauthorized: 'Sign in as admin to view audit logs.',
          forbidden: 'Sign in as admin to view audit logs.',
          offline: 'Audit ledger unavailable while the API policy surface is offline.',
        })
      )
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
      setError(
        describeApiFailure(err, {
          fallback: 'Unable to export audit logs.',
          unauthorized: 'Sign in as admin to export audit logs.',
          forbidden: 'Sign in as admin to export audit logs.',
          offline: 'Audit export unavailable while the API policy surface is offline.',
        })
      )
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="aml-page-pad aml-audit">
      <header className="aml-audit__hero">
        <div>
          <span className="aml-operations__eyebrow">Governance</span>
          <h2 className="aml-page-title">Audit ledger</h2>
          <p className="aml-incidents__lead">Filter operational events, export evidence for review, and trace incident lifecycle changes without leaving the governance deck.</p>
        </div>
        <div className="aml-audit__actions">
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
      </header>

      <div className="aml-audit__filters">
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

      {loading ? <p className="aml-audit__message">Loading audit logs...</p> : null}
      {error ? <p className="aml-audit__message aml-audit__message--error" role="alert">{error}</p> : null}

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
          {rows.length === 0 ? <p className="aml-audit__message">No audit rows for current filter.</p> : null}
          {rows.length > 0 ? (
            <div className="aml-audit__pager">
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

