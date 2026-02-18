import { test, expect } from '@playwright/test';

test('app home shows market overview + headlines', async ({ page }) => {
  await page.goto('/app');

  await expect(page.getByRole('heading', { name: 'VietMarket' })).toBeVisible();
  await expect(page.getByRole('heading', { name: /Market overview/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Headlines' })).toBeVisible();

  // Should render some rows eventually (if API reachable).
  // We allow empty in worst case, but should not error.
  await expect(page.locator('text=History API error')).toHaveCount(0);
});

test('symbol page shows chart + news section', async ({ page }) => {
  await page.goto('/app/symbol/VCB');

  await expect(page.getByRole('heading', { name: 'VCB' })).toBeVisible();
  await expect(page.getByText('Timeframe')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'News' })).toBeVisible();

  await expect(page.locator('text=History API error')).toHaveCount(0);
});
