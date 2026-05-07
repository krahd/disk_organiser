const { test, expect } = require("@playwright/test");
const path = require("path");

test("treemap side-panel opens via click and keyboard", async ({ page }) => {
  await page.addInitScript(() => {
    window._DISK_ORGANISER_API_BASE = "http://playwright.local";
  });

  // Prefer local file URL to keep tests independent from external servers.
  const indexPath = path.resolve(__dirname, "..", "index.html");
  const url = process.env.TEST_BASE ? `${process.env.TEST_BASE}/index.html` : `file://${indexPath}`;

  // Stub all API endpoints regardless of origin scheme.
  await page.route("**/*", async (route) => {
    const reqUrl = route.request().url();
    if (!reqUrl.includes("/api/")) {
      return route.continue();
    }

    // stub visualisation endpoint
    if (reqUrl.endsWith("/api/visualisation")) {
      const visual = {
        path: "/",
        size: 1000,
        children: [
          { path: "/dir1/file1.txt", size: 700 },
          { path: "/dir2/file2.txt", size: 300 },
        ],
      };
      return route.fulfill({
        status: 200,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ visualisation: visual }),
      });
    }

    // stub duplicates endpoint
    if (reqUrl.endsWith("/api/duplicates")) {
      return route.fulfill({
        status: 200,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          count: 1,
          duplicates: [
            {
              hash: "abc123",
              files: [
                { path: "/dir1/file1.txt", size: 700 },
                { path: "/dir2/file2.txt", size: 700 },
              ],
            },
          ],
        }),
      });
    }

    return route.fulfill({
      status: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
  });

  await page.goto(url);

  // Open Visualisation view
  await page.click("#nav-visualisation");
  await page.waitForSelector("#vis-run");

  // Trigger visualisation (this will hit our stub)
  await page.click("#vis-run");

  // Wait for the SVG treemap to render
  await page.waitForSelector("#vis-result svg");
  const cells = page.locator("g.treemap-cell");
  const count = await cells.count();
  expect(count).toBeGreaterThan(0);

  // Keyboard activation: focus first cell and press Enter
  await cells.nth(0).focus();
  await page.keyboard.press("Enter");

  const side = page.locator("#side-panel");
  await expect(side).toHaveAttribute("aria-hidden", "false");

  // Click the Find duplicates button inside the side panel
  const findBtn = side.locator("text=Find duplicates in this folder");
  await findBtn.click();

  // Expect the duplicate summary to appear
  await expect(side).toContainText("Found 1 duplicate groups");

  // Close the panel via Escape key
  await page.keyboard.press("Escape");
  await expect(side).toHaveAttribute("aria-hidden", "true");
});
