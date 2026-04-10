import { useCallback, useEffect, useState } from 'react'
import { apiClient } from '@/core/api-client'
import './DemoMode.css'

interface DemoModeProps {
    onStartDemo: () => void
}

const DEMO_DATASET_GUIDE: Array<{ filename: string; description: string }> = [
    { filename: 'demo_comprehensive.csv', description: 'Full scenario set spanning all major alert classes.' },
    { filename: 'demo_teleport_t1.csv', description: 'Tier 1 teleport events with impossible implied speed.' },
    { filename: 'demo_teleport_t2.csv', description: 'Tier 2 teleport events for suspicious movement.' },
    { filename: 'demo_turn_rate_t1.csv', description: 'Tier 1 turn-rate violations.' },
    { filename: 'demo_turn_rate_t2.csv', description: 'Tier 2 turn-rate anomalies.' },
    { filename: 'demo_position_invalid.csv', description: 'Invalid coordinate and position-quality events.' },
    { filename: 'demo_acceleration.csv', description: 'Acceleration and deceleration integrity violations.' },
    { filename: 'demo_heading_cog.csv', description: 'Heading and COG consistency mismatch cases.' },
    { filename: 'demo_normal.csv', description: 'Benign baseline track for control comparison.' },
]

export default function DemoMode({ onStartDemo }: DemoModeProps) {
    const [demoFiles, setDemoFiles] = useState<Array<{ filename: string; path: string; size_mb: number }>>([])
    const [loading, setLoading] = useState(true)

    const loadDemoFiles = useCallback(async () => {
        try {
            const result = await apiClient.listUploadedFiles()
            setDemoFiles(result.files.sort((a, b) => b.size_mb - a.size_mb))
        } catch (error) {
            if (import.meta.env.DEV) {
                console.error('Failed to load demo files:', error)
            }
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        void loadDemoFiles()
    }, [loadDemoFiles])

    const handleStartDemo = async (filePath: string) => {
        try {
            await apiClient.startReplay(filePath, 100, true, 100)
            onStartDemo()
        } catch (error) {
            if (import.meta.env.DEV) {
                console.error('Failed to start demo:', error)
            }
            alert('Failed to start demo. Please check if the file exists.')
        }
    }

    return (
        <div className="demo-mode">
            <div className="demo-header">
                <h3>Demo Execution</h3>
                <p>Select a scenario dataset to launch a replay run and observe alert generation in real time.</p>
                <div className="demo-features">
                    <p><strong>Recommended datasets:</strong></p>
                    <ul>
                        {DEMO_DATASET_GUIDE.map((entry) => (
                            <li key={entry.filename}>
                                <strong>{entry.filename}</strong> - {entry.description}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>

            {loading ? (
                <div className="demo-loading">Loading available files...</div>
            ) : demoFiles.length === 0 ? (
                <div className="demo-empty">
                    <p>No demo files available.</p>
                    <p>Upload a dataset first, or verify sample data is present in <code>data/raw/</code>.</p>
                </div>
            ) : (
                <div className="demo-files">
                    <p className="demo-instructions">
                        Choose a file to start a replay run. Processing metrics and detections will update live.
                    </p>
                    <div className="demo-file-list">
                        {demoFiles.map((file) => (
                            <div key={file.path} className="demo-file-card">
                                <div className="demo-file-info">
                                    <div className="demo-file-name">{file.filename}</div>
                                    <div className="demo-file-size">{file.size_mb.toFixed(2)} MB</div>
                                </div>
                                <button
                                    onClick={() => handleStartDemo(file.path)}
                                    className="btn-demo-start"
                                >
                                    Start Run
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <div className="demo-tips">
                <h4>Run Guidance</h4>
                <ul>
                    <li>Monitor processed-point count in the header demo status banner.</li>
                    <li>Use Triage and alert investigation to validate rule firings and severity distribution.</li>
                    <li>Compare Globe and Map views to inspect geographic context and movement traces.</li>
                    <li>Run a baseline dataset after anomaly datasets for contrast.</li>
                </ul>
            </div>
        </div>
    )
}
