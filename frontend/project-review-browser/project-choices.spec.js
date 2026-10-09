const { test, expect } = require("@playwright/test");
const fs = require("fs");
const reference = require("../__tests__/project-observation-fixture.json");
const byId = (page, name) => page.locator(`#observation-${name}`);

// Build the expectation independently of ProjectIntentModel and its serializer.
function referenceIntent() {
  const included = new Map(
    reference.decision.member_paths.map((member) => [member.entry_id, member.project_path])
  );
  return {
    members: reference.choices.map((choice) => ({
      entry_id: choice.entry.id,
      included: included.has(choice.entry.id),
      project_path: included.get(choice.entry.id) || choice.default_project_path,
    })),
    destination_root_id: reference.decision.destination_root_id,
    destination_folder: reference.decision.destination_folder,
  };
}
function intentDocument(intent = referenceIntent()) {
  return {
    schema_version: "disk-administration-project-intent/v1",
    document_kind: "user_authored_project_intent",
    source: {
      kind: "packaged_synthetic_observations",
      scenario_id: reference.scenario_id,
      source_revision: reference.source_revision,
      observation_digest: reference.observation_digest,
      reference_decision_digest: reference.reference_decision_digest,
    },
    intent,
  };
}
function filePayload(value, name = "aurora-choices.json") {
  return {
    name,
    mimeType: "application/json",
    buffer: Buffer.isBuffer(value) ? value : Buffer.from(JSON.stringify(value)),
  };
}
async function open(page) {
  const requests = [];
  page.on("request", (request) => {
    if (/^https?:/.test(request.url()))
      requests.push({ url: request.url(), method: request.method(), body: request.postData() });
  });
  await page.addInitScript(() => {
    const create = URL.createObjectURL.bind(URL);
    const revoke = URL.revokeObjectURL.bind(URL);
    window.choiceDownloadProbe = { created: [], revoked: [], types: [] };
    URL.createObjectURL = (blob) => {
      const url = create(blob);
      window.choiceDownloadProbe.created.push(url);
      window.choiceDownloadProbe.types.push(blob.type);
      return url;
    };
    URL.revokeObjectURL = (url) => {
      window.choiceDownloadProbe.revoked.push(url);
      return revoke(url);
    };
  });
  const loaded = page.waitForResponse((response) =>
    response.url().endsWith("/api/observation/reference")
  );
  await page.goto("/observation-draft");
  expect(await (await loaded).json()).toEqual(reference);
  await expect(byId(page, "status")).toContainText("Aurora reference loaded");
  await expect(byId(page, "save-choices")).toBeEnabled();
  await expect(byId(page, "open-choices")).toBeEnabled();
  await expect(byId(page, "save")).toBeDisabled();
  expect(requests.every((request) => new URL(request.url).origin === "http://127.0.0.1:8765")).toBe(
    true
  );
  expect(requests.map((request) => new URL(request.url).pathname).sort()).toEqual(
    [
      "/observation-draft",
      "/project-review-demo.css",
      "/project-intent-model.js",
      "/project-observation-demo.js",
      "/api/observation/reference",
    ].sort()
  );
  return requests;
}
async function capture(page) {
  return page.evaluate(
    (ids) => {
      const node = (name) => document.getElementById(`observation-${name}`);
      return {
        members: ids.map((entry_id, index) => ({
          entry_id,
          included: node(`member-${index}`).checked,
          project_path: node(`path-${index}`).value,
        })),
        destination_root_id: node("root").value,
        destination_folder: node("folder").value,
      };
    },
    reference.choices.map((choice) => choice.entry.id)
  );
}
async function review(page, activation = () => byId(page, "review-button").click()) {
  const result = page.waitForResponse((response) =>
    response.url().endsWith("/api/observation/review")
  );
  await activation();
  const response = await result;
  expect(response.status()).toBe(200);
  await expect(byId(page, "status")).toContainText("Draft reviewed");
  await expect(byId(page, "save")).toBeEnabled();
  return response.json();
}
async function download(page, control = "save-choices", activation) {
  const received = page.waitForEvent("download");
  await (activation ? activation() : byId(page, control).click());
  const file = await received;
  expect(await file.failure()).toBeNull();
  const filePath = await file.path();
  const bytes = fs.readFileSync(filePath);
  return { file, path: filePath, bytes, value: JSON.parse(bytes.toString("utf8")) };
}
async function choose(page, file, activation = () => byId(page, "open-choices").click()) {
  const requested = page.waitForEvent("filechooser");
  await activation();
  const chooser = await requested;
  expect(chooser.isMultiple()).toBe(false);
  await chooser.setFiles(file);
}
async function stage(page, file, activation) {
  await choose(page, file, activation);
  await expect(byId(page, "choices-preview")).toBeVisible();
  await expect(byId(page, "choices-status")).toContainText("Project choices opened");
  await expect(byId(page, "choices-preview-heading")).toBeFocused();
  await expect(byId(page, "choices-summary").locator("li")).toHaveCount(8);
  await expect(
    byId(page, "choices-summary").getByRole("heading", { name: "Current choices" })
  ).toBeVisible();
  await expect(
    byId(page, "choices-summary").getByRole("heading", { name: "Saved choices" })
  ).toBeVisible();
  await expect(byId(page, "choices-summary").locator("details")).not.toHaveAttribute("open", "");
}
async function retainedState(page) {
  return {
    choices: await capture(page),
    review: await byId(page, "review-content").innerHTML(),
    caption: await byId(page, "caption").textContent(),
    status: await byId(page, "status").textContent(),
    exportDisabled: await byId(page, "save").isDisabled(),
  };
}
async function tabTo(page, name) {
  for (let count = 0; count < 45; count++) {
    if (await byId(page, name).evaluate((node) => node === document.activeElement)) break;
    await page.keyboard.press("Tab");
  }
  await expect(byId(page, name)).toBeFocused();
}
async function evidence(page, testInfo, name) {
  const geometry = await page.evaluate(() => {
    const ids = [
      "save-choices",
      "open-choices",
      "choices-preview",
      "replace-choices",
      "cancel-choices",
    ];
    return {
      viewport: { width: innerWidth, height: innerHeight },
      zoom: getComputedStyle(document.documentElement).zoom,
      width: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      controls: ids.map((id) => {
        const node = document.getElementById(`observation-${id}`);
        const rect = node.getBoundingClientRect();
        return {
          id,
          hidden: node.hidden,
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
          scrollWidth: node.scrollWidth,
          clientWidth: node.clientWidth,
        };
      }),
    };
  });
  expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.width + 1);
  for (const control of geometry.controls) {
    expect(control.width).toBeGreaterThan(0);
    expect(control.scrollWidth).toBeLessThanOrEqual(control.clientWidth + 1);
  }
  fs.writeFileSync(
    testInfo.outputPath(`${name}-geometry.json`),
    JSON.stringify(geometry, null, 2) + "\n"
  );
  // Existing CI uploads this directory; do not duplicate the full-height PNG.
  await page.screenshot({ path: testInfo.outputPath(`${name}.png`), fullPage: true });
}

