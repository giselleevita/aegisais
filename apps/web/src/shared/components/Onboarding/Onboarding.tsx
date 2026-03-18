import { useState } from 'react'
import './Onboarding.css'

interface OnboardingProps {
    onComplete: () => void
    onSkip: () => void
}

export default function Onboarding({ onComplete, onSkip }: OnboardingProps) {
    const [currentStep, setCurrentStep] = useState(0)

    const steps = [
        {
            title: "Welcome to AegisAIS",
            content: (
                <div>
                    <p>AegisAIS is an AIS data integrity and anomaly detection tool.</p>
                    <p>This quick tour will show you how to use it.</p>
                </div>
            ),
        },
        {
            title: "1. Upload Your Data",
            content: (
                <div>
                    <p><strong>Step 1:</strong> Go to the sidebar and drag & drop your AIS data file</p>
                    <p>Supported formats: CSV, DAT, .csv.zst, .dat.zst</p>
                    <p>The system will automatically start processing your file.</p>
                </div>
            ),
        },
        {
            title: "2. Monitor Processing",
            content: (
                <div>
                    <p><strong>Step 2:</strong> Watch the Dashboard tab to see:</p>
                    <ul>
                        <li>Processing progress</li>
                        <li>Vessel count</li>
                        <li>Alert statistics</li>
                    </ul>
                </div>
            ),
        },
        {
            title: "3. View Alerts",
            content: (
                <div>
                    <p><strong>Step 3:</strong> Go to the Alerts tab to:</p>
                    <ul>
                        <li>Filter alerts by type, severity, status, or time</li>
                        <li>Update alert status (reviewed, resolved, false positive)</li>
                        <li>Add notes to alerts</li>
                        <li>Export alerts as CSV or JSON</li>
                    </ul>
                </div>
            ),
        },
        {
            title: "4. Explore Vessels",
            content: (
                <div>
                    <p><strong>Step 4:</strong> Use the Vessels tab to:</p>
                    <ul>
                        <li>View all tracked vessels</li>
                        <li>Filter by alert severity</li>
                        <li>Click any vessel to see detailed information</li>
                    </ul>
                </div>
            ),
        },
        {
            title: "5. Visualize on Map",
            content: (
                <div>
                    <p><strong>Step 5:</strong> Check the Map tab to:</p>
                    <ul>
                        <li>See vessel positions on an interactive map</li>
                        <li>View alert locations</li>
                        <li>Visualize vessel tracks</li>
                        <li>Click vessels to view details</li>
                    </ul>
                </div>
            ),
        },
        {
            title: "6. Vessel Details",
            content: (
                <div>
                    <p><strong>Step 6:</strong> When viewing a vessel, you can see:</p>
                    <ul>
                        <li><strong>Overview:</strong> Alert statistics and summary</li>
                        <li><strong>Alerts:</strong> All alerts for this vessel</li>
                        <li><strong>Track:</strong> Historical position track on map</li>
                    </ul>
                </div>
            ),
        },
        {
            title: "You're Ready!",
            content: (
                <div>
                    <p>You now know how to use AegisAIS!</p>
                    <p><strong>Tip:</strong> Check the "About AegisAIS" section in the sidebar for more information about alert types and detection rules.</p>
                    <p>Ready to get started? Upload your first file!</p>
                </div>
            ),
        },
    ]

    const handleNext = () => {
        if (currentStep < steps.length - 1) {
            setCurrentStep(currentStep + 1)
        } else {
            onComplete()
        }
    }

    const handlePrevious = () => {
        if (currentStep > 0) {
            setCurrentStep(currentStep - 1)
        }
    }

    return (
        <div className="onboarding-overlay">
            <div className="onboarding-modal">
                <div className="onboarding-header">
                    <h2>{steps[currentStep].title}</h2>
                    <button className="onboarding-close" onClick={onSkip}>
                        ✕
                    </button>
                </div>
                
                <div className="onboarding-content">
                    {steps[currentStep].content}
                </div>

                <div className="onboarding-progress">
                    {steps.map((_, index) => (
                        <div
                            key={index}
                            className={`progress-dot ${index === currentStep ? 'active' : ''} ${index < currentStep ? 'completed' : ''}`}
                        />
                    ))}
                </div>

                <div className="onboarding-actions">
                    <button
                        onClick={onSkip}
                        className="btn-skip"
                    >
                        Skip Tour
                    </button>
                    <div className="onboarding-nav">
                        <button
                            onClick={handlePrevious}
                            disabled={currentStep === 0}
                            className="btn-prev"
                        >
                            Previous
                        </button>
                        <button
                            onClick={handleNext}
                            className="btn-next"
                        >
                            {currentStep === steps.length - 1 ? 'Get Started' : 'Next'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
