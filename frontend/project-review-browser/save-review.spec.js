const { test, expect } = require("@playwright/test");
const fs = require("fs");
const byId = (page, name) => page.locator(`#observation-${name}`);
async function open(page) {
  await page.addInitScript(() => {
    const create = URL.createObjectURL.bind(URL);
    const revoke = URL.revokeObjectURL.bind(URL);
    window.syntheticDownloadProbe = {
      created: [],
      revoked: [],
      types: [],
      unrelated: "BROWSER_STATE_SENTINEL",
    };
    URL.createObjectURL = (blob) => {
      const url = create(blob);
      window.syntheticDownloadProbe.created.push(url);
      window.syntheticDownloadProbe.types.push(blob.type);
      return url;
    };
    URL.revokeObjectURL = (url) => {
      window.syntheticDownloadProbe.revoked.push(url);
      return revoke(url);
    };
  });
  await page.goto("/observation-draft");
  await expect(byId(page, "status")).toContainText("Aurora reference loaded");
  await expect(byId(page, "save")).toBeDisabled();
}
async function review(page) {
  const result = page.waitForResponse((response) =>
    response.url().endsWith("/api/observation/review")
  );
  await byId(page, "review-button").click();
  const response = await result;
  expect(response.status()).toBe(200);
  await expect(byId(page, "status")).toContainText("Draft reviewed");
  await expect(byId(page, "save")).toBeEnabled();
  return response.json();
}
async function download(page, activation = () => byId(page, "save").click()) {
  const received = page.waitForEvent("download");
  await activation();
  const file = await received;
  expect(await file.failure()).toBeNull();
  const bytes = fs.readFileSync(await file.path(), "utf8");
  return { file, bytes, report: JSON.parse(bytes) };
}
async function screenshot(page, testInfo, name) {
  const dimensions = await page.evaluate(() => ({
    width: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width + 1);
  const file = testInfo.outputPath(name);
  await page.screenshot({ path: file, fullPage: true });
  // The existing workflow uploads this output directory directly; avoid a
  // duplicate attachment copy of the same full-height PNG.
}
async function assertReport(page, saved, accepted) {
  const value = saved.report;
  expect(value).toMatchObject({
    schema_version: "disk-administration-observation-review-export/v1",
    report_kind: "synthetic_display_report",
    canonical_observation_export: false,
    replayable: false,
    synthetic: true,
    read_only: true,
    executable: false,
    execution_authority: null,
    undo_available: false,
    source_safe_to_erase: false,
    live_backup_verified: false,
    live_restore_verified: false,
    scenario_id: accepted.scenario_id,
    source_revision: accepted.source_revision,
    observation_digest: accepted.observation_digest,
    reference_decision_digest: accepted.reference_decision_digest,
    decision_revision: 2,
    decision_digest: accepted.draft.decision_digest,
    decision: accepted.decision,
  });
  expect(typeof value.observation_digest).toBe("string");
  expect(typeof value.decision_digest).toBe("string");
  expect(value.review.members.map((member) => member.entry_id)).toEqual(accepted.draft.member_ids);
  for (const [index, member] of value.review.members.entries()) {
    const original = accepted.draft.members[index];
    expect(member).toMatchObject({
      entry_id: original.entry_id,
      project_path: original.project_path,
      source: original.source,
      intended: original.intended,
      placement: original.placement,
      recorded_kind: original.observation.kind,
      recorded_logical_bytes: original.observation.logical_bytes,
      recorded_status: original.observation.status,
      recorded_hash_status: original.observation.hash.status,
      volume_id: null,
      content_version: null,
      dependency_coverage: "unknown",
      source_retained: true,
    });
  }
  expect(value.review.protection).toEqual(accepted.draft.protection);
  expect(value.review.capacity.known_recorded_path_logical_bytes).toBe(
    accepted.draft.capacity.known_recorded_path_logical_bytes
  );
  expect(value.review.capacity.unknown_size_members.map((member) => member.entry_id)).toEqual(
    accepted.draft.capacity.unknown_size_member_ids
  );
  for (const key of [
    "known_logical_copy_bytes",
    "required_destination_bytes",
    "observed_free_bytes",
    "physical_allocation_prediction",
  ])
    expect(value.review.capacity[key]).toBeNull();
  expect(value.review.capacity.reclaimed_bytes).toBe(0);
  expect(
    value.review.blockers.map(({ recorded_path_labels, explanation, ...issue }) => issue)
  ).toEqual(accepted.draft.blockers);
  const displayed = await byId(page, "review-content")
    .locator(".review-section")
    .filter({ hasText: "Evidence gaps and recorded conflicts" })
    .locator("li")
    .allTextContents();
  expect(value.review.blockers.map((issue) => issue.explanation)).toEqual(displayed);
  expect(value.review.limitations).toEqual(accepted.draft.limitations);
  expect(saved.file.suggestedFilename()).toBe(
    `disk-organiser-aurora-review-r2-${accepted.draft.decision_digest.slice(0, 12)}.json`
  );
  const token = await page.locator('meta[name="demo-process-token"]').getAttribute("content");
  expect(saved.bytes.includes(token)).toBe(false);
  expect(saved.bytes.includes("BROWSER_STATE_SENTINEL")).toBe(false);
  await expect
    .poll(() =>
      page.evaluate(() => {
        const state = window.syntheticDownloadProbe;
        return (
          state.created.length === state.revoked.length &&
          state.created.every((url) => state.revoked.filter((entry) => entry === url).length === 1)
        );
      })
    )
    .toBe(true);
  expect(
    await page.evaluate(() =>
      window.syntheticDownloadProbe.types.every((type) => type === "application/json")
    )
  ).toBe(true);
  const keys = [];
  const visit = (item) => {
    if (item && typeof item === "object") {
      for (const [key, value] of Object.entries(item)) {
        keys.push(key);
        visit(value);
      }
    }
  };
  visit(value);
  for (const forbidden of [
    "token",
    "headers",
    "credentials",
    "fingerprint",
    "ctime_ns",
    "mtime_ns",
    "object_id",
    "inode",
    "device",
  ])
    expect(keys).not.toContain(forbidden);
}

test("actual desktop JSON download matches the displayed accepted review and leaks no token or fingerprint", async ({
  page,
}, testInfo) => {
  await open(page);
  const requests = [];
  page.on("request", (request) => {
    if (/^https?:/.test(request.url())) requests.push(request.url());
  });
  await byId(page, "folder").fill('Aurora <img src=x onerror="alert(1)">');
  await byId(page, "path-0").fill("Design/approved.blend");
  const accepted = await review(page);
  const before = requests.length;
  const saved = await download(page);
  await assertReport(page, saved, accepted);
  expect(requests.length).toBe(before);
  await expect(page.locator("img")).toHaveCount(0);
  await expect(byId(page, "save-status")).toContainText("Download requested");
  fs.writeFileSync(testInfo.outputPath("aurora-reviewed-display-report.json"), saved.bytes);
  await screenshot(page, testInfo, "aurora-save-desktop.png");
});

test("390px download preserves stale unreadable alias evidence and Unknown protection", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page);
  for (const index of [3, 5, 6]) await byId(page, `member-${index}`).check();
  const accepted = await review(page);
  const saved = await download(page);
  await assertReport(page, saved, accepted);
  expect(saved.report.review.capacity.unknown_size_members.length).toBeGreaterThan(0);
  expect(
    saved.report.review.blockers.some((issue) => issue.code === "link_identity_unresolved")
  ).toBe(true);
  expect(saved.report.review.members.some((member) => member.recorded_status === "stale")).toBe(
    true
  );
  await screenshot(page, testInfo, "aurora-save-mobile-390.png");
});

