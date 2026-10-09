const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");
const fixture = path.resolve(
  __dirname,
  "../../prototypes/manual_planning/manual-plan.example.json"
);
const resultFixture = path.resolve(
  __dirname,
  "../../prototypes/manual_planning/manual-reported-result.example.json"
);
async function shot(page, info, name) {
  const file = info.outputPath(name);
  await page.screenshot({ path: file, fullPage: true });
  await info.attach(name, { path: file, contentType: "image/png" });
}
async function noOverflow(page) {
  const geometry = await page.evaluate(() => ({
    width: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(geometry.scroll).toBeLessThanOrEqual(geometry.width + 1);
}
async function singleLineControl(locator) {
  const geometry = await locator.evaluate((node) => {
    const rect = node.getBoundingClientRect();
    const range = document.createRange();
    range.selectNodeContents(node);
    const textLines = [...range.getClientRects()]
      .filter((line) => line.width > 0 && line.height > 0)
      .map((line) => Math.round(line.top));
    return { width: rect.width, height: rect.height, lines: [...new Set(textLines)].length };
  });
  expect(geometry.width).toBeGreaterThanOrEqual(44);
  expect(geometry.height).toBeGreaterThanOrEqual(44);
  expect(geometry.lines).toBe(1);
}
async function closeControlFits(page) {
  await singleLineControl(page.locator("#close-dialog"));
  const fit = await page.locator(".dialog-heading").evaluate((header) => {
    const title = header.querySelector("h2").getBoundingClientRect();
    const close = header.querySelector("button").getBoundingClientRect();
    return title.right <= close.left + 1;
  });
  expect(fit).toBe(true);
}
async function open(page) {
  await page.goto("/manual-workspace.html");
  await expect(page.getByRole("button", { name: "Name your first project" })).toBeVisible();
}
async function importPlan(page, file = fixture) {
  await page.locator("#open-file").setInputFiles(file);
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Replace current plan and open" }).click();
  await expect(page.locator("#status")).toContainText("Opened plan:");
}
async function createSimplePlan(page) {
  await page.getByRole("button", { name: "Name your first project" }).click();
  await page.getByLabel("Project name", { exact: true }).fill("Family photos");
  await page.getByRole("button", { name: "Create project", exact: true }).click();
  await page.getByRole("button", { name: "+ Add folder or file", exact: true }).click();
  await page.getByLabel("Folder or file name", { exact: true }).fill("Recent photos");
  await page
    .getByLabel("Where is it now, according to your records?", { exact: true })
    .selectOption("__new__");
  await page.getByLabel("Name the new location", { exact: true }).fill("Laptop");
  await page
    .getByLabel("Folder name or path (optional)", { exact: true })
    .fill("C:\\Photos\\Recent");
  await page.getByRole("button", { name: "Add to project", exact: true }).click();
}
test("guided real manual journey saves and reopens a lossless private artifact", async ({
  page,
}, info) => {
  const external = [],
    errors = [];
  page.on("request", (r) => {
    if (!r.url().startsWith("http://127.0.0.1:8767/")) external.push(r.url());
  });
  page.on("pageerror", (e) => errors.push(e.message));
  await page.setViewportSize({ width: 1440, height: 1050 });
  await open(page);
  await shot(page, info, "01-empty-desktop.png");
  await createSimplePlan(page);
  await expect(page.locator(".project-card small")).toHaveText("1 item listed");
  await page.getByRole("button", { name: "Next: where it lives →", exact: true }).click();
  await page.getByRole("button", { name: "Set intended home", exact: true }).click();
  await page.getByLabel("Named location", { exact: true }).selectOption("__new__");
  await page.getByLabel("Name the new location", { exact: true }).fill("Archive");
  await page
    .getByLabel("Folder name or path (optional)", { exact: true })
    .fill("Family collection");
  await page.getByRole("button", { name: "Set intended home", exact: true }).last().click();
  await expect(page.locator(".recorded-lane")).toContainText("Laptop");
  await expect(page.locator(".intended-lane")).toContainText("Archive");
  await shot(page, info, "02-recorded-and-intended.png");
  await page.getByRole("button", { name: "Next: how to protect it →", exact: true }).click();
  await page.getByRole("button", { name: "+ Add a target", exact: true }).click();
  await page.getByLabel("Target name", { exact: true }).fill("Backup at home");
  await page.getByRole("button", { name: "Add planned target", exact: true }).click();
  await expect(page.locator(".evidence-strip")).toContainText("Backup coverage unknown");
  await expect(page.locator(".check-card").first()).toContainText(
    "1 item included · 0 items excluded by you"
  );
  await shot(page, info, "03-planned-protection.png");
  const downloadEvent = page.waitForEvent("download");
  await page.getByRole("button", { name: "Save plan", exact: true }).first().click();
  await page.getByRole("button", { name: "Download plan file", exact: true }).click();
  const download = await downloadEvent,
    saved = info.outputPath("owned-roundtrip.json");
  await download.saveAs(saved);
  await expect(page.locator("#status")).toContainText(
    "Plan download requested; confirm it in Downloads"
  );
  const doc = JSON.parse(fs.readFileSync(saved, "utf8"));
  expect(doc.items[0].location.path_text).toBe("C:\\Photos\\Recent");
  expect(doc.projects[0].intended_home.path_text).toBe("Family collection");
  await page.getByRole("button", { name: "I saved the file", exact: true }).click();
  await importPlan(page, saved);
  await page.getByRole("button", { name: "Show details", exact: true }).click();
  expect(JSON.parse(await page.locator(".precision-panel pre").textContent())).toEqual(doc);
  expect(errors).toEqual([]);
  expect(external).toEqual([]);
  await noOverflow(page);
});
test("import preview, cancellation, invalid file and mixed reports keep their claims separate", async ({
  page,
}, info) => {
  await open(page);
  await importPlan(page, resultFixture);
  await page.getByRole("button", { name: /How to protect it/ }).click();
  await expect(
    page.getByText("You reported that this check passed", { exact: true })
  ).toBeVisible();
  await expect(
    page.getByText("You reported that this check failed", { exact: true })
  ).toBeVisible();
  await shot(page, info, "04-mixed-report-history.png");
  // Playwright intercepts the browser chooser and supplies an empty selection.
  // This tests selection cancellation, not clicking an OS-native Cancel button.
  const chooserEvent = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Open plan", exact: true }).click();
  const chooser = await chooserEvent;
  await chooser.setFiles([]);
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(
    page.getByText("You reported that this check failed", { exact: true })
  ).toBeVisible();
  await page.locator("#open-file").setInputFiles(fixture);
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(
    page.getByText("You reported that this check failed", { exact: true })
  ).toBeVisible();
  await page.locator("#open-file").setInputFiles({
    name: "invalid.json",
    mimeType: "application/json",
    buffer: Buffer.from('{"title":"a","title":"b"}'),
  });
  await expect(page.locator("#status")).toContainText("Plan not opened");
  await expect(
    page.getByText("You reported that this check failed", { exact: true })
  ).toBeVisible();
});
test("320 CSS pixel layout keeps every arrangement and dialog control reachable", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await open(page);
  await importPlan(page);
  await page.getByRole("button", { name: "Rename plan", exact: true }).click();
  await page
    .getByLabel("Plan title", { exact: true })
    .fill("Photo archive planning notes across laptop and offline drives");
  await page.getByRole("button", { name: "Save title", exact: true }).click();
  await singleLineControl(page.getByRole("button", { name: "Rename plan", exact: true }));
  await page.getByRole("button", { name: /Where it lives/ }).click();
  await noOverflow(page);
  await shot(page, info, "05-mobile-320-arrangement.png");
  await page.getByRole("button", { name: "Set intended home", exact: true }).click();
  await noOverflow(page);
  await expect(page.getByLabel("Named location", { exact: true })).toBeVisible();
  await closeControlFits(page);
  await shot(page, info, "06-mobile-320-dialog.png");
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await page.getByRole("button", { name: /How to protect it/ }).click();
  await noOverflow(page);
  await shot(page, info, "07-mobile-320-protection.png");
});
test("200 percent CSS zoom reflows with keyboard step navigation", async ({ page }, info) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await open(page);
  await importPlan(page);
  await page.evaluate(() => {
    document.documentElement.style.zoom = "2";
  });
  const target = page.getByRole("button", { name: /Where it lives/ });
  await target.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#step-heading")).toBeFocused();
  await noOverflow(page);
  await singleLineControl(page.getByRole("button", { name: "Rename plan", exact: true }));
  await shot(page, info, "08-css-zoom-200.png");
  await page.getByRole("button", { name: "Set intended home", exact: true }).focus();
  await page.keyboard.press("Enter");
  await noOverflow(page);
  await closeControlFits(page);
  await shot(page, info, "11-css-zoom-200-dialog.png");
});
test("keyboard-only entry, focus restoration and cancellation work without dragging", async ({
  page,
}, info) => {
  await open(page);
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to project workspace" })).toBeFocused();
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Name your first project" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByLabel("Project name", { exact: true })).toBeFocused();
  await page.keyboard.type("Keyboard project");
  await page.keyboard.press("Enter");
  await expect(page.locator("#project-title")).toBeFocused();
  await page.getByRole("button", { name: "Edit project", exact: true }).focus();
  await page.keyboard.press("Enter");
  await page.keyboard.type("Discarded");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Edit project", exact: true })).toBeFocused();
  await expect(page.locator("#project-title")).toHaveText("Keyboard project");
  await shot(page, info, "09-keyboard-focus.png");
});
test("long inert user text wraps and never becomes markup or a link", async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page);
  await createSimplePlan(page);
  await page.getByRole("button", { name: "Edit project", exact: true }).click();
  await page
    .getByLabel("Project name", { exact: true })
    .fill("<img src=x onerror=alert(1)> " + "LongName".repeat(24));
  await page.getByRole("button", { name: "Save project", exact: true }).click();
  expect(await page.locator("img,iframe").count()).toBe(0);
  await noOverflow(page);
  await shot(page, info, "10-long-text-mobile.png");
});
test("the complete functional workspace also starts directly from an owned file URL", async ({
  page,
}) => {
  const url = pathToFileURL(path.resolve(__dirname, "../manual-workspace.html")).href;
  await page.goto(url);
  await expect(page.getByRole("button", { name: "Name your first project" })).toBeVisible();
  await createSimplePlan(page);
  await expect(page.locator(".drive-heading")).toContainText("Laptop");
});