async function editSavedChoices(page) {
  await byId(page, "path-0").fill("Design/final-é-🛰.blend");
  await byId(page, "member-1").uncheck();
  await byId(page, "member-6").check();
  await byId(page, "member-3").check();
  await byId(page, "path-3").fill("Saved excluded path/é-🛰.data");
  await byId(page, "member-3").uncheck();
  await byId(page, "root").selectOption({ index: 0 });
  await byId(page, "folder").fill("Projects/Aurora résumé");
}

test("download reload cancel reselect replace and explicit Review preserve exactly eight source-bound choices", async ({
  page,
}, testInfo) => {
  const requests = await open(page);
  await editSavedChoices(page);
  const intent = await capture(page);
  const count = requests.length;
  const saved = await download(page);
  expect(requests).toHaveLength(count);
  expect(saved.file.suggestedFilename()).toBe("disk-organiser-aurora-project-choices.json");
  expect(saved.value).toEqual(intentDocument(intent));
  expect(saved.bytes.toString("utf8")).toBe(JSON.stringify(intentDocument(intent), null, 2) + "\n");
  expect(saved.bytes.length).toBeLessThanOrEqual(8192);
  expect(saved.value.intent.members[3]).toMatchObject({
    included: false,
    project_path: "Saved excluded path/é-🛰.data",
  });
  const token = await page.locator('meta[name="demo-process-token"]').getAttribute("content");
  expect(saved.bytes.toString("utf8")).not.toContain(token);
  fs.writeFileSync(testInfo.outputPath("aurora-project-choices.json"), saved.bytes);
  await expect
    .poll(() =>
      page.evaluate(() => {
        const state = window.choiceDownloadProbe;
        return (
          state.created.length === 1 &&
          state.revoked.length === 1 &&
          state.created[0] === state.revoked[0]
        );
      })
    )
    .toBe(true);
  expect(await page.evaluate(() => window.choiceDownloadProbe.types)).toEqual(["application/json"]);

  await page.reload();
  await expect(byId(page, "status")).toContainText("Aurora reference loaded");
  expect(await capture(page)).toEqual(referenceIntent());
  await byId(page, "folder").fill("Current reviewed edits");
  await review(page);
  const current = await retainedState(page);
  const beforeOpen = requests.length;
  await stage(page, saved.path);
  expect(await retainedState(page)).toEqual(current);
  await expect(byId(page, "choices-summary")).toContainText("Exclude:");
  await expect(byId(page, "choices-summary")).toContainText("Saved excluded path/é-🛰.data");
  await expect(byId(page, "choices-summary")).toContainText(
    "1 members added · 1 removed · 2 edited paths"
  );
  await evidence(page, testInfo, "aurora-project-choices-staged-desktop");
  await byId(page, "cancel-choices").click();
  await expect(byId(page, "open-choices")).toBeFocused();
  await expect(byId(page, "choices-preview")).toBeHidden();
  expect(await retainedState(page)).toEqual(current);
  // The same real on-disk download must fire change again after Cancel.
  await stage(page, saved.path);
  await byId(page, "replace-choices").click();
  await expect(byId(page, "review-button")).toBeFocused();
  expect(await capture(page)).toEqual(intent);
  await expect(byId(page, "path-3")).toBeDisabled();
  await expect(byId(page, "choices-preview")).toBeHidden();
  await expect(byId(page, "review-content")).toBeEmpty();
  await expect(byId(page, "save")).toBeDisabled();
  expect(requests).toHaveLength(beforeOpen);
  const result = await review(page);
  expect(requests).toHaveLength(beforeOpen + 1);
  expect(requests[beforeOpen].method).toBe("POST");
  expect(JSON.parse(requests[beforeOpen].body)).toEqual({
    expected_source_revision: reference.source_revision,
    expected_observation_digest: reference.observation_digest,
    expected_reference_decision_digest: reference.reference_decision_digest,
    member_paths: intent.members
      .filter((member) => member.included)
      .map(({ entry_id, project_path }) => ({ entry_id, project_path })),
    destination_root_id: intent.destination_root_id,
    destination_folder: intent.destination_folder,
  });
  expect(result.source_revision).toBe(reference.source_revision);
  expect(result.observation_digest).toBe(reference.observation_digest);
  expect(result.reference_decision_digest).toBe(reference.reference_decision_digest);
  expect(result.draft.executable).toBe(false);
  expect(result.draft.execution_authority).toBeNull();
  expect(result.draft.protection.live_backup_verified).toBe(false);
  expect(result.draft.protection.live_restore_verified).toBe(false);
  await expect(byId(page, "review-content")).toContainText("Unknown");
});