test("saved same-address intent stays unresolved and later collision export names the unselected occupant", async ({
  page,
}) => {
  await open(page);
  await byId(page, "member-1").uncheck();
  await byId(page, "member-2").uncheck();
  await byId(page, "root").selectOption({ index: 0 });
  await byId(page, "folder").fill("Project Aurora");
  const current = await review(page);
  const first = await download(page);
  await assertReport(page, first, current);
  expect(first.report.review.members[0].placement).toBe("current_address_requires_identity");
  await byId(page, "path-0").fill("design_v2.blend");
  await expect(byId(page, "save")).toBeDisabled();
  const collision = await review(page);
  const second = await download(page);
  await assertReport(page, second, collision);
  expect(second.file.suggestedFilename()).not.toBe(first.file.suggestedFilename());
  expect(
    second.report.review.blockers.some((issue) =>
      issue.recorded_path_labels.some((label) => label.includes("outside selectable membership"))
    )
  ).toBe(true);
});

test("pending late errors edits dismissal and reload cannot offer an old download", async ({
  page,
}) => {
  await open(page);
  await review(page);
  const downloads = [];
  page.on("download", (file) => downloads.push(file));
  let release;
  const held = new Promise((resolve) => {
    release = resolve;
  });
  let started;
  const intercepted = new Promise((resolve) => {
    started = resolve;
  });
  await page.route("**/api/observation/review", async (route) => {
    const response = await route.fetch();
    started();
    await held;
    try {
      await route.fulfill({ response });
    } catch (error) {
      if (!/closed|aborted|Target/.test(error.message)) throw error;
    }
  });
  await byId(page, "review-button").click();
  await intercepted;
  await expect(byId(page, "save")).toBeDisabled();
  await byId(page, "folder").fill("Unreviewed intent");
  release();
  await page.waitForTimeout(150);
  await expect(byId(page, "save")).toBeDisabled();
  await expect(byId(page, "review-content")).toBeEmpty();
  await page.unroute("**/api/observation/review");
  await page.route("**/api/observation/review", (route) =>
    route.fulfill({
      status: 409,
      contentType: "application/json",
      body: JSON.stringify({ error: "Reference changed" }),
    })
  );
  await byId(page, "review-button").click();
  await expect(byId(page, "error")).toContainText("reference changed");
  await expect(byId(page, "save")).toBeDisabled();
  await page.unroute("**/api/observation/review");
  await review(page);
  await byId(page, "dismiss").click();
  await expect(byId(page, "save")).toBeDisabled();
  await review(page);
  await byId(page, "reload").click();
  await expect(byId(page, "status")).toContainText("Aurora reference loaded");
  await expect(byId(page, "save")).toBeDisabled();
  expect(downloads).toHaveLength(0);
});

