"use strict";
const assert = require("node:assert/strict"),
  fs = require("node:fs"),
  path = require("node:path"),
  { fileURLToPath } = require("node:url");
const { JSDOM, VirtualConsole, ResourceLoader } = require("jsdom");
const root = path.resolve(__dirname, "../frontend"),
  C = require("../frontend/inventory-snapshot-model.js"),
  M = require("../frontend/manual-planning-model.js");
const example = fs.readFileSync(
    path.resolve(__dirname, "../prototypes/inventory_catalogue/owned-creative.example.json"),
    "utf8"
  ),
  partial = fs.readFileSync(
    path.resolve(__dirname, "../prototypes/inventory_catalogue/owned-archive.example.json"),
    "utf8"
  );
const checks = [];
class OwnedOnly extends ResourceLoader {
  fetch(url, options) {
    const p = new URL(url);
    if (p.protocol !== "file:" || path.dirname(fileURLToPath(p)) !== root)
      throw Error("Unexpected resource: " + url);
    return super.fetch(url, options);
  }
}
async function launch() {
  const errors = [],
    downloads = [],
    revoked = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => errors.push(e.message));
  const dom = await JSDOM.fromFile(path.join(root, "inventory-catalogue.html"), {
    runScripts: "dangerously",
    resources: new OwnedOnly(),
    pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(w) {
      w.TextEncoder = TextEncoder;
      w.TextDecoder = TextDecoder;
      w.HTMLDialogElement.prototype.showModal = function () {
        this.open = true;
      };
      w.HTMLDialogElement.prototype.close = function () {
        this.open = false;
      };
      w.URL.createObjectURL = (b) => {
        downloads.push(b);
        return "blob:owned-" + downloads.length;
      };
      w.URL.revokeObjectURL = (u) => revoked.push(u);
      w.HTMLAnchorElement.prototype.click = function () {};
    },
  });
  await new Promise((resolve) => dom.window.addEventListener("load", resolve));
  const d = dom.window.document;
  const click = (id) => d.getElementById(id).click();
  const submit = () =>
    d
      .getElementById("catalogue-form")
      .dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true }));
  const file = async (value, options = {}) => {
    const f = options.file || {
      size: options.size ?? Buffer.byteLength(value),
      arrayBuffer: async () => Buffer.from(value),
    };
    Object.defineProperty(d.getElementById("inventory-file"), "files", {
      configurable: true,
      value: [f],
    });
    d.getElementById("inventory-file").dispatchEvent(new dom.window.Event("change"));
    await new Promise((resolve) => setTimeout(resolve, 0));
  };
  const readBlob = (b) =>
    new Promise((resolve, reject) => {
      const r = new dom.window.FileReader();
      r.onload = () => resolve(r.result);
      r.onerror = reject;
      r.readAsText(b);
    });
  const text = () => d.body.textContent;
  const cards = () => d.querySelectorAll(".source-card");
  const add = async (v = example) => {
    await file(v);
    submit();
    assert.equal(
      d.getElementById("catalogue-error").hidden,
      true,
      d.getElementById("catalogue-error").textContent
    );
  };
  return { dom, d, click, submit, file, readBlob, text, cards, add, errors, downloads, revoked };
}
(async () => {
  const a = await launch(),
    { dom, d, click, submit, file, readBlob, text, cards, add } = a;
  assert.equal(cards().length, 0);
  assert.equal(d.getElementById("save-catalogue").disabled, true);
  assert.match(text(), /no drive connection or live scanner/);
  checks.push("empty-first catalogue discloses the missing native connection");
  await file(example);
  assert.equal(cards().length, 0);
  assert.equal(d.getElementById("catalogue-dialog").open, true);
  click("catalogue-cancel");
  assert.equal(cards().length, 0);
  checks.push("snapshot preview cancellation preserves empty catalogue");
  await add();
  assert.equal(cards().length, 1);
  assert.match(text(), /6.0 MiB/);
  assert.match(text(), /physical drives unverified/);
  checks.push("owned snapshot creates a source-scoped logical-size card");
  submit();
  assert.equal(cards().length, 1);
  checks.push("repeat confirmation cannot add the same record twice");
  await add(partial);
  assert.equal(cards().length, 2);
  assert.match(text(), /Partial folder record/);
  assert.match(text(), /Protection unknown/);
  checks.push("multiple historical locations preserve partial and unknown protection states");
  d.querySelectorAll(".source-actions button")[1].click();
  d.getElementById("catalogue-name").value = "Archive shelf <img src=x onerror=alert(1)>";
  submit();
  assert.match(text(), /Archive shelf <img/);
  assert.equal(d.querySelectorAll("img").length, 0);
  click("catalogue-details");
  assert.match(
    d.getElementById("source-details").textContent,
    /Original folder label: Owned example · creative folder/
  );
  checks.push("rename preserves origin and renders hostile-looking labels as text");
  const beforeDetails = text();
  click("catalogue-details");
  click("catalogue-details");
  assert.equal(text(), beforeDetails);
  checks.push("details toggle changes presentation only");
  const search = d.getElementById("catalogue-search");
  search.value = "Film.mov";
  search.dispatchEvent(new dom.window.Event("input"));
  assert.equal(d.querySelectorAll(".catalogue-entry").length, 1);
  assert.match(d.querySelector(".catalogue-entry").textContent, /archive folder/);
  assert.match(d.querySelector(".catalogue-entry").textContent, /Historical source date/);
  checks.push("offline search names the recorded location and observation date");
  search.value = "Missing-unrecorded-name";
  search.dispatchEvent(new dom.window.Event("input"));
  assert.match(text(), /No recorded matches/);
  assert.match(text(), /live storage has not been checked/);
  checks.push("empty search does not claim absence on live drives");
  search.value = "";
  search.dispatchEvent(new dom.window.Event("input"));
  const photos = [...d.querySelectorAll(".catalogue-entry")]
    .find((e) => e.querySelector("strong").textContent === "Photos")
    .querySelector("input");
  photos.click();
  assert.equal(d.getElementById("prepare-plan").disabled, false);
  assert.equal(
    [...d.querySelectorAll(".catalogue-entry")]
      .find((e) => e.querySelector("strong").textContent === "Photos/Trip.jpg")
      .querySelector("input").disabled,
    true
  );
  assert.equal(
    [...d.querySelectorAll(".catalogue-entry")]
      .find((e) => e.querySelector("strong").textContent === "External link")
      .querySelector("input").disabled,
    true
  );
  checks.push("project selection excludes links and overlapping descendants");
  click("prepare-plan");
  d.getElementById("catalogue-name").value = "Shared creative project";
  submit();
  assert.equal(a.downloads.length, 1);
  const plan = M.strictParse(await readBlob(a.downloads[0]));
  assert.equal(plan.items.length, 1);
  assert.match(plan.items[0].notes, /Original relative path: Photos/);
  assert.match(plan.drives[0].label, /Archive shelf/);
  assert.equal(plan.projects[0].intended_home, undefined);
  assert.equal(M.derive(plan).coverage, "unknown");
  assert.match(text(), /Manual plan download requested/);
  checks.push(
    "manual-plan export retains historical origin without destination or protection evidence"
  );
  click("save-catalogue");
  submit();
  const saved = await readBlob(a.downloads[1]);
  assert.equal(C.parse(saved).records.length, 2);
  assert.equal(d.getElementById("catalogue-saved").hidden, false);
  assert.match(text(), /download requested/);
  click("catalogue-saved");
  assert.match(text(), /confirmed saving this catalogue revision/);
  checks.push("download acknowledgement is distinct from requested save");
  await file(saved);
  click("catalogue-cancel");
  assert.equal(cards().length, 2);
  assert.match(d.getElementById("selection-count").textContent, /1 folder selected/);
  await file(saved);
  submit();
  assert.equal(cards().length, 2);
  assert.match(d.getElementById("selection-count").textContent, /0 files or folders selected/);
  assert.match(text(), /reopened/);
  checks.push(
    "catalogue cancellation preserves selection; confirmed reopen roundtrips sources and clears temporary choices"
  );
  for (const bad of [
    "{",
    "{}",
    '{"a":null,"a":null}',
    "\ufeff" + example,
    example.replace("inventory-snapshot/v1", "inventory-snapshot/v2"),
  ]) {
    await file(bad);
    assert.equal(cards().length, 2);
    assert.equal(d.getElementById("catalogue-dialog").open, false);
  }
  checks.push("malformed duplicate BOM and future-version imports preserve catalogue");
  await file("", {
    file: { size: 2, arrayBuffer: async () => new Uint8Array([0xc0, 0x80]).buffer },
  });
  assert.equal(cards().length, 2);
  assert.match(text(), /Could not open file/);
  checks.push("malformed UTF-8 is rejected without replacement text");
  let read = false;
  await file("", {
    file: {
      size: C.LIMITS.bytes + 1,
      arrayBuffer: async () => {
        read = true;
        throw Error("not reached");
      },
    },
  });
  assert.equal(read, false);
  assert.equal(cards().length, 2);
  checks.push("oversized artifact rejects before allocation");
  let resolve;
  await file("", {
    file: {
      size: Buffer.byteLength(example),
      arrayBuffer: () => new Promise((r) => (resolve = r)),
    },
  });
  click("open-inventory");
  resolve(Buffer.from(example));
  await new Promise((r) => setTimeout(r, 0));
  assert.equal(d.getElementById("catalogue-dialog").open, false);
  checks.push("newer picker invalidates earlier asynchronous import");
  await file("", {
    file: {
      size: Buffer.byteLength(example),
      arrayBuffer: () => new Promise((r) => (resolve = r)),
    },
  });
  d.querySelectorAll(".source-actions button")[1].click();
  d.getElementById("catalogue-name").value = "Later edit";
  submit();
  resolve(Buffer.from(example));
  await new Promise((r) => setTimeout(r, 0));
  assert.equal(d.getElementById("catalogue-dialog").open, false);
  assert.match(text(), /Later edit/);
  checks.push("editing while a file reads invalidates its stale preview");
  await file("", { file: { size: 10, arrayBuffer: async () => Buffer.from(example) } });
  assert.equal(cards().length, 2);
  assert.match(text(), /File changed while reading/);
  checks.push("file-size mismatch rejects atomically");
  await file("", {
    file: {
      size: 10,
      arrayBuffer: async () => {
        throw Error("owned unreadable file");
      },
    },
  });
  assert.equal(cards().length, 2);
  assert.match(text(), /owned unreadable file/);
  checks.push("unreadable file keeps prior records");
  await file(example);
  d.getElementById("catalogue-name").value = " ";
  submit();
  assert.equal(cards().length, 2);
  assert.equal(d.getElementById("catalogue-error").hidden, false);
  click("catalogue-close");
  checks.push("invalid labels preserve catalogue and allow correction or cancellation");
  const many = JSON.parse(example);
  many.entries = [many.entries[0]];
  for (let n = 0; n < 120; n++)
    many.entries.push({
      path: `entry-${String(n).padStart(3, "0")}`,
      kind: "file",
      status: "observed",
      logical_bytes: "1",
    });
  await add(JSON.stringify(many));
  d.getElementById("catalogue-search").value = "entry-";
  d.getElementById("catalogue-search").dispatchEvent(new dom.window.Event("input"));
  assert.equal(d.querySelectorAll(".catalogue-entry").length, 50);
  assert.match(d.getElementById("result-count").textContent, /120 matching records/);
  click("next-results");
  assert.match(d.getElementById("result-page").textContent, /Page 2 of 3/);
  click("next-results");
  assert.equal(d.querySelectorAll(".catalogue-entry").length, 20);
  assert.equal(d.getElementById("next-results").disabled, true);
  checks.push(
    "paginated search exposes every match and explicit total rather than silently truncating"
  );
  await file(example);
  dom.window.dispatchEvent(new dom.window.Event("pagehide"));
  submit();
  assert.equal(d.getElementById("catalogue-dialog").open, false);
  assert.equal(cards().length, 3);
  checks.push("navigation retires staged dialog authority without changing catalogue");
  await file("", {
    file: {
      size: Buffer.byteLength(example),
      arrayBuffer: () => new Promise((r) => (resolve = r)),
    },
  });
  dom.window.dispatchEvent(new dom.window.Event("pagehide"));
  resolve(Buffer.from(example));
  await new Promise((r) => setTimeout(r, 0));
  assert.equal(d.getElementById("catalogue-dialog").open, false);
  checks.push("navigation invalidates pending asynchronous imports");
  await add(example);
  await add(example);
  search.value = "Photos";
  search.dispatchEvent(new dom.window.Event("input"));
  const duplicateInputs = [...d.querySelectorAll(".catalogue-entry input")].filter(
    (n) => n.getAttribute("aria-label") === "Select Photos from Owned example · creative folder"
  );
  assert.equal(duplicateInputs.length, 2);
  const duplicateKey = duplicateInputs[1].dataset.selectionKey;
  duplicateInputs[1].click();
  assert.equal(d.activeElement.dataset.selectionKey, duplicateKey);
  assert.equal(
    [...d.querySelectorAll(".catalogue-entry input")].filter((n) => n.checked).length,
    1
  );
  checks.push("duplicate labels retain unique source selection and keyboard focus");
  assert.equal(
    dom.window.getComputedStyle(d.getElementById("previous-results")).whiteSpace,
    "nowrap"
  );
  assert.equal(dom.window.getComputedStyle(d.getElementById("next-results")).flexShrink, "0");
  checks.push("pagination controls retain no-wrap nonshrinking display safeguards");
  assert.deepEqual(a.errors, []);
  checks.push("owned-only resource loader observed no script or external request error");
  await new Promise((r) => setTimeout(r, 1100));
  assert.equal(a.revoked.length, a.downloads.length);
  checks.push("all export object URLs are released after download requests");
  dom.window.close();
  const readable = await launch(),
    rd = readable.d;
  const dated = JSON.parse(example),
    raw = "2026-12-31T23:59:59.123456-03:30";
  dated.source.observed_at = raw;
  await readable.file(JSON.stringify(dated));
  assert.match(
    rd.getElementById("catalogue-dialog-body").textContent,
    /31 Dec 2026, 23:59 UTC-03:30/
  );
  readable.submit();
  const dateNode = rd.querySelector(".source-date time");
  assert.equal(dateNode.textContent, "31 Dec 2026, 23:59 UTC-03:30");
  assert.equal(dateNode.dateTime, raw);
  assert.equal(rd.querySelector(".catalogue-entry time").textContent, dateNode.textContent);
  readable.click("catalogue-details");
  assert.match(
    rd.getElementById("source-details").textContent,
    /Original claimed date \(ISO\): 2026-12-31T23:59:59.123456-03:30/
  );
  checks.push("readable source dates retain the unconverted original ISO under details");
  const choose = (path) =>
    [...rd.querySelectorAll(".catalogue-entry")]
      .find((e) => e.querySelector("strong").textContent === path)
      .querySelector("input")
      .click();
  const words = () => rd.getElementById("selection-count").textContent;
  assert.equal(words(), "0 files or folders selected");
  choose("Readme.txt");
  assert.equal(words(), "1 file selected");
  choose("Drafts/Notes.txt");
  assert.equal(words(), "2 files selected");
  choose("Photos");
  assert.equal(words(), "2 files and 1 folder selected");
  choose("Drafts/Notes.txt");
  choose("Drafts");
  assert.equal(words(), "1 file and 2 folders selected");
  assert.match(readable.cards()[0].textContent, /1 file and 2 folders in your project selection/);
  readable.click("prepare-plan");
  assert.match(
    rd.getElementById("catalogue-dialog-body").textContent,
    /1 file and 2 folders across 1 labelled location/
  );
  readable.click("catalogue-cancel");
  readable.click("clear-selection");
  choose("Photos");
  assert.equal(words(), "1 folder selected");
  assert.match(
    rd.querySelector(".project-selection").textContent,
    /Folder contents are not counted separately/
  );
  checks.push("plain selection counts distinguish zero, singular, plural and mixed files/folders");
  const beforeBad = rd.getElementById("source-cards").textContent;
  for (const invalid of ["2026-10-09", "2026-10-09T07:00:00", "2026-02-30T07:00:00Z"]) {
    dated.source.observed_at = invalid;
    await readable.file(JSON.stringify(dated));
    assert.equal(rd.getElementById("catalogue-dialog").open, false);
    assert.equal(rd.getElementById("source-cards").textContent, beforeBad);
    assert.equal(words(), "1 folder selected");
  }
  checks.push("incomplete or invalid source dates cannot replace retained records or selection");
  dated.source.observed_at = "2026-10-09T07:00:00-00:00";
  await readable.add(JSON.stringify(dated));
  assert.equal(
    rd.querySelectorAll(".source-date time")[1].textContent,
    "9 Oct 2026, 07:00 UTC (local offset unknown)"
  );
  assert.deepEqual(readable.errors, []);
  checks.push("unknown local offset is explicit rather than converted to the host timezone");
  readable.dom.window.close();
  const comp = await launch(), cd = comp.d;
  assert.equal(cd.getElementById("choose-comparison").disabled, true);
  await comp.add();
  assert.equal(cd.getElementById("choose-comparison").disabled, true);
  const compareExample = fs.readFileSync(path.resolve(__dirname, "../prototypes/inventory_catalogue/owned-comparison.example.json"), "utf8");
  await comp.add(compareExample);
  assert.equal(cd.getElementById("choose-comparison").disabled, false);
  const savedBefore = cd.getElementById("source-cards").textContent;
  cd.querySelector(".catalogue-entry input:not(:disabled)").click();
  const selectionBefore = cd.getElementById("selection-count").textContent;
  comp.click("choose-comparison"); comp.click("catalogue-cancel");
  assert.equal(cd.getElementById("comparison-view").hidden, true);
  checks.push("comparison is disabled until two records exist; cancelled pair does not change state");
  comp.click("choose-comparison");
  const choices = cd.querySelectorAll("#catalogue-dialog-body select");
  assert.match(choices[0].options[0].textContent, /Record 1:/);
  choices[1].value = choices[0].value; comp.submit();
  assert.match(cd.getElementById("catalogue-error").textContent, /different saved records/);
  assert.equal(cd.getElementById("comparison-view").hidden, true);
  choices[1].selectedIndex = 1; comp.submit();
  assert.equal(cd.getElementById("comparison-view").hidden, false);
  assert.equal(cd.querySelectorAll(".comparison-row").length, 8);
  assert.match(cd.getElementById("comparison-result-count").textContent, /8 recorded paths/);
  assert.match(cd.getElementById("comparison-view").textContent, /Matching names and sizes do not prove identical contents/);
  assert.match(cd.querySelector(".comparison-details").textContent.replace(/\s+/g, " "), /complete within the recorded folder policy, not a whole-drive inventory/);
  assert.match(cd.getElementById("comparison-sources").textContent, /Partial picture/);
  assert.match(cd.getElementById("comparison-source-details").textContent, /2026-10-08T20:15:00-03:00/);
  checks.push("explicit pair exposes full counts, partial coverage and raw dates without identity claims");
  const filter = cd.getElementById("comparison-filter");
  const chooseFilter = (value) => { filter.value = value; filter.dispatchEvent(new comp.dom.window.Event("change")); };
  chooseFilter("matching"); assert.equal(cd.querySelectorAll(".comparison-row").length, 3);
  assert.match(cd.getElementById("comparison-results").textContent, /contents have not been compared/);
  chooseFilter("different"); assert.equal(cd.querySelectorAll(".comparison-row").length, 1);
  assert.match(cd.getElementById("comparison-results").textContent, /4.0 MiB/);
  assert.match(cd.getElementById("comparison-results").textContent, /5.0 MiB/);
  chooseFilter("left"); assert.equal(cd.querySelectorAll(".comparison-row").length, 2);
  assert.match(cd.getElementById("comparison-results").textContent, /Not listed in this snapshot/);
  chooseFilter("uncertain"); assert.equal(cd.querySelectorAll(".comparison-row").length, 1);
  assert.match(cd.getElementById("comparison-results").textContent, /unsupported/);
  assert.equal(cd.getElementById("source-cards").textContent, savedBefore.replace(/0 files or folders in your project selection/, "1 folder in your project selection"));
  assert.equal(cd.getElementById("selection-count").textContent, selectionBefore);
  checks.push("all comparison groups preserve source records and manual selection; approximate sizes retain disagreement");
  comp.click("choose-comparison"); comp.click("catalogue-close");
  assert.equal(filter.value, "uncertain"); assert.equal(cd.querySelectorAll(".comparison-row").length, 1);
  comp.click("choose-comparison");
  const leftChoice = cd.getElementById("comparison-left-choice"), rightChoice = cd.getElementById("comparison-right-choice"), temp = leftChoice.value;
  leftChoice.value = rightChoice.value; rightChoice.value = temp; comp.submit();
  assert.match(cd.querySelector(".comparison-source h3").textContent, /second project folder/);
  assert.equal(filter.value, "");
  checks.push("cancel preserves previous pair and filter; explicit reversal does not infer time order");
  comp.click("clear-comparison"); assert.equal(cd.getElementById("comparison-view").hidden, true);
  assert.equal(cd.activeElement.id, "choose-comparison");
  assert.equal(cd.getElementById("selection-count").textContent, selectionBefore);
  checks.push("closing comparison returns focus and leaves planning selection unchanged");
  const manySnapshot = JSON.parse(example); manySnapshot.entries = [manySnapshot.entries[0], ...Array.from({length: 110}, (_, n) => ({path: `item${String(n).padStart(3, "0")}`, kind: "file", status: "observed", logical_bytes: "1"}))];
  await comp.add(JSON.stringify(manySnapshot));
  comp.click("choose-comparison"); cd.getElementById("comparison-right-choice").selectedIndex = 2; comp.submit();
  assert.equal(cd.querySelectorAll(".comparison-row").length, 50); assert.match(cd.getElementById("comparison-result-count").textContent, /116 recorded paths/);
  comp.click("comparison-next"); assert.match(cd.getElementById("comparison-page").textContent, /Page 2 of 3/);
  comp.click("comparison-next"); assert.equal(cd.querySelectorAll(".comparison-row").length, 16);
  assert.equal(cd.getElementById("comparison-next").disabled, true);
  chooseFilter("matching"); assert.match(cd.getElementById("comparison-results").textContent, /No recorded paths in this group/); assert.match(cd.getElementById("comparison-page").textContent, /Page 1 of 1/);
  checks.push("comparison pagination counts every path and empty groups reset the page without silent omission");
  const compareReopened = C.add(C.empty(), JSON.parse(example), "Reopened location");
  await comp.file(C.exportCatalogue(compareReopened)); comp.submit();
  assert.equal(cd.getElementById("comparison-view").hidden, true);
  assert.equal(cd.getElementById("choose-comparison").disabled, true);
  assert.equal(cd.getElementById("selection-count").textContent, "0 files or folders selected");
  assert.deepEqual(comp.errors, []); comp.dom.window.close();
  checks.push("confirmed catalogue replacement retires pair state; no script/resource errors");
  console.log(
    `PASS: ${checks.length} catalogue DOM checks\n` + checks.map((x) => "  " + x).join("\n")
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
