const { test, expect } = require("@playwright/test");
const path = require("path");

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window._DISK_ORGANISER_API_BASE = "http://playwright.local";
  });

  await page.route("**/*", async (route) => {
    const url = route.request().url();
    if (!url.includes("/api/")) {
      return route.continue();
    }
    const json = (payload, status = 200) =>
      route.fulfill({
        status,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

    if (url.endsWith("/api/ops")) return json({ ops: {} });
    if (url.endsWith("/api/analyse/start")) return json({ job_id: "job-playwright-1" });
    if (url.endsWith("/api/scan/cancel")) return json({ cancelled: "job-playwright-1" });
    if (url.endsWith("/api/analyse/reason")) {
      return json({
        op: { id: "op-playwright" },
        summary: { actions: 1, groups: { "Semantic groups": 1 }, bytes: 512 },
        analysis_capabilities: {
          ocr: { available: false, image: false, pdf: false, missing: ["pytesseract"] },
          embeddings: {
            available: false,
            disabled: false,
            model: "all-MiniLM-L6-v2",
            missing: ["sentence-transformers"],
          },
        },
        grouped: {
          "Semantic groups": [
            {
              action: "move",
              from: "/tmp/a.txt",
              to: "/tmp/Organised/a.txt",
              confidence: 0.9,
              reason: "test",
            },
          ],
        },
        actions: [
          {
            action: "move",
            from: "/tmp/a.txt",
            to: "/tmp/Organised/a.txt",
            confidence: 0.9,
            reason: "test",
          },
        ],
      });
    }
    if (url.endsWith("/api/organise/execute")) return json({ executed: [] });
    if (url.endsWith("/api/organise/undo")) return json({ actions: [], summary: {} });
    if (url.endsWith("/api/chat")) return json({ actions: [] });
    return json({});
  });
});

async function installMockEventSource(page) {
  await page.evaluate(() => {
    class MockEventSource {
      static instances = [];

      constructor(url) {
        this.url = url;
        this.onmessage = null;
        this.onerror = null;
        this.closed = false;
        MockEventSource.instances.push(this);
      }

      close() {
        this.closed = true;
      }
    }

    window.EventSource = MockEventSource;
    window.__emitAnalysisEvent = (payload) => {
      const latest = MockEventSource.instances[MockEventSource.instances.length - 1];
      if (latest && typeof latest.onmessage === "function") {
        latest.onmessage({ data: JSON.stringify(payload) });
      }
    };
  });
}

test("analysis cancelled state is visible with interruption messaging", async ({ page }) => {
  const indexPath = path.resolve(__dirname, "..", "index.html");
  const url = process.env.TEST_BASE ? `${process.env.TEST_BASE}/index.html` : `file://${indexPath}`;
  await page.goto(url);
  await installMockEventSource(page);

  await page.click("#nav-organise");
  await page.waitForSelector("#analysis-run");

  await page.click("#analysis-run");
  await page.waitForSelector("#analysis-progress-text");

  await page.evaluate(() => {
    window.__emitAnalysisEvent({ status: "cancelled", error: "cancelled" });
  });

  const progressText = page.locator("#analysis-progress-text");
  await expect(progressText).toContainText("Analysis cancelled");

  // Visual assertion: interruption text remains clearly visible to users.
  await expect(progressText).toHaveCSS("display", "block");
});

test("analysis failed state shows visible alert banner", async ({ page }) => {
  const indexPath = path.resolve(__dirname, "..", "index.html");
  const url = process.env.TEST_BASE ? `${process.env.TEST_BASE}/index.html` : `file://${indexPath}`;
  await page.goto(url);
  await installMockEventSource(page);

  await page.click("#nav-organise");
  await page.waitForSelector("#analysis-run");

  await page.click("#analysis-run");
  await page.waitForSelector("#analysis-progress-text");

  await page.evaluate(() => {
    window.__emitAnalysisEvent({ status: "failed", error: "simulated backend failure" });
  });

  const progressText = page.locator("#analysis-progress-text");
  await expect(progressText).toContainText("Analysis failed");

  const alert = page.locator("#app-alert");
  await expect(alert).toContainText("Analysis failed: simulated backend failure");
  await expect(alert).toHaveClass(/visible/);
  await expect(alert).toHaveCSS("opacity", "1");
});
