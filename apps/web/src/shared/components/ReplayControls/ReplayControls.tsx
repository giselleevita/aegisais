import { useCallback, useEffect, useState } from 'react'
import { apiClient } from '@/core/api-client'
import { describeApiFailure } from '@/core/api-errors'
import type { ReplayStatus, WebSocketMessage } from '@/shared/types/common'
import FileDropZone from '@/shared/components/FileDropZone/FileDropZone'
import './ReplayControls.css'

interface ReplayControlsProps {
    lastMessage?: WebSocketMessage | null
}

export default function ReplayControls({ lastMessage }: ReplayControlsProps) {
    const [status, setStatus] = useState<ReplayStatus | null>(null)
    const [filePath, setFilePath] = useState('data/raw/demo_ais.csv')
    const [speedup, setSpeedup] = useState(100.0)
    const [useStreaming, setUseStreaming] = useState(true)
    // Keep batch size as a string so the user can freely edit
    // (including temporarily empty or with leading zeros)
    const [batchSize, setBatchSize] = useState<string>('100')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [statusError, setStatusError] = useState<string | null>(null)

    const loadStatus = useCallback(async () => {
        try {
            const data = await apiClient.getReplayStatus()
            setStatus(data)
        } catch (error) {
            if (import.meta.env.DEV) {
                console.error('Failed to load replay status:', error)
            }
        }
    }, [])

    // Listen for error messages from WebSocket
    useEffect(() => {
        if (lastMessage?.kind === 'error') {
            setError(lastMessage.message || 'An error occurred')
        }
    }, [lastMessage])

    const loadStatus = useCallback(async () => {
        try {
            const data = await apiClient.getReplayStatus()
            setStatus(data)
            setStatusError(null)
        } catch (error) {
            setStatus(null)
            setStatusError(
                describeApiFailure(error, {
                    fallback: 'Unable to load replay status.',
                    unauthorized: 'Sign in to access replay controls.',
                    offline: 'Replay control link degraded. Restore the API policy surface to recover status telemetry.',
                })
            )
            if (import.meta.env.DEV) {
                console.error('Failed to load replay status:', error)
            }
        }
    }, [])

    useEffect(() => {
        void loadStatus()
        const interval = setInterval(() => {
            void loadStatus()
        }, 1000)
        return () => clearInterval(interval)
    }, [loadStatus])

    const handleStart = async () => {
        if (!filePath.trim()) {
            setError('Please enter a file path before starting replay.')
            return
        }
        // Parse batch size safely
        const parsedBatchSize = Number(batchSize) || 1
        try {
            setLoading(true)
            setError(null)
            await apiClient.startReplay(filePath, speedup, useStreaming, parsedBatchSize)
            await loadStatus()
        } catch (err) {
            setError(
                describeApiFailure(err, {
                    fallback: 'Unable to start replay.',
                    unauthorized: 'Sign in to start replay.',
                    offline: 'Replay start unavailable while the API policy surface is offline.',
                })
            )
        } finally {
            setLoading(false)
        }
    }

    const handleStop = async () => {
        try {
            setError(null)
            await apiClient.stopReplay()
            await loadStatus()
        } catch (err) {
            setError(
                describeApiFailure(err, {
                    fallback: 'Unable to stop replay.',
                    unauthorized: 'Sign in to stop replay.',
                    offline: 'Replay stop unavailable while the API policy surface is offline.',
                })
            )
        }
    }

    const handleFileDrop = async (file: File) => {
        try {
            setLoading(true)
            setError(null)

            // Step 1: Upload file
            const result = await apiClient.uploadFile(file)

            // Automatically set the file path
            setFilePath(result.path)

            // Step 2: Start replay
            try {
                const parsedBatchSize = Number(batchSize) || 1
                await apiClient.startReplay(result.path, speedup, useStreaming, parsedBatchSize)

                // Wait a bit and check if it's actually running
                await new Promise(resolve => setTimeout(resolve, 1500))
                await loadStatus()

                // Check again after another delay
                setTimeout(async () => {
                    await loadStatus()
                    const newStatus = await apiClient.getReplayStatus()
                    if (!newStatus.running && newStatus.processed === 0) {
                        setError('Replay may have failed to start. Check server logs for details.')
                    }
                }, 2000)
            } catch (replayError) {
                setError(
                    describeApiFailure(replayError, {
                        fallback: 'Replay failed to start.',
                        unauthorized: 'Sign in to start replay.',
                        offline: 'Replay start unavailable while the API policy surface is offline.',
                    })
                )
            }
        } catch (err) {
            setError(
                describeApiFailure(err, {
                    fallback: 'Upload failed.',
                    unauthorized: 'Sign in to upload a replay file.',
                    offline: 'File ingest unavailable while the API policy surface is offline.',
                })
            )
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="replay-controls">
            <p className="replay-controls__title">Replay</p>

            <div className="replay-status">
                <div className={`status-indicator ${status?.running ? 'running' : 'stopped'}`} aria-live="polite">
                    {status?.running ? '● Running' : '○ Stopped'}
                </div>
                {status && (
                    <div className="status-details" role="status" aria-live="polite">
                        <div>Processed: {status.processed.toLocaleString()}</div>
                        {status.last_timestamp && (
                            <div className="timestamp">
                                {new Date(status.last_timestamp).toLocaleString()}
                            </div>
                        )}
                    </div>
                )}
                {statusError ? <div className="replay-status__note" role="status">Status feed degraded. {statusError}</div> : null}
                {error ? <div className="replay-error" role="alert">Warning: {error}</div> : null}
            </div>

            <div className="replay-form">
                <div className="form-group">
                    <label>Upload File (Drag & Drop)</label>
                    <FileDropZone
                        onFileDrop={handleFileDrop}
                        acceptedTypes={['.csv', '.dat', '.zst']}
                        maxSizeMB={5000}
                    />
                </div>

                <div className="form-group">
                    <label htmlFor="file-path">File Path</label>
                    <input
                        id="file-path"
                        type="text"
                        value={filePath}
                        onChange={(e) => setFilePath(e.target.value)}
                        placeholder="data/raw/file.dat.zst or file.csv.zst"
                        disabled={status?.running || loading}
                    />
                    <small className="form-help-text">
                        Drag & drop a file above, or enter a path manually
                    </small>
                </div>

                <div className="form-group">
                    <label htmlFor="speedup">Speedup</label>
                    <input
                        id="speedup"
                        type="number"
                        value={speedup}
                        onChange={(e) => setSpeedup(Number(e.target.value))}
                        min="0.1"
                        step="0.1"
                        disabled={status?.running}
                    />
                </div>

                <div className="form-group">
                    <label htmlFor="use-streaming">
                        <input
                            id="use-streaming"
                            type="checkbox"
                            checked={useStreaming}
                            onChange={(e) => setUseStreaming(e.target.checked)}
                            disabled={status?.running}
                        />
                        Use Streaming (for large files)
                    </label>
                </div>

                <div className="form-group">
                    <label htmlFor="batch-size">Batch Size</label>
                    <input
                        id="batch-size"
                        type="number"
                        value={batchSize}
                        onChange={(e) => setBatchSize(e.target.value)}
                        min="1"
                        max="10000"
                        step="10"
                        disabled={status?.running}
                    />
                    <small className="form-help-text">
                        Points per database commit (100-1000 recommended for large files)
                    </small>
                </div>

                <div className="form-actions">
                    <button
                        onClick={handleStart}
                        disabled={status?.running || loading}
                        className="btn btn-primary"
                    >
                        Start Replay
                    </button>
                    <button
                        onClick={handleStop}
                        disabled={!status?.running}
                        className="btn btn-danger"
                    >
                        Stop Replay
                    </button>
                </div>
            </div>
        </div>
    )
}

