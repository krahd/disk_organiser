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

function buildReasonPayload(overrides = {}) {
  const payload = {
    op: { id: "op-1" },
    summary: { actions: 2, groups: { "Semantic groups": 2 }, bytes: 2048 },
    analysis_capabilities: {
      ocr: { available: false, image: false, pdf: false, missing: ["pytesseract"] },
      embeddings: {
        available: false,
        disabled: false,
        model: "all-MiniLM-L6-v2",
        missing: ["sentence-transformers"],
      },
    },
    grouped: {
      "Semantic groups": [
        {
          action: "move",
          from: "/tmp/a.txt",
          to: "/tmp/Organised/a.txt",
          confidence: 0.88,
          reason: "Similar content",
          near_duplicate_signals: ["content-overlap"],
        },
        {
          action: "move",
          from: "/tmp/b.txt",
          to: "/tmp/Organised/b.txt",
          confidence: 0.81,
          reason: "Similar content",
          near_duplicate_signals: ["content-overlap"],
        },
      ],
    },
    actions: [
      {
        action: "move",
        from: "/tmp/a.txt",
        to: "/tmp/Organised/a.txt",
        confidence: 0.88,
        reason: "Similar content",
        near_duplicate_signals: ["content-overlap"],
      },
      {
        action: "move",
        from: "/tmp/b.txt",
        to: "/tmp/Organised/b.txt",
        confidence: 0.81,
        reason: "Similar content",
        near_duplicate_signals: ["content-overlap"],
      },
    ],
  };

  return {
    ...payload,
    ...overrides,
    analysis_capabilities: {
      ...payload.analysis_capabilities,
      ...(overrides.analysis_capabilities || {}),
      ocr: {
        ...payload.analysis_capabilities.ocr,
        ...((overrides.analysis_capabilities && overrides.analysis_capabilities.ocr) || {}),
      },
      embeddings: {
        ...payload.analysis_capabilities.embeddings,
        ...((overrides.analysis_capabilities && overrides.analysis_capabilities.embeddings) || {}),
      },
    },
  };
}

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

