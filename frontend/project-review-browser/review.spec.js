const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

async function open(page) {
  await page.goto("/");
  await expect(page.locator("#status")).toContainText("Reference decision loaded");
}
async function review(page) {
  await page.getByRole("button", { name: "Review proposed layout", exact: true }).click();
  await expect(page.locator("#status")).toContainText("Draft reviewed");
}
async function screenshot(page, testInfo, name) {
  const path = testInfo.outputPath(name);
  await page.screenshot({ path, fullPage: true });
  await testInfo.attach(name, { path, contentType: "image/png" });
}
async function noOverflow(page) {
  const dimensions = await page.evaluate(() => ({
    width: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width + 1);
}

async function clickZoomedReview(page, testInfo) {
  const button = page.locator("#review-button");
  await expect(button).toBeVisible();
  await expect(button).toBeEnabled();
  // The locked browser/locator combination failed hit-testing at root CSS zoom.
  // Diagnose and verify the browser's actual hit target before a normal pointer
  // click; never force a locator click or invoke the control through JavaScript.
  await button.evaluate((node) => node.scrollIntoView({ block: "center", inline: "center" }));
  const geometry = await button.evaluate((node) => {
    const rect = node.getBoundingClientRect();
    const zoom = Number.parseFloat(getComputedStyle(document.documentElement).zoom) || 1;
    const centre = { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
    const candidates = [
      { source: "DOM viewport rectangle", ...centre },
      { source: "CSS-zoom-scaled rectangle", x: centre.x * zoom, y: centre.y * zoom },
    ].map((point) => {
      const target = document.elementFromPoint(point.x, point.y);
      return {
        ...point,
        hit: target && target.id,
        buttonHit: target === node || node.contains(target),
      };
    });
    return {
      zoom,
      rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
      viewport: { width: innerWidth, height: innerHeight },
      candidates,
    };
  });
  const geometryPath = testInfo.outputPath("zoom-pointer-geometry.json");
  fs.mkdirSync(path.dirname(geometryPath), { recursive: true });
  fs.writeFileSync(geometryPath, JSON.stringify(geometry, null, 2) + "\n");
  await testInfo.attach("zoom-pointer-geometry.json", {
    path: geometryPath,
    contentType: "application/json",
  });
  const point = geometry.candidates.find(
    (candidate) =>
      candidate.buttonHit &&
      candidate.x >= 0 &&
      candidate.y >= 0 &&
      candidate.x < geometry.viewport.width &&
      candidate.y < geometry.viewport.height
  );
  expect(point, JSON.stringify(geometry)).toBeTruthy();
  expect(
    await page.evaluate(({ x, y }) => {
      const target = document.elementFromPoint(x, y);
      const node = document.getElementById("review-button");
      return target === node || node.contains(target);
    }, point)
  ).toBe(true);
  await page.mouse.click(point.x, point.y);
  await expect(page.locator("#status")).toContainText("Draft reviewed");
}

test("actual desktop review uses the Python evaluator and presents exact paths", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  const external = [];
  const errors = [];
  page.on("request", (request) => {
    if (!request.url().startsWith("http://127.0.0.1:8765/")) external.push(request.url());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  await open(page);
  await expect(
    page.getByText("Simulated project; no drives or providers connected", { exact: true })
  ).toBeVisible();
  await screenshot(page, testInfo, "desktop-reference.png");
  await page.locator("#member-extra").check();
  await expect(page.locator("#state-extra")).toHaveText("Added");
  await page.locator("#destination-folder").fill("Client projects/Harbour revised");
  await review(page);
  await expect(page.locator("#review-content")).toContainText(
    "Harbour revised/Exports/delivery.mov"
  );
  await expect(page.locator("#review-content")).toContainText(
    "A current-version independent copy is not established"
  );
  await screenshot(page, testInfo, "desktop-reviewed-protection-gap.png");
  await page.locator("#dismiss").click();
  await expect(page.locator("#review-caption")).toContainText("Reference proposal");
  await expect(page.locator("#member-extra")).not.toBeChecked();
  await expect(page.locator("#review-button")).toBeFocused();
  await noOverflow(page);
  expect(external).toEqual([]);
  expect(errors).toEqual([]);
});

test("keyboard-only membership and review, dependency explanation and dismissal", async ({
  page,
}, testInfo) => {
  await open(page);
  await page.keyboard.press("Tab");
  await expect(page.getByText("Skip to project review", { exact: true })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.locator("#scenario")).toBeFocused();
  for (let i = 0; i < 5; i += 1) await page.keyboard.press("Tab");
  await expect(page.locator("#member-edit")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.locator("#member-media")).toBeFocused();
  await page.keyboard.press("Space");
  await expect(page.locator("#state-media")).toHaveText("Removed");
  for (let i = 0; i < 5; i += 1) await page.keyboard.press("Tab");
  await expect(page.locator("#review-button")).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#status")).toContainText("Draft reviewed");
  await expect(page.locator("#review-heading")).toBeFocused();
  await expect(page.locator("#review-content")).toContainText("depends on a member you removed");
  await screenshot(page, testInfo, "keyboard-dependency-blocker.png");
  await page.keyboard.press("Shift+Tab");
  await expect(page.locator("#dismiss")).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#review-button")).toBeFocused();
});

test("mobile uncertain evidence stays readable and scoped", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page);
  await page.locator("#scenario").selectOption("harbour-uncertain");
  await expect(page.locator("#status")).toContainText("Reference decision loaded");
  await expect(page.locator("#review-content")).toContainText("A member is a placeholder");
  await expect(page.locator("#review-content")).toContainText("Sample-scoped exercise");
  await expect(page.locator("#review-content")).toContainText(
    "Whole selected project meets fixture restore requirement: no"
  );
  await expect(page.locator("#review-content")).toContainText("Configuration only");
  await noOverflow(page);
  await screenshot(page, testInfo, "mobile-uncertain-evidence.png");
  await page.locator("#destination-volume").selectOption("shelf");
  await review(page);
  await expect(page.locator("#review-content")).toContainText("destination is not online");
  await noOverflow(page);
});

test("200 percent rendered zoom and narrow reflow have no horizontal overflow", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 1280, height: 1000 });
  await open(page);
  // This is an actual rendered CSS-zoom check, not a claim of native browser-UI zoom.
  await page.evaluate(() => {
    document.documentElement.style.zoom = "2";
  });
  await page.locator("#destination-folder").fill("A long but valid folder name for Harbour");
  await clickZoomedReview(page, testInfo);
  await noOverflow(page);
  await screenshot(page, testInfo, "desktop-rendered-200-percent.png");
  await page.evaluate(() => {
    document.documentElement.style.zoom = "";
  });
  await page.setViewportSize({ width: 320, height: 800 });
  await noOverflow(page);
  await screenshot(page, testInfo, "narrow-320-reflow.png");
});

