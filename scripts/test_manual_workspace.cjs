"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { fileURLToPath } = require("node:url");
const { JSDOM, VirtualConsole, ResourceLoader } = require("jsdom");
const root = path.resolve(__dirname, "../frontend");
const checks = [];
class OwnedOnly extends ResourceLoader {
  fetch(url, options) {
    const p = new URL(url);
    if (p.protocol !== "file:" || path.dirname(fileURLToPath(p)) !== root)
      throw Error("Unexpected external request: " + url);
    return super.fetch(url, options);
  }
}
async function launch() {
  const errors = [],
    downloads = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => errors.push(e.message));
  const dom = await JSDOM.fromFile(path.join(root, "manual-workspace.html"), {
    runScripts: "dangerously",
    resources: new OwnedOnly(),
    pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(w) {
      w.HTMLDialogElement.prototype.showModal = function () {
        this.open = true;
      };
      w.HTMLDialogElement.prototype.close = function () {
        this.open = false;
      };
      w.URL.createObjectURL = (blob) => {
        downloads.push(blob);
        return "blob:owned-test-download";
      };
      w.URL.revokeObjectURL = () => {};
      w.HTMLAnchorElement.prototype.click = function () {};
      w.TextEncoder = TextEncoder;
      w.TextDecoder = TextDecoder;
    },
  });
  await new Promise((resolve) => dom.window.addEventListener("load", resolve));
  const { document: d } = dom.window;
  const text = () => d.body.textContent;
  const buttons = (name) =>
    [...d.querySelectorAll("button")].filter(
      (b) => b.textContent.trim() === name && !b.closest("[hidden]")
    );
  const click = (name) => {
    const b = buttons(name)[0];
    assert.ok(b, "Button missing: " + name);
    b.click();
  };
  const input = (label) => {
    const lab = [...d.querySelectorAll("label")].find((l) => l.textContent === label);
    assert.ok(lab, "Field missing: " + label);
    return d.getElementById(lab.htmlFor);
  };
  const fill = (label, value) => {
    const f = input(label);
    f.value = value;
    f.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
  };
  const submit = () => {
    d.getElementById("editor-form").dispatchEvent(
      new dom.window.Event("submit", { bubbles: true, cancelable: true })
    );
    assert.equal(
      d.getElementById("dialog-error").hidden,
      true,
      d.getElementById("dialog-error").textContent
    );
  };
  const json = () => {
    const pre = d.querySelector(".precision-panel pre");
    assert.ok(pre, "Show details must be enabled");
    return JSON.parse(pre.textContent);
  };
  const checkbox = (label, checked) => {
    const row = [...d.querySelectorAll("#dialog-body label")].find((l) => l.textContent === label);
    assert.ok(row, "Checkbox missing: " + label);
    row.querySelector("input").checked = checked;
  };
  const openFile = async (value, size) => {
    const file = {
      size: size ?? Buffer.byteLength(value),
      arrayBuffer: async () => Buffer.from(value),
    };
    Object.defineProperty(d.getElementById("open-file"), "files", {
      configurable: true,
      value: [file],
    });
    d.getElementById("open-file").dispatchEvent(new dom.window.Event("change"));
    await new Promise((resolve) => setTimeout(resolve, 0));
  };
  return { dom, d, text, click, fill, input, submit, json, checkbox, errors, downloads, openFile };
}
(async () => {
  const a = await launch();
  const { d, click, fill, input, submit, json, checkbox, text } = a;
  assert.match(text(), /What do you want to look after/);
  assert.doesNotMatch(text(), /Family photos/);
  checks.push("starts with an empty manual plan");
  click("Name your first project");
  fill("Project name", "Fotografías <img src=x onerror=alert(1)>");
  submit();
  assert.match(text(), /List meaningful folders/);
  assert.equal(d.querySelectorAll("img").length, 0);
  checks.push("creates a real named project with safe text rendering");
  click("Show details");
  let state = json();
  assert.equal(state.projects.length, 1);
  assert.equal(state.protection_plans.length, 1);
  assert.equal(state.revision, 2);
  checks.push("project plus protection intent is one atomic revision");
  click("+ Add folder or file");
  fill("Folder or file name", "Recent photos");
  fill("Where is it now, according to your records?", "__new__");
  fill("Name the new location", "Laptop");
  fill("Folder name or path (optional)", "C:\\Photos\\Recent");
  submit();
  state = json();
  assert.equal(state.items.length, 1);
  assert.equal(state.drives.length, 1);
  assert.equal(state.projects[0].member_item_ids.length, 1);
  assert.equal(state.items[0].location.path_text, "C:\\Photos\\Recent");
  checks.push("guided scope creation atomically names a drive and adds membership");
  click("Edit recorded item");
  fill("Folder or file name", "Corrected photos");
  submit();
  assert.equal(json().items[0].label, "Corrected photos");
  checks.push("mistaken names can be corrected");
  click("Next: where it lives →");
  click("Set intended home");
  fill("Named location", "__new__");
  fill("Name the new location", "Photo archive");
  fill("Folder name or path (optional)", "Family collection");
  submit();
  state = json();
  assert.equal(state.projects[0].intended_home.path_text, "Family collection");
  assert.equal(state.items[0].location.drive_id, state.drives[0].id);
  checks.push("intended home remains distinct from recorded location");
  click("Change intended home");
  fill("Named location", "");
  fill("Folder name or path (optional)", "");
  submit();
  assert.ok(!json().projects[0].intended_home);
  checks.push("mistaken intended home can be cleared");
  click("Next: how to protect it →");
  click("+ Add a target");
  fill("Target name", "Backup shelf");
  fill("Destination kind", "sync_service");
  submit();
  state = json();
  assert.equal(state.backup_targets.length, 1);
  assert.equal(state.protection_plans[0].target_ids.length, 1);
  assert.match(text(), /Sync alone does not establish versioned backup/);
  assert.match(text(), /Backup coverage unknown/);
  checks.push("target intent never promotes coverage and sync warning is visible");
  click("Edit preferences");
  fill("Desired frequency", "weekly");
  fill("Desired retention (optional)", "One year");
  fill("Desired independent copies (optional)", "2");
  submit();
  const beforeDetails = json();
  click("Hide details");
  click("Show details");
  assert.deepEqual(json(), beforeDetails);
  checks.push("details toggle preserves exact model and hidden policy fields");
  click("Prepare a restore checklist");
  fill("Which planned target?", json().backup_targets[0].id);
  checkbox("Corrected photos", true);
  fill("What do you intend to try?", "sample");
  fill(
    "Describe the actual sample or scope",
    "Three images from Corrected photos; exact versions unknown."
  );
  submit();
  state = json();
  assert.equal(state.restore_plans.length, 1);
  assert.equal(state.restore_plans[0].checks.length, 8);
  checks.push("creates a meaningful sample restore checklist");
  const clickReport = (index) =>
    [...d.querySelectorAll(".check-row")][index].querySelector("button").click();
  clickReport(5);
  fill("Your result for this check", "reports_pass");
  fill("What happened? (optional)", "Three images opened.");
  submit();
  d.getElementById("editor-form").dispatchEvent(
    new a.dom.window.Event("submit", { cancelable: true })
  );
  state = json();
  assert.equal(state.restore_plans[0].checks[5].user_reports.length, 1);
  checks.push("repeat submit cannot duplicate a report");
  clickReport(6);
  fill("Your result for this check", "reports_fail");
  fill("What happened? (optional)", "Capture date mismatch.");
  submit();
  assert.match(text(), /You reported that this check passed/);
  assert.match(text(), /You reported that this check failed/);
  checks.push("mixed sample pass and metadata failure remain distinct");

  assert.equal(json().restore_plans[0].reported_context.target.label, "Backup shelf");
  assert.equal(json().restore_plans[0].reported_context.items[0].label, "Corrected photos");
  checks.push("first report captures immutable target and item descriptions");
  click("Edit target record");
  fill("Target name", "Corrected target");
  submit();
  assert.equal(json().backup_targets[0].label, "Corrected target");
  assert.equal(json().restore_plans[0].reported_context.target.label, "Backup shelf");
  assert.match(text(), /Target recorded at first report: Backup shelf/);
  assert.match(text(), /Current descriptions differ/);
  checks.push("correcting the current target preserves historical names and displays drift");
  d.querySelectorAll(".steps button")[0].click();
  click("Edit recorded item");
  fill("Folder or file name", "Current photos");
  fill("Folder name or path (optional)", "C:\\Photos\\Corrected");
  submit();
  assert.equal(json().items[0].label, "Current photos");
  assert.equal(json().restore_plans[0].reported_context.items[0].label, "Corrected photos");
  assert.equal(
    json().restore_plans[0].reported_context.items[0].location.path_text,
    "C:\\Photos\\Recent"
  );
  d.querySelectorAll(".steps button")[2].click();
  assert.match(text(), /Selected at first report: Corrected photos/);
  checks.push("correcting a current source path and label does not rebind reported history");
  click("Prepare a new exercise");
  fill("Checklist name", "Second exercise");
  submit();
  state = json();
  assert.equal(state.restore_plans.length, 2);
  assert.equal(state.restore_plans[0].checks[6].user_reports[0].result, "reports_fail");
  assert.ok(state.restore_plans[1].checks.every((c) => !c.user_reports));
  assert.notEqual(state.restore_plans[0].checks[0].id, state.restore_plans[1].checks[0].id);
  checks.push("changed exercise receives new keys and no inherited reports");
  click("Choose or remove planned targets");
  checkbox("Corrected target", false);
  submit();
  assert.match(text(), /historical exercise differs/);
  assert.equal(json().restore_plans[0].checks[6].user_reports.length, 1);
  checks.push("target changes preserve and flag historical exercise references");
  const full = json();
  click("Save plan");
  assert.match(d.getElementById("dialog-intro").textContent, /plaintext, not encrypted/);
  submit();
  assert.equal(a.downloads.length, 1);
  assert.match(text(), /Plan download requested; confirm it in Downloads/);
  const beforeUnload = new a.dom.window.Event("beforeunload", { cancelable: true });
  a.dom.window.dispatchEvent(beforeUnload);
  assert.equal(beforeUnload.defaultPrevented, true);
  click("I saved the file");
  const savedUnload = new a.dom.window.Event("beforeunload", { cancelable: true });
  a.dom.window.dispatchEvent(savedUnload);
  assert.equal(savedUnload.defaultPrevented, false);
  checks.push("download request is truthful and unsaved state waits for acknowledgement");
  await a.openFile('{"schema_version":"bad"}');
  assert.match(text(), /Plan not opened/);
  assert.deepEqual(json(), full);
  checks.push("malformed import preserves current plan");
  await a.openFile("{}", 1048577);
  assert.match(text(), /exceeds the 1 MiB/);
  assert.deepEqual(json(), full);
  checks.push("oversized file is rejected before read");
  const sample = fs.readFileSync(
    path.resolve(__dirname, "../prototypes/manual_planning/manual-plan.example.json"),
    "utf8"
  );
  await a.openFile(sample);
  assert.equal(d.getElementById("editor-dialog").open, true);
  click("Cancel");
  assert.deepEqual(json(), full);
  checks.push("cancelled staged import preserves current plan");
  await a.openFile(JSON.stringify(full));
  submit();
  assert.deepEqual(json(), full);
  assert.match(text(), /Opened plan:/);
  checks.push("save/reopen round trip preserves all records, paths and history");

  await a.openFile(Buffer.from([0xc3, 0x28]));
  assert.match(text(), /valid UTF-8/);
  assert.deepEqual(json(), full);
  checks.push("malformed UTF-8 is rejected without replacement characters");
  await a.openFile('{"title":"first","title":"second"}');
  assert.match(text(), /Plan not opened/);
  assert.deepEqual(json(), full);
  checks.push("duplicate-key JSON never reaches workspace replacement");
  const future = { ...full, schema_version: "disk-organiser/manual-storage-plan/v2" };
  await a.openFile(JSON.stringify(future));
  assert.match(text(), /Plan not opened/);
  assert.deepEqual(json(), full);
  checks.push("future versions leave current workspace intact");
  await a.openFile("\ufeff" + JSON.stringify(full));
  assert.match(text(), /Plan not opened/);
  assert.deepEqual(json(), full);
  checks.push("a UTF-8 BOM is preserved for strict rejection");
  click("Edit project");
  fill("Project name", "Discarded rename");
  d.getElementById("editor-dialog").dispatchEvent(
    new a.dom.window.Event("cancel", { cancelable: true })
  );
  assert.deepEqual(json(), full);
  assert.equal(d.getElementById("editor-dialog").open, false);
  checks.push("Escape cancels an interrupted edit without changing state");
  click("Edit recorded item");
  fill("Where is it now, according to your records?", "");
  fill("Folder name or path (optional)", "Path without a location");
  d.getElementById("editor-form").dispatchEvent(
    new a.dom.window.Event("submit", { cancelable: true })
  );
  assert.equal(d.getElementById("dialog-error").hidden, false);
  assert.match(d.getElementById("dialog-error").textContent, /Choose or name a location/);
  assert.deepEqual(json(), full);
  assert.equal(d.getElementById("editor-dialog").open, true);
  click("Cancel");
  checks.push("invalid edits preserve the plan and keep entered fields for correction");
  click("Edit recorded item");
  fill("What is it?", "whole_drive");
  fill("Where is it now, according to your records?", "");
  fill("Folder name or path (optional)", "");
  d.getElementById("editor-form").dispatchEvent(
    new a.dom.window.Event("submit", { cancelable: true })
  );
  assert.match(d.getElementById("dialog-error").textContent, /whole-drive scope needs/);
  assert.deepEqual(json(), full);
  click("Cancel");
  checks.push("whole-drive scopes require an explicit drive record");
  const itemArchive = [...d.querySelectorAll(".precision-panel button")].find(
    (b) => b.textContent === "Archive record"
  );
  itemArchive.click();
  submit();
  let archived = json();
  assert.equal(archived.items[0].archived, true);
  assert.deepEqual(archived.projects[0].member_item_ids, full.projects[0].member_item_ids);
  assert.deepEqual(archived.restore_plans, full.restore_plans);
  checks.push("archiving retains membership and historical report references");
  click("Choose project members");
  checkbox("Current photos (archived record)", false);
  submit();
  assert.equal(json().projects[0].member_item_ids.length, 0);
  assert.equal(json().items.length, 1);
  assert.deepEqual(json().restore_plans, full.restore_plans);
  click("Next: where it lives →");
  click("Next: how to protect it →");
  assert.match(text(), /historical exercise differs/);
  checks.push("removing project membership preserves source records and report history");
  click("Edit target record");
  fill("Target name", "Unselected corrected target");
  submit();
  assert.equal(json().backup_targets[0].label, "Unselected corrected target");
  click("Archive target record");
  submit();
  assert.equal(json().backup_targets[0].archived, true);
  assert.deepEqual(json().restore_plans, full.restore_plans);
  checks.push("unselected targets remain editable and reference-preserving archive is available");
  const beforeDetail = json();
  click("Hide details");
  click("Show details");
  assert.deepEqual(json(), beforeDetail);
  checks.push("details toggle also preserves archived and historical data");
  const b = await launch();
  b.click("Show details");
  const empty = b.json();
  b.click("Save plan");
  b.submit();
  assert.equal(b.downloads.length, 1);
  assert.equal(b.json().projects.length, 0);
  checks.push("empty unfinished plans can be saved");
  await b.openFile(JSON.stringify(empty));
  b.submit();
  assert.deepEqual(b.json(), empty);
  b.dom.window.close();
  checks.push("empty plans reopen without inventing locations or protection");

  const race = await launch();
  race.click("Name your first project");
  race.fill("Project name", "Race project");
  race.submit();
  let resolveRead;
  const delayed = {
    size: Buffer.byteLength(sample),
    arrayBuffer: () =>
      new Promise((resolve) => {
        resolveRead = resolve;
      }),
  };
  Object.defineProperty(race.d.getElementById("open-file"), "files", {
    configurable: true,
    value: [delayed],
  });
  race.d.getElementById("open-file").dispatchEvent(new race.dom.window.Event("change"));
  race.click("Edit project");
  race.fill("Project name", "My unfinished newer edit");
  resolveRead(Buffer.from(sample));
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(race.d.getElementById("dialog-title").textContent, "Edit this project");
  assert.equal(race.input("Project name").value, "My unfinished newer edit");
  race.click("Cancel");
  checks.push("delayed import cannot replace a newer editor or discard its typed fields");
  Object.defineProperty(race.d.getElementById("open-file"), "files", {
    configurable: true,
    value: [delayed],
  });
  race.d.getElementById("open-file").dispatchEvent(new race.dom.window.Event("change"));
  race.click("Open plan");
  race.d.getElementById("open-file").dispatchEvent(new race.dom.window.Event("cancel"));
  resolveRead(Buffer.from(sample));
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(race.d.getElementById("editor-dialog").open, false);
  assert.equal(race.d.getElementById("project-title").textContent, "Race project");
  checks.push("a newer picker intent and cancellation invalidate an earlier pending read");

  race.click("Show details");
  race.d.querySelectorAll(".steps button")[2].click();
  race.click("Prepare a restore checklist");
  race.click("+ Add a custom check");
  const descriptions = [...race.d.querySelectorAll("#dialog-body label")].filter(
    (l) => l.textContent === "Check description"
  );
  const custom = race.d.getElementById(descriptions.at(-1).htmlFor);
  custom.value = "Check colour profile in my own application";
  race.submit();
  assert.equal(
    race.json().restore_plans[0].checks.at(-1).label,
    "Check colour profile in my own application"
  );
  assert.equal(race.json().restore_plans[0].checks.at(-1).kind, "other");
  checks.push("draft checklists support user-written custom checks");
  race.click("Edit checklist");
  const labels = [...race.d.querySelectorAll("#dialog-body label")].filter(
    (l) => l.textContent === "Check description"
  );
  race.d.getElementById(labels[0].htmlFor).value = "Locate my intended snapshot manually";
  race.submit();
  assert.equal(
    race.json().restore_plans[0].checks[0].label,
    "Locate my intended snapshot manually"
  );
  checks.push("draft checklist descriptions can be corrected before any report");
  race.dom.window.close();
  const counts = await launch();
  counts.click("Name your first project");
  counts.fill("Project name", "Count examples");
  counts.submit();
  assert.equal(counts.d.querySelector(".project-card small").textContent, "0 items listed");
  for (const [name, expected] of [
    ["First folder", "1 item listed"],
    ["Second folder", "2 items listed"],
  ]) {
    counts.click("+ Add folder or file");
    counts.fill("Folder or file name", name);
    counts.submit();
    assert.equal(counts.d.querySelector(".project-card small").textContent, expected);
  }
  counts.d.querySelectorAll(".steps button")[2].click();
  assert.match(counts.text(), /2 items included · 0 items excluded by you/);
  counts.click("Choose included items");
  counts.checkbox("First folder", false);
  counts.submit();
  assert.match(counts.text(), /1 item included · 1 item excluded by you/);
  counts.d.querySelectorAll(".steps button")[3].click();
  assert.equal(counts.d.querySelector(".summary-stat span").textContent, "items listed");
  checks.push("listed and included counts use plain singular/plural item labels");
  counts.click("Edit project");
  const closeStyle = counts.dom.window.getComputedStyle(counts.d.getElementById("close-dialog"));
  assert.equal(closeStyle.flexShrink, "0");
  assert.equal(closeStyle.whiteSpace, "nowrap");
  assert.equal(closeStyle.minHeight, "44px");
  assert.equal(closeStyle.minWidth, "44px");
  counts.click("Cancel");
  const rename = [...counts.d.querySelectorAll(".overview-heading button")].find(
    (b) => b.textContent === "Rename plan"
  );
  const renameStyle = counts.dom.window.getComputedStyle(rename);
  assert.equal(renameStyle.flexShrink, "0");
  assert.equal(renameStyle.whiteSpace, "nowrap");
  assert.equal(
    counts.dom.window.getComputedStyle(counts.d.querySelector(".overview-heading")).flexWrap,
    "wrap"
  );
  checks.push("Close and Rename controls retain nonshrinking no-wrap CSS safeguards");
  counts.dom.window.close();
  assert.deepEqual(a.errors, []);
  checks.push("no uncaught script errors or external resource requests");
  const csp = d.querySelector('meta[http-equiv="Content-Security-Policy"]').content;
  assert.match(csp, /connect-src 'none'/);
  assert.match(csp, /form-action 'none'/);
  assert.equal(d.querySelectorAll("iframe").length, 0);
  checks.push("CSP denies connections and form transmission");
  if (process.env.MANUAL_WORKSPACE_RESULTS)
    fs.writeFileSync(
      process.env.MANUAL_WORKSPACE_RESULTS,
      JSON.stringify(
        {
          passed: checks.length,
          checks,
          visualAcceptance: "not run; Chromium process sockets unavailable",
        },
        null,
        2
      )
    );
  console.log(`PASS: ${checks.length} DOM integration checks`);
  checks.forEach((c) => console.log("  " + c));
  a.dom.window.close();
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