test("invalid stale oversized and non-UTF-8 files leave current choices and accepted report unchanged", async ({
  page,
}) => {
  const requests = await open(page);
  await byId(page, "folder").fill("Keep these reviewed choices");
  await review(page);
  const current = await retainedState(page);
  const report = await download(page, "save");
  const cases = [
    ["actual-review-report", report.bytes],
    ["empty", Buffer.alloc(0)],
    ["truncated-json", Buffer.from('{"schema_version":')],
    ["bad-UTF-8", Buffer.from([0xc3, 0x28])],
    [
      "UTF-8-BOM",
      Buffer.concat([
        Buffer.from([0xef, 0xbb, 0xbf]),
        Buffer.from(JSON.stringify(intentDocument())),
      ]),
    ],
    ["oversized", Buffer.alloc(8193, 32)],
    [
      "duplicate-key",
      Buffer.from(
        JSON.stringify(intentDocument()).replace(
          '{"schema_version":',
          '{"schema_version":"duplicate","schema_version":'
        )
      ),
    ],
    ["review-authority", { ...intentDocument(), executable: true }],
    [
      "stale-revision",
      { ...intentDocument(), source: { ...intentDocument().source, source_revision: 2 } },
    ],
    [
      "stale-observations",
      {
        ...intentDocument(),
        source: { ...intentDocument().source, observation_digest: "0".repeat(64) },
      },
    ],
    [
      "stale-decision",
      {
        ...intentDocument(),
        source: { ...intentDocument().source, reference_decision_digest: "0".repeat(64) },
      },
    ],
    [
      "missing-member",
      {
        ...intentDocument(),
        intent: { ...referenceIntent(), members: referenceIntent().members.slice(1) },
      },
    ],
    [
      "unknown-member",
      {
        ...intentDocument(),
        intent: {
          ...referenceIntent(),
          members: referenceIntent().members.map((member, index) =>
            index ? member : { ...member, entry_id: "unlisted" }
          ),
        },
      },
    ],
    [
      "invalid-path",
      { ...intentDocument(), intent: { ...referenceIntent(), destination_folder: "../outside" } },
    ],
  ];
  const before = requests.length;
  for (const [name, value] of cases) {
    await choose(page, filePayload(value, `${name}.json`));
    await expect(byId(page, "choices-status")).toContainText(
      /could not be opened|no larger than 8 KiB/
    );
    await expect(byId(page, "choices-preview")).toBeHidden();
    expect(await retainedState(page), name).toEqual(current);
    expect(requests, name).toHaveLength(before);
  }
  const repeatedReport = await download(page, "save");
  expect(repeatedReport.bytes).toEqual(report.bytes);
  expect(requests).toHaveLength(before);
});

