import { useOutletContext } from 'react-router-dom'
import ErrorBoundary from '@/shared/components/ErrorBoundary'
import ReplayControls from '@/shared/components/ReplayControls/ReplayControls'
import type { AmlOutletContext } from '@/aml/amlOutletContext'

export default function LabPage() {
  const { lastMessage } = useOutletContext<AmlOutletContext>()

  return (
    <div className="aml-page-pad">
      <h2 className="aml-page-title">Lab — replay &amp; upload</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', maxWidth: '52rem' }}>
        Training and batch replay live here instead of a global sidebar, so the default mission stays
        operations-first (triage and map context).
      </p>
      <ErrorBoundary>
        <ReplayControls lastMessage={lastMessage} />
      </ErrorBoundary>
    </div>
  )
}
