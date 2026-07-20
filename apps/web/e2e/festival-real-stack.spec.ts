import { expect, test } from '@playwright/test'

const realStack = process.env.REAL_STACK === '1'
const username = process.env.FESTIVAL_TEST_USERNAME
const password = process.env.FESTIVAL_TEST_PASSWORD

test.describe('Festival real-stack acceptance', () => {
  test.skip(!realStack, 'Set REAL_STACK=1 to run against the isolated Docker acceptance stack')

  test('runs two offline reset → replay → fusion → analyst-map cycles without mocked APIs', async ({ page }) => {
    if (!username || !password) throw new Error('Festival acceptance credentials are required')

    const externalRequests: string[] = []
    await page.route('**/*', async (route) => {
      const url = new URL(route.request().url())
      const localProtocol = url.protocol === 'data:' || url.protocol === 'blob:'
      const localHost = ['localhost', '127.0.0.1', '::1'].includes(url.hostname)
      if (localProtocol || localHost) {
        await route.continue()
        return
      }
      externalRequests.push(url.toString())
      await route.abort('blockedbyclient')
    })

    await page.addInitScript(() => {
      localStorage.setItem('aegisais_onboarding_completed', 'true')
      localStorage.setItem('aegisais_ui_mode', 'aml')
      localStorage.setItem('aegisais_ui_role', 'admin')
    })

    await page.goto('/')
    await page.getByPlaceholder('User').fill(username)
    await page.getByPlaceholder('Password').fill(password)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByText('Signed in')).toBeVisible()
    await expect.poll(() => page.evaluate(() => Boolean(localStorage.getItem('aegisais_access_token')))).toBe(true)

    for (let cycle = 1; cycle <= 2; cycle += 1) {
      await page.goto('/admin')
      await expect.poll(() => page.evaluate(() => Boolean(localStorage.getItem('aegisais_access_token')))).toBe(true)
      await expect(page.getByRole('heading', { name: 'Admin & control plane' })).toBeVisible()
      await page.getByRole('button', { name: 'Reset' }).click()
      await expect(page.getByText(/State: idle/)).toBeVisible()
      await page.getByRole('button', { name: 'Start 3-minute demo' }).click()
      await expect(page.getByText(/State: (starting|running)/)).toBeVisible()
      await expect(page.getByText(/State: completed/)).toBeVisible({ timeout: 15_000 })
      await expect(page.getByText(/5\/5 observations/)).toBeVisible()
      await expect(page.getByText(/[1-9][0-9]* fused alerts/)).toBeVisible({ timeout: 10_000 })

      await page.goto('/map')
      await expect(page.getByText(/Natural Earth Baltic vector basemap loaded locally/)).toBeVisible()
      await expect(page.getByRole('checkbox', { name: 'SAR detections' })).toBeChecked()
      const mapSummary = page.locator('p.sr-only[role="status"]')
      await expect(mapSummary).toContainText(/[1-9][0-9]* SAR detections/, { timeout: 10_000 })
      await expect(mapSummary).toContainText(/[1-9][0-9]* fused events/)
    }

    expect(externalRequests, `External requests attempted: ${externalRequests.join(', ')}`).toEqual([])
  })
})
