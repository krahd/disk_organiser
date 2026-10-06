/* eslint-env browser */
(() => {
  const $ = (id) => document.getElementById(id);
  let token;
  let busy = false;
  let current = null;
  let generation = 0;
  const status = (message) => {
    $("status").textContent = message;
  };
  const node = (tag, text, className) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    return el;
  };
  const bytes = (n) => {
    if (n < 1024) return `${n} B`;
    if (n < 1048576) return `${(n / 1024).toFixed(2)} KiB`;
    return `${(n / 1048576).toFixed(2)} MiB`;
  };
  async function api(path, body) {
    const response = await fetch(
      `/api/guided/${path}`,
      body === undefined
        ? { cache: "no-store" }
        : {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Guided-Token": token },
            body: JSON.stringify(body),
          }
    );
    const data = await response.json();
    if (!response.ok)
      throw new Error(
        data.error || `Request failed (${response.status}). Refresh history before retrying.`
      );
    return data;
  }
  function setBusy(value) {
    busy = value;
    $("scan").disabled = value || !token;
    $("refresh").disabled = value || !token;
    $("root").disabled = value;
    document.querySelectorAll(".operation-button").forEach((button) => {
      button.disabled = value || (button._approval && !button._approval.checked);
    });
  }
  async function run(work) {
    if (busy) return;
    setBusy(true);
    try {
      await work();
    } catch (error) {
      status(
        `${error.message} If the connection was interrupted, refresh history before doing anything else.`
      );
    } finally {
      setBusy(false);
    }
  }
  function table(actions) {
    const wrap = node("div", undefined, "table-wrap");
    const el = node("table");
    const head = node("thead");
    const tr = node("tr");
    ["Original (kept)", "New copy, relative to chosen folder", "Why / size"].forEach((text) =>
      tr.append(node("th", text))
    );
    head.append(tr);
    el.append(head);
    const body = node("tbody");
    actions.forEach((action) => {
      const row = node("tr");
      row.append(
        node("td", action.source),
        node("td", action.destination),
        node("td", `${action.reason}. ${bytes(action.fingerprint.size)}`)
      );
      ["Original (kept)", "New copy, relative to chosen folder", "Why / size"].forEach(
        (label, index) => {
          row.children[index].dataset.label = label;
        }
      );
      body.append(row);
    });
    el.append(body);
    wrap.append(el);
    return wrap;
  }
  function showPlan(plan) {
    current = plan;
    const preview = $("preview");
    preview.replaceChildren();
    preview.hidden = false;
    preview.append(node("h2", "2. Review every copy"));
    preview.firstChild.id = "preview-title";
    preview.append(
      node(
        "p",
        `${plan.actions.length} copies · ${bytes(plan.bytes)} extra data · ${bytes(
          plan.required_bytes
        )} free space required including reserve`
      )
    );
    preview.append(node("p", `Chosen folder: ${plan.root}`));
    preview.append(
      node(
        "p",
        "This preview expires in one hour. All sources are checked again before any copies are created. New and skipped files will stay unchanged.",
        "muted"
      )
    );
    preview.append(table(plan.actions));
    if (plan.skipped.length) {
      const details = node("details");
      details.append(node("summary", `${plan.skipped.length} skipped entries: review reasons`));
      const list = node("ul");
      plan.skipped.forEach((item) => list.append(node("li", `${item.path}: ${item.reason}`)));
      details.append(list);
      preview.append(details);
    }
    if (!plan.actions.length) {
      preview.append(
        node("p", "Nothing supported to copy. Choose a folder with supported top-level files.")
      );
      return;
    }
    const label = node("label", undefined, "check");
    const approval = node("input");
    approval.type = "checkbox";
    approval.id = "approve";
    label.append(
      approval,
      node(
        "span",
        "I reviewed every destination and approve these copies. This is a local, unsynchronised folder, not a network drive. No other app is editing it."
      )
    );
    preview.append(label);
    const apply = node("button", "3. Create the reviewed copies", "operation-button");
    apply._approval = approval;
    apply.id = "apply";
    apply.disabled = true;
    approval.addEventListener("change", () => {
      apply.disabled = !approval.checked || busy;
    });
    apply.addEventListener("click", () => {
      if (!approval.checked || !current) return;
      run(async () => {
        const result = await api(`plans/${plan.id}/apply`, { approved: true, local_only: true });
        current = null;
        preview.hidden = true;
        status(
          result.state === "completed"
            ? `Verified ${result.actions.length} copies. Originals kept. Review the output folder before any next steps.`
            : `Stopped safely with state ${result.state}. ${result.error || "Use recovery below."}`
        );
        await history();
      });
    });
    preview.append(apply);
  }
  async function history() {
    const { plans } = await api("plans");
    const list = $("history");
    list.replaceChildren();
    if (!plans.length) list.append(node("p", "No plans yet. Start with a preview above.", "muted"));
    plans.forEach((plan) => {
      const item = node("div", undefined, "history-item");
      item.append(
        node("h3", `${plan.state.replaceAll("_", " ")} · ${plan.actions.length} copies`),
        node("p", `${plan.root}/${plan.output}`)
      );
      if (plan.error) item.append(node("p", plan.error, "notice"));
      if (plan.conflicts?.length) {
        const details = node("details");
        details.open = true;
        details.append(node("summary", "Retained for manual inspection"));
        plan.conflicts.forEach((conflict) =>
          details.append(node("p", `${conflict.path}: ${conflict.reason}`))
        );
        item.append(details);
      }
      if (plan.state === "preview") {
        const button = node("button", "Review saved preview", "secondary operation-button");
        button.onclick = () => {
          if (!busy) showPlan(plan);
        };
        item.append(button);
      }
      if (
        ["completed", "applying", "interrupted", "recovering", "recovery_blocked"].includes(
          plan.state
        )
      ) {
        const paths = node("details");
        paths.append(
          node("summary", "Review this plan’s copy paths before recovery"),
          table(plan.actions)
        );
        item.append(paths);
        const label = node("label", undefined, "check");
        const checkbox = node("input");
        checkbox.type = "checkbox";
        label.append(
          checkbox,
          node(
            "span",
            "Remove only this plan’s unchanged verified copies. Keep all originals and any files that cannot be verified."
          )
        );
        const button = node(
          "button",
          "Undo / recover generated copies",
          "secondary operation-button"
        );
        button._approval = checkbox;
        button.disabled = true;
        checkbox.onchange = () => {
          button.disabled = !checkbox.checked || busy;
        };
        button.onclick = () => {
          if (!checkbox.checked) return;
          run(async () => {
            const result = await api(`plans/${plan.id}/recover`, { approved: true });
            current = null;
            $("preview").hidden = true;
            status(
              result.state === "undone"
                ? "Verified generated copies removed. Originals kept."
                : "Recovery stopped at conflicts. Uncertain files were retained; inspect the paths below."
            );
            await history();
          });
        };
        item.append(label, button);
      }
      list.append(item);
    });
  }
  $("root").addEventListener("input", () => {
    generation++;
    current = null;
    $("preview").hidden = true;
  });
  $("scan-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const version = ++generation;
    current = null;
    $("preview").hidden = true;
    run(async () => {
      status("Reading metadata and verifying local file hashes. No source files are changed.");
      const plan = await api("plans", { root: $("root").value.trim() });
      if (version !== generation) return;
      showPlan(plan);
      status("Preview saved. No copies have been made.");
      await history();
    });
  });
  $("refresh").onclick = () =>
    run(async () => {
      await history();
      status("History refreshed. Check interrupted operations before making another plan.");
    });
  setBusy(true);
  api("session")
    .then(async (data) => {
      token = data.token;
      await history();
    })
    .catch((error) =>
      status(
        `Could not reach the local backend: ${error.message}. Open this page from the application’s localhost /ui/ address.`
      )
    )
    .finally(() => setBusy(false));
})();
