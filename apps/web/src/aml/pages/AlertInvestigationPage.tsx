import { useEffect, useState } from 'react'
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom'
import { apiClient } from '@/core/api-client'
import type { Alert } from '@/shared/types/common'
import {
  formatAlertType,
  getAlertClassification,
  getSeverityLevel,
  renderEvidence,
} from '@/features/alerts/lib/alertEvidence'
import type { AmlOutletContext } from '@/aml/amlOutletContext'
import { AML_OPERATIONS_PATH } from '@/aml/amlRoutes'
import './alert-investigation.css'

export default function AlertInvestigationPage() {
  const { alertId } = useParams()
  const id = Number(alertId)
  const navigate = useNavigate()
  const { lastMessage } = useOutletContext<AmlOutletContext>()

  const [alertRecord, setAlertRecord] = useState<Alert | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [statusDraft, setStatusDraft] = useState('new')
  const [notesDraft, setNotesDraft] = useState('')
  const [actionError, setActionError] = useState<string | null>(null)

  useEffect(() => {
    if (!Number.isFinite(id)) return
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        const a = await apiClient.getAlert(id)
        if (!cancelled) {
          setAlertRecord(a)
          setStatusDraft(a.status || 'new')
          setNotesDraft(a.notes || '')
        }
      } catch {
        if (!cancelled) setAlertRecord(null)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id])

  useEffect(() => {
    if (!lastMessage || !('type' in lastMessage)) return
    if (lastMessage.type !== 'alert_status_updated') return
    if (lastMessage.alert_id !== id) return
    const nextStatus = lastMessage.status || 'new'
    setStatusDraft(nextStatus)
    setAlertRecord((prev) => (prev ? { ...prev, status: nextStatus } : prev))
  }, [lastMessage, id])

  const handleSave = async () => {
    if (!alertRecord) return
    try {
      setActionError(null)
      await apiClient.updateAlertStatus(alertRecord.id, statusDraft, notesDraft)
      const refreshed = await apiClient.getAlert(alertRecord.id)
      setAlertRecord(refreshed)
      setEditing(false)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Update failed'
      setActionError(msg)
    }
  }

  if (!Number.isFinite(id)) {
    return (
      <div className="aml-page-pad">
        <p>Invalid alert id.</p>
        <Link to={AML_OPERATIONS_PATH}>Back to operations</Link>
      </div>
    )
  }

  if (loading) {
    return <div className="aml-page-pad aml-inv">Loading investigation…</div>
  }

  if (!alertRecord) {
    return (
      <div className="aml-page-pad aml-inv">
        <p>Alert not found.</p>
        <button type="button" className="aml-inv__back" onClick={() => navigate(-1)}>
          Back
        </button>
      </div>
    )
  }

  const sev = getSeverityLevel(alertRecord.severity)

  return (
    <div className="aml-page-pad aml-inv">
      <div className="aml-inv__toolbar">
        <button type="button" className="aml-inv__back" onClick={() => navigate(-1)}>
          ← Back
        </button>
        <Link to={AML_OPERATIONS_PATH} className="aml-inv__link">
          Operations
        </Link>
        <Link
          to={`${AML_OPERATIONS_PATH}?mmsi=${encodeURIComponent(alertRecord.mmsi)}`}
          className="aml-inv__link"
        >
          Map + vessel
        </Link>
      </div>

      <article className={`aml-inv__card severity-${sev}`}>
        <header className="aml-inv__header">
          <div>
            <p className="aml-inv__eyebrow">Investigation</p>
            <h1 className="aml-inv__title">{formatAlertType(alertRecord.type)}</h1>
            <p className="aml-inv__summary">{alertRecord.summary}</p>
          </div>
          <div className="aml-inv__badges">
            <span className={`severity-badge severity-${sev}`}>{alertRecord.severity}</span>
            <span className={`status-badge status-${alertRecord.status || 'new'}`}>{alertRecord.status || 'new'}</span>
          </div>
        </header>

        <section className="aml-inv__meta">
          <div>
            <span className="label">MMSI</span>
            <span>{alertRecord.mmsi}</span>
          </div>
          <div>
            <span className="label">Time</span>
            <span>{new Date(alertRecord.timestamp).toLocaleString()}</span>
          </div>
          <div>
            <span className="label">Class</span>
            <span>{getAlertClassification(alertRecord.type).tierLabel}</span>
          </div>
        </section>

        {alertRecord.evidence ? (
          <section className="aml-inv__evidence">
            <h2 className="aml-inv__h2">Evidence</h2>
            {renderEvidence(alertRecord)}
          </section>
        ) : null}

        {alertRecord.notes && !editing ? (
          <section className="aml-inv__notes">
            <h2 className="aml-inv__h2">Notes</h2>
            <p>{alertRecord.notes}</p>
          </section>
        ) : null}

        <section className="aml-inv__actions">
          <h2 className="aml-inv__h2">Disposition</h2>
          {actionError ? <p className="aml-inv__error" role="alert">{actionError}</p> : null}
          {editing ? (
            <div className="aml-inv__edit">
              <select
                value={statusDraft}
                onChange={(e) => setStatusDraft(e.target.value)}
                className="aml-inv__select"
              >
                <option value="new">New</option>
                <option value="reviewed">Reviewed</option>
                <option value="resolved">Resolved</option>
                <option value="false_positive">False Positive</option>
              </select>
              <textarea
                value={notesDraft}
                onChange={(e) => setNotesDraft(e.target.value)}
                placeholder="Analyst notes…"
                className="aml-inv__textarea"
                rows={4}
              />
              <div className="aml-inv__edit-buttons">
                <button type="button" className="aml-inv__btn-primary" onClick={() => void handleSave()}>
                  Save
                </button>
                <button
                  type="button"
                  className="aml-inv__btn-ghost"
                  onClick={() => {
                    setEditing(false)
                    setActionError(null)
                    setStatusDraft(alertRecord.status || 'new')
                    setNotesDraft(alertRecord.notes || '')
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              className="aml-inv__btn-primary"
              onClick={() => {
                setActionError(null)
                setEditing(true)
              }}
            >
              Update status
            </button>
          )}
        </section>
      </article>
    </div>
  )
}
