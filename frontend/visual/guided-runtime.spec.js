// Real local Flask runtime with isolated synthetic fixtures, intended for CI.
const { test, expect } = require("@playwright/test");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");
let base, root, server;
const url = "http://127.0.0.1:5179/ui/";
test.beforeAll(async () => {
  base = fs.mkdtempSync(path.join(os.tmpdir(), "disk-guided-ui-"));
  root = path.join(base, "Example folder");
  fs.mkdirSync(root);
  fs.writeFileSync(path.join(root, "Project notes.txt"), "Synthetic document fixture\n");
  fs.writeFileSync(path.join(root, "Cover.png"), "Synthetic image bytes, not decoded\n");
  fs.writeFileSync(path.join(root, "Unknown.xyz"), "Kept unchanged\n");
  server = spawn(
    "python",
    ["-c", "from backend.app import app; app.run(host='127.0.0.1',port=5179,debug=False)"],
    {
      env: {
        ...process.env,
        DISK_ORGANISER_DATA_DIR: path.join(base, "state"),
        DISK_ORGANISER_OPEN_BROWSER: "0",
        MODEL_PROVIDER: "local_only",
      },
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
});
test.afterAll(() => {
  if (server) server.kill();
});
test("guided real scan, approval, verified copies, reload and recovery", async ({
  page,
}, testInfo) => {
  const external = [];
  page.on("request", (request) => {
    if (!request.url().startsWith("http://127.0.0.1:5179/")) external.push(request.url());
  });
  await page.goto(url);
  await page.getByLabel("Absolute folder path").fill(root);
  await page.getByRole("button", { name: "Scan and preview" }).click();
  await expect(page.getByRole("heading", { name: "2. Review every copy" })).toBeVisible();
  await expect(page.locator("#apply")).toBeDisabled();
  expect(fs.readdirSync(root).filter((name) => name.startsWith("Organised-"))).toHaveLength(0);
  await page.screenshot({
    path: testInfo.outputPath("guided-desktop-preview.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: testInfo.outputPath("guided-mobile-preview.png"), fullPage: true });
  await page.locator("#approve").check();
  await page.locator("#apply").click();
  await expect(page.locator("#status")).toContainText("Verified 2 copies");
  const output = fs.readdirSync(root).find((name) => name.startsWith("Organised-"));
  expect(fs.readFileSync(path.join(root, output, "Documents", "Project notes.txt"), "utf8")).toBe(
    "Synthetic document fixture\n"
  );
  await page.reload();
  await expect(page.locator("#history")).toContainText("completed");
  const recover = page.getByRole("button", { name: "Undo / recover generated copies" });
  await expect(recover).toBeDisabled();
  await page.locator("#history input[type=checkbox]").check();
  await recover.click();
  await expect(page.locator("#status")).toContainText("Originals kept");
  expect(fs.existsSync(path.join(root, output))).toBe(false);
  expect(fs.readFileSync(path.join(root, "Project notes.txt"), "utf8")).toBe(
    "Synthetic document fixture\n"
  );
  expect(external).toEqual([]);
  await page.screenshot({ path: testInfo.outputPath("guided-recovered.png"), fullPage: true });
});
