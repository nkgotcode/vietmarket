import { defineConfig, devices } from '@playwright/test';

const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'on-first-retry',
    extraHTTPHeaders: {
      'x-e2e-bypass': process.env.E2E_BYPASS_TOKEN || 'missing',
    },
  },
  webServer: {
    command: `bash -lc "E2E_BYPASS_AUTH=1 E2E_BYPASS_TOKEN=${process.env.E2E_BYPASS_TOKEN || 'devtoken'} npm run dev -- -p ${PORT}"`,
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