test("exact 8 KiB file admits a staged preview and HTML-looking Unicode paths remain text", async ({
  page,
}) => {
  const requests = await open(page);
  const intent = referenceIntent();
  intent.destination_folder = 'Aurora <img src=x onerror="alert(1)"> é🛰';
  const json = Buffer.from(JSON.stringify(intentDocument(intent)));
  const exact = Buffer.concat([json, Buffer.alloc(8192 - json.length, 32)]);
  const before = requests.length;
  await stage(page, filePayload(exact));
  await expect(byId(page, "choices-summary")).toContainText(intent.destination_folder);
  await expect(page.locator("img")).toHaveCount(0);
  expect(await capture(page)).toEqual(referenceIntent());
  await byId(page, "replace-choices").click();
  expect(await capture(page)).toEqual(intent);
  expect(requests).toHaveLength(before);
});

for (const layout of [
  { name: "320", width: 320, height: 740, zoom: 1 },
  { name: "390", width: 390, height: 844, zoom: 1 },
  { name: "zoom-200", width: 1280, height: 900, zoom: 2 },
])
  test(`${layout.name} keyboard Save Open Cancel Replace and Review retain focus and readable staged choices`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: layout.width, height: layout.height });
    const requests = await open(page);
    await byId(page, "path-0").fill("Design/" + "x".repeat(100) + ".blend");
    const intent = await capture(page);
    await page.evaluate((zoom) => {
      document.documentElement.style.zoom = String(zoom);
    }, layout.zoom);
    await tabTo(page, "save-choices");
    const before = requests.length;
    const saved = await download(page, "save-choices", () => page.keyboard.press("Enter"));
    await page.keyboard.press("Tab");
    await expect(byId(page, "open-choices")).toBeFocused();
    await stage(page, saved.path, () => page.keyboard.press("Enter"));
    await evidence(page, testInfo, `aurora-project-choices-${layout.name}`);
    await page.keyboard.press("Tab");
    await expect(byId(page, "choices-summary").locator("summary")).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(byId(page, "choices-summary").locator("details")).toHaveAttribute("open", "");
    if (layout.name !== "390")
      await evidence(page, testInfo, `aurora-project-choices-${layout.name}-expanded`);
    await page.keyboard.press("Tab");
    await expect(byId(page, "replace-choices")).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(byId(page, "cancel-choices")).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(byId(page, "open-choices")).toBeFocused();
    expect(await capture(page)).toEqual(intent);
    await stage(page, saved.path, () => page.keyboard.press("Enter"));
    await tabTo(page, "replace-choices");
    await expect(byId(page, "replace-choices")).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(byId(page, "review-button")).toBeFocused();
    await expect(byId(page, "save")).toBeDisabled();
    expect(requests).toHaveLength(before);
    await review(page, () => page.keyboard.press("Enter"));
    await expect(byId(page, "review-heading")).toBeFocused();
    expect(requests).toHaveLength(before + 1);
  });

