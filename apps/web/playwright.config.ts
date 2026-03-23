import { defineConfig, devices } from '@playwright/test'

/**
 * E2E against the Vite dev server. API calls default to `VITE_API_BASE_URL` / localhost:8001;
 * tests mock `/v1/*` routes so the real API is optional.
 *
 * Override the app URL: `BASE_URL=http://127.0.0.1:4173 npm run test:e2e` (e.g. after `vite build && vite preview`).
 * Skip starting webServer by setting `BASE_URL` to an already-running server.
 */
const baseURL = process.env.BASE_URL ?? 'http://127.0.0.1:5174'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [['list']],
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: process.env.BASE_URL
    ? undefined
    : {
        command: 'npm run dev -- --host 127.0.0.1 --port 5174 --strictPort',
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
})
