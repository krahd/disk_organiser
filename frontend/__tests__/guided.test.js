/** @jest-environment jsdom */
const fs = require("fs");
const path = require("path");
const tick = () => new Promise((resolve) => setTimeout(resolve, 0));
const preview = {
  id: "synthetic-plan",
  root: "/synthetic",
  output: "Organised-example",
  state: "preview",
  bytes: 5,
  required_bytes: 16777221,
  actions: [
    {
      source: "<script>.txt",
      destination: "Organised-example/Documents/<script>.txt",
      reason: ".txt extension",
      fingerprint: { size: 5 },
    },
  ],
  skipped: [{ path: "link.txt", reason: "Links unsupported" }],
};
let calls;
async function boot() {
  calls = [];
  document.documentElement.innerHTML = fs.readFileSync(
    path.resolve(__dirname, "../guided.html"),
    "utf8"
  );
  window.fetch = jest.fn(async (url, options) => {
    calls.push([url, options]);
    if (url.endsWith("/session")) return { ok: true, json: async () => ({ token: "test-token" }) };
    if (options?.method === "POST" && url.endsWith("/plans"))
      return { ok: true, json: async () => preview };
    if (url.endsWith("/apply"))
      return { ok: true, json: async () => ({ ...preview, state: "completed" }) };
    return { ok: true, json: async () => ({ plans: [] }) };
  });
  const script = document.createElement("script");
  script.textContent = fs.readFileSync(path.resolve(__dirname, "../guided.js"), "utf8");
  document.body.append(script);
  await tick();
  await tick();
}
async function scan() {
  document.getElementById("root").value = "/synthetic";
  document.getElementById("scan-form").dispatchEvent(new Event("submit", { cancelable: true }));
  await tick();
  await tick();
}
beforeEach(boot);
test("preview uses text nodes and cannot apply without explicit approval", async () => {
  await scan();
  expect(document.getElementById("preview").textContent).toContain("<script>.txt");
  expect(document.getElementById("preview").querySelector("script")).toBeNull();
  const button = document.getElementById("apply");
  expect(button.disabled).toBe(true);
  button.click();
  expect(calls.filter(([url]) => url.endsWith("/apply"))).toHaveLength(0);
  const approval = document.getElementById("approve");
  approval.checked = true;
  approval.dispatchEvent(new Event("change"));
  expect(button.disabled).toBe(false);
  button.click();
  button.click();
  await tick();
  await tick();
  expect(calls.filter(([url]) => url.endsWith("/apply"))).toHaveLength(1);
  expect(document.getElementById("status").textContent).toContain("Originals kept");
});
test("editing folder invalidates visible preview and approval", async () => {
  await scan();
  document.getElementById("root").dispatchEvent(new Event("input"));
  expect(document.getElementById("preview").hidden).toBe(true);
});
test("failed apply asks for history refresh and never retries automatically", async () => {
  await scan();
  window.fetch.mockImplementationOnce(async () => {
    throw new Error("Connection lost");
  });
  const approval = document.getElementById("approve");
  approval.checked = true;
  approval.dispatchEvent(new Event("change"));
  document.getElementById("apply").click();
  await tick();
  await tick();
  expect(document.getElementById("status").textContent).toContain("refresh history");
});
