import { expect, test, type Page } from '@playwright/test'

type MockClaims = {
  sub: string
  role: string
  clearances: string[]
  releasability: string[]
  licenses: string[]
  org_id?: string
}

function tokenPayload(claims: Record<string, unknown>): string {
  const bytes = new TextEncoder().encode(JSON.stringify(claims))
  let binary = ''
  bytes.forEach((b) => {
    binary += String.fromCharCode(b)
  })
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

async function mockMissionApi(page: Page, getClaims: () => MockClaims) {
  let currentAlertStatus = 'new'

  await page.route('**/v1/auth/context', async (route) => {
    const claims = getClaims()
    const clearances = claims.clearances.map((value) => String(value).toUpperCase())
    const releasability = claims.releasability.map((value) => String(value).toUpperCase())
    const licenses = claims.licenses.map((value) => String(value))

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        viewer: {
          userId: claims.sub,
          organizationId: claims.org_id ?? 'e2e-org',
          role: claims.role,
          clearances,
          releasability,
          licenses,
        },
        claims: {
          role: claims.role,
          clearances,
          releasability,
          licenses,
        },
        timestamp: new Date().toISOString(),
      }),
    })
  })

  await page.route('**/v1/layers/manifest', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        generatedAt: new Date().toISOString(),
        layers: [
          {
            id: 'ports-major',
            name: 'Major Ports',
            domain: 'ports',
            licensedFeature: 'ports:read',
            updatedAt: new Date().toISOString(),
            source: 'telegeography',
            objectKeyPrefix: 'telegeography/ports/major',
          },
        ],
      }),
    })
  })

  await page.route('**/v1/replay/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ running: false, processed: 0 }),
    })
  })

  await page.route('**/v1/vessels?**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          mmsi: '111000111',
          lat: 57.6,
          lon: 18.5,
          sog: 11.2,
          heading: 220,
          timestamp: new Date().toISOString(),
          last_alert_severity: 74,
        },
      ]),
    })
  })

  await page.route('**/v1/vessels/*/track**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { lat: 57.5, lon: 18.3, timestamp: new Date().toISOString() },
        { lat: 57.6, lon: 18.5, timestamp: new Date().toISOString() },
      ]),
    })
  })

  await page.route('**/v1/watchlist**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })

  await page.route('**/v1/sanctions/watchlist/sync', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'synced',
        source: 'OFAC SDN + EU Consolidated',
        mmsi_count: 14,
        imo_count: 6,
        name_count: 9,
      }),
    })
  })

  await page.route('**/v1/alerts?**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 101,
          type: 'TELEPORT',
          severity: 82,
          mmsi: '111000111',
          summary: 'Unrealistic position jump near critical corridor',
          timestamp: new Date().toISOString(),
          status: currentAlertStatus,
          notes: null,
          evidence: { p2_lat: 57.6, p2_lon: 18.5 },
        },
      ]),
    })
  })

  await page.route('**/v1/alerts/101/status', async (route) => {
    const body = route.request().postDataJSON() as { status?: string } | undefined
    currentAlertStatus = body?.status ?? currentAlertStatus
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 101,
        type: 'TELEPORT',
        severity: 82,
        mmsi: '111000111',
        summary: 'Unrealistic position jump near critical corridor',
        timestamp: new Date().toISOString(),
        status: currentAlertStatus,
        notes: null,
        evidence: { p2_lat: 57.6, p2_lon: 18.5 },
      }),
    })
  })

  await page.route('**/v1/alerts/101', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 101,
        type: 'TELEPORT',
        severity: 82,
        mmsi: '111000111',
        summary: 'Unrealistic position jump near critical corridor',
        timestamp: new Date().toISOString(),
        status: 'new',
        notes: 'Investigate immediately',
        evidence: { p2_lat: 57.6, p2_lon: 18.5 },
      }),
    })
  })

  await page.route('**/v1/incidents?**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 9001,
          title: 'Baltic corridor anomaly',
          status: 'triaged',
          evidence_bundle: { alert_ids: [101] },
        },
      ]),
    })
  })

  await page.route('**/v1/incidents/9001', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 9001,
        title: 'Baltic corridor anomaly',
        status: 'triaged',
        evidence_bundle: { alert_ids: [101], notes: 'Cross-check sensor fusion' },
      }),
    })
  })

  await page.route('**/v1/audit/logs**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 12,
          timestamp: new Date().toISOString(),
          user_id: 'ops-lead',
          action: 'incident.update',
          resource_id: '9001',
          resource_type: 'incident',
          change_summary: 'Status set to triaged',
          details: {},
        },
      ]),
    })
  })
}

