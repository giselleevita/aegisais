import './AboutAegisAIS.css'

export default function AboutAegisAIS() {
    return (
        <section className="about-panel">
            <details open>
                <summary className="about-title">📖 About AegisAIS</summary>
                <div className="about-content">
                    <div className="about-section">
                        <p className="about-one-liner">
                            <strong>AegisAIS is an AIS data integrity and anomaly detection tool.</strong>
                            It ingests AIS points, maintains short track history per vessel, and raises alerts when data
                            appears physically impossible or internally inconsistent.
                        </p>
                    </div>

                    <div className="about-section">
                        <h4 className="about-section-title">Scope</h4>
                        <div className="about-subsection">
                            <div className="about-subsection-label">What it is:</div>
                            <ul className="about-list-compact">
                                <li>Data integrity checker for AIS feeds</li>
                                <li>Physics-based anomaly detector</li>
                                <li>Alert generation and evidence tracking</li>
                            </ul>
                        </div>
                        <div className="about-subsection">
                            <div className="about-subsection-label">What it is not:</div>
                            <ul className="about-list-compact">
                                <li>Maritime traffic radar or charting UI</li>
                                <li>Route planner or ETA engine</li>
                                <li>Generic "everything abnormal" alert system</li>
                            </ul>
                        </div>
                    </div>

                    <div className="about-section">
                        <h4 className="about-section-title">Architecture</h4>
                        <ol className="about-architecture-list">
                            <li>
                                <div className="architecture-step">
                                    <span className="architecture-number">1</span>
                                    <div>
                                        <strong>Ingestion & Track State</strong>
                                        <p>AIS points are ingested and stored in a per-vessel <em>track store</em> (last 5 points per MMSI).</p>
                                    </div>
                                </div>
                            </li>
                            <li>
                                <div className="architecture-step">
                                    <span className="architecture-number">2</span>
                                    <div>
                                        <strong>Rules Engine</strong>
                                        <p>Rules evaluate pairs or windows of consecutive points to check speed, turn rate, position validity, and field consistency.</p>
                                    </div>
                                </div>
                            </li>
                            <li>
                                <div className="architecture-step">
                                    <span className="architecture-number">3</span>
                                    <div>
                                        <strong>Alerts & Delivery</strong>
                                        <p>When a rule fires, alerts are stored, vessel state is updated, and events are streamed to the UI via WebSocket.</p>
                                    </div>
                                </div>
                            </li>
                        </ol>
                    </div>

                    <div className="about-section">
                        <h4 className="about-section-title">Alert Classification</h4>
                        <div className="alert-tier-card tier-integrity">
                            <div className="alert-tier-header">
                                <span className="alert-tier-icon">🔴</span>
                                <strong>Integrity Violations</strong>
                            </div>
                            <p className="alert-tier-description">
                                Hard physics or data integrity violations (teleports, impossible turns, invalid positions).
                                <br />
                                <em>Rare but high severity (70-100)</em>
                            </p>
                        </div>
                        <div className="alert-tier-card tier-suspicious">
                            <div className="alert-tier-header">
                                <span className="alert-tier-icon">🟡</span>
                                <strong>Suspicious / Data Quality</strong>
                            </div>
                            <p className="alert-tier-description">
                                Softer signals (medium teleports, moderate turns, SOG mismatches).
                                <br />
                                <em>More frequent, useful for dashboards (15-60)</em>
                            </p>
                        </div>
                    </div>

                    <div className="about-section">
                        <h4 className="about-section-title">Design Principles</h4>
                        <div className="principles-grid">
                            <div className="principle-item">
                                <strong>High Signal</strong>
                                <p>Integrity alerts should almost never be false positives</p>
                            </div>
                            <div className="principle-item">
                                <strong>Explainable</strong>
                                <p>Every alert includes evidence (dt, distance, speed, rate)</p>
                            </div>
                            <div className="principle-item">
                                <strong>Deterministic</strong>
                                <p>Same input stream → same alerts</p>
                            </div>
                            <div className="principle-item">
                                <strong>Robust</strong>
                                <p>Handles gaps, noise, and missing fields gracefully</p>
                            </div>
                        </div>
                    </div>
                </div>
            </details>
        </section>
    )
}

