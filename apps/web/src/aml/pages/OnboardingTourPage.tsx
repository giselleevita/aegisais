import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { apiClient } from '@/core/api-client'
import './onboarding-tour.css'

type AlertRules = {
  geoFenceMeters: number
  spoofingScore: number
  darkWindowMinutes: number
}

const DEFAULT_RULES: AlertRules = {
  geoFenceMeters: 2500,
  spoofingScore: 72,
  darkWindowMinutes: 45,
}

const DEFAULT_BALTIC_DATA_PATH = 'data/itdae/baltic_replay.ndjson'

function loadStoredRules(): AlertRules {
  try {
    const raw = window.localStorage.getItem('aegis.onboarding.alert-rules')
    if (!raw) return DEFAULT_RULES
    const parsed = JSON.parse(raw) as Partial<AlertRules>
    return {
      geoFenceMeters: Number(parsed.geoFenceMeters) || DEFAULT_RULES.geoFenceMeters,
      spoofingScore: Number(parsed.spoofingScore) || DEFAULT_RULES.spoofingScore,
      darkWindowMinutes: Number(parsed.darkWindowMinutes) || DEFAULT_RULES.darkWindowMinutes,
    }
  } catch {
    return DEFAULT_RULES
  }
}

export default function OnboardingTourPage() {
  const [fleetFile, setFleetFile] = useState<File | null>(null)
  const [importStatus, setImportStatus] = useState<string>('')
  const [isImporting, setIsImporting] = useState(false)

  const [rules, setRules] = useState<AlertRules>(() => loadStoredRules())
  const [rulesSavedAt, setRulesSavedAt] = useState<string>('')

  const [demoMode, setDemoMode] = useState(false)
  const [demoStatus, setDemoStatus] = useState<string>('')
  const [isDemoLoading, setIsDemoLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const status = await apiClient.getReplayStatus()
        if (!cancelled) setDemoMode(status.running)
      } catch {
        if (!cancelled) setDemoStatus('Replay status unavailable. You can still start demo mode.')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const rulesSummary = useMemo(
    () =>
      `Geofence ${rules.geoFenceMeters}m · Spoofing score ${rules.spoofingScore}+ · Dark-window ${rules.darkWindowMinutes}m`,
    [rules]
  )

  const handleFleetImport = async (event: FormEvent) => {
    event.preventDefault()
    if (!fleetFile) {
      setImportStatus('Choose a CSV or NDJSON fleet file first.')
      return
    }

    setIsImporting(true)
    setImportStatus('Uploading fleet data...')
    try {
      const upload = await apiClient.uploadFile(fleetFile)
      setImportStatus(`Fleet import queued from ${upload.filename} (${upload.size_mb.toFixed(2)} MB).`)
    } catch (error) {
      setImportStatus(error instanceof Error ? error.message : 'Fleet import failed.')
    } finally {
      setIsImporting(false)
    }
  }

  const saveRules = (event: FormEvent) => {
    event.preventDefault()
    window.localStorage.setItem('aegis.onboarding.alert-rules', JSON.stringify(rules))
    setRulesSavedAt(new Date().toLocaleTimeString())
  }

  const handleDemoToggle = async (enabled: boolean) => {
    setIsDemoLoading(true)
    setDemoStatus(enabled ? 'Starting Baltic scenario replay...' : 'Stopping replay...')

    try {
      if (enabled) {
        await apiClient.getItdaeBalticGeofences()
        await apiClient.startReplay(DEFAULT_BALTIC_DATA_PATH, 120, true, 150)
        setDemoMode(true)
        setDemoStatus('Demo mode enabled with Baltic scenario loaded.')
      } else {
        await apiClient.stopReplay()
        setDemoMode(false)
        setDemoStatus('Demo mode disabled.')
      }
    } catch (error) {
      setDemoStatus(error instanceof Error ? error.message : 'Unable to update demo mode.')
    } finally {
      setIsDemoLoading(false)
    }
  }

  return (
    <section className="aml-page-pad aml-onboarding" aria-label="Onboarding tour">
      <header className="aml-onboarding__header">
        <h2 className="aml-page-title">Onboarding Tour</h2>
        <p>
          Guided setup for new analysts: import your fleet baseline, tune alert rules, and launch Baltic
          scenario demo mode.
        </p>
      </header>

      <div className="aml-onboarding__grid">
        <article className="aml-onboarding__card">
          <h3>1. Fleet Import Wizard</h3>
          <p>Upload initial vessel lists so triage and watchlist workflows start with known entities.</p>
          <form onSubmit={handleFleetImport} className="aml-onboarding__form">
            <input
              type="file"
              accept=".csv,.json,.ndjson"
              onChange={(event) => setFleetFile(event.target.files?.[0] ?? null)}
            />
            <button type="submit" disabled={isImporting}>
              {isImporting ? 'Importing...' : 'Import Fleet'}
            </button>
          </form>
          {importStatus ? <p className="aml-onboarding__status">{importStatus}</p> : null}
        </article>

        <article className="aml-onboarding__card">
          <h3>2. Alert Rule Configuration</h3>
          <p>Set baseline thresholds for suspicious movement patterns before analysts open live triage.</p>
          <form onSubmit={saveRules} className="aml-onboarding__form aml-onboarding__rules">
            <label>
              Geofence breach distance (m)
              <input
                type="number"
                min={100}
                step={100}
                value={rules.geoFenceMeters}
                onChange={(event) =>
                  setRules((prev) => ({ ...prev, geoFenceMeters: Number(event.target.value) }))
                }
              />
            </label>
            <label>
              Spoofing confidence score
              <input
                type="number"
                min={1}
                max={100}
                value={rules.spoofingScore}
                onChange={(event) =>
                  setRules((prev) => ({ ...prev, spoofingScore: Number(event.target.value) }))
                }
              />
            </label>
            <label>
              AIS dark-window threshold (minutes)
              <input
                type="number"
                min={5}
                step={5}
                value={rules.darkWindowMinutes}
                onChange={(event) =>
                  setRules((prev) => ({ ...prev, darkWindowMinutes: Number(event.target.value) }))
                }
              />
            </label>
            <button type="submit">Save Rules</button>
          </form>
          <p className="aml-onboarding__status">{rulesSummary}</p>
          {rulesSavedAt ? <p className="aml-onboarding__muted">Saved at {rulesSavedAt}</p> : null}
        </article>

        <article className="aml-onboarding__card">
          <h3>3. Demo Mode (Baltic Scenario)</h3>
          <p>
            Toggle demo mode to preload Baltic geofences and begin replay using the default scenario data.
          </p>
          <div className="aml-onboarding__toggle-row">
            <button
              type="button"
              disabled={isDemoLoading || demoMode}
              onClick={() => handleDemoToggle(true)}
            >
              Enable Demo
            </button>
            <button
              type="button"
              disabled={isDemoLoading || !demoMode}
              onClick={() => handleDemoToggle(false)}
            >
              Disable Demo
            </button>
          </div>
          <p className="aml-onboarding__status">{demoStatus || (demoMode ? 'Demo mode active.' : 'Demo mode off.')}</p>
        </article>
      </div>
    </section>
  )
}