test.describe('Mission workflow', () => {
  let currentClaims: MockClaims

  test.beforeEach(async ({ page }) => {
    const claims = {
      sub: 'e2e-admin',
      role: 'admin',
      clearances: ['SECRET'],
      releasability: ['NATO'],
      licenses: ['ports:read', 'aviation:read', 'admin:org'],
    }
    currentClaims = claims
    const token = `header.${tokenPayload(claims)}.sig`

    await page.addInitScript((bootToken) => {
      localStorage.setItem('aegisais_access_token', bootToken)
      localStorage.setItem('aegisais_ui_role', 'admin')
      localStorage.setItem('aegisais_ui_mode', 'aml')
      localStorage.setItem('aegisais_onboarding_completed', 'true')
    }, token)

    await mockMissionApi(page, () => currentClaims)
  })

  test('covers analyst triage to governance flow', async ({ page }) => {
    await page.goto('/triage')
    await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeVisible()
    await expect(page.locator('.alerts-panel')).toBeVisible()

    await page.locator('.alerts-panel').press('r')
    await expect(page.locator('.status-badge.status-reviewed').first()).toBeVisible()

    await page.getByRole('link', { name: 'Investigate' }).first().click()
    await expect(page).toHaveURL(/\/alerts\/101$/)

    await page.getByRole('link', { name: 'Map + vessel' }).click()
    await expect(page).toHaveURL(/\/triage\?mmsi=111000111$/)

    await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Incidents' }).click()
    await expect(page).toHaveURL(/\/incidents$/)

    await page.getByRole('link', { name: /#9001 Baltic corridor anomaly/ }).click()
    await expect(page).toHaveURL(/\/incidents\/9001$/)
    await expect(page.getByText('Evidence bundle')).toBeVisible()

    const nav = page.getByRole('navigation', { name: 'Main navigation' })
    await nav.getByRole('link', { name: 'Governance' }).click()
    await nav.getByRole('link', { name: 'Audit' }).click()
    await expect(page).toHaveURL(/\/audit$/)
    await expect(page.getByRole('cell', { name: 'incident.update' })).toBeVisible()
  })

  test('supports field keyboard shortcuts and visual modes', async ({ page }) => {
    await page.goto('/triage')
    await expect(page.getByRole('navigation', { name: 'Breadcrumb' })).toBeVisible()

    await page.keyboard.press('Alt+2')
    await expect(page).toHaveURL(/\/map$/)

    await page.keyboard.press('ControlOrMeta+K')
    await expect(page.getByRole('dialog', { name: 'Command palette' })).toBeVisible()
    await page.getByPlaceholder('Type a command or page...').fill('watchlist')
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/\/watchlist$/)

    await page.keyboard.press('ControlOrMeta+K')
    await page.getByPlaceholder('Type a command or page...').fill('open audit')
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/\/audit$/)

    await page.keyboard.press('?')
    await expect(page.getByRole('dialog', { name: 'Keyboard shortcuts' })).toBeVisible()

    await page.keyboard.press('Alt+H')
    await expect(page.locator('.aml-app')).toHaveClass(/aml-app--high-contrast/)

    await page.keyboard.press('Alt+6')
    await expect(page).toHaveURL(/\/admin$/)
  })

  test('covers intelligence policy redirects for the globe route', async ({ page }) => {
    const restrictedClaims = {
      sub: 'e2e-analyst',
      role: 'analyst',
      clearances: ['RESTRICTED'],
      releasability: ['NATO'],
      licenses: ['ports:read'],
    }
    const restrictedToken = `header.${tokenPayload(restrictedClaims)}.sig`

    await page.goto('/triage')
    await expect(
      page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Intelligence' })
    ).toBeVisible()

    currentClaims = restrictedClaims
    await page.evaluate((nextToken) => {
      localStorage.setItem('aegisais_access_token', nextToken)
      localStorage.setItem('aegisais_ui_role', 'analyst')
      window.dispatchEvent(new Event('aegisais-auth-changed'))
    }, restrictedToken)

    await page.goto('/globe')
    await expect(page).toHaveURL(/\/triage$/)
    await expect(page.getByText('Globe requires CONFIDENTIAL clearance.')).toBeVisible()
  })

  test('covers supervisor sanctions flow and empty-state resilience', async ({ page }) => {
    await page.goto('/')

    await page.evaluate(() => {
      localStorage.setItem('aegisais_ui_role', 'supervisor')
      window.dispatchEvent(new Event('aegisais-auth-changed'))
    })

    await page.route('**/v1/watchlist', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })
    await page.route('**/v1/incidents?**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })
    await page.route('**/v1/alerts?**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })
    await page.route('**/v1/vessels?**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })

    await page.goto('/sanctions')
    await expect(page.getByRole('heading', { name: 'Sanctions & Watchlist' })).toBeVisible()
    await page.getByRole('button', { name: 'Sync Now' }).click()
    await expect(page.getByText('Sync Complete')).toBeVisible()
    await expect(page.getByText('OFAC SDN + EU Consolidated')).toBeVisible()

    await page.goto('/triage')
    await expect(page.getByText('No alerts found')).toBeVisible()

    await page.goto('/incidents')
    await expect(page.getByText('No incidents found.')).toBeVisible()
  })

  test('covers redesigned governance and control-plane surfaces', async ({ page }) => {
    await page.goto('/incidents')
    await expect(page.getByRole('heading', { name: 'Incident registry' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Case queue' })).toBeVisible()
    await expect(page.getByRole('combobox', { name: 'Filter incidents by status' })).toBeVisible()

    await page.getByRole('link', { name: /#9001 Baltic corridor anomaly/ }).click()
    await expect(page).toHaveURL(/\/incidents\/9001$/)
    await expect(page.getByRole('heading', { name: 'Incident #9001' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Disposition' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Evidence bundle' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Activity timeline' })).toBeVisible()

    await page.goto('/audit')
    await expect(page.getByRole('heading', { name: 'Audit ledger' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Export CSV' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'incident.update' })).toBeVisible()

    await page.goto('/admin')
    await expect(page.getByRole('heading', { name: 'Admin & control plane' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'External feeds' })).toBeVisible()
    await expect(page.getByText('Satellite AIS')).toBeVisible()
  })
})
