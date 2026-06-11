import { test, expect } from '@playwright/test'

test.describe('AML shell navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.removeItem('aegisais_access_token')
      localStorage.setItem('aegisais_ui_mode', 'aml')
      localStorage.setItem('aegisais_ui_role', 'admin')
    })
    await page.route('**/v1/integrations/feeds', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          timestamp: new Date().toISOString(),
          feeds: [
            {
              id: 'satellite_ais',
              label: 'Satellite AIS',
              status: 'partial',
              detail: 'adapter not fully configured',
            },
            { id: 'sar_eo', label: 'SAR / EO', status: 'disconnected', detail: null },
            { id: 'rf_sigint', label: 'RF (SIGINT)', status: 'disconnected', detail: null },
          ],
        }),
      })
    })
    await page.route('**/v1/audit/logs**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 1,
            organisation_id: 1,
            timestamp: new Date().toISOString(),
            user_id: 'admin',
            action: 'incident.update',
            resource_id: '123',
            resource_type: 'incident',
            change_summary: 'Incident updated',
            details: {},
            correlation_id: null,
          },
        ]),
      })
    })
    await page.route('**/v1/audit/logs/export/csv**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/csv',
        headers: { 'Content-Disposition': 'attachment; filename="audit_logs_export.csv"' },
        body: 'ID,Timestamp,User ID,Action,Resource ID,Resource Type,Change Summary,Details JSON,Correlation ID\n1,ts,admin,incident.update,123,incident,Incident updated,{},\n',
      })
    })
  })

  test('redirects / to /triage and shows triage queue', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/triage$/)

    const nav = page.getByRole('navigation', { name: 'Main navigation' })
    await expect(nav.getByRole('link', { name: 'Triage' })).toHaveAttribute('aria-current', 'page')

    await expect(page.locator('.alerts-panel')).toBeVisible()
  })

  test('navigates between Triage, Map, Admin, Incidents, and Audit', async ({ page }) => {
    await page.goto('/triage')

    const nav = page.getByRole('navigation', { name: 'Main navigation' })
    const sections = page.getByRole('navigation', { name: 'Product sections' })
    await nav.getByRole('link', { name: 'Map' }).click()
    await expect(page).toHaveURL(/\/map$/)

    await sections.getByRole('link', { name: 'Governance' }).click()
    await nav.getByRole('link', { name: 'Admin' }).click()
    await expect(page).toHaveURL(/\/admin$/)

    await sections.getByRole('link', { name: 'Operations' }).click()
    await nav.getByRole('link', { name: 'Incidents' }).click()
    await expect(page).toHaveURL(/\/incidents$/)
    await expect(page.getByRole('heading', { name: 'Incidents' })).toBeVisible()
    await expect(page.locator('.aml-incidents__detail')).toContainText('Incident details')

    await nav.getByRole('link', { name: 'Triage' }).click()
    await expect(page).toHaveURL(/\/triage$/)

    await sections.getByRole('link', { name: 'Governance' }).click()
    await nav.getByRole('link', { name: 'Audit' }).click()
    await expect(page).toHaveURL(/\/audit$/)
  })

  test('Admin shows feed rows from integrations API (mocked)', async ({ page }) => {
    await page.goto('/admin')
    await expect(page.getByRole('heading', { name: 'Admin & control plane' })).toBeVisible()
    const feedsList = page.getByRole('list', { name: 'Optional feed integrations' })
    await expect(feedsList.getByText('Satellite AIS')).toBeVisible()
    await expect(page.getByText('Partial')).toBeVisible()
    await expect(page.getByText('adapter not fully configured')).toBeVisible()
  })

  test('supports dedicated incident detail route', async ({ page }) => {
    await page.goto('/incidents/123')
    await expect(page).toHaveURL(/\/incidents\/123$/)
    await expect(page.getByRole('link', { name: 'Back to incidents' })).toBeVisible()
  })

  test('shows audit page with admin access message', async ({ page }) => {
    await page.goto('/audit')
    await expect(page.getByRole('heading', { name: 'Audit ledger' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'incident.update' })).toBeVisible()
    await page.getByRole('button', { name: 'Export CSV' }).click()
  })
})
