import { useState } from 'react'
import DemoMode from './DemoMode'
import './WelcomePage.css'

interface WelcomePageProps {
    onStartOnboarding?: () => void
}

export default function WelcomePage({ onStartOnboarding }: WelcomePageProps) {
    const [showDemo, setShowDemo] = useState(false)

    return (
        <div className="welcome-page">
            <div className="welcome-hero">
                <h1 className="welcome-title">🛡️ Welcome to AegisAIS</h1>
                <p className="welcome-subtitle">
                    AIS Data Integrity and Anomaly Detection Tool
                </p>
                {onStartOnboarding && (
                    <button onClick={onStartOnboarding} className="welcome-tour-btn">
                        📖 Take a Tour
                    </button>
                )}
            </div>

            <div className="welcome-content">
                <section className="welcome-section">
                    <h2>What is AegisAIS?</h2>
                    <p>
                        <strong>AegisAIS</strong> is an automated data integrity checker for Automatic Identification System (AIS) 
                        maritime data. It ingests AIS position reports, maintains track history per vessel, and automatically 
                        detects physically impossible or internally inconsistent data patterns.
                    </p>
                </section>

                <section className="welcome-section">
                    <h2>Key Features</h2>
                    <div className="features-grid">
                        <div className="feature-card">
                            <div className="feature-icon">🚢</div>
                            <h3>Vessel Tracking</h3>
                            <p>Maintains real-time position and state for each vessel (MMSI) with track history.</p>
                        </div>
                        <div className="feature-card">
                            <div className="feature-icon">⚠️</div>
                            <h3>Anomaly Detection</h3>
                            <p>Detects teleportation, impossible turn rates, invalid positions, and data inconsistencies.</p>
                        </div>
                        <div className="feature-card">
                            <div className="feature-icon">📊</div>
                            <h3>Alert System</h3>
                            <p>Tiered alert system with severity scoring and detailed evidence for each detection.</p>
                        </div>
                        <div className="feature-card">
                            <div className="feature-icon">📁</div>
                            <h3>File Processing</h3>
                            <p>Process CSV, DAT, and compressed (.zst) AIS data files with streaming support for large datasets.</p>
                        </div>
                    </div>
                </section>

                <section className="welcome-section">
                    <h2>How It Works</h2>
                    <ol className="how-it-works">
                        <li>
                            <strong>Upload AIS Data</strong>
                            <p>Drag and drop your AIS data file (CSV, DAT, or .zst compressed) in the sidebar.</p>
                        </li>
                        <li>
                            <strong>Automatic Processing</strong>
                            <p>The system processes points in real-time, maintaining track history and running detection rules.</p>
                        </li>
                        <li>
                            <strong>Alert Generation</strong>
                            <p>When anomalies are detected, alerts are generated with detailed evidence and severity scores.</p>
                        </li>
                        <li>
                            <strong>Review & Analyze</strong>
                            <p>View alerts by type, severity, or vessel. Examine evidence to understand what triggered each alert.</p>
                        </li>
                    </ol>
                </section>

                <section className="welcome-section">
                    <h2>Alert Types</h2>
                    <div className="alert-types">
                        <div className="alert-type-group">
                            <h3>Tier 1: Integrity Alerts</h3>
                            <p>High-confidence detections of physically impossible events:</p>
                            <ul>
                                <li><strong>TELEPORT</strong> - Implied speed exceeds vessel capabilities</li>
                                <li><strong>TURN_RATE</strong> - Impossible turn rates at high speed</li>
                                <li><strong>POSITION_INVALID</strong> - Out-of-bounds or stuck positions</li>
                                <li><strong>HEADING_COG_CONSISTENCY</strong> - Wild heading/COG changes</li>
                            </ul>
                        </div>
                        <div className="alert-type-group">
                            <h3>Tier 2: Suspicious Behavior</h3>
                            <p>Lower-threshold detections indicating data quality issues:</p>
                            <ul>
                                <li><strong>TELEPORT_T2</strong> - Suspicious medium-speed jumps</li>
                                <li><strong>TURN_RATE_T2</strong> - Moderate turn rate anomalies</li>
                                <li><strong>ACCELERATION</strong> - Impossible acceleration/deceleration</li>
                            </ul>
                        </div>
                    </div>
                </section>

                <section className="welcome-section">
                    <h2>Getting Started</h2>
                    <div className="getting-started">
                        <div className="step-card">
                            <div className="step-number">1</div>
                            <div>
                                <h3>Upload Your Data</h3>
                                <p>Use the file upload area in the sidebar to select your AIS data file. Supported formats: CSV, DAT, .csv.zst, .dat.zst</p>
                            </div>
                        </div>
                        <div className="step-card">
                            <div className="step-number">2</div>
                            <div>
                                <h3>Monitor Processing</h3>
                                <p>Watch the Dashboard tab to see processing progress, vessel count, and alert statistics in real-time.</p>
                            </div>
                        </div>
                        <div className="step-card">
                            <div className="step-number">3</div>
                            <div>
                                <h3>Review Alerts</h3>
                                <p>Switch to the Alerts tab to filter and examine detected anomalies. Each alert includes detailed evidence.</p>
                            </div>
                        </div>
                        <div className="step-card">
                            <div className="step-number">4</div>
                            <div>
                                <h3>Explore Vessels</h3>
                                <p>View the Vessels tab to see all tracked vessels and their latest positions and alert severities.</p>
                            </div>
                        </div>
                    </div>
                </section>

                <section className="welcome-section welcome-note">
                    <p>
                        <strong>Note:</strong> AegisAIS focuses on <em>data integrity</em> - detecting physically impossible 
                        or inconsistent data. It is not a maritime traffic visualization tool, route planner, or general 
                        anomaly detection system.
                    </p>
                </section>

                <section className="welcome-section">
                    <div className="demo-section">
                        <h2>Try It Now</h2>
                        {!showDemo ? (
                            <div className="demo-cta">
                                <p>Ready to see AegisAIS in action? Start with a demo!</p>
                                <button onClick={() => setShowDemo(true)} className="btn-demo-cta">
                                    🚀 Start Demo Mode
                                </button>
                            </div>
                        ) : (
                            <DemoMode onStartDemo={() => setShowDemo(false)} />
                        )}
                    </div>
                </section>
            </div>
        </div>
    )
}
