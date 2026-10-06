// Real browser + local Flask; all paths below are newly-created synthetic fixtures.
const { test, expect } = require("@playwright/test");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");
let base, server;
const url = "http://127.0.0.1:5179/ui/";
test.describe.configure({ mode: "serial" });
async function startServer(enableCopies = true) {
  const env = {
    ...process.env,
    DISK_ORGANISER_DATA_DIR: path.join(base, "state"),
    DISK_ORGANISER_OPEN_BROWSER: "0",
    MODEL_PROVIDER: "local_only",
  };
  if (enableCopies) env.DISK_ORGANISER_ENABLE_GUIDED_COPIES = "1";
  else delete env.DISK_ORGANISER_ENABLE_GUIDED_COPIES;
  server = spawn(
    "python",
    ["-c", "from backend.app import app; app.run(host='127.0.0.1',port=5179,debug=False)"],
    {
      env,
      stdio: "pipe",
    }
  );
  let logs = "";
  server.stderr.on("data", (chunk) => {
    logs += chunk;
  });
  for (let i = 0; i < 100; i++) {
    if (server.exitCode !== null) throw new Error(logs);
    try {
      if ((await fetch(url)).ok) return;
    } catch (_) {}
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`Synthetic server did not start: ${logs}`);
}
async function stopServer() {
  if (!server || server.exitCode !== null) return;
  const closed = new Promise((resolve) => server.once("exit", resolve));
  server.kill();
  await closed;
}
function folder(name, entries) {
  const root = path.join(base, name);
  fs.mkdirSync(root);
  for (const [name, content] of entries) fs.writeFileSync(path.join(root, name), content);
  return root;
}
async function scan(page, root, copies = false) {
  await page.goto(url);
  if (copies) await page.getByRole("radio", { name: "Explore an organised copy" }).check();
  await page.getByLabel("Absolute folder path").fill(root);
  await page.getByRole("button", { name: "Scan and preview" }).click();
  await expect(page.getByRole("heading", { name: "2. Understand this folder" })).toBeVisible();
}
async function screenshot(page, testInfo, name) {
  // History can expand after the overview heading appears. Capture completed
  // states only once the whole operation is idle; loading is intentionally held.
  if (name !== "guided-loading.png") await expect(page.locator("#refresh")).toBeEnabled();
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  const png = await page.screenshot({ path: testInfo.outputPath(name), fullPage: true });
  expect(png.readUInt32BE(20)).toBe(height);
  expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBe(height);
}
test.beforeAll(async () => {
  base = fs.mkdtempSync(path.join(os.tmpdir(), "disk-guided-ux-"));
  await startServer();
});
test.afterAll(stopServer);
test.beforeEach(async ({ page }) => {
  const pageErrors = [],
    external = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (request) => {
    if (!request.url().startsWith("http://127.0.0.1:5179/")) external.push(request.url());
  });
  page._errors = pageErrors;
  page._external = external;
});
test.afterEach(async ({ page }) => {
  expect(page._errors).toEqual([]);
  expect(page._external).toEqual([]);
});

test("overview, exact approval, verified copies and retained history on desktop/mobile", async ({
  page,
}, testInfo) => {
  const root = folder("Example folder", [
    ["Project notes.txt", "Synthetic document\n"],
    ["Cover.png", "Synthetic image bytes\n"],
    ["Unknown.xyz", "Left unchanged\n"],
  ]);
  await scan(page, root);
  await expect(page.locator("#copy-effects")).toBeHidden();
  await expect(page.locator("#preview")).toContainText("2 supported files");
  await expect(page.locator("#preview")).toContainText("1 entry left out");
  await screenshot(page, testInfo, "guided-desktop-overview.png");
  await page.getByRole("button", { name: "Review the copy layout" }).click();
  await expect(page.locator("#apply")).toBeDisabled();
  expect(fs.readdirSync(root).filter((name) => name.startsWith("Organised-"))).toHaveLength(0);
  await screenshot(page, testInfo, "guided-desktop-preview.png");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page
      .locator("#preview td")
      .first()
      .evaluate((el) => getComputedStyle(el).display)
  ).toBe("block");
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  await screenshot(page, testInfo, "guided-mobile-preview.png");
  await page.locator("#approve").check();
  await page.locator("#apply").click();
  await expect(page.locator("#status")).toContainText("Verified 2 copies");
  const output = fs.readdirSync(root).find((name) => name.startsWith("Organised-"));
  expect(fs.readFileSync(path.join(root, output, "Documents", "Project notes.txt"), "utf8")).toBe(
    "Synthetic document\n"
  );
  await page.reload();
  await expect(page.locator("#history")).toContainText("Copies verified");
  await expect(page.locator("#history")).toContainText("Automatic copy removal is unavailable");
  await expect(page.locator("#history input[type=checkbox]")).toHaveCount(0);
  expect(fs.existsSync(path.join(root, output))).toBe(true);
  expect(fs.readFileSync(path.join(root, "Project notes.txt"), "utf8")).toBe(
    "Synthetic document\n"
  );
  await screenshot(page, testInfo, "guided-retained-result.png");
});