for (const change of ["input", "silent-control", "reload", "persisted-pageshow"])
  test(`a delayed local file read cannot stage obsolete choices after ${change}`, async ({
    page,
  }) => {
    await page.addInitScript(() => {
      const read = FileReader.prototype.readAsArrayBuffer;
      window.pendingChoiceReads = [];
      FileReader.prototype.readAsArrayBuffer = function (file) {
        // Delay the native local read, then deliver its real ArrayBuffer/onload.
        window.pendingChoiceReads.push({ reader: this, read: () => read.call(this, file) });
      };
    });
    const requests = await open(page);
    const intent = referenceIntent();
    intent.destination_folder = "Do not restore this obsolete intent";
    await choose(page, filePayload(intentDocument(intent)));
    await expect(byId(page, "choices-status")).toContainText("Reading project choices locally");
    if (change === "input") await byId(page, "folder").fill("Newer local choices");
    if (change === "silent-control")
      await byId(page, "folder").evaluate((node) => {
        node.value = "Newer local choices";
      });
    if (change === "reload") {
      await byId(page, "reload").click();
      await expect(byId(page, "status")).toContainText("Aurora reference loaded");
    }
    if (change === "persisted-pageshow") {
      // Explicit lifecycle-handler coverage, not a claim that Chromium used bfcache.
      const refreshed = page.waitForResponse((response) =>
        response.url().endsWith("/api/observation/reference")
      );
      await page.evaluate(() => {
        window.dispatchEvent(new PageTransitionEvent("pagehide", { persisted: true }));
        window.dispatchEvent(new PageTransitionEvent("pageshow", { persisted: true }));
      });
      await refreshed;
      await expect(byId(page, "status")).toContainText("Aurora reference loaded");
    }
    const before = requests.length;
    await page.evaluate(async () => {
      const pending = window.pendingChoiceReads.shift();
      const finished = new Promise((resolve) =>
        pending.reader.addEventListener("loadend", resolve, { once: true })
      );
      pending.read();
      await finished;
    });
    await expect(byId(page, "choices-preview")).toBeHidden();
    await expect(byId(page, "folder")).toHaveValue(
      change === "input" || change === "silent-control"
        ? "Newer local choices"
        : reference.decision.destination_folder
    );
    await expect(byId(page, "save")).toBeDisabled();
    expect(requests).toHaveLength(before);
  });

test("editing staged choices prevents obsolete replacement and navigation resets the stage", async ({
  page,
}) => {
  const requests = await open(page);
  const intent = referenceIntent();
  intent.destination_folder = "Saved but never approved";
  await stage(page, filePayload(intentDocument(intent)));
  await byId(page, "folder").evaluate((node) => {
    node.value = "Silent current edit";
  });
  const before = requests.length;
  await byId(page, "replace-choices").click();
  await expect(byId(page, "choices-status")).toContainText("Current choices changed");
  await expect(byId(page, "choices-preview")).toBeHidden();
  await expect(byId(page, "folder")).toHaveValue("Silent current edit");
  expect(requests).toHaveLength(before);
  await stage(page, filePayload(intentDocument(intent)));
  await page.getByRole("link", { name: "Harbour project review", exact: true }).click();
  await expect(page.locator("#status")).toContainText("Reference decision loaded");
  await page.goBack();
  await expect(byId(page, "status")).toContainText("Aurora reference loaded");
  await expect(byId(page, "choices-preview")).toBeHidden();
  expect(await capture(page)).toEqual(referenceIntent());
  await expect(byId(page, "save")).toBeDisabled();
});
