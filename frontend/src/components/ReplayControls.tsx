import { useEffect, useState } from 'react'
import { apiClient } from '../api/client'
import type { ReplayStatus } from '../api/client'
import FileDropZone from './FileDropZone'
import './ReplayControls.css'

interface ReplayControlsProps {
    lastMessage?: any
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

    // Listen for error messages from WebSocket
    useEffect(() => {
        if (lastMessage?.kind === 'error') {
            setError(lastMessage.message || 'An error occurred')
        }
    }, [lastMessage])

    useEffect(() => {
        loadStatus()
        const interval = setInterval(loadStatus, 1000)
        return () => clearInterval(interval)
    }, [])

    const loadStatus = async () => {
        try {
            const data = await apiClient.getReplayStatus()
            setStatus(data)
        } catch (error) {
            console.error('Failed to load replay status:', error)
        }
    }

    const handleStart = async () => {
        if (!filePath.trim()) {
            alert('Please enter a file path')
            return
        }
        // Parse batch size safely
        const parsedBatchSize = Number(batchSize) || 1
        try {
            setLoading(true)
            await apiClient.startReplay(filePath, speedup, useStreaming, parsedBatchSize)
            await loadStatus()
        } catch (error: any) {
            alert(`Failed to start replay: ${error.message}`)
        } finally {
            setLoading(false)
        }
    }

    const handleStop = async () => {
        try {
            await apiClient.stopReplay()
            await loadStatus()
        } catch (error: any) {
            alert(`Failed to stop replay: ${error.message}`)
        }
    }

    const handleFileDrop = async (file: File) => {
        try {
            setLoading(true)
            setError(null)

            // Step 1: Upload file
            console.log('Uploading file:', file.name)
            const result = await apiClient.uploadFile(file)
            console.log('File uploaded successfully:', result)

            // Automatically set the file path
            setFilePath(result.path)

            // Step 2: Start replay
            console.log('Starting replay with path:', result.path, 'speedup:', speedup)
            try {
                const parsedBatchSize = Number(batchSize) || 1
                const replayResult = await apiClient.startReplay(result.path, speedup, useStreaming, parsedBatchSize)
                console.log('Replay start response:', replayResult)

                // Wait a bit and check if it's actually running
                await new Promise(resolve => setTimeout(resolve, 1500))
                await loadStatus()

                // Check again after another delay
                setTimeout(async () => {
                    await loadStatus()
                    const newStatus = await apiClient.getReplayStatus()
                    console.log('Replay status check:', newStatus)
                    if (!newStatus.running && newStatus.processed === 0) {
                        setError('Replay may have failed to start. Check server logs for details.')
                    }
                }, 2000)
            } catch (replayError: any) {
                console.error('Replay start error:', replayError)
                const errorMsg = replayError.message || 'Failed to start replay'
                setError(`Replay failed: ${errorMsg}`)
                alert(`Replay failed: ${errorMsg}`)
            }
        } catch (error: any) {
            console.error('Upload error:', error)
            const errorMessage = error.message || 'Unknown error occurred'
            setError(`Upload failed: ${errorMessage}`)
            alert(`Upload failed: ${errorMessage}`)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="replay-controls">
            <h3>Replay Controls</h3>

            <div className="replay-status">
                <div className={`status-indicator ${status?.running ? 'running' : 'stopped'}`}>
                    {status?.running ? '● Running' : '○ Stopped'}
                </div>
                {status && (
                    <div className="status-details">
                        <div>Processed: {status.processed.toLocaleString()}</div>
                        {status.last_timestamp && (
                            <div className="timestamp">
                                {new Date(status.last_timestamp).toLocaleString()}
                            </div>
                        )}
                    </div>
                )}
                {error && (
                    <div style={{ color: 'red', marginTop: '0.5rem', fontSize: '0.875rem' }}>
                        ⚠️ {error}
                    </div>
                )}
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
                    <small style={{ display: 'block', marginTop: '0.25rem', color: '#6b7280' }}>
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
                    <small style={{ display: 'block', marginTop: '0.25rem', color: '#6b7280' }}>
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

