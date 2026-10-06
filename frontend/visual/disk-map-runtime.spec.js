// Actual Chromium UI, serving only local frontend assets. No drive scanner or action API.
const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");
const http = require("http");
const assets = require("../model-assets/bundled.js");
const modelAPI = require("../disk-map-model.js");
const fixture = () => JSON.parse(assets.exampleText);
const base = "http://127.0.0.1:5181";
let server;
const files = {
  "/disk-map.html": ["disk-map.html", "text/html"],
  "/disk-map.css": ["disk-map.css", "text/css"],
  "/disk-map.js": ["disk-map.js", "application/javascript"],
  "/disk-map-model.js": ["disk-map-model.js", "application/javascript"],
  "/disk-map-worker.js": ["disk-map-worker.js", "application/javascript"],
  "/model-assets/bundled.js": ["model-assets/bundled.js", "application/javascript"],
  "/images/logo.svg": ["images/logo.svg", "image/svg+xml"],
};
test.beforeAll(async () => {
  const loaded = Object.fromEntries(
    Object.entries(files).map(([url, [name, type]]) => [
      url,
      { body: fs.readFileSync(path.join(__dirname, "..", name)), type },
    ])
  );
  server = http.createServer((request, response) => {
    const asset = loaded[request.url];
    if (request.method !== "GET" || !asset) {
      response.writeHead(404);
      response.end();
      return;
    }
    response.writeHead(200, { "Content-Type": asset.type, "Cache-Control": "no-store" });
    response.end(asset.body);
  });
  await new Promise((resolve) => server.listen(5181, "127.0.0.1", resolve));
});
test.afterAll(async () => {
  if (server) await new Promise((resolve) => server.close(resolve));
});
test.beforeEach(async ({ page }) => {
  page._unexpected = [];
  page._errors = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (request.method() !== "GET" || url.origin !== base || !files[url.pathname])
      page._unexpected.push(request.url());
  });
  page.on("pageerror", (error) => page._errors.push(error.message));
  await page.goto(`${base}/disk-map.html`);
});
test.afterEach(async ({ page }) => {
  expect(page._unexpected).toEqual([]);
  expect(page._errors).toEqual([]);
});
async function example(page) {
  await page.getByRole("button", { name: "Explore synthetic example" }).click();
  await expect(page.locator("#map-title")).toHaveText("Bundled synthetic example");
  await expect(page.locator("#cancel-import")).toBeHidden();
}
async function open(page, data, name = "synthetic.json") {
  await page.locator("#model-file").setInputFiles({
    name,
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(data)),
  });
  await expect(page.locator("#map-title")).toHaveText(name);
  await expect(page.locator("#cancel-import")).toBeHidden();
}
async function screenshot(page, info, name, pending = false) {
  if (!pending) await expect(page.locator("#cancel-import")).toBeHidden();
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  const png = await page.screenshot({ path: info.outputPath(name), fullPage: true });
  expect(png.readUInt32BE(20)).toBe(height);
  expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBe(height);
}
function emptySnapshot() {
  const m = fixture(),
    root = m.entries.find((e) => e.parent_id === null);
  m.entries = [root];
  m.scan.status = "complete";
  m.scan.errors = [];
  m.scan.exclusions = [];
  m.scan.coverage = {
    ...m.scan.coverage,
    entries_observed: 1,
    status_counts: { observed: 1 },
    hashed_files: 0,
    hash_attempts: 0,
    hashed_bytes: 0,
    hash_status_counts: {},
    complete_within_policy: true,
  };
  m.scan.hash_policy = "metadata_only";
  m.scan.limits.hash_files = false;
  m.directories = [
    {
      ...m.directories.find((d) => d.entry_id === root.id),
      direct_member_ids: [],
      logical_bytes: 0,
      observed_files: 0,
      uncertain_entries: 0,
      coverage: { complete: true, reasons: [] },
    },
  ];
  Object.assign(m.aggregates, {
    logical_bytes_by_path: 0,
    logical_bytes_by_observed_object: 0,
    known_allocated_bytes_by_observed_object: null,
    allocation_unknown_objects: 0,
    object_identity_unknown_paths: 0,
    observed_regular_files: 0,
    distinct_observed_file_objects: 0,
    hard_link_alias_paths: 0,
    status_counts: { observed: 1 },
    by_extension_category: {},
    partial: false,
  });
  m.evidence = [];
  m.findings = [];
  m.relationships = [];
  m.plan_alternatives = [];
  m.changes = { ...m.changes, added: [root.id] };
  modelAPI.validate(m, assets.schema);
  return m;
}