test("repeated actual reviews use the immutable reference and current-home collision stays honest", async ({
  page,
}) => {
  await open(page);
  for (const folder of ["First home", "Second home", "Third home"]) {
    await page.locator("#destination-folder").fill(folder);
    await review(page);
    await expect(page.locator("#review-content")).toContainText(`${folder}/edit.project`);
  }
  await page.locator("#destination-volume").selectOption("working");
  await page.locator("#destination-folder").fill("Projects/Harbour");
  await review(page);
  await expect(page.locator("#review-content")).toContainText("already occupied");
  await page.reload();
  await expect(page.locator("#destination-folder")).toHaveValue("Client projects/Harbour");
});

test("editing or dismissing a pending request cannot revive its late result or error", async ({
  page,
}) => {
  await open(page);
  let release;
  const wait = new Promise((resolve) => {
    release = resolve;
  });
  await page.route("**/api/review", async (route) => {
    const response = await route.fetch();
    await wait;
    await route.fulfill({ response }).catch(() => {});
  });
  await page.locator("#review-button").click();
  await expect(page.locator("#status")).toContainText("Reviewing");
  await page.locator("#destination-folder").fill("A newer edit");
  release();
  await expect(page.locator("#status")).toContainText("Draft changed");
  await expect(page.locator("#review-content")).toBeEmpty();
  await page.unroute("**/api/review");
  let rejectOld;
  const old = new Promise((resolve) => {
    rejectOld = resolve;
  });
  await page.route("**/api/review", async (route) => {
    await old;
    await route
      .fulfill({ status: 500, contentType: "application/json", body: '{"error":"Late error"}' })
      .catch(() => {});
  });
  await page.locator("#review-button").click();
  await page.locator("#dismiss").click();
  rejectOld();
  await expect(page.locator("#status")).toContainText("dismissed");
  await expect(page.locator("#error")).toBeHidden();
});

test("scenario switch and reload ignore pending reviews; HTML-looking names stay text", async ({
  page,
}) => {
  await open(page);
  let release;
  const wait = new Promise((resolve) => {
    release = resolve;
  });
  await page.route("**/api/review", async (route) => {
    const response = await route.fetch();
    await wait;
    await route.fulfill({ response }).catch(() => {});
  });
  await page.locator("#review-button").click();
  await page.locator("#scenario").selectOption("harbour-uncertain");
  await expect(page.locator("#review-content")).toContainText("Sample-scoped exercise");
  release();
  await expect(page.locator("#review-content")).toContainText("A member is a placeholder");
  await page.unroute("**/api/review");
  await page.locator("#destination-folder").fill("<img src=x onerror=alert(1)>");
  await review(page);
  await expect(page.locator("#review-content")).toContainText("<img src=x onerror=alert(1)>");
  await expect(page.locator("img")).toHaveCount(0);
  await expect(page.locator("#review-content")).toContainText("not portable");
  await page.locator("#reload").click();
  await expect(page.locator("#destination-folder")).toHaveValue("Client projects/Harbour");
});
