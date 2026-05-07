/**
 * @jest-environment jsdom
 */

const fs = require("fs");
const path = require("path");

function jsonResponse(payload) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => payload,
  });
}

function errorResponse(payload, status = 500) {
  return Promise.resolve({
    ok: false,
    status,
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

function buildLargeReasonPayload(actionCount = 120) {
  const actions = Array.from({ length: actionCount }, (_, index) => ({
    action: "move",
    from: `/tmp/in-${index}.txt`,
    to: `/tmp/Organised/in-${index}.txt`,
    confidence: 0.8,
    reason: "Large payload semantic grouping",
    near_duplicate_signals: ["content-overlap"],
  }));

  return buildReasonPayload({
    summary: {
      actions: actionCount,
      groups: { "Semantic groups": actionCount },
      bytes: 1024 * actionCount,
    },
    grouped: {
      "Semantic groups": actions,
    },
    actions,
  });
}

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

function lastEventSource() {
  return global.EventSource.instances[global.EventSource.instances.length - 1];
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
      if (url === "/api/scan/cancel") return jsonResponse({ cancelled: "job-1" });
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
    lastEventSource().emit({ status: "finished", progress: { processed: 2 } });
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

  test("execute payload supports empty selected_actions", async () => {
    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    lastEventSource().emit({ status: "finished", progress: { processed: 2 } });
    await flush();
    await flush();

    const checkboxes = Array.from(
      document.querySelectorAll(".analysis-action input[type='checkbox']")
    );
    checkboxes.forEach((checkbox) => {
      checkbox.checked = false;
      checkbox.dispatchEvent(new Event("change"));
    });

    document.querySelector(".analysis-controls .btn.primary").click();
    await flush();

    const executeCall = fetchMock.mock.calls
      .filter(([url]) => url === "/api/organise/execute")
      .pop();
    expect(executeCall).toBeTruthy();
    const body = JSON.parse(executeCall[1].body);
    expect(body.selected_actions).toEqual([]);
  });

  test("execute payload includes create_snapshot when enabled", async () => {
    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    lastEventSource().emit({ status: "finished", progress: { processed: 2 } });
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

    lastEventSource().emit({ status: "finished", progress: { processed: 2 } });
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

    const checkboxes = Array.from(
      document.querySelectorAll(".analysis-action input[type='checkbox']")
    );
    expect(checkboxes.length).toBe(1);
  });

  test("shows capability warning banner when optional enhancements are unavailable", async () => {
    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    lastEventSource().emit({ status: "finished", progress: { processed: 2 } });
    await flush();
    await flush();

    const banner = document.querySelector(".capability-banner");
    expect(banner).toBeTruthy();
    expect(banner.textContent).toContain("Optional enhancements unavailable");
    expect(banner.textContent).toContain("Disabled:");
    expect(banner.textContent).toContain("OCR:");
    expect(banner.textContent).toContain("unavailable");
    expect(banner.textContent).toContain("Missing: pytesseract");
    expect(banner.textContent).toContain("Embedding:");
    expect(banner.textContent).toContain("Missing: sentence-transformers");
  });

  test("preview undo sends dry_run request for current operation", async () => {
    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    lastEventSource().emit({ status: "finished", progress: { processed: 2 } });
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

    lastEventSource().emit({ status: "finished", progress: { processed: 2 } });
    await flush();
    await flush();

    const banner = document.querySelector(".capability-banner");
    expect(banner).toBeTruthy();
    expect(banner.textContent).toContain("All optional analysis enhancements available");
    expect(banner.textContent).toContain("OCR and embedding similarity are available");
    expect(banner.textContent).toContain("OCR: available");
    expect(banner.textContent).toContain("Embedding: available");
    expect(banner.textContent).toContain("Dependencies installed");
  });

  test("renders capability banner and actions for large analysis payload", async () => {
    fetchMock.mockImplementation((url) => {
      if (url === "/api/ops") return jsonResponse({ ops: {} });
      if (url === "/api/analyse/start") return jsonResponse({ job_id: "job-1" });
      if (url === "/api/analyse/reason") return jsonResponse(buildLargeReasonPayload(120));
      if (url === "/api/organise/execute") return jsonResponse({ executed: [] });
      if (url === "/api/chat") return jsonResponse(buildReasonPayload());
      if (url === "/api/organise/undo") return jsonResponse({ actions: [], summary: {} });
      return jsonResponse({});
    });

    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    lastEventSource().emit({ status: "finished", progress: { processed: 120 } });
    await flush();
    await flush();

    const banner = document.querySelector(".capability-banner");
    expect(banner).toBeTruthy();
    expect(banner.textContent).toContain("Optional enhancements unavailable");

    const cards = document.querySelectorAll(".analysis-action");
    expect(cards.length).toBe(120);
  });

  test("cancel analysis posts cancellation request and shows cancelled state", async () => {
    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    const cancelButton = document.getElementById("analysis-cancel");
    expect(cancelButton).toBeTruthy();
    cancelButton.click();
    await flush();

    const cancelCall = fetchMock.mock.calls.find(([url]) => url === "/api/scan/cancel");
    expect(cancelCall).toBeTruthy();
    expect(JSON.parse(cancelCall[1].body)).toEqual({ job_id: "job-1" });

    lastEventSource().emit({ status: "cancelled", error: "cancelled" });
    await flush();

    const progressText = document.getElementById("analysis-progress-text");
    expect(progressText.textContent).toContain("Analysis cancelled");
  });

  test("cancel analysis surfaces API error", async () => {
    fetchMock.mockImplementation((url) => {
      if (url === "/api/ops") return jsonResponse({ ops: {} });
      if (url === "/api/analyse/start") return jsonResponse({ job_id: "job-1" });
      if (url === "/api/scan/cancel") {
        return errorResponse(
          { error: { code: "cancel_failed", message: "failed to cancel" } },
          500
        );
      }
      return jsonResponse({});
    });

    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    const cancelButton = document.getElementById("analysis-cancel");
    cancelButton.click();
    await flush();

    const alert = document.getElementById("app-alert");
    expect(alert).toBeTruthy();
    expect(alert.textContent).toContain("Cancel request failed: failed to cancel");
    expect(cancelButton.disabled).toBe(false);
  });

  test("analysis start failure surfaces API error", async () => {
    fetchMock.mockImplementation((url) => {
      if (url === "/api/ops") return jsonResponse({ ops: {} });
      if (url === "/api/analyse/start") {
        return errorResponse(
          { error: { code: "validation_error", message: "paths must be non-empty strings" } },
          400
        );
      }
      return jsonResponse({});
    });

    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    const alert = document.getElementById("app-alert");
    expect(alert).toBeTruthy();
    expect(alert.textContent).toContain("Analysis start failed: paths must be non-empty strings");
  });

  test("reasoning failure surfaces API error after finished job", async () => {
    fetchMock.mockImplementation((url) => {
      if (url === "/api/ops") return jsonResponse({ ops: {} });
      if (url === "/api/analyse/start") return jsonResponse({ job_id: "job-1" });
      if (url === "/api/scan/cancel") return jsonResponse({ cancelled: "job-1" });
      if (url === "/api/analyse/reason") {
        return errorResponse(
          { error: { code: "analysis_failed", message: "analysis failed" } },
          500
        );
      }
      return jsonResponse({});
    });

    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    lastEventSource().emit({ status: "finished", progress: { processed: 2 } });
    await flush();
    await flush();

    const alert = document.getElementById("app-alert");
    expect(alert).toBeTruthy();
    expect(alert.textContent).toContain("Reasoning failed: analysis failed");
  });

  test("reasoning cancelled response shows actionable message", async () => {
    fetchMock.mockImplementation((url) => {
      if (url === "/api/ops") return jsonResponse({ ops: {} });
      if (url === "/api/analyse/start") return jsonResponse({ job_id: "job-1" });
      if (url === "/api/scan/cancel") return jsonResponse({ cancelled: "job-1" });
      if (url === "/api/analyse/reason") {
        return errorResponse(
          { error: { code: "job_cancelled", message: "analysis job was cancelled" } },
          409
        );
      }
      return jsonResponse({});
    });

    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    lastEventSource().emit({ status: "finished", progress: { processed: 2 } });
    await flush();
    await flush();

    const alert = document.getElementById("app-alert");
    expect(alert).toBeTruthy();
    expect(alert.textContent).toContain(
      "Reasoning skipped: analysis was cancelled. Run analysis again."
    );
  });

  test("reasoning not-ready response shows wait message", async () => {
    fetchMock.mockImplementation((url) => {
      if (url === "/api/ops") return jsonResponse({ ops: {} });
      if (url === "/api/analyse/start") return jsonResponse({ job_id: "job-1" });
      if (url === "/api/scan/cancel") return jsonResponse({ cancelled: "job-1" });
      if (url === "/api/analyse/reason") {
        return errorResponse(
          { error: { code: "job_not_ready", message: "analysis job is not finished" } },
          409
        );
      }
      return jsonResponse({});
    });

    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    lastEventSource().emit({ status: "finished", progress: { processed: 2 } });
    await flush();
    await flush();

    const alert = document.getElementById("app-alert");
    expect(alert).toBeTruthy();
    expect(alert.textContent).toContain(
      "Reasoning deferred: analysis is still running. Please wait."
    );
  });

  test("analysis failed status from SSE shows failure without reasoning call", async () => {
    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    lastEventSource().emit({ status: "failed", error: "index read failed" });
    await flush();

    const alert = document.getElementById("app-alert");
    expect(alert).toBeTruthy();
    expect(alert.textContent).toContain("Analysis failed: index read failed");

    const reasonCall = fetchMock.mock.calls.find(([url]) => url === "/api/analyse/reason");
    expect(reasonCall).toBeUndefined();

    const progressText = document.getElementById("analysis-progress-text");
    expect(progressText.textContent).toContain("Analysis failed");
  });

  test("chat refine failure surfaces API error and reenables button", async () => {
    fetchMock.mockImplementation((url) => {
      if (url === "/api/ops") return jsonResponse({ ops: {} });
      if (url === "/api/analyse/start") return jsonResponse({ job_id: "job-1" });
      if (url === "/api/scan/cancel") return jsonResponse({ cancelled: "job-1" });
      if (url === "/api/analyse/reason") return jsonResponse(buildReasonPayload());
      if (url === "/api/chat") {
        return errorResponse(
          { error: { code: "chat_failed", message: "chat refinement failed" } },
          500
        );
      }
      if (url === "/api/organise/undo") return jsonResponse({ actions: [], summary: {} });
      return jsonResponse({});
    });

    document.getElementById("nav-organise").click();
    await flush();

    document.getElementById("analysis-run").click();
    await flush();

    lastEventSource().emit({ status: "finished", progress: { processed: 2 } });
    await flush();
    await flush();

    const chatInput = document.getElementById("analysis-chat-message");
    chatInput.value = "avoid downloads";
    const chatButton = document.getElementById("analysis-chat-send");
    chatButton.click();
    await flush();

    const alert = document.getElementById("app-alert");
    expect(alert).toBeTruthy();
    expect(alert.textContent).toContain("Chat refinement failed: chat refinement failed");
    expect(chatButton.disabled).toBe(false);
  });
});
