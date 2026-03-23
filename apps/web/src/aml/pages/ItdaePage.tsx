import ErrorBoundary from '@/shared/components/ErrorBoundary'
import ITDAEPanel from '@/features/itdae/components/ITDAEPanel'

export default function ItdaePage() {
  return (
    <div className="aml-page-pad">
      <ErrorBoundary>
        <ITDAEPanel />
      </ErrorBoundary>
    </div>
  )
}
