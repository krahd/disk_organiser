const { test, expect } = require("@playwright/test");
const fs = require("fs"),
  path = require("path"),
  { pathToFileURL } = require("url");
const first = path.resolve(
  __dirname,
  "../../prototypes/inventory_catalogue/owned-creative.example.json"
);
const second = path.resolve(
  __dirname,
  "../../prototypes/inventory_catalogue/owned-archive.example.json"
);
async function shot(page, info, name, options = {}) {
  const p = info.outputPath(name);
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
  await page.screenshot({ path: p, fullPage: true, ...options });
  await info.attach(name, { path: p, contentType: "image/png" });
}
async function open(page) {
  await page.goto("/inventory-catalogue.html");
  await expect(page.getByRole("heading", { name: "Where did you keep it?" })).toBeVisible();
}
async function add(page, file = first, label) {
  await page.locator("#inventory-file").setInputFiles(file);
  await expect(page.getByRole("dialog")).toBeVisible();
  if (label) await page.getByLabel("Your location label", { exact: true }).fill(label);
  await page.getByRole("button", { name: "Add separate snapshot record", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
}
async function singleLineControl(control) {
  const lines = await control.evaluate((node) => {
    const range = document.createRange();
    range.selectNodeContents(node);
    return [
      ...new Set(
        [...range.getClientRects()]
          .filter((r) => r.width > 0 && r.height > 0)
          .map((r) => Math.round(r.top))
      ),
    ].length;
  });
  expect(lines).toBe(1);
}
async function geometry(page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth
    )
  ).toBeLessThanOrEqual(1);
  const buttons = await page.locator("button:visible").evaluateAll((nodes) =>
    nodes.map((n) => ({
      h: n.getBoundingClientRect().height,
      w: n.getBoundingClientRect().width,
    }))
  );
  for (const b of buttons) {
    expect(b.h).toBeGreaterThanOrEqual(44);
    expect(b.w).toBeGreaterThanOrEqual(44);
  }
}
test("multi-location overview, offline search, source-preserving plan and catalogue downloads", async ({
  page,
}, info) => {
  const external = [],
    errors = [];
  page.on("request", (r) => {
    if (!r.url().startsWith("http://127.0.0.1:8768/")) external.push(r.url());
  });
  page.on("pageerror", (e) => errors.push(e.message));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await open(page);
  await shot(page, info, "20-catalogue-empty.png");
  await add(page, first, "Working drive · creative folder");
  await add(page, second, "Archive drive · saved projects");
  await expect(page.locator(".source-card")).toHaveCount(2);
  await expect(page.locator("#catalogue-count")).toContainText("physical drives unverified");
  await expect(page.locator(".source-card").last()).toContainText("Partial folder record");
  await shot(page, info, "21-catalogue-overview.png");
  await page.getByLabel("Search recorded names and paths", { exact: true }).fill("Film.mov");
  await expect(page.locator(".catalogue-entry")).toHaveCount(1);
  await expect(page.locator(".catalogue-entry")).toContainText("Archive drive");
  await expect(page.locator(".catalogue-entry")).toContainText("Historical source date");
  await shot(page, info, "22-catalogue-offline-search.png");
  await page
    .getByRole("checkbox", {
      name: "Select Exports/Film.mov from Archive drive · saved projects",
      exact: true,
    })
    .check();
  await page.getByLabel("Search recorded names and paths", { exact: true }).fill("Photos");
  await page
    .getByRole("checkbox", {
      name: "Select Photos from Working drive · creative folder",
      exact: true,
    })
    .check();
  await expect(
    page.getByRole("checkbox", {
      name: "Select Photos/Trip.jpg from Working drive · creative folder",
      exact: true,
    })
  ).toBeDisabled();
  await page.getByLabel("Search recorded names and paths", { exact: true }).fill("");
  await expect(page.locator("#selection-count")).toContainText("2 selected scopes");
  await page.locator(".project-selection").scrollIntoViewIfNeeded();
  await expect(page.locator("#selected-scopes")).toContainText("Photos");
  await expect(page.locator("#selected-scopes")).toContainText("Exports/Film.mov");
  await shot(page, info, "23-catalogue-project-selection.png", { fullPage: false });
  const selectedFilm = page.getByRole("checkbox", {
    name: "Select Exports/Film.mov from Archive drive · saved projects",
    exact: true,
  });
  await selectedFilm.scrollIntoViewIfNeeded();
  await expect(selectedFilm).toBeChecked();
  await shot(page, info, "32-catalogue-selected-file-viewport.png", { fullPage: false });
  await page.getByRole("button", { name: "Create a manual plan", exact: true }).click();
  await page.getByLabel("Project name", { exact: true }).fill("Scattered creative project");
  const pe = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download manual plan", exact: true }).click();
  const pd = await pe,
    pp = info.outputPath("owned-exported-plan.json");
  await pd.saveAs(pp);
  const plan = JSON.parse(fs.readFileSync(pp, "utf8"));
  expect(plan.items).toHaveLength(2);
  expect(plan.drives).toHaveLength(2);
  expect(plan.projects[0].intended_home).toBeUndefined();
  expect(plan.items[0].notes).toContain("Imported historical snapshot claim");
  await page.getByRole("button", { name: "Save catalogue", exact: true }).click();
  const ce = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download catalogue", exact: true }).click();
  const cd = await ce,
    cp = info.outputPath("owned-saved-catalogue.json");
  await cd.saveAs(cp);
  await page.getByRole("button", { name: "I saved the catalogue", exact: true }).click();
  await page.locator("#inventory-file").setInputFiles(cp);
  await page.getByRole("button", { name: "Replace catalogue and open", exact: true }).click();
  await expect(page.locator(".source-card")).toHaveCount(2);
  await expect(page.locator("#selection-count")).toContainText("0 selected scopes");
  await expect(page.locator("#catalogue-status")).toContainText("reopened");
  await geometry(page);
  expect(external).toEqual([]);
  expect(errors).toEqual([]);
  await page.goto("/manual-workspace.html");
  await page.locator("#open-file").setInputFiles(pp);
  await page.getByRole("button", { name: "Replace current plan and open", exact: true }).click();
  await expect(page.locator("#workspace")).toContainText("Scattered creative project");
  await expect(page.locator("#workspace")).toContainText("Exports/Film.mov".split("/").pop());
  await expect(page.locator("#workspace")).toContainText("Photos");
});
test("320-pixel catalogue and long-label rename stay usable", async ({ page }, info) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await open(page);
  await add(page, first, "External archive · " + "long folder description ".repeat(7));
  await add(page, second, "Second recorded location");
  await geometry(page);
  await singleLineControl(page.locator("#previous-results"));
  await singleLineControl(page.locator("#next-results"));
  await shot(page, info, "24-catalogue-mobile.png");
  await page.getByRole("button", { name: "Rename label", exact: true }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await geometry(page);
  const fits = await page
    .locator("#catalogue-dialog .dialog-heading")
    .evaluate(
      (n) =>
        n.querySelector("h2").getBoundingClientRect().right <=
        n.querySelector("button").getBoundingClientRect().left + 1
    );
  expect(fits).toBe(true);
  const focusClearance = await page.locator("#catalogue-name").evaluate((input) => {
    const note = input.nextElementSibling;
    return note.getBoundingClientRect().top - input.getBoundingClientRect().bottom;
  });
  expect(focusClearance).toBeGreaterThanOrEqual(8);
  await shot(page, info, "25-catalogue-mobile-dialog.png");
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
});
test("200 percent CSS zoom keeps overview, search and source details readable", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  await open(page);
  await add(page);
  await add(page, second);
  await page.evaluate(() => {
    document.documentElement.style.zoom = "2";
  });
  await page.evaluate(() => window.scrollTo(0, 0));
  const pointerEvidence = await page.locator("#catalogue-details").evaluate((control) => {
    const r = control.getBoundingClientRect();
    const zoom = Number(getComputedStyle(document.documentElement).zoom);
    const centre = { x: (r.left + r.right) / 2, y: (r.top + r.bottom) / 2 };
    const points = [1, zoom, 1 / zoom].map((factor) => {
      const x = centre.x * factor,
        y = centre.y * factor;
      const hit = document.elementFromPoint(x, y);
      return {
        factor,
        x,
        y,
        hit: hit?.id || hit?.tagName || null,
        matches: hit === control || control.contains(hit),
      };
    });
    return { zoom, rect: { left: r.left, top: r.top, right: r.right, bottom: r.bottom }, points };
  });
  const cdp = await page.context().newCDPSession(page);
  const { root } = await cdp.send("DOM.getDocument");
  const { nodeId } = await cdp.send("DOM.querySelector", {
    nodeId: root.nodeId,
    selector: "#catalogue-details",
  });
  const { quads } = await cdp.send("DOM.getContentQuads", { nodeId });
  const quad = quads[0];
  const quadPoint = {
    x: (quad[0] + quad[2] + quad[4] + quad[6]) / 4,
    y: (quad[1] + quad[3] + quad[5] + quad[7]) / 4,
  };
  const quadHit = await page.evaluate(({ x, y }) => {
    const hit = document.elementFromPoint(x, y),
      control = document.getElementById("catalogue-details");
    return {
      hit: hit?.id || hit?.tagName || null,
      matches: hit === control || control.contains(hit),
    };
  }, quadPoint);
  await cdp.detach();
  console.log(
    "ZOOM_NATIVE_HIT_TEST " +
      JSON.stringify({ ...pointerEvidence, cdpQuad: quad, cdpCentre: quadPoint, cdpHit: quadHit })
  );
  const visiblePoint = pointerEvidence.points.find((point) => point.matches);
  expect(
    visiblePoint,
    "The zoomed control must have an unobstructed native hit-test point"
  ).toBeTruthy();
  // This is an actual pointer event at a native hit-tested point, never a forced
  // locator click or DOM .click(). Record the chosen coordinates for diagnosis.
  await page.mouse.click(visiblePoint.x, visiblePoint.y);
  await expect(page.locator("#catalogue-details")).toHaveAttribute("aria-pressed", "true");
  await page.locator("#catalogue-details").focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#catalogue-details")).toHaveAttribute("aria-pressed", "false");
  await page.keyboard.press("Enter");
  await expect(page.locator("#catalogue-details")).toHaveAttribute("aria-pressed", "true");
  await geometry(page);
  const searchWidth = await page
    .locator("#catalogue-search")
    .evaluate((input) => input.getBoundingClientRect().width);
  expect(searchWidth).toBeGreaterThanOrEqual(240);
  const searchLayout = await page.locator(".search-controls").evaluate((group) => {
    const children = [...group.children].map((n) => n.getBoundingClientRect());
    return children[0].right <= children[1].left + 1 || children[0].bottom <= children[1].top + 1;
  });
  expect(searchLayout).toBe(true);
  await shot(page, info, "26-catalogue-css-zoom.png");
});
test("keyboard cancellation restores focus and repeated confirmation is single-use", async ({
  page,
}, info) => {
  await open(page);
  await add(page);
  const rename = page.getByRole("button", { name: "Rename label", exact: true });
  await rename.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByLabel("Your location label", { exact: true })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(rename).toBeFocused();
  await shot(page, info, "27-catalogue-keyboard.png");
  await page.locator("#inventory-file").setInputFiles(first);
  await page.getByRole("button", { name: "Add separate snapshot record", exact: true }).click();
  await page.locator("#catalogue-form").evaluate((f) => {
    f.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });
  await expect(page.locator(".source-card")).toHaveCount(2);
});
test("partial, hostile text and no-match states never imply live evidence", async ({
  page,
}, info) => {
  await open(page);
  const s = JSON.parse(fs.readFileSync(second, "utf8"));
  s.source.label = "<img src=x onerror=alert(1)> owned fixture";
  await add(page, {
    name: "owned-hostile.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(s)),
  });
  await expect(page.locator("img")).toHaveCount(0);
  await page.getByRole("button", { name: "Show details", exact: true }).click();
  await expect(page.locator("#source-details")).toContainText(s.source.label);
  await expect(page.getByRole("checkbox", { name: /Select External link/ })).toBeDisabled();
  await page
    .getByLabel("Search recorded names and paths", { exact: true })
    .fill("not-present-in-record");
  await expect(page.locator("#catalogue-results")).toContainText("No recorded matches");
  await expect(page.locator("#catalogue-results")).toContainText(
    "live storage has not been checked"
  );
  await shot(page, info, "28-catalogue-no-match.png");
});
test("navigation dismisses staged changes and direct file launch works", async ({ page }, info) => {
  await page.goto(pathToFileURL(path.resolve(__dirname, "../inventory-catalogue.html")).href);
  await add(page);
  await page.getByRole("button", { name: "Rename label", exact: true }).click();
  await page
    .getByLabel("Your location label", { exact: true })
    .fill("Uncommitted navigation label");
  await page.evaluate(() => window.dispatchEvent(new Event("pagehide")));
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(page.locator(".source-card")).not.toContainText("Uncommitted navigation label");
  await shot(page, info, "29-catalogue-direct-file.png");
  // Exercise real history as well as the deterministic pending-read lifecycle probe.
  page.on("dialog", async (dialog) => {
    await dialog.accept();
  });
  await page.getByRole("button", { name: "Rename label", exact: true }).click();
  await page.getByLabel("Your location label", { exact: true }).fill("Uncommitted history label");
  const priorUrl = page.url();
  await page.goto("http://127.0.0.1:8768/manual-workspace.html");
  await page.goBack();
  await expect(page).toHaveURL(priorUrl);
  await expect(page.getByRole("dialog")).not.toBeVisible();
  const retained = await page.locator(".source-card").count();
  await page
    .locator("#catalogue-form")
    .evaluate((form) =>
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }))
    );
  await expect(page.locator(".source-card")).toHaveCount(retained);
  await expect(page.locator("#source-cards")).not.toContainText("Uncommitted history label");
});

test("maximum decimal sizes and duplicate labels stay bounded and separately focusable", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await open(page);
  const s = JSON.parse(fs.readFileSync(first, "utf8"));
  s.entries = [s.entries[0]];
  for (let n = 0; n < 1999; n++)
    s.entries.push({
      path: `large-file-${n}`,
      kind: "file",
      status: "observed",
      logical_bytes: "9".repeat(30),
    });
  const input = {
    name: "owned-large-claim.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(s)),
  };
  await add(page, input, "Same label");
  await add(page, first, "Same label");
  await add(page, first, "Same label");
  await geometry(page);
  await shot(page, info, "30-catalogue-large-byte-claims.png");
  await page.getByLabel("Search recorded names and paths", { exact: true }).fill("Photos");
  await page
    .getByRole("checkbox", { name: "Select Photos from Same label", exact: true })
    .nth(1)
    .check();
  await expect(
    page.getByRole("checkbox", { name: "Select Photos from Same label", exact: true }).nth(1)
  ).toBeFocused();
});
