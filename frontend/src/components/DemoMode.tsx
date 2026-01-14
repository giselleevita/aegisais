import { useState, useEffect } from 'react'
import { apiClient } from '../api/client'
import './DemoMode.css'

interface DemoModeProps {
    onStartDemo: () => void
}

export default function DemoMode({ onStartDemo }: DemoModeProps) {
    const [demoFiles, setDemoFiles] = useState<Array<{ filename: string; path: string; size_mb: number }>>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        loadDemoFiles()
    }, [])

    const loadDemoFiles = async () => {
        try {
            const result = await apiClient.listUploadedFiles()
            setDemoFiles(result.files)
        } catch (error) {
            if (import.meta.env.DEV) {
                // eslint-disable-next-line no-console
                console.error('Failed to load demo files:', error)
            }
        } finally {
            setLoading(false)
        }
    }

    const handleStartDemo = async (filePath: string) => {
        try {
            await apiClient.startReplay(filePath, 100, true, 100)
            onStartDemo()
        } catch (error) {
            if (import.meta.env.DEV) {
                // eslint-disable-next-line no-console
                console.error('Failed to start demo:', error)
            }
            alert('Failed to start demo. Please check if the file exists.')
        }
    }

    return (
        <div className="demo-mode">
            <div className="demo-header">
                <h3>🚀 Try Demo Mode</h3>
                <p>Start with a sample file to see how AegisAIS works</p>
                <div className="demo-features">
                    <p><strong>Available demo files:</strong></p>
                    <ul>
                        <li><strong>demo_comprehensive.csv</strong> - All alert types (recommended)</li>
                        <li><strong>demo_teleport_t1.csv</strong> - TELEPORT Tier 1 (impossible speed)</li>
                        <li><strong>demo_teleport_t2.csv</strong> - TELEPORT Tier 2 (suspicious speed)</li>
                        <li><strong>demo_turn_rate_t1.csv</strong> - TURN_RATE Tier 1 (impossible turn)</li>
                        <li><strong>demo_turn_rate_t2.csv</strong> - TURN_RATE Tier 2 (suspicious turn)</li>
                        <li><strong>demo_position_invalid.csv</strong> - Invalid coordinates</li>
                        <li><strong>demo_acceleration.csv</strong> - Impossible acceleration</li>
                        <li><strong>demo_heading_cog.csv</strong> - Heading/COG mismatch</li>
                        <li><strong>demo_normal.csv</strong> - Normal track (no alerts)</li>
                    </ul>
                </div>
            </div>

            {loading ? (
                <div className="demo-loading">Loading available files...</div>
            ) : demoFiles.length === 0 ? (
                <div className="demo-empty">
                    <p>No demo files available.</p>
                    <p>Upload a file first, or check the <code>data/raw/</code> directory for sample data.</p>
                </div>
            ) : (
                <div className="demo-files">
                    <p className="demo-instructions">
                        Select a file to start the demo. The system will process it and show you alerts in real-time.
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
                                    Start Demo
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <div className="demo-tips">
                <h4>💡 Demo Tips</h4>
                <ul>
                    <li>Watch the Dashboard to see processing progress</li>
                    <li>Check the Alerts tab for detected anomalies</li>
                    <li>View vessels on the Map to see spatial patterns</li>
                    <li>Click any vessel to see detailed information</li>
                </ul>
            </div>
        </div>
    )
}
