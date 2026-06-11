import { test, expect, type Page } from '@playwright/test'

async function mockAuthAndWatchlistApi(page: Page) {
  await page.route('**/v1/auth/login', async (route) => {
    if (route.request().method() !== 'POST') {
      await route.continue()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access_token: 'e2e-mock-access-token', token_type: 'bearer' }),
    })
  })

  await page.route('**/v1/watchlist', async (route) => {
    const method = route.request().method()
    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
      return
    }
    if (method === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          mmsi: '123456789',
          label: '',
          priority: 'medium',
          added_by_id: 1,
          created_at: new Date().toISOString(),
          is_active: true,
        }),
      })
      return
    }
    if (method === 'DELETE') {
      await route.fulfill({ status: 204, body: '' })
      return
    }
    await route.continue()
  })
}

test.describe('Watchlist smoke', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('aegisais_onboarding_completed', 'true')
      localStorage.removeItem('aegisais_access_token')
      localStorage.setItem('aegisais_ui_mode', 'aml')
      localStorage.setItem('aegisais_ui_role', 'analyst')
    })
    await mockAuthAndWatchlistApi(page)
  })

  test('logs in via UI and shows Watchlist panel', async ({ page }) => {
    await page.goto('/')

    await page.getByPlaceholder('User').fill('e2e-user')
    await page.getByPlaceholder('Password').fill('e2e-pass')
    await page.getByRole('button', { name: 'Sign in' }).click()

    await expect(page.getByText('Signed in')).toBeVisible()

    await page.goto('/watchlist')

    await expect(page.locator('.watchlist-panel')).toBeVisible()
    await expect(page.locator('.watchlist-panel').getByRole('heading', { name: 'Watchlist' })).toBeVisible()
  })
})
