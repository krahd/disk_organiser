/** @jest-environment jsdom */
const fs = require("fs");
const path = require("path");
const { TextEncoder, TextDecoder } = require("util");
const assets = require("../model-assets/bundled.js");
const fixture = () => JSON.parse(assets.exampleText);
const tick = () => new Promise((resolve) => setTimeout(resolve, 0));
const flush = async () => {
  await tick();
  await tick();
};
let readers, workers, storageSpy;
class ControlledReader {
  constructor() {
    this.readyState = 0;
    readers.push(this);
  }
  readAsArrayBuffer(file) {
    this.file = file;
    this.readyState = 1;
  }
  abort() {
    this.readyState = 2;
    this.onabort?.();
  }
}
const $ = (id) => document.getElementById(id);
function finish(reader, text) {
  reader.result = new TextEncoder().encode(text).buffer;
  reader.readyState = 2;
  reader.onload();
}
function select(name = "example.json", size = 100) {
  Object.defineProperty($("model-file"), "files", { configurable: true, value: [{ name, size }] });
  $("model-file").dispatchEvent(new Event("change"));
  return readers[readers.length - 1];
}
async function open(data = fixture(), name = "import.json") {
  const reader = select(name, JSON.stringify(data).length);
  finish(reader, JSON.stringify(data));
  await flush();
}
async function example() {
  $("example").click();
  await flush();
}
const cards = () => [...document.querySelectorAll("#map-results .result-card")];
const byText = (text) =>
  [...document.querySelectorAll("button")].find((b) => b.textContent === text);