test("keyboard choice and closing an approved preview do not perform a file operation", async ({
  page,
}, testInfo) => {
  const root = folder("Keyboard example", [["Notes.txt", "Synthetic keyboard fixture"]]);
  await page.goto(url);
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to folder choices" })).toBeFocused();
  const understand = page.getByRole("radio", { name: "Understand what is here" });
  await understand.focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("radio", { name: "Explore an organised copy" })).toBeChecked();
  await page.getByLabel("Absolute folder path").fill(root);
  await page.getByRole("button", { name: "Scan and preview" }).click();
  await expect(page.getByRole("heading", { name: "2. Understand this folder" })).toBeFocused();
  await page.locator("#approve").check();
  await page.getByRole("button", { name: "Close preview" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#preview")).toBeHidden();
  await expect(page.locator("#root")).toBeFocused();
  expect(fs.readdirSync(root)).toEqual(["Notes.txt"]);
  await screenshot(page, testInfo, "guided-closed-preview.png");
});

test("empty supported set explains skipped files without claiming an empty folder", async ({
  page,
}, testInfo) => {
  const root = folder("Unsupported example", [
    ["Unrecognised.xyz", "Synthetic unsupported fixture"],
  ]);
  fs.mkdirSync(path.join(root, "Nested"));
  await scan(page, root);
  await expect(page.locator("#preview")).toContainText("does not mean the folder is empty");
  await expect(page.locator("#apply")).toHaveCount(0);
  await page.getByText("2 entries left out: see why").click();
  await screenshot(page, testInfo, "guided-empty-supported.png");
});

test("500-file list stays bounded and filtering does not change copy scope", async ({
  page,
}, testInfo) => {
  const root = folder(
    "Many files",
    Array.from({ length: 500 }, (_, i) => [
      `Project-${String(i).padStart(3, "0")}-synthetic-long-name-for-layout.txt`,
      `Synthetic ${i}`,
    ])
  );
  await scan(page, root, true);
  await expect(page.locator("#preview tbody tr")).toHaveCount(25);
  await page.locator("#approve").check();
  await page.getByRole("button", { name: "Next 25" }).click();
  await expect(page.locator("#approve")).not.toBeChecked();
  await page.getByLabel("Find a file or destination").fill("Project-499");
  await expect(page.locator("#preview tbody tr")).toHaveCount(1);
  await expect(page.locator("#apply")).toHaveText("Create 500 reviewed copies");
  await expect(page.locator("#preview")).toContainText("Full plan: 500 copies");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  await screenshot(page, testInfo, "guided-large-list-filtered.png");
});

test("loading and uncertain apply never invite an automatic retry", async ({ page }, testInfo) => {
  const root = folder("Interrupted example", [["Notes.txt", "Synthetic interrupted fixture"]]);
  let release;
  const waitForRelease = new Promise((resolve) => {
    release = resolve;
  });
  await page.route("**/api/guided/plans", async (route) => {
    if (route.request().method() === "POST") await waitForRelease;
    return route.continue();
  });
  await page.goto(url);
  await page.getByRole("radio", { name: "Explore an organised copy" }).check();
  await page.getByLabel("Absolute folder path").fill(root);
  await page.getByRole("button", { name: "Scan and preview" }).click();
  await expect(page.locator("#status")).toContainText("Reading this folder");
  await expect(page.locator("#scan")).toBeDisabled();
  await screenshot(page, testInfo, "guided-loading.png");
  release();
  await expect(page.locator("#approve")).toBeVisible();
  await page.route("**/apply", (route) => route.abort("connectionfailed"));
  await page.locator("#approve").check();
  await page.locator("#apply").click();
  await expect(page.locator("#status")).toContainText("not confirmed");
  await expect(page.locator("#scan")).toBeDisabled();
  await expect(page.locator("#apply")).toHaveCount(0);
  await screenshot(page, testInfo, "guided-uncertain-result.png");
  await page.getByRole("button", { name: "Refresh session and history" }).click();
  await expect(page.locator("#scan")).toBeEnabled();
  expect(fs.readdirSync(root)).toEqual(["Notes.txt"]);
});

test("restart makes saved preview read-only and requires a deliberate new scan", async ({
  page,
}, testInfo) => {
  const root = folder("Restart example", [["Notes.txt", "Synthetic restart fixture"]]);
  await scan(page, root, true);
  await expect(page.locator("#apply")).toBeDisabled();
  await stopServer();
  await startServer();
  await page.reload();
  const record = page.locator(".history-item").filter({ hasText: root });
  await expect(record).toContainText("Preview needs a new scan");
  await record.getByRole("button", { name: "Review saved preview" }).click();
  await page.getByRole("button", { name: "Review the copy layout" }).click();
  await expect(page.locator("#apply")).toHaveCount(0);
  await expect(page.locator("#preview")).toContainText("Scan the folder again");
  await screenshot(page, testInfo, "guided-restart-read-only.png");
  await page.getByRole("button", { name: "Choose this folder for a new scan" }).click();
  await expect(page.locator("#root")).toHaveValue(root);
  await expect(page.locator("#preview")).toBeHidden();
  expect(fs.readdirSync(root)).toEqual(["Notes.txt"]);
});

test("default build remains read-only even after reviewing a complete layout", async ({
  page,
}, testInfo) => {
  await stopServer();
  await startServer(false);
  const root = folder("Read only default", [["Notes.txt", "Synthetic read-only fixture"]]);
  await scan(page, root, true);
  await expect(page.locator("#safety-title")).toContainText("Read-only preview");
  await expect(page.locator("#preview")).toContainText("scanning again will not enable it");
  await expect(page.locator("#apply")).toHaveCount(0);
  await expect(page.locator("#approve")).toHaveCount(0);
  expect(fs.readdirSync(root)).toEqual(["Notes.txt"]);
  await screenshot(page, testInfo, "guided-read-only-default.png");
});

test("read-only session survives backend restart after deliberate refresh without page reload", async ({
  page,
}, testInfo) => {
  const root = folder("Session restart read only", [
    ["Notes.txt", "Synthetic session-only fixture"],
  ]);
  await scan(page, root);
  let posts = 0;
  page.on("request", (request) => {
    if (request.method() === "POST") posts++;
  });
  await stopServer();
  await startServer(false);
  await page.getByRole("button", { name: "Scan and preview" }).click();
  await expect(page.locator("#status")).toContainText("No request is retried automatically");
  await expect(page.locator("#scan")).toBeDisabled();
  expect(posts).toBe(1);
  await page.getByRole("button", { name: "Refresh session and history" }).click();
  await expect(page.locator("#scan")).toBeEnabled();
  expect(posts).toBe(1);
  await page.getByRole("button", { name: "Scan and preview" }).click();
  await expect(page.locator("#status")).toContainText("Overview saved");
  expect(posts).toBe(2);
  await expect(page.locator("#apply")).toHaveCount(0);
  expect(fs.readdirSync(root)).toEqual(["Notes.txt"]);
  await screenshot(page, testInfo, "guided-session-reconnected.png");
});

test("unsupported scanning preserves readable history without offering a scan", async ({
  page,
}, testInfo) => {
  await page.route("**/api/guided/session", (route) =>
    route.fulfill({
      json: {
        token: "read-only-test",
        capabilities: { scan: { enabled: false }, copy_apply: { enabled: false } },
      },
    })
  );
  await page.route("**/api/guided/plans", (route) =>
    route.fulfill({
      json: {
        plans: [],
        blocked_records: 0,
        capabilities: { scan: { enabled: false }, copy_apply: { enabled: false } },
      },
    })
  );
  await page.goto(url);
  await expect(page.locator("#scan")).toBeDisabled();
  await expect(page.locator("#scan-availability")).toContainText(
    "Scanning is unavailable on this platform"
  );
  await expect(page.locator("#refresh")).toBeEnabled();
  await page.getByRole("button", { name: "Refresh session and history" }).click();
  await expect(page.locator("#status")).toContainText("Session and history refreshed");
  await expect(page.locator("#scan")).toBeDisabled();
  await screenshot(page, testInfo, "guided-scan-unsupported.png");
});
