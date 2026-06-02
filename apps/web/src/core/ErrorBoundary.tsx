import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
    children: ReactNode
    fallback?: ReactNode
    label?: string
}

interface State {
    hasError: boolean
    message: string
}

export class ErrorBoundary extends Component<Props, State> {
    state: State = { hasError: false, message: '' }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, message: error.message }
    }

    componentDidCatch(error: Error, info: ErrorInfo) {
        console.error(`[ErrorBoundary:${this.props.label ?? 'root'}]`, error, info.componentStack)
    }

    render() {
        if (this.state.hasError) {
            return this.props.fallback ?? (
                <div role="alert" style={{
                    padding: '2rem',
                    margin: '1rem',
                    borderRadius: '8px',
                    border: '1px solid #ef4444',
                    background: 'rgba(239,68,68,0.08)',
                    color: '#fca5a5',
                    fontFamily: 'monospace',
                    fontSize: '0.85rem',
                }}>
                    <strong style={{ display: 'block', marginBottom: '0.5rem' }}>
                        [{this.props.label ?? 'Component'} crashed]
                    </strong>
                    <span>{this.state.message}</span>
                    <br />
                    <button
                        style={{ marginTop: '1rem', cursor: 'pointer' }}
                        onClick={() => this.setState({ hasError: false, message: '' })}
                    >
                        Retry
                    </button>
                </div>
            )
        }
        return this.props.children
    }
}