test("desktop map exposes hypotheses, their evidence and non-executable review choices", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await example(page);
  await expect(page.locator("#coverage-banner")).toContainText("Partial snapshot");
  await expect(page.locator("#storage-summary")).toContainText("Physical / recoverable space");
  await screenshot(page, info, "disk-map-desktop-overview.png");
  const project = page
    .locator("#map-results article")
    .filter({ hasText: "Possible directory role: project" });
  await project.getByRole("button", { name: "Inspect evidence" }).click();
  await expect(page.locator("#detail-content")).toContainText("pyproject.toml");
  await expect(page.locator("#detail-content")).toContainText("do not prove purpose");
  await expect(page.locator("#detail-title")).toBeFocused();
  await screenshot(page, info, "disk-map-project-evidence.png");
  await page.getByRole("button", { name: "Compare read-only review choices" }).click();
  await expect(page.locator("#detail-content")).toContainText(
    "Read-only questions, not an organisation plan"
  );
  await expect(page.locator("#detail-content")).toContainText(
    "Relationship confidence is separate"
  );
  await screenshot(page, info, "disk-map-review-choices.png");
  expect(
    await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))
  ).toEqual({ local: 0, session: 0 });
});

test("mobile relationships and path observations remain readable and keyboard accessible", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await example(page);
  await page.getByRole("tab", { name: "Questions", exact: true }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "Folders", exact: true })).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "Relationships", exact: true })).toHaveAttribute(
    "aria-selected",
    "true"
  );
  const family = page
    .locator("#map-results article")
    .filter({ hasText: "Possible versions or exports" });
  await family.getByRole("button", { name: "Inspect evidence" }).click();
  await expect(page.locator("#detail-content")).toContainText("do not prove version lineage");
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  await screenshot(page, info, "disk-map-mobile-relationship.png");
  await page.getByRole("button", { name: "Close details" }).click();
  await expect(family.getByRole("button", { name: "Inspect evidence" })).toBeFocused();
  await page.getByRole("tab", { name: "All entries", exact: true }).click();
  await page.getByLabel("Find a path, group or question").fill("no-such-file");
  await expect(page.locator("#result-count")).toContainText("No matches");
  await screenshot(page, info, "disk-map-mobile-empty-search.png");
});

test("unknown accounting is different from an observed zero and stale freshness is explicit", async ({
  page,
}, info) => {
  const m = fixture();
  m.entries.forEach((e) => {
    e.allocated_bytes = null;
    e.allocation_source = "unknown";
  });
  m.aggregates.known_allocated_bytes_by_observed_object = null;
  m.aggregates.allocation_unknown_objects = m.aggregates.distinct_observed_file_objects;
  m.scan.started_at = "2090-01-01T00:00:00Z";
  await open(page, m, "unknown-allocation.json");
  await expect(page.locator(".metric").filter({ hasText: "Known allocated bytes" })).toContainText(
    "Unknown"
  );
  await page.locator("#scope-details > summary").click();
  await expect(page.locator("#scope-content")).toContainText("Freshness is unknown");
  await screenshot(page, info, "disk-map-unknown-allocation.png");
  await open(page, emptySnapshot(), "zero-observed-files.json");
  await expect(
    page.locator(".metric").filter({ hasText: "Logical size across observed paths" })
  ).toContainText("0 B");
  await expect(
    page.locator(".metric").filter({ hasText: "Physical / recoverable space" })
  ).toContainText("Unknown");
  await expect(page.locator("#map-results")).toContainText("does not prove");
  await screenshot(page, info, "disk-map-observed-zero.png");
});

