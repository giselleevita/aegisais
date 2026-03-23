import ErrorBoundary from '@/shared/components/ErrorBoundary'
import WatchlistPanel from '@/features/vessels/components/WatchlistPanel'

export default function WatchlistPage() {
  return (
    <div className="aml-page-pad">
      <ErrorBoundary>
        <WatchlistPanel />
      </ErrorBoundary>
    </div>
  )
}