test("320px keyboard save repeated clicks and cancellation request retain the same accepted report", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await open(page);
  const accepted = await review(page);
  await page.keyboard.press("Tab");
  await expect(byId(page, "review-content").locator("summary")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(byId(page, "save")).toBeFocused();
  const first = await download(page, () => page.keyboard.press("Enter"));
  await assertReport(page, first, accepted);
  const requested = page.waitForEvent("download");
  await page.keyboard.press("Enter");
  const cancellation = await requested;
  await cancellation.cancel();
  const cancelOutcome = await cancellation.failure();
  // Small local JSON may finish before cancellation arrives. Record the actual
  // outcome instead of claiming a completed download was cancelled.
  expect([null, "canceled"]).toContain(cancelOutcome);
  fs.writeFileSync(
    testInfo.outputPath("aurora-download-cancellation.json"),
    JSON.stringify({ requested: true, failure: cancelOutcome }, null, 2) + "\n"
  );
  await expect(byId(page, "save")).toBeEnabled();
  const repeated = await download(page);
  expect(repeated.bytes).toBe(first.bytes);
  await screenshot(page, testInfo, "aurora-save-keyboard-320.png");
});

test("200 percent CSS zoom keeps keyboard Save and the report boundary readable", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await open(page);
  const accepted = await review(page);
  await page.evaluate(() => {
    document.documentElement.style.zoom = "2";
  });
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await expect(byId(page, "save")).toBeFocused();
  const saved = await download(page, () => page.keyboard.press("Enter"));
  await assertReport(page, saved, accepted);
  await expect(byId(page, "save-help")).toContainText("not replayable");
  await screenshot(page, testInfo, "aurora-save-zoom-200.png");
});

test("a silent control change while review is pending cannot enable an old export", async ({
  page,
}) => {
  await open(page);
  await review(page);
  let release;
  const held = new Promise((resolve) => {
    release = resolve;
  });
  let started;
  const intercepted = new Promise((resolve) => {
    started = resolve;
  });
  await page.route("**/api/observation/review", async (route) => {
    const response = await route.fetch();
    started();
    await held;
    await route.fulfill({ response });
  });
  await byId(page, "review-button").click();
  await intercepted;
  // Deliberately simulate an autofill/script value change with no input event.
  await byId(page, "folder").evaluate((node) => {
    node.value = "Silently newer browser intent";
  });
  release();
  await expect(byId(page, "status")).toContainText("Intent changed");
  await expect(byId(page, "review-content")).toBeEmpty();
  await expect(byId(page, "save")).toBeDisabled();
  await page.unroute("**/api/observation/review");
  const accepted = await review(page);
  const saved = await download(page);
  await assertReport(page, saved, accepted);
  expect(saved.report.decision.destination_folder).toBe("Silently newer browser intent");
});