test("invalid and oversized imports preserve the accepted map and allow the same file again", async ({
  page,
}, info) => {
  await example(page);
  const bad = fixture();
  bad.relationships[0].member_ids = ["unknown-id"];
  await page.locator("#model-file").setInputFiles({
    name: "bad.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(bad)),
  });
  await expect(page.locator("#map-status")).toContainText("missing or repeated reference");
  await expect(page.locator("#map-title")).toHaveText("Bundled synthetic example");
  await screenshot(page, info, "disk-map-rejected-import.png");
  await page.locator("#model-file").setInputFiles({
    name: "large.json",
    mimeType: "application/json",
    buffer: Buffer.alloc(8 * 1024 * 1024 + 1, 32),
  });
  await expect(page.locator("#map-status")).toContainText("was not read");
  await open(page, fixture(), "same.json");
  await expect(page.locator("#model-file")).toHaveValue("");
  await open(page, fixture(), "same.json");
  await expect(page.locator("#model-file")).toHaveValue("");
  await expect(page.locator("#map-status")).toContainText("Export opened");
});

test("imported labels are literal text and clearing removes private snapshot details", async ({
  page,
}, info) => {
  const m = fixture();
  m.findings[0].title = '<img src="https://invalid.example/collect" onerror="alert(1)">';
  m.scan.roots[0].path = "/synthetic-private-path-marker";
  await open(page, m, "private-export.json");
  await expect(page.locator("#map-results")).toContainText("<img src=");
  await expect(page.locator("#map-results img,#map-results script")).toHaveCount(0);
  await expect(page.locator('#map-content a[href^="file:"]')).toHaveCount(0);
  await page.getByRole("button", { name: "Clear this tab" }).click();
  await expect(page.locator("#map-content")).toBeHidden();
  await expect(page.locator("body")).not.toContainText("synthetic-private-path-marker");
  await expect(page.locator("#map-title")).toHaveText("Storage snapshot");
  await screenshot(page, info, "disk-map-cleared.png");
});

test("controlled delayed imports cannot replace a cancelled or cleared view", async ({
  page,
}, info) => {
  await example(page);
  await page.evaluate(() => {
    window.__mapReaders = [];
    window.FileReader = class {
      constructor() {
        this.readyState = 0;
        window.__mapReaders.push(this);
      }
      readAsArrayBuffer() {
        this.readyState = 1;
      }
      abort() {
        this.readyState = 2;
        this.onabort?.();
      }
    };
  });
  await page.locator("#model-file").setInputFiles({
    name: "pending.json",
    mimeType: "application/json",
    buffer: Buffer.from(assets.exampleText),
  });
  await expect(page.locator("#cancel-import")).toBeVisible();
  await screenshot(page, info, "disk-map-opening.png", true);
  await page.getByRole("button", { name: "Cancel opening" }).click();
  await page.evaluate((text) => {
    const reader = window.__mapReaders[0];
    reader.result = new TextEncoder().encode(text).buffer;
    reader.readyState = 2;
    reader.onload();
  }, assets.exampleText);
  await expect(page.locator("#map-title")).toHaveText("Bundled synthetic example");
  await page.locator("#model-file").setInputFiles({
    name: "later.json",
    mimeType: "application/json",
    buffer: Buffer.from(assets.exampleText),
  });
  await page.getByRole("button", { name: "Clear this tab" }).click();
  await page.evaluate((text) => {
    const reader = window.__mapReaders[1];
    reader.result = new TextEncoder().encode(text).buffer;
    reader.readyState = 2;
    reader.onload();
  }, assets.exampleText);
  await expect(page.locator("#map-content")).toBeHidden();
  await expect(page.locator("#map-title")).toHaveText("Storage snapshot");
});