beforeEach(async () => {
  readers = [];
  workers = [];
  window.Worker = class {
    constructor(url) {
      if (url !== "disk-map-worker.js") throw new Error("Unexpected worker URL");
      workers.push(this);
      this.terminated = false;
    }
    postMessage({ text, bytes, ticket }) {
      setTimeout(() => {
        if (this.terminated) return;
        try {
          if (bytes !== undefined) {
            try {
              text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
            } catch (_) {
              throw new Error("The export is not valid UTF-8 text.");
            }
          }
          this.accepted = window.DiskMapModel.parse(text, window.DiskMapAssets.schema);
          this.onmessage({ data: { ticket, accepted: this.accepted } });
        } catch (error) {
          this.onmessage({ data: { ticket, error: error.message } });
        }
      }, 0);
    }
    terminate() {
      this.terminated = true;
    }
  };
  document.documentElement.innerHTML = fs.readFileSync(
    path.join(__dirname, "../disk-map.html"),
    "utf8"
  );
  window.FileReader = ControlledReader;
  window.TextDecoder = TextDecoder;
  window.TextEncoder = TextEncoder;
  window.fetch = jest.fn(() =>
    Promise.reject(new Error("Network is forbidden in the export viewer"))
  );
  storageSpy = jest.spyOn(Storage.prototype, "setItem");
  for (const file of ["model-assets/bundled.js", "disk-map-model.js", "disk-map.js"]) {
    const s = document.createElement("script");
    s.textContent = fs.readFileSync(path.join(__dirname, "..", file), "utf8");
    document.body.append(s);
  }
  await flush();
});
afterEach(() => {
  expect(window.fetch).not.toHaveBeenCalled();
  expect(storageSpy).not.toHaveBeenCalled();
  storageSpy.mockRestore();
});
test("synthetic map distinguishes coverage, logical data and unknown physical space", async () => {
  await example();
  expect($("map-content").hidden).toBe(false);
  expect($("model-origin").textContent).toContain("FABRICATED EXAMPLE");
  expect($("coverage-banner").textContent).toContain("Partial snapshot");
  expect($("storage-summary").textContent).toContain("Unknown");
  expect($("storage-summary").textContent).toContain("Logical size across observed paths");
  expect($("storage-summary").textContent).not.toContain("safe to delete");
  expect($("map-status").textContent).toContain(
    "no file contents or current disk state were verified"
  );
  expect(document.activeElement.id).toBe("map-title");
});
test("project hypothesis opens concrete evidence, uncertainty and unchanged review choices", async () => {
  await example();
  const project = cards().find((c) => c.textContent.includes("Possible directory role: project"));
  expect(project).toBeDefined();
  const trigger = project.querySelector("button");
  trigger.click();
  expect($("detail-content").textContent).toContain("pyproject.toml");
  expect($("detail-content").textContent).toContain("Hypothesis");
  expect($("detail-content").textContent).toContain("do not prove purpose");
  byText("Compare read-only review choices").click();
  expect($("detail-content").textContent).toContain(
    "Read-only questions, not an organisation plan"
  );
  expect($("detail-content").textContent).toContain("Retain the current structure");
  expect($("detail-content").textContent).toContain("Relationship confidence is separate");
  $("detail-back").click();
  expect($("detail-title").textContent).toContain("Possible directory role");
  $("detail-close").click();
  expect($("map-detail").hidden).toBe(true);
  expect(document.activeElement).toBe(trigger);
});
test("folder roles, relationship evidence and keyboard tabs keep interpretation separate", async () => {
  await example();
  $("tab-findings").focus();
  $("tab-findings").dispatchEvent(
    new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true })
  );
  expect(document.activeElement.id).toBe("tab-directories");
  expect($("tab-directories").getAttribute("aria-selected")).toBe("true");
  $("map-filter").value = "project";
  $("map-filter").dispatchEvent(new Event("change"));
  expect(cards()).toHaveLength(1);
  expect(cards()[0].textContent).toContain("Possible project");
  $("tab-relationships").click();
  expect($("view-explanation").textContent).toContain("backup sufficiency");
  const family = cards().find((c) => c.textContent.includes("Possible versions or exports"));
  family.querySelector("button").click();
  expect($("detail-content").textContent).toContain("do not prove version lineage");
  expect($("detail-content").textContent).toContain("Underlying paths");
  expect(document.querySelectorAll('button[id="apply"],button[id="recover"]')).toHaveLength(0);
});
test("search and empty filters do not change whole-snapshot totals", async () => {
  await example();
  const totals = $("storage-summary").textContent;
  $("tab-entries").click();
  $("map-search").value = "not-a-real-path";
  $("map-search").dispatchEvent(new Event("input"));
  expect($("result-count").textContent).toContain("No matches");
  expect($("storage-summary").textContent).toBe(totals);
  $("map-search").value = "";
  $("map-search").dispatchEvent(new Event("input"));
  expect(cards()).toHaveLength(16);
});
test("capped related observations disclose the omitted count", async () => {
  const data = fixture(),
    relationship = data.relationships[0];
  for (let i = 0; i < 28; i++)
    data.relationships.push({ ...relationship, id: `synthetic-extra-relationship-${i}` });
  const member = data.entries.find((entry) => entry.id === relationship.member_ids[0]);
  await open(data);
  $("tab-entries").click();
  cards()
    .find((card) => card.textContent.includes(member.relative_path))
    .querySelector("button")
    .click();
  expect($("detail-content").textContent).toMatch(/25 of \d+ related observations/);
  expect($("detail-content").textContent).toContain("original export");
});
test("invalid or oversized replacement preserves the previous view without reading oversized bytes", async () => {
  await example();
  const before = $("map-content").innerHTML;
  const invalid = select("broken.json");
  finish(invalid, "not JSON");
  await flush();
  expect($("map-status").textContent).toContain("not valid JSON");
  expect($("map-content").innerHTML).toBe(before);
  const count = readers.length;
  select("large.json", 8 * 1024 * 1024 + 1);
  expect(readers.length).toBe(count);
  expect($("map-status").textContent).toContain("was not read");
  expect($("map-content").innerHTML).toBe(before);
});
test("newer import wins and cancelling retains the last accepted view", async () => {
  await example();
  const first = select("first.json"),
    second = select("second.json");
  expect(first.readyState).toBe(2);
  finish(second, assets.exampleText);
  await flush();
  finish(first, assets.exampleText);
  await flush();
  expect($("map-title").textContent).toBe("second.json");
  const third = select("third.json");
  $("cancel-import").click();
  finish(third, assets.exampleText);
  await flush();
  expect($("map-title").textContent).toBe("second.json");
  expect($("map-status").textContent).toContain("cancelled");
});
test("clear interrupts pending validation and removes all imported labels and paths", async () => {
  const data = fixture();
  data.scan.roots[0].path = "/private-synthetic-marker";
  await open(data, "private-synthetic-export.json");
  const pending = select("late.json");
  finish(pending, assets.exampleText);
  $("clear-model").click();
  await flush();
  expect($("map-content").hidden).toBe(true);
  expect($("clear-model").disabled).toBe(true);
  expect(document.body.textContent).not.toContain("private-synthetic-marker");
  expect($("map-title").textContent).toBe("Storage snapshot");
  expect(document.activeElement.id).toBe("example");
});
test("file selection clears immediately so the same path can be reopened", async () => {
  const first = select("same.json");
  expect($("model-file").value).toBe("");
  finish(first, assets.exampleText);
  await flush();
  const second = select("same.json");
  expect(second).not.toBe(first);
  expect($("model-file").value).toBe("");
  finish(second, assets.exampleText);
  await flush();
  expect($("map-title").textContent).toBe("same.json");
});
test("read errors and malformed UTF-8 preserve the accepted snapshot", async () => {
  await example();
  const before = $("map-content").innerHTML;
  const failed = select();
  failed.onerror();
  expect($("map-content").innerHTML).toBe(before);
  const malformed = select();
  malformed.result = new Uint8Array([0xff]).buffer;
  malformed.readyState = 2;
  malformed.onload();
  await flush();
  expect($("map-status").textContent).toContain("not valid UTF-8");
  expect($("map-content").innerHTML).toBe(before);
});
test("imported strings stay literal and do not create elements or requests", async () => {
  const data = fixture();
  data.findings[0].title = '<img src=x onerror="throw 1">';
  await open(data, "<script>test</script>.json");
  expect($("map-title").textContent).toBe("<script>test</script>.json");
  expect($("map-results").textContent).toContain("<img src=x");
  expect($("map-results").querySelector("img,script")).toBeNull();
  expect(document.querySelector('meta[http-equiv="Content-Security-Policy"]').content).toContain(
    "connect-src 'none'"
  );
});
test("unknown allocation and future capture time are explicit", async () => {
  const data = fixture();
  data.entries.forEach((e) => {
    e.allocated_bytes = null;
    e.allocation_source = "unknown";
  });
  data.aggregates.known_allocated_bytes_by_observed_object = null;
  data.aggregates.allocation_unknown_objects = data.aggregates.distinct_observed_file_objects;
  data.scan.started_at = "2090-01-01T00:00:00Z";
  await open(data);
  expect($("storage-summary").textContent).toContain("Known allocated bytesUnknown");
  expect($("scope-content").textContent).toContain("Recorded time is in the future");
  expect($("scope-content").textContent).toContain("Freshness is unknown");
});

