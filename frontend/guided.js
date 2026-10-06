/* eslint-env browser */
(() => {
  const $ = (id) => document.getElementById(id);
  let token;
  let copyEnabled = false;
  let scanEnabled = false;
  let busy = false;
  let current = null;
  let generation = 0;
  let mustRefresh = true;
  let detailCounter = 0;
  const status = (message, kind = "info") => {
    $("status").textContent = message;
    $("status").dataset.kind = kind;
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
  const amount = (count, word) => `${count} ${word}${count === 1 ? "" : "s"}`;
  const focus = (element) => element.focus({ preventScroll: false });
  const goal = () => document.querySelector('input[name="goal"]:checked').value;
  const category = (action) => action.destination.split("/")[1] || "Other";
  const stateName = (plan) =>
    ({
      preview: !copyEnabled
        ? "Read-only layout preview"
        : plan.can_apply === true
        ? "Preview only"
        : "Preview needs a new scan",
      completed: "Copies verified",
      applying: "Copy result needs checking",
      interrupted: "Copying interrupted",
    }[plan.state] || "Saved record needs checking");
  function capabilities(value) {
    copyEnabled = value?.copy_apply?.enabled === true;
    scanEnabled = value?.scan?.enabled === true;
    $("scan-availability").hidden = scanEnabled;
    $("scan-availability").textContent =
      value?.scan?.enabled === false
        ? "Scanning is unavailable on this platform. This bounded preview requires supported macOS/Linux file APIs. Saved history is still available."
        : "Scanning support has not been confirmed. Refresh session and history to reconnect. Saved history remains available when the local app can be reached.";
    $("safety-title").textContent = copyEnabled
      ? "Synthetic development mode: copying enabled, removal unavailable."
      : "Read-only preview. Copying is not enabled.";
    $("mode-description").textContent = copyEnabled
      ? "This restricted development mode keeps originals and uses extra space. Automatic copy removal is unavailable because saved history cannot prove ownership. Use only disposable synthetic fixtures; never erase source media based on a report."
      : "You can inspect a local file-type overview and compare a proposed copy layout. This workflow will not apply that layout. The wider Disk Map, project relationships and reviewed transaction/recovery layer are still being developed.";
  }
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
    if (!response.ok) {
      const error = new Error(data.error || `Request failed (${response.status}).`);
      error.status = response.status;
      throw error;
    }
    return data;
  }
  async function loadSession() {
    const data = await api("session");
    if (typeof data.token !== "string" || !data.token)
      throw new Error("The local app did not provide a valid session.");
    token = data.token;
    capabilities(data.capabilities);
  }
  function setBusy(value) {
    busy = value;
    $("scan").disabled = value || !token || !scanEnabled || mustRefresh;
    $("refresh").disabled = value;
    $("root").disabled = value;
    $("goals").disabled = value;
    $("preview").setAttribute("aria-busy", String(value));
    document.querySelectorAll(".operation-button").forEach((button) => {
      button.disabled =
        value ||
        mustRefresh ||
        (button._needsScan && !scanEnabled) ||
        (button._approval && (!button._approval.checked || !copyEnabled));
    });
  }
  async function run(work) {
    if (busy) return;
    setBusy(true);
    try {
      await work();
    } catch (error) {
      if (error.status === 403) {
        token = null;
        mustRefresh = true;
        closePreview();
      }
      status(
        `${error.message} Refresh session and history before trying again. No request is retried automatically.`,
        "error"
      );
    } finally {
      setBusy(false);
    }
  }
  function closePreview(message) {
    generation++;
    current = null;
    $("preview").replaceChildren();
    $("preview").hidden = true;
    if (message) status(message);
  }
  // Filtering and paging are display-only. Approval always covers the complete plan.
  function exactPaths(actions, onBrowse = () => {}) {
    const wrap = node("div", undefined, "exact-paths");
    const id = `path-filter-${++detailCounter}`;
    const label = node("label", "Find a file or destination");
    label.htmlFor = id;
    const search = node("input");
    search.type = "search";
    search.id = id;
    search.placeholder = "Filter this list";
    const count = node("p", undefined, "muted");
    count.setAttribute("role", "status");
    const tableWrap = node("div", undefined, "table-wrap");
    const navigation = node("div", undefined, "list-navigation");
    const previous = node("button", "Previous 25", "secondary");
    previous.type = "button";
    const next = node("button", "Next 25", "secondary");
    next.type = "button";
    let page = 0;
    function render() {
      const query = search.value.trim().toLocaleLowerCase();
      const matches = actions.filter((a) =>
        `${a.source} ${a.destination} ${a.reason}`.toLocaleLowerCase().includes(query)
      );
      page = Math.min(page, Math.max(0, Math.ceil(matches.length / 25) - 1));
      const start = page * 25;
      count.textContent = matches.length
        ? `Showing ${start + 1}–${Math.min(start + 25, matches.length)} of ${
            matches.length
          } matching files. Full plan: ${actions.length} copies.`
        : `No matching files. Full plan: ${actions.length} copies.`;
      const table = node("table");
      const caption = node(
        "caption",
        "Exact paths, relative to the chosen folder. Originals stay in place."
      );
      const head = node("thead");
      const row = node("tr");
      const labels = ["Original (kept)", "New copy", "Why / size"];
      labels.forEach((text) => {
        const th = node("th", text);
        th.scope = "col";
        row.append(th);
      });
      head.append(row);
      table.append(caption, head);
      const body = node("tbody");
      matches.slice(start, start + 25).forEach((action) => {
        const tr = node("tr");
        [
          action.source,
          action.destination,
          `${action.reason}. ${bytes(action.fingerprint.size)}`,
        ].forEach((text, i) => {
          const td = node("td", text);
          td.dataset.label = labels[i];
          tr.append(td);
        });
        body.append(tr);
      });
      table.append(body);
      tableWrap.replaceChildren(table);
      previous.disabled = page === 0;
      next.disabled = start + 25 >= matches.length;
      navigation.hidden = matches.length <= 25;
    }
    search.oninput = () => {
      page = 0;
      onBrowse();
      render();
    };
    previous.onclick = () => {
      page--;
      onBrowse();
      render();
    };
    next.onclick = () => {
      page++;
      onBrowse();
      render();
    };
    navigation.append(previous, next);
    wrap.append(label, search, count, tableWrap, navigation);
    render();
    return wrap;
  }
  function rescanButton(plan) {
    const button = node(
      "button",
      "Choose this folder for a new scan",
      "secondary operation-button"
    );
    button.type = "button";
    button._needsScan = true;
    button.disabled = !scanEnabled;
    button.onclick = () => {
      if (busy || mustRefresh || !scanEnabled) return;
      closePreview(
        copyEnabled
          ? "Folder selected. Scan again to check its current files before reviewing a new copy request."
          : "Folder selected. Scan again for a current read-only overview. Copying remains disabled."
      );
      $("root").value = plan.root;
      focus($("root"));
    };
    return button;
  }
  function showPlan(plan, fromHistory = false) {
    current = plan;
    const preview = $("preview");
    preview.replaceChildren();
    preview.hidden = false;
    const heading = node("h2", "2. Understand this folder");
    heading.id = "preview-title";
    heading.tabIndex = -1;
    const top = node("div", undefined, "section-heading");
    const close = node("button", "Close preview", "secondary operation-button");
    close.onclick = () => {
      if (!busy) {
        closePreview("Preview closed. No new copies were requested. The record stays in history.");
        focus($("root"));
      }
    };
    top.append(heading, close);
    preview.append(top, node("p", plan.root, "folder-path"));
    if (fromHistory)
      preview.append(
        node(
          "p",
          "Saved snapshot: these counts describe the scan, not a live view of this folder.",
          "notice"
        )
      );
    const groups = new Map();
    plan.actions.forEach((a) => {
      const key = category(a);
      const group = groups.get(key) || { count: 0, bytes: 0 };
      group.count++;
      group.bytes += a.fingerprint.size;
      groups.set(key, group);
    });
    const summary = node(
      "p",
      `${amount(plan.actions.length, "supported file")} · ${bytes(plan.bytes)} of copyable data · ${
        plan.skipped.length
      } ${plan.skipped.length === 1 ? "entry" : "entries"} left out`
    );
    preview.append(summary);
    const overview = node("ul", undefined, "category-grid");
    [...groups]
      .sort((a, b) => b[1].bytes - a[1].bytes)
      .forEach(([name, group]) => {
        const item = node("li");
        item.append(
          node("strong", name),
          node("span", `${amount(group.count, "file")} · ${bytes(group.bytes)}`)
        );
        overview.append(item);
      });
    preview.append(
      overview,
      node(
        "p",
        "This overview uses filename extensions only. It does not identify projects, duplicates or file contents. Files inside nested folders are not counted.",
        "muted"
      )
    );
    if (plan.skipped.length) {
      const details = node("details");
      details.append(
        node(
          "summary",
          `${plan.skipped.length} ${
            plan.skipped.length === 1 ? "entry" : "entries"
          } left out: see why`
        )
      );
      const list = node("ul", undefined, "skipped-list");
      plan.skipped.forEach((item) => list.append(node("li", `${item.path}: ${item.reason}`)));
      details.append(list);
      preview.append(details);
    }
    if (!plan.actions.length) {
      preview.append(
        node(
          "p",
          "There are no supported top-level files to copy. This does not mean the folder is empty. Check the entries left out, or choose another fully local folder.",
          "notice"
        )
      );
      preview.append(rescanButton(plan));
      focus(heading);
      return;
    }
    const compare = node("div", undefined, "comparison");
    compare.append(node("h3", "What would help next?"));
    const cards = node("div", undefined, "choices");
    const keep = node("div", undefined, "choice");
    const keepText = node("div");
    keepText.append(
      node("h4", "Leave the folder as it is"),
      node("p", "Keep this overview and your existing layout. No extra file space used.")
    );
    const leave = node("button", "Keep the current layout", "secondary operation-button");
    leave.onclick = () => {
      if (!busy) {
        closePreview(
          "Current layout kept. No copies requested. You can revisit the saved overview later."
        );
        focus($("root"));
      }
    };
    keepText.append(leave);
    keep.append(keepText);
    const copy = node("div", undefined, "choice");
    const copyText = node("div");
    copyText.append(
      node("h4", "Try a separate file-type layout"),
      node(
        "p",
        `${plan.actions.length} copies grouped into ${groups.size} folders. Uses ${bytes(
          plan.bytes
        )} extra data; requires ${bytes(
          plan.required_bytes
        )} free including reserve. Originals stay where they are.`
      )
    );
    const explore = node("button", "Review the copy layout", "secondary operation-button");
    copyText.append(explore);
    copy.append(copyText);
    cards.append(keep, copy);
    compare.append(cards);
    preview.append(compare);
    const effects = node("div", undefined, "effects");
    effects.id = "copy-effects";
    effects.hidden = goal() === "understand";
    const effectsTitle = node("h3", "3. Review the exact effects");
    effectsTitle.tabIndex = -1;
    effects.append(
      effectsTitle,
      node("p", `New folder: ${plan.root}/${plan.output}`, "folder-path")
    );
    effects.append(
      node(
        "p",
        `This proposed layout would copy all ${plan.actions.length} listed files. Filtering the list does not select a subset. No original will be moved, renamed or removed.`,
        "scope-note"
      )
    );
    const approval = node("input");
    approval.type = "checkbox";
    approval.id = "approve";
    const revoke = () => {
      approval.checked = false;
      const apply = $("apply");
      if (apply) apply.disabled = true;
    };
    effects.append(exactPaths(plan.actions, revoke));
    effects.append(
      node(
        "p",
        "Copies use private permissions and do not preserve original metadata, including Finder tags, timestamps and access rules. Automatic copy removal is unavailable. A separate backup is still needed.",
        "notice"
      )
    );
    if (!copyEnabled) {
      effects.append(
        node(
          "p",
          "This is a read-only layout preview. Creating copies is disabled in this workflow; scanning again will not enable it. The transaction and recovery layer needs further independent review.",
          "notice"
        )
      );
    } else if (plan.can_apply !== true || plan.state !== "preview") {
      effects.append(
        node(
          "p",
          "This saved plan cannot authorise copying. Scan the folder again to check its current files and create a fresh plan.",
          "notice"
        ),
        rescanButton(plan)
      );
    } else {
      effects.append(
        node(
          "p",
          "The preview expires one hour after scanning and becomes unusable after the app restarts. Sources are checked again before copying.",
          "muted"
        )
      );
      const label = node("label", undefined, "check");
      label.append(
        approval,
        node(
          "span",
          `I reviewed the complete plan of ${plan.actions.length} copies, including files hidden by filters or other pages. This folder is local and unsynchronised, not a network drive. No other app is editing it. I understand automatic removal is unavailable.`
        )
      );
      const apply = node(
        "button",
        `Create ${plan.actions.length} reviewed copies`,
        "operation-button"
      );
      apply.id = "apply";
      apply._approval = approval;
      apply.disabled = true;
      approval.onchange = () => {
        apply.disabled = !approval.checked || busy || mustRefresh || !copyEnabled;
      };
      apply.onclick = () => {
        if (
          !approval.checked ||
          busy ||
          mustRefresh ||
          current !== plan ||
          !copyEnabled ||
          plan.can_apply !== true
        )
          return;
        run(async () => {
          revoke();
          status(
            "Creating and verifying the reviewed copies. Keep the app open. There is no safe cancellation during this operation; a lost connection does not mean it stopped."
          );
          let result;
          try {
            result = await api(`plans/${plan.id}/apply`, { approved: true, local_only: true });
          } catch (error) {
            mustRefresh = true;
            closePreview();
            throw new Error(
              `The copy result is not confirmed. ${error.message} Do not submit another copy request until you refresh history.`
            );
          }
          closePreview();
          status(
            result.state === "completed"
              ? `Verified ${result.actions.length} copies. Originals kept. Inspect the output in saved results. Automatic copy removal is unavailable.`
              : `Copying did not complete. Originals and any generated copies are retained. ${
                  result.error || "Check the saved result before continuing."
                }`,
            result.state === "completed" ? "success" : "error"
          );
          await history();
        });
      };
      effects.append(label, apply);
    }
    explore.onclick = () => {
      if (!busy) {
        effects.hidden = false;
        revoke();
        focus(effectsTitle);
      }
    };
    preview.append(effects);
    focus(heading);
  }
  async function history() {
    const data = await api("plans");
    if (data.capabilities) capabilities(data.capabilities);
    const list = $("history");
    list.replaceChildren();
    $("history-notice").hidden = !data.blocked_records;
    $("history-notice").textContent = data.blocked_records
      ? `${data.blocked_records} saved records could not be validated. Their files and history are retained. They cannot authorise copying or removal; do not delete them based on this screen.`
      : "";
    if (!data.plans.length)
      list.append(node("p", "No readable plans yet. Start with a folder overview above.", "muted"));
    data.plans.forEach((plan) => {
      const item = node("article", undefined, "history-item");
      item.append(
        node("h3", stateName(plan)),
        node("p", `${plan.actions.length} planned copies · ${plan.root}`, "folder-path")
      );
      if (plan.state !== "preview") {
        item.append(
          node("p", `Output: ${plan.root}/${plan.output}`, "folder-path"),
          node(
            "p",
            "Automatic copy removal is unavailable. Keep the originals, generated files and saved history. Inspect the output manually; this record does not establish that files are safe to erase.",
            "notice"
          )
        );
      }
      if (plan.error) item.append(node("p", plan.error, "notice"));
      const button = node(
        "button",
        plan.state === "preview" ? "Review saved preview" : "Inspect saved plan",
        "secondary operation-button"
      );
      button.onclick = () => {
        if (!busy && !mustRefresh) showPlan(plan, true);
      };
      item.append(button);
      list.append(item);
    });
  }
  $("root").oninput = () => closePreview();
  document.querySelectorAll('input[name="goal"]').forEach((input) => {
    input.onchange = () => {
      if (current && !busy) showPlan(current, true);
    };
  });
  $("scan-form").onsubmit = (event) => {
    event.preventDefault();
    if (busy || mustRefresh || !token || !scanEnabled) return;
    closePreview();
    const version = ++generation;
    run(async () => {
      status(
        "Reading this folder and verifying file hashes locally. Larger files may take a while. No source files are changed; a preview record will be saved."
      );
      const plan = await api("plans", { root: $("root").value.trim() });
      if (version !== generation) return;
      showPlan(plan);
      status("Overview saved. No copies have been made.", "success");
      await history();
    });
  };
  $("refresh").onclick = () =>
    run(async () => {
      mustRefresh = true;
      token = null;
      closePreview();
      await loadSession();
      await history();
      mustRefresh = false;
      status(
        copyEnabled
          ? "Session and history refreshed. Check the latest result before deciding what to do. Any copy request needs a newly reviewed plan."
          : "Session and history refreshed. Saved snapshots do not show current folder changes. Scan again for a current read-only overview when scanning is supported."
      );
    });
  setBusy(true);
  loadSession()
    .then(async () => {
      await history();
      mustRefresh = false;
    })
    .catch((error) =>
      status(
        `Could not load the local app: ${error.message} Open its localhost /ui/ address. If it is already open, refresh this page.`,
        "error"
      )
    )
    .finally(() => setBusy(false));
})();
