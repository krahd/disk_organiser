const { test, expect } = require("@playwright/test");
const path = require("path");
const { pathToFileURL } = require("url");

// Browser-owned synthetic responses only; no backend or resource network access.
test.beforeEach(async ({ page }) => {
  const frontendUrl = pathToFileURL(path.resolve(__dirname, "..")).href + "/";
  await page.route("**/*", (route) => {
    if (route.request().url().startsWith(frontendUrl)) return route.continue();
    return route.abort();
  });
  await page.addInitScript(() => {
    window.historyFixture = { rows: {}, details: {}, requests: [], unexpected: [] };
    window.fetch = async (url, options) => {
      const fixture = window.historyFixture;
      fixture.requests.push({ url, options });
      let payload;
      if (url === "/api/ops") payload = { ops: fixture.rows };
      else if (url === "/api/recycle/list") payload = { recycle: fixture.rows };
      else if (url === "/api/ops/synthetic-op/preview") payload = fixture.details;
      else if (url === "/api/organise/undo" || url === "/api/recycle/delete_op") {
        payload = fixture.details;
      } else {
        fixture.unexpected.push(url);
        throw new Error(`Unexpected mocked request: ${url}`);
      }
      return { ok: true, status: 200, json: async () => payload };
    };
  });
  await page.goto(pathToFileURL(path.resolve(__dirname, "..", "index.html")).href);
});

test.afterEach(async ({ page }) => {
  expect(await page.evaluate(() => window.historyFixture.unexpected)).toEqual([]);
});

for (const section of ["organise", "recycle"]) {
  const listId = section === "organise" ? "ops-list" : "recycle-list";
  test(`${section} renders inert history fields literally`, async ({ page }) => {
    const id = '<span data-fixture="id">ID</span> &amp; " 雪';
    const status = '</em><b data-fixture="status">State</b>';
    await page.evaluate(
      ({ id, status }) => {
        window.historyFixture.rows = { [id]: { status } };
      },
      { id, status }
    );
    await page.click(`#nav-${section}`);
    const title = page.locator(`#${listId} > .card > div`).first();
    expect(await title.textContent()).toBe(`Op: ${id} — ${status}`);
    expect(
      await title.locator(":scope > *").evaluateAll((els) => els.map((el) => el.tagName))
    ).toEqual(["STRONG", "EM"]);
    await expect(title.locator("em > *")).toHaveCount(0);
    await expect(page.locator("[data-fixture]")).toHaveCount(0);
    expect(
      await title.locator("*").evaluateAll((els) => els.every((el) => !el.attributes.length))
    ).toBe(true);
    expect(await page.evaluate(() => window.historyFixture.requests)).toEqual([
      { url: section === "organise" ? "/api/ops" : "/api/recycle/list" },
    ]);
  });

  test(`${section} preserves the normal history layout`, async ({ page }, testInfo) => {
    await page.evaluate(() => {
      window.historyFixture.rows = {
        "synthetic-op": {
          status: "complete",
          metadata: { note: "Synthetic history fixture" },
          files: [{ path: "synthetic-report.txt", size: 128 }],
        },
      };
    });
    await page.click(`#nav-${section}`);
    await expect(page.locator(`#${listId} > .card`)).toHaveCount(1);
    const title = page.locator(`#${listId} > .card > div`).first();
    expect(await title.innerHTML()).toBe("<strong>Op:</strong> synthetic-op — <em>complete</em>");
    await expect(page.locator(`#nav-${section}`)).toHaveAttribute("aria-current", "page");
    await page.screenshot({ path: testInfo.outputPath(`${section}-history.png`), fullPage: true });
  });
}

test("all operation details stay literal and replace the previous response", async ({ page }) => {
  const details = {
    status: '</pre><b data-fixture="detail">Text</b><pre>',
    note: "&amp; 雪\nnext",
  };
  await page.evaluate((details) => {
    window.historyFixture.rows = { "synthetic-op": { status: "preview" } };
    window.historyFixture.details = details;
  }, details);
  await page.click("#nav-organise");
  for (const label of ["View Details", "Preview Undo", "Preview Delete"]) {
    await page.locator("#ops-list").getByRole("button", { name: label, exact: true }).click();
    await expect(page.locator("#ops-detail > pre")).toHaveCount(1);
    expect(await page.locator("#ops-detail > pre").textContent()).toBe(
      JSON.stringify(details, null, 2)
    );
    await expect(page.locator("#ops-detail > pre > *")).toHaveCount(0);
    await expect(page.locator("[data-fixture]")).toHaveCount(0);
  }
  await page.evaluate(() => {
    window.historyFixture.details = { status: "second response" };
  });
  await page.getByRole("button", { name: "View Details", exact: true }).click();
  expect(await page.locator("#ops-detail").textContent()).toBe(
    JSON.stringify({ status: "second response" }, null, 2)
  );
  await expect(page.locator("#ops-detail > pre")).toHaveCount(1);
});