describe("Organise analysis flow", () => {
  let fetchMock;
  let scriptLoaded = false;

  beforeAll(() => {
    document.documentElement.innerHTML = fs.readFileSync(
      path.resolve(__dirname, "..", "index.html"),
      "utf8"
    );

    class MockEventSource {
      static instances = [];

      constructor(url) {
        this.url = url;
        this.onmessage = null;
        this.onerror = null;
        this.closed = false;
        MockEventSource.instances.push(this);
      }

      close() {
        this.closed = true;
      }

      emit(data) {
        if (this.onmessage) {
          this.onmessage({ data: JSON.stringify(data) });
        }
      }
    }

    global.EventSource = MockEventSource;

    fetchMock = jest.fn((url, options = {}) => {
      if (url === "/api/ops") return jsonResponse({ ops: {} });
      if (url === "/api/analyse/start") return jsonResponse({ job_id: "job-1" });
      if (url === "/api/analyse/reason") return jsonResponse(buildReasonPayload());
      if (url === "/api/organise/execute") return jsonResponse({ executed: [{}, {}] });
      if (url === "/api/chat") {
        return jsonResponse({
          op: { id: "op-1" },
          summary: { actions: 1, groups: { "Semantic groups": 1 }, bytes: 1024 },
          grouped: {
            "Semantic groups": [
              {
                action: "move",
                from: "/tmp/a.txt",
                to: "/tmp/Organised/a.txt",
                confidence: 0.92,
                reason: "Refined plan",
                near_duplicate_signals: ["embedding-similarity"],
              },
            ],
          },
          actions: [
            {
              action: "move",
              from: "/tmp/a.txt",
              to: "/tmp/Organised/a.txt",
              confidence: 0.92,
              reason: "Refined plan",
              near_duplicate_signals: ["embedding-similarity"],
            },
          ],
        });
      }
      if (url === "/api/organise/undo") return jsonResponse({ actions: [], summary: {} });
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

  test("execute payload includes selected action indexes", async () => {
    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    expect(global.EventSource.instances.length).toBeGreaterThan(0);
    global.EventSource.instances[0].emit({ status: "finished", progress: { processed: 2 } });
    await flush();
    await flush();

    const checkboxes = Array.from(
      document.querySelectorAll(".analysis-action input[type='checkbox']")
    );
    expect(checkboxes.length).toBe(2);

    checkboxes[1].checked = false;
    checkboxes[1].dispatchEvent(new Event("change"));

    document.querySelector(".analysis-controls .btn.primary").click();
    await flush();

    const executeCall = fetchMock.mock.calls.find(([url]) => url === "/api/organise/execute");
    expect(executeCall).toBeTruthy();

    const body = JSON.parse(executeCall[1].body);
    expect(body.op_id).toBe("op-1");
    expect(body.selected_actions).toEqual([0]);
  });

  test("execute payload includes create_snapshot when enabled", async () => {
    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    global.EventSource.instances[0].emit({ status: "finished", progress: { processed: 2 } });
    await flush();
    await flush();

    const snapshotToggle = document.getElementById("analysis-create-snapshot");
    snapshotToggle.checked = true;
    snapshotToggle.dispatchEvent(new Event("change"));

    document.querySelector(".analysis-controls .btn.primary").click();
    await flush();

    const executeCall = fetchMock.mock.calls.find(([url]) => url === "/api/organise/execute");
    expect(executeCall).toBeTruthy();
    const body = JSON.parse(executeCall[1].body);
    expect(body.create_snapshot).toBe(true);
  });

  test("chat refine sends message and op id payload", async () => {
    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    global.EventSource.instances[0].emit({ status: "finished", progress: { processed: 2 } });
    await flush();
    await flush();

    const chatInput = document.getElementById("analysis-chat-message");
    chatInput.value = "avoid moving from downloads";
    document.getElementById("analysis-chat-send").click();
    await flush();

    const chatCall = fetchMock.mock.calls.find(([url]) => url === "/api/chat");
    expect(chatCall).toBeTruthy();

    const body = JSON.parse(chatCall[1].body);
    expect(body.op_id).toBe("op-1");
    expect(body.message).toBe("avoid moving from downloads");
  });

  test("shows capability warning banner when optional enhancements are unavailable", async () => {
    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    global.EventSource.instances[0].emit({ status: "finished", progress: { processed: 2 } });
    await flush();
    await flush();

    const banner = document.querySelector(".capability-banner");
    expect(banner).toBeTruthy();
    expect(banner.textContent).toContain("Optional enhancements unavailable");
    expect(banner.textContent).toContain("Disabled:");
  });

  test("preview undo sends dry_run request for current operation", async () => {
    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    global.EventSource.instances[0].emit({ status: "finished", progress: { processed: 2 } });
    await flush();
    await flush();

    const controls = document.querySelectorAll(".analysis-controls .btn");
    expect(controls.length).toBeGreaterThanOrEqual(2);
    controls[1].click();
    await flush();

    const undoCall = fetchMock.mock.calls.find(([url]) => url === "/api/organise/undo");
    expect(undoCall).toBeTruthy();
    const body = JSON.parse(undoCall[1].body);
    expect(body.op_id).toBe("op-1");
    expect(body.dry_run).toBe(true);
  });

  test("shows capability success banner when optional enhancements are available", async () => {
    fetchMock.mockImplementation((url) => {
      if (url === "/api/ops") return jsonResponse({ ops: {} });
      if (url === "/api/analyse/start") return jsonResponse({ job_id: "job-1" });
      if (url === "/api/analyse/reason") {
        return jsonResponse(
          buildReasonPayload({
            analysis_capabilities: {
              ocr: { available: true, image: true, pdf: true, missing: [] },
              embeddings: {
                available: true,
                disabled: false,
                model: "all-MiniLM-L6-v2",
                missing: [],
              },
            },
          })
        );
      }
      if (url === "/api/organise/execute") return jsonResponse({ executed: [{}, {}] });
      if (url === "/api/chat") return jsonResponse(buildReasonPayload());
      if (url === "/api/organise/undo") return jsonResponse({ actions: [], summary: {} });
      return jsonResponse({});
    });

    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    global.EventSource.instances[0].emit({ status: "finished", progress: { processed: 2 } });
    await flush();
    await flush();

    const banner = document.querySelector(".capability-banner");
    expect(banner).toBeTruthy();
    expect(banner.textContent).toContain("All optional analysis enhancements available");
    expect(banner.textContent).toContain("OCR and embedding similarity are available");
  });
});
