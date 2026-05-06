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
      if (url === "/api/analyse/reason") {
        return jsonResponse({
          op: { id: "op-1" },
          summary: { actions: 2, groups: { "Semantic groups": 2 }, bytes: 2048 },
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
        });
      }
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
});
