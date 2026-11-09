import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e', fullyParallel: false, workers: 1, timeout: 90_000,
  expect: { timeout: 12_000 }, retries: 0,
  use: { baseURL: 'http://127.0.0.1:5180', trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 } } }],
  webServer: [
    { command: 'node scripts/e2e-api.mjs', url: 'http://127.0.0.1:8811/readiness', timeout: 120_000, reuseExistingServer: false },
    { command: 'npm run dev -- --host 127.0.0.1 --port 5180 --strictPort', url: 'http://127.0.0.1:5180', env: { VITE_API_BASE_URL: 'http://127.0.0.1:8811/api/v1' }, timeout: 60_000, reuseExistingServer: false },
  ],
});
