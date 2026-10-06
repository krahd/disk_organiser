/** @jest-environment jsdom */
const fs = require("fs");
const path = require("path");
const tick = () => new Promise((resolve) => setTimeout(resolve, 0));
const flush = async () => {
  await tick();
  await tick();
};
const fixture = (count = 1) => ({
  id: "synthetic-plan",
  root: "/synthetic",
  output: "Organised-example",
  state: "preview",
  can_apply: true,
  recovery_available: false,
  bytes: 5 * count,
  required_bytes: 16777216 + 5 * count,
  actions: Array.from({ length: count }, (_, i) => ({
    source: i ? `File-${i}.txt` : "<script>.txt",
    destination: `Organised-example/Documents/${i ? `File-${i}.txt` : "<script>.txt"}`,
    reason: ".txt extension; content is not interpreted",
    fingerprint: { size: 5 },
  })),
  skipped: [{ path: "Nested folder", reason: "Nested folders unsupported" }],
});
let calls, preview, records;
async function boot() {
  calls = [];
  preview = fixture();
  records = [];
  document.documentElement.innerHTML = fs.readFileSync(
    path.resolve(__dirname, "../guided.html"),
    "utf8"
  );
  window.fetch = jest.fn(async (url, options) => {
    calls.push([url, options]);
    if (url.endsWith("/session"))
      return {
        ok: true,
        json: async () => ({
          token: "test-token",
          capabilities: { copy_apply: { enabled: true } },
        }),
      };
    if (options?.method === "POST" && url.endsWith("/plans"))
      return { ok: true, json: async () => preview };
    if (url.endsWith("/apply")) {
      records = [{ ...preview, state: "completed", can_apply: false }];
      return { ok: true, json: async () => records[0] };
    }
    return { ok: true, json: async () => ({ plans: records, blocked_records: 0 }) };
  });
  const script = document.createElement("script");
  script.textContent = fs.readFileSync(path.resolve(__dirname, "../guided.js"), "utf8");
  document.body.append(script);
  await flush();
}
async function scan(copies = true) {
  if (copies) document.querySelector('[value="copies"]').checked = true;
  document.getElementById("root").value = "/synthetic";
  document.getElementById("scan-form").dispatchEvent(new Event("submit", { cancelable: true }));
  await flush();
}
const button = (text) =>
  [...document.querySelectorAll("button")].find((el) => el.textContent === text);
