import { test, expect } from '@playwright/test'

test.describe('AML shell navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.removeItem('aegisais_access_token')
      localStorage.removeItem('aegisais_ui_mode')
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
  })

  test('redirects / to /triage and shows triage queue', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/triage$/)

    const nav = page.getByRole('navigation', { name: 'Main navigation' })
    await expect(nav.getByRole('link', { name: 'Operations' })).toHaveAttribute('aria-current', 'page')

    await expect(page.locator('.alerts-panel')).toBeVisible()
  })

  test('navigates between Operations, Map, Lab, and Admin', async ({ page }) => {
    await page.goto('/triage')

    const nav = page.getByRole('navigation', { name: 'Main navigation' })
    await nav.getByRole('link', { name: 'Map' }).click()
    await expect(page).toHaveURL(/\/map$/)

    await nav.getByRole('link', { name: 'Lab' }).click()
    await expect(page).toHaveURL(/\/lab$/)

    await nav.getByRole('link', { name: 'Admin' }).click()
    await expect(page).toHaveURL(/\/admin$/)

    await nav.getByRole('link', { name: 'Operations' }).click()
    await expect(page).toHaveURL(/\/triage$/)

    await nav.getByRole('link', { name: 'About' }).click()
    await expect(page).toHaveURL(/\/about$/)
  })

  test('Admin shows feed rows from integrations API (mocked)', async ({ page }) => {
    await page.goto('/admin')
    await expect(page.getByRole('heading', { name: 'Admin & control plane' })).toBeVisible()
    const feedsList = page.getByRole('list', { name: 'Optional feed integrations' })
    await expect(feedsList.getByText('Satellite AIS')).toBeVisible()
    await expect(page.getByText('Partial')).toBeVisible()
    await expect(page.getByText('adapter not fully configured')).toBeVisible()
  })
})
