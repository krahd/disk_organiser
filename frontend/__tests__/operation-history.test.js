/**
 * @jest-environment jsdom
 */

const fs = require("fs");
const path = require("path");

// Inert strings only: no scripts, events, resource URLs or real stored data.
const textCases = [
  ["plain", "op-1", "complete"],
  ["markup", '<span data-fixture="id">ID</span>', '<b data-fixture="status">Status</b>'],
  ["closing tags", '</em><span data-fixture="id">ID</span>', "</div><i>Status</i>"],
  ["quotes and entities", '" \' data-fixture="id" &amp; < >', "\" ' &lt; &gt; &"],
  ["Unicode and newlines", "op-é雪\nsecond line", "ready\t雪"],
];

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("Operation and recycle history rendering", () => {
  let rows;
  let details;
  let fetchMock;

  beforeAll(() => {
    document.documentElement.innerHTML = fs.readFileSync(
      path.resolve(__dirname, "..", "index.html"),
      "utf8"
    );
    fetchMock = jest.fn((url, options) => {
      let payload;
      if (url === "/api/ops") payload = { ops: rows };
      else if (url === "/api/recycle/list") payload = { recycle: rows };
      else if (url.startsWith("/api/ops/") && url.endsWith("/preview")) payload = details;
      else if (["/api/organise/undo", "/api/recycle/delete_op"].includes(url)) {
        if (!options || options.method !== "POST") throw new Error("Expected a mocked POST");
        payload = details;
      } else throw new Error(`Unexpected request: ${url}`);
      return Promise.resolve({ ok: true, status: 200, json: async () => payload });
    });
    global.fetch = fetchMock;
    const script = document.createElement("script");
    script.textContent = fs.readFileSync(path.resolve(__dirname, "..", "main.js"), "utf8");
    document.head.appendChild(script);
    document.dispatchEvent(new Event("DOMContentLoaded"));
  });

  beforeEach(() => {
    rows = {};
    details = { actions: [], summary: {} };
    fetchMock.mockClear();
  });

  afterAll(() => {
    clearTimeout(document.getElementById("app-alert")?._timeout);
  });

  async function open(section) {
    document.getElementById(`nav-${section}`).click();
    await flush();
    return document.getElementById(section === "organise" ? "ops-list" : "recycle-list");
  }

  function button(card, label) {
    return Array.from(card.querySelectorAll("button")).find((el) => el.textContent === label);
  }

  describe.each(["organise", "recycle"])("%s listing", (section) => {
    test.each(textCases)(
      "keeps %s fields literal inside the original structure",
      async (_, id, status) => {
        const metadata = { note: '<span data-fixture="metadata">note</span> &amp;' };
        const file = { path: '<i data-fixture="path">file</i>', size: "<b>12</b>" };
        rows = { [id]: { status, metadata, files: [file] } };
        const list = await open(section);
        const card = list.firstElementChild;
        const title = card.firstElementChild;
        expect(list.children).toHaveLength(1);
        expect(card.className).toBe("card");
        expect(title.textContent).toBe(`Op: ${id} — ${status}`);
        expect(title.children).toHaveLength(2);
        expect(Array.from(title.children, (el) => el.tagName)).toEqual(["STRONG", "EM"]);
        expect(title.firstElementChild.textContent).toBe("Op:");
        expect(title.lastElementChild.textContent).toBe(String(status));
        expect(title.firstElementChild.children).toHaveLength(0);
        expect(title.lastElementChild.children).toHaveLength(0);
        for (const el of [title, ...title.children]) expect(el.attributes).toHaveLength(0);
        expect(card.children[1].textContent).toBe(JSON.stringify(metadata));
        expect(card.children[1].children).toHaveLength(0);
        expect(list.querySelector("[data-fixture]")).toBeNull();
        if (section === "recycle") {
          expect(card.children[2].tagName).toBe("UL");
          expect(card.querySelector("li").textContent).toBe(`${file.path} — ${file.size} bytes`);
          expect(card.querySelector("li").children).toHaveLength(0);
        }
        expect(document.getElementById(`nav-${section}`).getAttribute("aria-pressed")).toBe("true");
        expect(document.getElementById(`nav-${section}`).getAttribute("aria-current")).toBe("page");
        expect(fetchMock.mock.calls).toEqual([
          [section === "organise" ? "/api/ops" : "/api/recycle/list"],
        ]);
      }
    );

    test.each([null, undefined, false, 0])(
      "preserves display coercion for status %s",
      async (status) => {
        rows = { "op-1": { status } };
        const list = await open(section);
        expect(list.querySelector("em").textContent).toBe(String(status));
      }
    );

    test("preserves ordinary title markup, button order and classes across repeated navigation", async () => {
      rows = { "op-1": { status: "complete" } };
      const labels =
        section === "organise"
          ? ["View Details", "Undo", "Preview Undo", "Preview Delete", "Delete Backup"]
          : ["Undo (restore)", "Preview Undo", "Preview Delete", "Delete Backup (permanent)"];
      for (let visit = 0; visit < 2; visit += 1) {
        const list = await open(section);
        expect(list.children).toHaveLength(1);
        expect(list.firstElementChild.firstElementChild.innerHTML).toBe(
          "<strong>Op:</strong> op-1 — <em>complete</em>"
        );
        expect(Array.from(list.querySelectorAll("button"), (el) => el.textContent)).toEqual(labels);
        expect(Array.from(list.querySelectorAll("button"), (el) => el.className)).toEqual(
          labels.map((label) => (label.startsWith("Delete Backup") ? "btn secondary" : "btn"))
        );
        document.getElementById("nav-visualisation").click();
      }
    });

    test("keeps an empty response empty", async () => {
      expect((await open(section)).children).toHaveLength(0);
    });
  });

  test.each(["View Details", "Preview Undo", "Preview Delete"])(
    "%s displays JSON as one literal pre and replaces stale detail",
    async (label) => {
      const id = "synthetic-op";
      rows = { [id]: { status: "preview" } };
      const card = (await open("organise")).firstElementChild;
      details = {
        id: '<span data-fixture="detail">literal</span>',
        status: '</pre><b data-fixture="outside">text</b><pre>',
        note: "\" ' &amp; < > 雪\nnext",
      };
      await button(card, label).onclick();
      const container = document.getElementById("ops-detail");
      expect(container.children).toHaveLength(1);
      const pre = container.firstElementChild;
      expect(pre.tagName).toBe("PRE");
      expect(pre.attributes).toHaveLength(0);
      expect(pre.children).toHaveLength(0);
      expect(pre.textContent).toBe(JSON.stringify(details, null, 2));
      expect(document.querySelector("[data-fixture]")).toBeNull();
      details = { status: "second response" };
      await button(card, label).onclick();
      expect(container.children).toHaveLength(1);
      expect(container.firstElementChild.textContent).toBe(JSON.stringify(details, null, 2));
      expect(container.contains(pre)).toBe(false);
    }
  );

  test.each([
    ["organise", "View Details", null, null],
    ["organise", "Undo", "/api/organise/undo", false],
    ["organise", "Preview Undo", "/api/organise/undo", true],
    ["organise", "Preview Delete", "/api/recycle/delete_op", true],
    ["organise", "Delete Backup", "/api/recycle/delete_op", false],
    ["recycle", "Undo (restore)", "/api/organise/undo", false],
    ["recycle", "Preview Undo", "/api/organise/undo", true],
    ["recycle", "Preview Delete", "/api/recycle/delete_op", true],
    ["recycle", "Delete Backup (permanent)", "/api/recycle/delete_op", false],
  ])("%s %s retains the exact request contract", async (section, label, endpoint, dryRun) => {
    const id = 'op-"<&amp;雪';
    rows = { [id]: { status: "preview" } };
    const card = (await open(section)).firstElementChild;
    fetchMock.mockClear();
    await button(card, label).onclick();
    await flush();
    if (endpoint === null) {
      expect(fetchMock.mock.calls).toEqual([[`/api/ops/${id}/preview`]]);
    } else {
      expect(fetchMock.mock.calls[0]).toEqual([
        endpoint,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(dryRun ? { op_id: id, dry_run: true } : { op_id: id }),
        },
      ]);
      const reloads = section === "recycle" || !dryRun;
      expect(fetchMock.mock.calls.slice(1)).toEqual(
        reloads ? [[section === "organise" ? "/api/ops" : "/api/recycle/list"]] : []
      );
    }
  });
});
