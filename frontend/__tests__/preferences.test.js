/**
 * @jest-environment jsdom
 */

const fs = require("fs");
const path = require("path");

function jsonResponse(payload) {
  return Promise.resolve({
    ok: true,
    json: async () => payload,
  });
}

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

describe("Preferences and Ollama controls", () => {
  let fetchMock;
  let scriptLoaded = false;

  beforeAll(() => {
    document.documentElement.innerHTML = fs.readFileSync(
      path.resolve(__dirname, "..", "index.html"),
      "utf8"
    );

    fetchMock = jest.fn((url, options = {}) => {
      if (url === "/api/ops") return jsonResponse({ ops: {} });
      if (url === "/api/model" && (!options.method || options.method === "GET")) {
        return jsonResponse({ model: "modelito" });
      }
      if (url === "/api/preferences" && (!options.method || options.method === "GET")) {
        return jsonResponse({ preferences: { ollama_model: "llama3.2:3b" } });
      }
      if (url === "/api/ollama/status") {
        return jsonResponse({
          sdk_available: true,
          installed: true,
          running: true,
          local_models: ["llama3.2:3b"],
          running_models: ["llama3.2:3b"],
        });
      }
      if (url === "/api/model" && options.method === "POST") {
        return jsonResponse({ model: JSON.parse(options.body).model });
      }
      if (url === "/api/preferences" && options.method === "POST") {
        return jsonResponse({ preferences: JSON.parse(options.body).preferences });
      }
      if (url === "/api/ollama/install")
        return jsonResponse({ ok: true, action: "install", ollama: {} });
      if (url === "/api/ollama/start")
        return jsonResponse({ ok: true, action: "start", ollama: {} });
      if (url === "/api/ollama/stop") return jsonResponse({ ok: true, action: "stop", ollama: {} });
      if (url === "/api/ollama/pull") {
        return jsonResponse({
          ok: true,
          action: "pull",
          model: JSON.parse(options.body).model,
          ollama: {},
        });
      }
      if (url === "/api/ollama/serve") {
        return jsonResponse({
          ok: true,
          action: "serve",
          model: JSON.parse(options.body || "{}").model,
          ollama: {},
        });
      }
      if (url === "/api/ollama/delete") {
        return jsonResponse({
          ok: true,
          action: "delete",
          model: JSON.parse(options.body).model,
          ollama: {},
        });
      }
      return jsonResponse({});
    });

    global.fetch = fetchMock;

    if (!scriptLoaded) {
      const scriptContent = fs.readFileSync(path.resolve(__dirname, "..", "main.js"), "utf8");
      const scriptEl = document.createElement("script");
      scriptEl.textContent = scriptContent;
      document.head.appendChild(scriptEl);
      scriptLoaded = true;
    }
    document.dispatchEvent(new Event("DOMContentLoaded"));
  });

  beforeEach(() => {
    fetchMock.mockClear();
  });

  test("renders Ollama controls and saves provider plus model preference", async () => {
    document.getElementById("nav-preferences").click();
    await flush();
    await flush();

    expect(document.getElementById("ollama-install")).toBeTruthy();
    expect(document.getElementById("ollama-start")).toBeTruthy();
    expect(document.getElementById("ollama-stop")).toBeTruthy();
    expect(document.getElementById("ollama-pull")).toBeTruthy();
    expect(document.getElementById("ollama-serve")).toBeTruthy();
    expect(document.getElementById("ollama-delete")).toBeTruthy();

    document.getElementById("pref-ollama-model").value = "qwen2.5:7b";
    document.getElementById("pref-save").click();
    await flush();
    await flush();

    const modelCall = fetchMock.mock.calls.find(
      ([url, options]) => url === "/api/model" && options && options.method === "POST"
    );
    const prefsCall = fetchMock.mock.calls.find(
      ([url, options]) => url === "/api/preferences" && options && options.method === "POST"
    );

    expect(modelCall).toBeTruthy();
    expect(JSON.parse(modelCall[1].body)).toEqual({ model: "modelito" });
    expect(prefsCall).toBeTruthy();
    expect(JSON.parse(prefsCall[1].body).preferences.ollama_model).toBe("qwen2.5:7b");
  });

  test("wires Ollama lifecycle buttons to API endpoints", async () => {
    document.getElementById("nav-preferences").click();
    await flush();
    await flush();

    document.getElementById("ollama-model-name").value = "llama3.2:3b";
    document.getElementById("ollama-install").click();
    document.getElementById("ollama-start").click();
    document.getElementById("ollama-stop").click();
    document.getElementById("ollama-pull").click();
    document.getElementById("ollama-serve").click();
    document.getElementById("ollama-delete").click();
    await flush();
    await flush();

    expect(fetchMock.mock.calls.some(([url]) => url === "/api/ollama/install")).toBe(true);
    expect(fetchMock.mock.calls.some(([url]) => url === "/api/ollama/start")).toBe(true);
    expect(fetchMock.mock.calls.some(([url]) => url === "/api/ollama/stop")).toBe(true);
    expect(fetchMock.mock.calls.some(([url]) => url === "/api/ollama/pull")).toBe(true);
    expect(fetchMock.mock.calls.some(([url]) => url === "/api/ollama/serve")).toBe(true);
    expect(fetchMock.mock.calls.some(([url]) => url === "/api/ollama/delete")).toBe(true);
  });
});
