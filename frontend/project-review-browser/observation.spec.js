const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");
const byId = (page, name) => page.locator(`#observation-${name}`);
async function open(page) {
  await page.goto("/observation-draft");
  await expect(byId(page, "status")).toContainText("Aurora reference loaded");
}
async function review(page) {
  const received = page.waitForResponse((response) =>
    response.url().endsWith("/api/observation/review")
  );
  await byId(page, "review-button").click();
  const response = await received;
  expect(response.status()).toBe(200);
  await expect(byId(page, "status")).toContainText("Draft reviewed");
  return response.json();
}
async function screenshot(page, testInfo, name) {
  const file = testInfo.outputPath(name);
  await page.screenshot({ path: file, fullPage: true });
  await testInfo.attach(name, { path: file, contentType: "image/png" });
}
async function noOverflow(page) {
  const value = await page.evaluate(() => ({
    width: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(value.scroll).toBeLessThanOrEqual(value.width + 1);
}
async function assertUnknown(page) {
  const content = byId(page, "review-content");
  for (const label of [
    "Required copy space",
    "Available destination space",
    "Physical drive identity",
    "Current content versions",
    "Application dependencies",
    "Backup targets and coverage",
    "Independent copy count",
    "Restore scope and usability",
  ]) {
    await expect(content.locator(".metric").filter({ hasText: label }).locator("dd")).toHaveText(
      "Unknown"
    );
  }
  await expect(content).toContainText("Logical copy bytes: Unknown");
  await expect(content).toContainText("Live backup verified: false. Live restore verified: false.");
  await expect(content).not.toContainText("KEEP CURRENT");
}
async function clickZoomedReview(page, testInfo) {
  const button = byId(page, "review-button");
  await expect(button).toBeVisible();
  await expect(button).toBeEnabled();
  // Normal pointer activation with actual hit-testing, matching the accepted
  // suite's diagnostic for the locked Chromium/root CSS zoom combination.
  await button.evaluate((node) => node.scrollIntoView({ block: "center", inline: "center" }));
  const geometry = await button.evaluate((node) => {
    const rect = node.getBoundingClientRect();
    const zoom = Number.parseFloat(getComputedStyle(document.documentElement).zoom) || 1;
    const centre = { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
    const candidates = [
      { source: "DOM viewport rectangle", ...centre },
      { source: "CSS-zoom-scaled rectangle", x: centre.x * zoom, y: centre.y * zoom },
    ].map((point) => {
      const hit = document.elementFromPoint(point.x, point.y);
      return { ...point, hit: hit && hit.id, buttonHit: hit === node || node.contains(hit) };
    });
    return {
      zoom,
      rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
      viewport: { width: innerWidth, height: innerHeight },
      candidates,
    };
  });
  const file = testInfo.outputPath("aurora-zoom-pointer-geometry.json");
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(geometry, null, 2) + "\n");
  await testInfo.attach("aurora-zoom-pointer-geometry.json", {
    path: file,
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
  await page.mouse.click(point.x, point.y);
  await expect(byId(page, "status")).toContainText("Draft reviewed");
}

test("Aurora desktop bridges from Harbour, reviews explicit intent, and retains source identity", async ({
  page,
}, testInfo) => {
  const unexpected = [];
  page.on("request", (request) => {
    if (!request.url().startsWith("http://127.0.0.1:8765/")) unexpected.push(request.url());
  });
  await page.goto("/");
  await expect(page.locator("#status")).toContainText("Reference decision loaded");
  await page
    .getByRole("link", { name: "Review Aurora from synthetic recorded observations" })
    .click();
  await expect(byId(page, "status")).toContainText("Aurora reference loaded");
  const reference = await page.evaluate(async () =>
    (
      await fetch("/api/observation/reference", {
        headers: {
          "X-Demo-Token": document.querySelector('meta[name="demo-process-token"]').content,
        },
      })
    ).json()
  );
  await expect(byId(page, "scope")).toContainText(
    "8 fixed selectable examples from 32 observation records across 2 recorded roots"
  );
  await assertUnknown(page);
  expect(
    await byId(page, "members").evaluate(
      (node) => getComputedStyle(node).gridTemplateColumns.split(" ").length
    )
  ).toBe(2);
  await byId(page, "path-0").fill("Design/final.blend");
  await byId(page, "folder").fill("Projects/Aurora review");
  const result = await review(page);
  expect(result.source_revision).toBe(reference.source_revision);
  expect(result.observation_digest).toBe(reference.observation_digest);
  expect(result.reference_decision_digest).toBe(reference.reference_decision_digest);
  expect(result.decision.member_paths[0].project_path).toBe("Design/final.blend");
  await expect(byId(page, "review-content")).toContainText(
    "Projects/Aurora review/Design/final.blend"
  );
  await assertUnknown(page);
  await noOverflow(page);
  await screenshot(page, testInfo, "aurora-desktop-reviewed.png");
  expect(unexpected).toEqual([]);
});

test("current recorded address remains unresolved and an unselected occupant stays visible", async ({
  page,
}, testInfo) => {
  await open(page);
  await byId(page, "member-1").uncheck();
  await byId(page, "member-2").uncheck();
  await byId(page, "root").selectOption({ index: 0 });
  await byId(page, "folder").fill("Project Aurora");
  const same = await review(page);
  expect(same.draft.members[0].placement).toBe("current_address_requires_identity");
  await expect(byId(page, "review-content")).toContainText(
    "Same recorded address; physical identity is still Unknown"
  );
  await assertUnknown(page);
  await byId(page, "member-2").check();
  await byId(page, "path-0").fill("design_v2.blend");
  const conflict = await review(page);
  expect(
    conflict.draft.blockers.some((issue) => issue.code === "observed_target_path_overlap")
  ).toBe(true);
  const issue = byId(page, "review-content")
    .locator("li")
    .filter({ hasText: "outside selectable membership" });
  await expect(issue).toContainText("Project Aurora/design_v2.blend");
  await expect(issue).not.toContainText("All selected members");
  await expect(issue).not.toContainText("pyproject.toml");
  await assertUnknown(page);
  await noOverflow(page);
  await screenshot(page, testInfo, "aurora-recorded-overlap.png");
});

test("390px review retains stale, unreadable and alias uncertainty", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page);
  for (const index of [3, 5, 6]) await byId(page, `member-${index}`).check();
  const result = await review(page);
  expect(result.draft.capacity.unknown_size_member_ids.length).toBeGreaterThan(0);
  expect(result.draft.blockers.some((issue) => issue.code === "link_identity_unresolved")).toBe(
    true
  );
  await expect(byId(page, "review-content")).toContainText(
    "Alias paths are not independent copies"
  );
  await expect(byId(page, "review-content")).toContainText("not-readable.data");
  await expect(byId(page, "review-content")).toContainText("Recorded state: stale");
  await assertUnknown(page);
  await noOverflow(page);
  await screenshot(page, testInfo, "aurora-mobile-390.png");
});

test("320px review reflows long intended paths and expanded provenance", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await open(page);
  await byId(page, "path-0").fill("Design/" + "x".repeat(100) + ".blend");
  await review(page);
  await byId(page, "review-content").locator("summary").click();
  await expect(byId(page, "review-content")).toContainText("Source revision 1. Observation digest");
  await assertUnknown(page);
  await noOverflow(page);
  await screenshot(page, testInfo, "aurora-reflow-320.png");
});

test("200 percent CSS zoom permits a hit-tested pointer review with visible Unknown metrics", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await open(page);
  await byId(page, "folder").fill("Aurora at enlarged scale");
  await page.evaluate(() => {
    document.documentElement.style.zoom = "2";
  });
  await clickZoomedReview(page, testInfo);
  const memberLayout = await byId(page, "members").evaluate((node) => ({
    columns: getComputedStyle(node).gridTemplateColumns.split(" ").length,
    labels: [...node.querySelectorAll(".member-row label")].map((label) =>
      Number.parseFloat(getComputedStyle(label).width)
    ),
  }));
  expect(memberLayout.columns).toBe(1);
  expect(Math.min(...memberLayout.labels)).toBeGreaterThanOrEqual(200);
  const layoutFile = testInfo.outputPath("aurora-zoom-member-layout.json");
  fs.writeFileSync(layoutFile, JSON.stringify(memberLayout, null, 2) + "\n");
  await testInfo.attach("aurora-zoom-member-layout.json", {
    path: layoutFile,
    contentType: "application/json",
  });
  await assertUnknown(page);
  await noOverflow(page);
  await screenshot(page, testInfo, "aurora-zoom-200.png");
});

test("keyboard-only editing, review and dismissal preserve focus and reference", async ({
  page,
}, testInfo) => {
  await open(page);
  await page.keyboard.press("Tab");
  await expect(page.locator(".skip-link")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Harbour project review", exact: true })
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(byId(page, "reload")).toBeFocused();
  for (let count = 0; count < 4; count++) await page.keyboard.press("Tab");
  await expect(byId(page, "member-0")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(byId(page, "path-0")).toBeFocused();
  await page.keyboard.press("Control+A");
  await page.keyboard.type("Design/keyboard.blend");
  for (let count = 0; count < 20; count++) {
    if (await byId(page, "review-button").evaluate((node) => node === document.activeElement))
      break;
    await page.keyboard.press("Tab");
  }
  await expect(byId(page, "review-button")).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(byId(page, "status")).toContainText("Draft reviewed");
  await expect(byId(page, "review-heading")).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(byId(page, "dismiss")).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(byId(page, "review-button")).toBeFocused();
  await expect(byId(page, "path-0")).toHaveValue("design_v1.blend");
  await expect(byId(page, "caption")).toContainText("Reference observation draft");
  await noOverflow(page);
  await screenshot(page, testInfo, "aurora-keyboard-dismissed.png");
});

for (const action of ["edit", "dismiss", "reload"])
  test(`late observation response cannot revive the draft after ${action}`, async ({ page }) => {
    await open(page);
    let release;
    const held = new Promise((resolve) => {
      release = resolve;
    });
    let intercepted;
    const started = new Promise((resolve) => {
      intercepted = resolve;
    });
    await page.route("**/api/observation/review", async (route) => {
      const response = await route.fetch();
      intercepted();
      await held;
      try {
        await route.fulfill({ response });
      } catch (failure) {
        if (!/closed|aborted|Target/.test(failure.message)) throw failure;
      }
    });
    await byId(page, "review-button").click();
    await started;
    if (action === "edit") await byId(page, "folder").fill("Latest intent");
    if (action === "dismiss") await byId(page, "dismiss").click();
    if (action === "reload") {
      await byId(page, "reload").click();
      await expect(byId(page, "status")).toContainText("Aurora reference loaded");
    }
    release();
    await page.waitForTimeout(150);
    if (action === "edit") {
      await expect(byId(page, "folder")).toHaveValue("Latest intent");
      await expect(byId(page, "review-content")).toBeEmpty();
    } else await expect(byId(page, "caption")).toContainText("Reference observation draft");
    await expect(byId(page, "error")).toBeHidden();
  });

test("stale reference error retains intent for retry and HTML-looking paths stay text", async ({
  page,
}) => {
  await open(page);
  await page.route("**/api/observation/review", (route) =>
    route.fulfill({
      status: 409,
      contentType: "application/json",
      body: JSON.stringify({ error: "Stale reference" }),
    })
  );
  await byId(page, "folder").fill('Intent <img src=x onerror="alert(1)">');
  await byId(page, "review-button").click();
  await expect(byId(page, "error")).toContainText("reference changed");
  await expect(byId(page, "review-content")).toBeEmpty();
  await page.unroute("**/api/observation/review");
  await review(page);
  await expect(byId(page, "review-content")).toContainText('<img src=x onerror="alert(1)">');
  await expect(page.locator("img")).toHaveCount(0);
  await assertUnknown(page);
});

test("navigation back and forward reloads reference rather than persisting stale edits", async ({
  page,
}) => {
  await open(page);
  await byId(page, "folder").fill("Unsaved local intent");
  await page.getByRole("link", { name: "Harbour project review", exact: true }).click();
  await expect(page.locator("#status")).toContainText("Reference decision loaded");
  await page.goBack();
  await expect(byId(page, "status")).toContainText("Aurora reference loaded");
  await expect(byId(page, "folder")).toHaveValue("Projects/Aurora");
  await expect(byId(page, "caption")).toContainText("Reference observation draft");
  await page.goForward();
  await expect(page.locator("#status")).toContainText("Reference decision loaded");
});