test("complex imports stay off the main thread and reject before expanding the DOM", async ({
  page,
}, info) => {
  await example(page);
  const data = fixture();
  data.scan.uncertainties = Array(200000).fill("");
  await page.evaluate(() => {
    window.__mapBeats = 0;
    window.__mapTimer = setInterval(() => window.__mapBeats++, 1);
  });
  await page.locator("#model-file").setInputFiles({
    name: "complex.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(data)),
  });
  await expect(page.locator("#map-status")).toContainText("bounded presentation limit");
  const beats = await page.evaluate(() => {
    clearInterval(window.__mapTimer);
    return window.__mapBeats;
  });
  expect(beats).toBeGreaterThan(0);
  await expect(page.locator("#map-title")).toHaveText("Bundled synthetic example");
  expect(await page.locator("#map-content *").count()).toBeLessThanOrEqual(7000);
  expect((await page.locator("#map-content").textContent()).length).toBeLessThanOrEqual(
    2 * 1024 * 1024
  );
  await screenshot(page, info, "disk-map-bounded-rejection.png");
});

test("long labels wrap at narrow width and enlarged text while evidence remains bounded", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const data = fixture();
  data.scan.roots[0].path = "/synthetic/" + "Root".repeat(200);
  data.evidence[0].observations = Object.fromEntries(
    Array.from({ length: 120 }, (_, i) => [`${i}-${"Key".repeat(75)}`, "Value ".repeat(300)])
  );
  const finding = data.findings.find((f) => f.evidence_ids.includes(data.evidence[0].id));
  await open(page, data, "LongFilename".repeat(19) + ".json");
  await page.locator("#scope-details > summary").click();
  await page
    .locator("#map-results article")
    .filter({ hasText: finding.title })
    .getByRole("button", { name: "Inspect evidence" })
    .click();
  await expect(page.locator("#detail-content")).toContainText("Showing 10 of 120 evidence fields");
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  await screenshot(page, info, "disk-map-long-labels-mobile.png");
  await page.evaluate(() => {
    document.documentElement.style.fontSize = "200%";
  });
  await expect(page.locator("html")).toHaveCSS("font-size", "32px");
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  await screenshot(page, info, "disk-map-enlarged-text.png");
});

test("member paging retains keyboard focus when the final Next control disappears", async ({
  page,
}, info) => {
  const { flatModel } = require("../__tests__/disk-map-fixtures.js");
  await open(page, flatModel(60), "sixty-synthetic-members.json");
  await page.locator("#map-results").getByRole("button", { name: "Inspect evidence" }).click();
  const next = page.getByRole("button", { name: "Show next 25 members" });
  await next.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#detail-content [role=status]")).toBeFocused();
  await expect(page.locator("#detail-content [role=status]")).toContainText("26–50");
  await next.click();
  await expect(next).toBeHidden();
  await expect(page.locator("#detail-content [role=status]")).toBeFocused();
  await expect(page.locator("#detail-content [role=status]")).toContainText("51–60");
  await screenshot(page, info, "disk-map-member-final-page.png");
  await page.getByRole("button", { name: "Previous members" }).click();
  await expect(page.locator("#detail-content [role=status]")).toContainText("26–50");
});

test("a failed detached render keeps the accepted map and detail intact", async ({
  page,
}, info) => {
  await example(page);
  await page
    .locator("#map-results article")
    .filter({ hasText: "Possible directory role: project" })
    .getByRole("button", { name: "Inspect evidence" })
    .click();
  const before = await page.locator("#map-content").innerHTML();
  await page.evaluate(() => {
    const original = document.createElement.bind(document);
    window.__mapRenderFailure = false;
    document.createElement = function (tag, options) {
      if (tag === "article" && !window.__mapRenderFailure) {
        window.__mapRenderFailure = true;
        throw new Error("Synthetic render preparation failure");
      }
      return original(tag, options);
    };
  });
  await page.locator("#model-file").setInputFiles({
    name: "replacement.json",
    mimeType: "application/json",
    buffer: Buffer.from(assets.exampleText),
  });
  await expect(page.locator("#map-status")).toContainText("previous accepted view is unchanged");
  expect(await page.evaluate(() => window.__mapRenderFailure)).toBe(true);
  expect(await page.locator("#map-content").innerHTML()).toBe(before);
  await screenshot(page, info, "disk-map-preserved-after-render-error.png");
});
