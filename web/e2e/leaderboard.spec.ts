import { test, expect } from '@playwright/test';

test('homepage renders with empty leaderboard', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('h1, h2').first()).toBeVisible();
  // No crash, no error boundary.
});
