import { test, expect } from '@playwright/test';

test('app home shows market overview + headlines + pagination', async ({ page }) => {
  await page.goto('/app');

  await expect(page.getByRole('heading', { name: 'VietMarket' })).toBeVisible();
  await expect(page.getByRole('heading', { name: /Market overview/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Headlines' })).toBeVisible();

  await expect(page.locator('text=History API error')).toHaveCount(0);

  const items = page.locator('section:has(h2:has-text("Headlines")) li');
  await expect(items.first()).toBeVisible();

  const count1 = await items.count();
  const btn = page.getByRole('button', { name: /Load more|No more/i }).first();
  if ((await btn.textContent())?.includes('Load more')) {
    await btn.click();
    await expect.poll(async () => await items.count()).toBeGreaterThan(count1);
  }
});

test('symbol page shows chart + news + fundamentals sections', async ({ page }) => {
  await page.goto('/app/symbol/VCB');

  await expect(page.getByRole('heading', { name: 'VCB' })).toBeVisible();
  await expect(page.getByText('Timeframe')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'News' })).toBeVisible();
  await expect(page.getByRole('heading', { name: /Fundamentals/i })).toBeVisible();

  await expect(page.locator('text=History API error')).toHaveCount(0);
});
