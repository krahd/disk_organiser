/**
 * @jest-environment jsdom
 */

const fs = require("fs");
const path = require("path");

describe("Preview modal UI", () => {
  beforeAll(() => {
    const html = fs.readFileSync(path.resolve(__dirname, "..", "index.html"), "utf8");
    document.documentElement.innerHTML = html;
    // load main.js into the DOM by creating a script element
    const scriptContent = fs.readFileSync(path.resolve(__dirname, "..", "main.js"), "utf8");
    const scriptEl = document.createElement("script");
    scriptEl.textContent = scriptContent;
    document.head.appendChild(scriptEl);
    // dispatch DOMContentLoaded so the app initializes
    document.dispatchEvent(new Event("DOMContentLoaded"));
    global.openPreviewModal = window.openPreviewModal;
    global.closePreviewModal = window.closePreviewModal;
    global.formatBytes = window.formatBytes;
  });

  test("formatBytes produces human readable strings", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(1024)).toBe("1.00 KB");
    expect(formatBytes(1024 * 1024)).toBe("1.00 MB");
  });

  test("opening modal inserts title and actions", () => {
    const preview = {
      op: { id: "op-123" },
      summary: { actions: 2, files: 2, bytes: 2048 },
      actions: [
        { action: "move", src: "/tmp/a", dst: "/recycle/a", size: 1024 },
        { action: "delete", src: "/tmp/b", dst: "", size: 1024 },
      ],
    };

    openPreviewModal(preview);
    const modal = document.getElementById("preview-modal");
    expect(modal.classList.contains("hidden")).toBe(false);
    const title = document.getElementById("preview-modal-title");
    expect(title.textContent).toContain("op-123");
    const body = document.getElementById("preview-modal-body");
    expect(body.textContent).toContain("/tmp/a");
    expect(body.textContent).toContain("/tmp/b");
    // close
    closePreviewModal();
    expect(modal.classList.contains("hidden")).toBe(true);
  });
});
