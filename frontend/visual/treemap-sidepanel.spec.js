const { test, expect } = require('@playwright/test');

test('treemap side-panel opens via click and keyboard', async ({ page }) => {
  // base URL is configurable via TEST_BASE environment variable for CI flexibility
  const base = process.env.TEST_BASE || 'http://127.0.0.1:8000';

  // stub visualisation endpoint
  await page.route('**/api/visualisation', async (route) => {
    const visual = {
      path: '/',
      size: 1000,
      children: [
        { path: '/dir1/file1.txt', size: 700 },
        { path: '/dir2/file2.txt', size: 300 },
      ],
    };
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ visualisation: visual }),
    });
  });

  // stub duplicates endpoint
  await page.route('**/api/duplicates', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        count: 1,
        duplicates: [
          {
            hash: 'abc123',
            files: [
              { path: '/dir1/file1.txt', size: 700 },
              { path: '/dir2/file2.txt', size: 700 },
            ],
          },
        ],
      }),
    });
  });

  await page.goto(`${base}/index.html`);

  // Open Visualisation view
  await page.click('#nav-visualisation');
  await page.waitForSelector('#vis-run');

  // Trigger visualisation (this will hit our stub)
  await page.click('#vis-run');

  // Wait for the SVG treemap to render
  await page.waitForSelector('#vis-result svg');
  const cells = page.locator('g.treemap-cell');
  const count = await cells.count();
  expect(count).toBeGreaterThan(0);

  // Keyboard activation: focus first cell and press Enter
  await cells.nth(0).focus();
  await page.keyboard.press('Enter');

  const side = page.locator('#side-panel');
  await expect(side).toHaveAttribute('aria-hidden', 'false');

  // Click the Find duplicates button inside the side panel
  const findBtn = side.locator('text=Find duplicates in this folder');
  await findBtn.click();

  // Expect the duplicate summary to appear
  await expect(side.locator('text=Found 1 duplicate groups')).toBeVisible();

  // Close the panel via Escape key
  await page.keyboard.press('Escape');
  await expect(side).toHaveAttribute('aria-hidden', 'true');
});
