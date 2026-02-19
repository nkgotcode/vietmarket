import { test, expect } from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';

const outDir = path.resolve(process.cwd(), '..', '..', 'deploy', 'status');

test('checkpoint-c home wiring + badge screenshot', async ({ page }) => {
  await page.goto('/app');
  await expect(page.getByRole('heading', { name: /v1 analytics \+ health/i })).toBeVisible();
  await expect(page.getByText(/Fresh|Degraded/).first()).toBeVisible();

  fs.mkdirSync(outDir, { recursive: true });
  await page.screenshot({ path: path.join(outDir, 'checkpoint-c-home.png'), fullPage: true });
});

test('checkpoint-c symbol wiring + status screenshot', async ({ page }) => {
  await page.goto('/app/symbol/VCB');
  await expect(page.getByRole('heading', { name: /Ticker intelligence \(v1\)/i })).toBeVisible();
  await expect(page.getByText(/Status:/)).toBeVisible();

  fs.mkdirSync(outDir, { recursive: true });
  await page.screenshot({ path: path.join(outDir, 'checkpoint-c-symbol-vcb.png'), fullPage: true });
});
