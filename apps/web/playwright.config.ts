import { defineConfig, devices } from '@playwright/test'

/**
 * E2E against the Vite dev server. API calls default to `VITE_API_BASE_URL` / localhost:8081;
 * tests mock `/v1/*` routes so the real API is optional.
 *
 * Override the app URL: `BASE_URL=http://127.0.0.1:5174 npm run test:e2e` (e.g. after `vite build && vite preview`).
 * Skip starting webServer by setting `BASE_URL` to an already-running server.
 */
const e2ePort = process.env.E2E_PORT ?? '5174'
const baseURL = process.env.BASE_URL ?? `http://127.0.0.1:${e2ePort}`

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
        command: `npm run dev -- --host 127.0.0.1 --port ${e2ePort} --strictPort`,
        url: baseURL,
        // Always use a fresh server for deterministic local/CI runs.
        reuseExistingServer: false,
        timeout: 120_000,
      },
})