const approve = () => {
  const el = document.getElementById("approve");
  el.checked = true;
  el.dispatchEvent(new Event("change"));
};
beforeEach(boot);
test("overview defaults to understanding, keeps exact effects behind a deliberate next step", async () => {
  await scan(false);
  expect(document.getElementById("copy-effects").hidden).toBe(true);
  expect(document.getElementById("preview").textContent).toContain("1 supported file");
  button("Review the copy layout").click();
  expect(document.getElementById("copy-effects").hidden).toBe(false);
  expect(document.activeElement.textContent).toBe("3. Review the exact effects");
});
test("safe text nodes and explicit approval; repeated clicks send one request", async () => {
  await scan();
  expect(document.getElementById("preview").textContent).toContain("<script>.txt");
  expect(document.getElementById("preview").querySelector("script")).toBeNull();
  expect(document.querySelector('td[data-label="Why / size"]')).not.toBeNull();
  const apply = document.getElementById("apply");
  expect(apply.disabled).toBe(true);
  apply.click();
  expect(calls.filter(([url]) => url.endsWith("/apply"))).toHaveLength(0);
  approve();
  apply.click();
  apply.click();
  await flush();
  expect(calls.filter(([url]) => url.endsWith("/apply"))).toHaveLength(1);
  expect(document.getElementById("status").textContent).toContain("Originals kept");
  expect(document.getElementById("history").textContent).toContain(
    "Automatic copy removal is unavailable"
  );
  expect(calls.some(([url]) => url.endsWith("/recover"))).toBe(false);
});
test("editing the folder and closing the preview discard approval", async () => {
  await scan();
  approve();
  document.getElementById("root").dispatchEvent(new Event("input"));
  expect(document.getElementById("preview").hidden).toBe(true);
  expect(document.getElementById("approve")).toBeNull();
  await scan();
  approve();
  button("Close preview").click();
  expect(document.getElementById("preview").hidden).toBe(true);
  expect(document.activeElement.id).toBe("root");
});
test("choosing to keep the layout sends no file operation", async () => {
  await scan();
  button("Keep the current layout").click();
  expect(document.getElementById("status").textContent).toContain("No copies requested");
  expect(calls.filter(([url]) => /apply|recover/.test(url))).toHaveLength(0);
});
test("ambiguous apply clears approval and blocks new requests until history succeeds", async () => {
  await scan();
  window.fetch.mockImplementationOnce(async () => {
    throw new Error("Connection lost");
  });
  approve();
  document.getElementById("apply").click();
  await flush();
  expect(document.getElementById("status").textContent).toContain("not confirmed");
  expect(document.getElementById("scan").disabled).toBe(true);
  expect(document.getElementById("apply")).toBeNull();
  window.fetch.mockImplementationOnce(async () => {
    throw new Error("Still offline");
  });
  document.getElementById("refresh").click();
  await flush();
  expect(document.getElementById("scan").disabled).toBe(true);
  document.getElementById("refresh").click();
  await flush();
  expect(document.getElementById("scan").disabled).toBe(false);
});
test("saved previews without explicit capability cannot offer approval", async () => {
  preview.can_apply = false;
  await scan();
  expect(document.getElementById("apply")).toBeNull();
  expect(document.getElementById("approve")).toBeNull();
  expect(document.getElementById("preview").textContent).toContain("Scan the folder again");
  delete preview.can_apply;
  await scan();
  expect(document.getElementById("apply")).toBeNull();
});
test("500-file preview is paged and filtering never implies subset approval", async () => {
  preview = fixture(500);
  await scan();
  expect(document.querySelectorAll("#preview tbody tr")).toHaveLength(25);
  approve();
  button("Next 25").click();
  expect(document.querySelector("#preview tbody").textContent).toContain("File-25.txt");
  expect(document.getElementById("approve").checked).toBe(false);
  const search = document.querySelector('input[type="search"]');
  search.value = "File-499.txt";
  search.dispatchEvent(new Event("input"));
  expect(document.querySelectorAll("#preview tbody tr")).toHaveLength(1);
  expect(document.getElementById("preview").textContent).toContain("Full plan: 500 copies");
  expect(document.getElementById("apply").textContent).toContain("500");
  search.value = "no-such-file";
  search.dispatchEvent(new Event("input"));
  expect(document.getElementById("preview").textContent).toContain("No matching files");
});
test("empty supported set explains incomplete coverage and has no apply", async () => {
  preview = fixture(0);
  await scan();
  expect(document.getElementById("apply")).toBeNull();
  expect(document.getElementById("preview").textContent).toContain(
    "does not mean the folder is empty"
  );
});
test("invalid saved records are counted and retained without recovery controls", async () => {
  window.fetch.mockImplementationOnce(async () => ({
    ok: true,
    json: async () => ({ plans: [], blocked_records: 2 }),
  }));
  document.getElementById("refresh").click();
  await flush();
  expect(document.getElementById("history-notice").hidden).toBe(false);
  expect(document.getElementById("history-notice").textContent).toContain("2 saved records");
  expect(document.body.textContent).not.toContain("Undo / recover generated copies");
});
test("saved record review restores the overview without trusting persisted approval", async () => {
  records = [{ ...fixture(), can_apply: false }];
  document.getElementById("refresh").click();
  await flush();
  button("Review saved preview").click();
  expect(document.getElementById("preview").textContent).toContain("Saved snapshot");
  expect(document.getElementById("apply")).toBeNull();
  button("Choose this folder for a new scan").click();
  expect(document.getElementById("root").value).toBe("/synthetic");
  expect(
    calls.filter(([url, opts]) => url.endsWith("/plans") && opts?.method === "POST")
  ).toHaveLength(0);
});

test("read-only capability cannot be overcome by a plan capability and does not suggest rescan enables copying", async () => {
  window.fetch.mockImplementationOnce(async () => ({
    ok: true,
    json: async () => ({
      plans: [],
      blocked_records: 0,
      capabilities: { copy_apply: { enabled: false } },
    }),
  }));
  document.getElementById("refresh").click();
  await flush();
  await scan();
  expect(document.getElementById("apply")).toBeNull();
  expect(document.getElementById("preview").textContent).toContain(
    "scanning again will not enable it"
  );
  expect(document.getElementById("safety-title").textContent).toContain("Read-only preview");
});
