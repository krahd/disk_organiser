const fs = require("fs");
const path = require("path");
const { TextDecoder, TextEncoder } = require("util");
const { createObservationDemo } = require("../project-observation-demo");
const model = require("../project-intent-model");
const fixture = require("./project-observation-fixture.json");
const copy = (value) => JSON.parse(JSON.stringify(value));
const id = (name) => document.getElementById(`observation-${name}`);
const settle = () => new Promise((resolve) => setTimeout(resolve, 0));
const response = (value) => ({ ok: true, status: 200, json: async () => copy(value) });
let fetchMock, readers, listeners, blobs, createURL, revokeURL;
function editor() {
  return {
    members: fixture.choices.map((choice, index) => ({
      entry_id: choice.entry.id,
      included: id(`member-${index}`).checked,
      project_path: id(`path-${index}`).value,
    })),
    destination_root_id: id("root").value,
    destination_folder: id("folder").value,
  };
}
function fileText() {
  const intent = editor();
  intent.members[1].included = false;
  intent.members[1].project_path = "Unused/edited path";
  intent.members[0].project_path = "Design/saved.blend";
  intent.destination_root_id = fixture.roots[0].id;
  intent.destination_folder = "Saved choices";
  return model.serialise(intent, fixture);
}
function chooseFile(size = 100) {
  Object.defineProperty(id("choices-file"), "files", { configurable: true, value: [{ size }] });
  id("choices-file").dispatchEvent(new Event("change"));
  return readers[readers.length - 1];
}
function read(text) {
  const reader = chooseFile();
  reader.succeed(text);
  return reader;
}
function edit(name, value, silent = false) {
  const element = id(name);
  if (element.type === "checkbox") element.checked = value;
  else element.value = value;
  if (!silent) element.dispatchEvent(new Event("input", { bubbles: true }));
}
async function accepted() {
  const result = copy(fixture);
  result.decision_revision = 2;
  fetchMock.mockResolvedValueOnce(response(result));
  id("form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  await settle();
  expect(id("save").disabled).toBe(false);
}
function snapshot() {
  return {
    editor: editor(),
    html: id("review-content").innerHTML,
    saveDisabled: id("save").disabled,
  };
}
beforeEach(async () => {
  document.documentElement.innerHTML = fs
    .readFileSync(path.join(__dirname, "../project-observation-demo.html"), "utf8")
    .replace(/<!doctype html>/i, "");
  readers = [];
  listeners = [];
  blobs = [];
  const add = window.addEventListener.bind(window);
  jest.spyOn(window, "addEventListener").mockImplementation((name, listener, ...args) => {
    if (["pageshow", "pagehide"].includes(name)) listeners.push([name, listener]);
    add(name, listener, ...args);
  });
  class Reader {
    constructor() {
      this.readyState = 0;
      readers.push(this);
    }
    readAsArrayBuffer() {
      this.readyState = 1;
    }
    abort() {
      this.readyState = 2;
      if (this.onabort) this.onabort();
    }
    succeed(text) {
      const bytes = typeof text === "string" ? new TextEncoder().encode(text) : text;
      this.result = new window.Uint8Array(bytes).buffer;
      this.readyState = 2;
      this.onload();
    }
  }
  jest.spyOn(window, "FileReader").mockImplementation(() => new Reader());
  Object.defineProperty(window, "TextDecoder", { configurable: true, value: TextDecoder });
  jest.spyOn(window, "Blob").mockImplementation((parts, options) => {
    const value = { parts, options };
    blobs.push(value);
    return value;
  });
  createURL = jest.fn(() => `blob:choices-${blobs.length}`);
  revokeURL = jest.fn();
  Object.defineProperty(window.URL, "createObjectURL", { configurable: true, value: createURL });
  Object.defineProperty(window.URL, "revokeObjectURL", { configurable: true, value: revokeURL });
  jest.spyOn(window.HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  fetchMock = jest.fn().mockResolvedValue(response(fixture));
  await createObservationDemo(document, fetchMock).ready;
});
afterEach(() => {
  for (const [name, listener] of listeners) {
    if (name === "pagehide") listener();
    window.removeEventListener(name, listener);
  }
  jest.restoreAllMocks();
});

test("saves all editable choices before Review without transmitting them", async () => {
  edit("path-3", "../unfinished: text");
  const before = snapshot();
  id("save-choices").click();
  expect(blobs).toHaveLength(1);
  expect(model.parse(blobs[0].parts[0], fixture)).toEqual(editor());
  expect(blobs[0].options.type).toBe("application/json");
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(snapshot()).toEqual(before);
  expect(id("choices-status").textContent).toContain("download requested");
  await settle();
  expect(revokeURL).toHaveBeenCalledTimes(1);
});

test("opening stages without replacing; Cancel preserves accepted review and edits", async () => {
  await accepted();
  const before = snapshot();
  read(fileText());
  expect(id("choices-preview").hidden).toBe(false);
  expect(id("choices-summary").textContent).toContain(
    "0 members added · 1 removed · 2 edited paths"
  );
  expect(id("choices-summary").querySelectorAll(".destination-grid .current-layout")).toHaveLength(
    2
  );
  expect(id("choices-summary").textContent).toContain("Current choices");
  expect(id("choices-summary").textContent).toContain("Saved choices");
  expect(id("choices-summary").querySelector("details").open).toBe(false);
  expect(document.activeElement).toBe(id("choices-preview-heading"));
  expect(snapshot()).toEqual(before);
  id("cancel-choices").click();
  expect(snapshot()).toEqual(before);
  expect(id("choices-preview").hidden).toBe(true);
  expect(document.activeElement).toBe(id("open-choices"));
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

test("Replace restores every choice but no accepted review or report export", async () => {
  await accepted();
  const input = fileText();
  read(input);
  id("replace-choices").click();
  expect(editor()).toEqual(model.parse(input, fixture));
  expect(id("save").disabled).toBe(true);
  expect(id("review-content").textContent).toBe("");
  expect(document.activeElement).toBe(id("review-button"));
  expect(id("choices-status").textContent).toContain("Review again");
  expect(fetchMock).toHaveBeenCalledTimes(2);
  id("form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  expect(JSON.parse(fetchMock.mock.calls[2][1].body)).toEqual(
    model.requestFor(model.parse(input, fixture), fixture)
  );
  await settle();
});

test.each([
  ["malformed JSON", () => "{"],
  ["invalid UTF-8", () => new Uint8Array([0xc0, 0xaf])],
  [
    "saved display report",
    () =>
      JSON.stringify({
        schema_version: "disk-administration-observation-review-export/v1",
        report_kind: "synthetic_display_report",
      }),
  ],
  [
    "stale source",
    () => {
      const file = JSON.parse(fileText());
      file.source.source_revision++;
      return JSON.stringify(file);
    },
  ],
  [
    "extra evidence",
    () => {
      const file = JSON.parse(fileText());
      file.intent.evidence = { verified: true };
      return JSON.stringify(file);
    },
  ],
  [
    "relative traversal",
    () => {
      const file = JSON.parse(fileText());
      file.intent.destination_folder = "../other";
      return JSON.stringify(file);
    },
  ],
  ["post-read oversize", () => " ".repeat(8193)],
])("%s preserves controls, report DOM and export", async (_name, input) => {
  await accepted();
  const before = snapshot();
  read(input());
  expect(snapshot()).toEqual(before);
  expect(id("choices-preview").hidden).toBe(true);
  expect(id("choices-status").textContent).toContain("unchanged");
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

test("oversized file is rejected before reading", async () => {
  await accepted();
  const before = snapshot();
  chooseFile(8193);
  expect(readers).toHaveLength(0);
  expect(snapshot()).toEqual(before);
});

test("file read failure and retry preserve prior review", async () => {
  await accepted();
  const before = snapshot();
  const reader = chooseFile();
  reader.onerror();
  expect(snapshot()).toEqual(before);
  expect(id("choices-status").textContent).toContain("retry");
  read(fileText());
  expect(id("choices-preview").hidden).toBe(false);
});

test("empty picker and repeated same-file selections do not mutate current choices", () => {
  const click = jest.spyOn(id("choices-file"), "click").mockImplementation(() => {});
  const before = snapshot();
  id("open-choices").click();
  Object.defineProperty(id("choices-file"), "files", { configurable: true, value: [] });
  id("choices-file").dispatchEvent(new Event("change"));
  expect(snapshot()).toEqual(before);
  expect(click).toHaveBeenCalledTimes(1);
  const input = fileText();
  read(input);
  id("cancel-choices").click();
  read(input);
  expect(id("choices-preview").hidden).toBe(false);
  expect(snapshot()).toEqual(before);
});

test("a later file selection wins over a delayed earlier read", () => {
  const firstText = fileText();
  const first = chooseFile();
  const secondText = JSON.parse(firstText);
  secondText.intent.destination_folder = "Second choice";
  const second = chooseFile();
  second.succeed(JSON.stringify(secondText));
  first.succeed(firstText);
  expect(id("choices-summary").textContent).toContain("Second choice");
  id("replace-choices").click();
  expect(id("folder").value).toBe("Second choice");
});

test.each([false, true])(
  "%s silent unchecked edit during file read cannot be overwritten",
  (silent) => {
    const input = fileText();
    const reader = chooseFile();
    edit("path-7", "New unchecked edit", silent);
    const before = snapshot();
    reader.succeed(input);
    id("replace-choices").click();
    expect(snapshot()).toEqual(before);
    expect(id("choices-preview").hidden).toBe(true);
  }
);

test.each(["folder", "path-7", "member-7", "root"])(
  "silent %s edit invalidates staged replacement",
  (name) => {
    read(fileText());
    const value =
      name === "member-7" ? true : name === "root" ? fixture.roots[0].id : "New current edit";
    edit(name, value, true);
    const before = snapshot();
    id("replace-choices").click();
    expect(snapshot()).toEqual(before);
    expect(id("choices-preview").hidden).toBe(true);
    expect(id("choices-status").textContent).toContain("changed after opening");
  }
);

test.each(["reload", "dismiss", "pagehide", "pageshow"])(
  "late file read cannot survive %s",
  async (action) => {
    const input = fileText();
    const reader = chooseFile();
    if (action === "pagehide") listeners.find(([name]) => name === "pagehide")[1]();
    else if (action === "pageshow")
      listeners.find(([name]) => name === "pageshow")[1]({ persisted: true });
    else id(action).click();
    await settle();
    const before = snapshot();
    reader.succeed(input);
    expect(snapshot()).toEqual(before);
    expect(id("choices-preview").hidden).toBe(true);
  }
);

test("replacement cancels pending review and its late result cannot restore report export", async () => {
  let finish;
  fetchMock.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      })
  );
  id("form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  const signal = fetchMock.mock.calls[1][1].signal;
  const input = fileText();
  read(input);
  id("replace-choices").click();
  expect(signal.aborted).toBe(true);
  const value = copy(fixture);
  value.decision_revision = 2;
  finish(response(value));
  await settle();
  expect(editor()).toEqual(model.parse(input, fixture));
  expect(id("save").disabled).toBe(true);
  expect(id("review-content").textContent).toBe("");
});

test("HTML-like imported text is shown literally", () => {
  const input = JSON.parse(fileText());
  input.intent.members[0].project_path = '<img onerror="fake()">.blend';
  read(JSON.stringify(input));
  expect(id("choices-summary").querySelector("img")).toBeNull();
  expect(id("choices-summary").textContent).toContain('<img onerror="fake()">.blend');
});

test("failed download and repeated Save leave choices and review unchanged", async () => {
  await accepted();
  const before = snapshot();
  createURL.mockImplementationOnce(() => {
    throw new Error("unavailable");
  });
  id("save-choices").click();
  expect(snapshot()).toEqual(before);
  expect(id("choices-status").textContent).toContain("could not be saved");
  id("save-choices").click();
  id("save-choices").click();
  await settle();
  expect(snapshot()).toEqual(before);
  expect(revokeURL).toHaveBeenCalledTimes(2);
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

test("silent edit at download creation stops the stale choices download", () => {
  createURL.mockImplementationOnce(() => {
    edit("path-7", "Changed synchronously", true);
    return "blob:stale";
  });
  id("save-choices").click();
  expect(window.HTMLAnchorElement.prototype.click).not.toHaveBeenCalled();
  expect(revokeURL).toHaveBeenCalledWith("blob:stale");
  expect(id("choices-status").textContent).toContain("changed before download");
});

test("page exit during URL creation prevents later activation and cleans the new URL", () => {
  createURL.mockImplementationOnce(() => {
    listeners.find(([name]) => name === "pagehide")[1]();
    return "blob:exited";
  });
  id("save-choices").click();
  expect(window.HTMLAnchorElement.prototype.click).not.toHaveBeenCalled();
  expect(revokeURL).toHaveBeenCalledWith("blob:exited");
});

test("reload during activation preserves the current source-loading status", async () => {
  let finish;
  fetchMock.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      })
  );
  window.HTMLAnchorElement.prototype.click.mockImplementationOnce(() => id("reload").click());
  id("save-choices").click();
  expect(id("choices-status").textContent).toBe("Load the Aurora reference first.");
  finish(response(fixture));
  await settle();
});

test("combined activation and cleanup failure remains visible and retries on page cleanup", () => {
  window.HTMLAnchorElement.prototype.click.mockImplementationOnce(() => {
    throw new Error("Activation failed");
  });
  revokeURL.mockImplementationOnce(() => {
    throw new Error("Revoke failed");
  });
  id("save-choices").click();
  expect(id("choices-status").textContent).toContain("cleanup failed");
  const url = createURL.mock.results[0].value;
  listeners.find(([name]) => name === "pagehide")[1]();
  expect(revokeURL.mock.calls.filter(([value]) => value === url)).toHaveLength(2);
});

test("stale download cleanup failure is not hidden by the changed-choices status", () => {
  createURL.mockImplementationOnce(() => {
    edit("path-7", "Changed", true);
    return "blob:stale-cleanup";
  });
  revokeURL.mockImplementationOnce(() => {
    throw new Error("Revoke failed");
  });
  id("save-choices").click();
  expect(id("choices-status").textContent).toContain("cleanup failed");
  expect(window.HTMLAnchorElement.prototype.click).not.toHaveBeenCalled();
});