test("a preparation/render error preserves the whole old model, controls, detail and focus", async () => {
  await example();
  const project = cards().find((c) => c.textContent.includes("Possible directory role: project"));
  project.querySelector("button").click();
  $("map-search").value = "project";
  $("map-search").dispatchEvent(new Event("input"));
  const before = $("map-content").innerHTML,
    focused = document.activeElement;
  const original = document.createElement.bind(document);
  let injected = false;
  const spy = jest.spyOn(document, "createElement").mockImplementation((tag) => {
    if (tag === "article" && !injected) {
      injected = true;
      throw new Error("Synthetic preparation failure");
    }
    return original(tag);
  });
  try {
    await open(fixture(), "replacement.json");
  } finally {
    spy.mockRestore();
  }
  expect(injected).toBe(true);
  expect($("map-content").innerHTML).toBe(before);
  expect(document.activeElement).toBe(focused);
  expect($("map-status").textContent).toContain("previous accepted view is unchanged");
});
test("uncertainty/evidence disclosure has bounded nodes and explicit omitted counts", async () => {
  const data = fixture();
  data.scan.uncertainties = Array.from({ length: 100 }, (_, i) => `Uncertainty ${i}`);
  data.evidence[0].observations = Object.fromEntries(
    Array.from({ length: 120 }, (_, i) => [`Field-${i}`, "Detail ".repeat(200)])
  );
  await open(data);
  expect($("scope-content").textContent).toContain("Showing 20 of");
  expect($("scope-content").querySelectorAll("li").length).toBeLessThan(50);
  const found = data.findings.find((f) => f.evidence_ids.includes(data.evidence[0].id));
  cards()
    .find((c) => c.textContent.includes(found.title))
    .querySelector("button")
    .click();
  expect($("detail-content").textContent).toContain("Showing 10 of 120 evidence fields");
  expect($("detail-content").textContent).toContain("summary limited");
  expect($("map-content").querySelectorAll("*").length).toBeLessThanOrEqual(7000);
  expect($("map-content").textContent.length).toBeLessThanOrEqual(2 * 1024 * 1024);
});
test("empty searches never expand or iterate the unique path index", async () => {
  await example();
  const accepted = workers[0].accepted;
  const iterator = accepted.searchPaths[Symbol.iterator].bind(accepted.searchPaths);
  const spy = jest.fn(iterator);
  accepted.searchPaths[Symbol.iterator] = spy;
  $("tab-entries").click();
  expect(spy).not.toHaveBeenCalled();
  $("map-search").value = "Notes";
  $("map-search").dispatchEvent(new Event("input"));
  expect(spy).toHaveBeenCalledTimes(1);
});
test("member pagination keeps focus on the announced page when Next disappears", async () => {
  await open(require("./disk-map-fixtures.js").flatModel(60));
  cards()[0].querySelector("button").click();
  const next = byText("Show next 25 members");
  next.focus();
  next.click();
  expect(document.activeElement.textContent).toContain("26–50");
  next.click();
  expect(next.hidden).toBe(true);
  expect(document.activeElement.textContent).toContain("51–60");
  byText("Previous members").click();
  expect(document.activeElement.textContent).toContain("26–50");
});
test("Cancel terminates worker validation without losing the accepted view", async () => {
  await example();
  const before = $("map-content").innerHTML;
  const previousWorker = window.Worker;
  let terminated = false;
  window.Worker = class {
    postMessage() {}
    terminate() {
      terminated = true;
    }
  };
  try {
    const pending = select("pending-validation.json");
    finish(pending, assets.exampleText);
    await tick();
    $("cancel-import").click();
    await flush();
  } finally {
    window.Worker = previousWorker;
  }
  expect(terminated).toBe(true);
  expect($("map-content").innerHTML).toBe(before);
  expect($("map-status").textContent).toContain("cancelled");
});
