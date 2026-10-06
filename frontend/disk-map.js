/* Read-only export explorer. Imported strings become text nodes, never URLs or HTML. */
(() => {
  "use strict";
  let renderRoot = document,
    renderBudget = null;
  const $ = (id) =>
    renderRoot === document
      ? document.getElementById(id)
      : renderRoot.id === id
      ? renderRoot
      : renderRoot.querySelector(`#${id}`);
  const mapTemplate = $("map-content").cloneNode(true);
  const LIST_LIMIT = 20,
    EVIDENCE_LIMIT = 10,
    PAIR_LIMIT = 10;
  const MAX_RENDER_NODES = 2000,
    MAX_RENDER_TEXT = 512 * 1024;
  const MAX_DOM_NODES = 7000,
    MAX_DOM_TEXT = 2 * 1024 * 1024;
  let worker = null,
    settleCancelledWorker = null;
  const assets = window.DiskMapAssets,
    contract = window.DiskMapModel;
  let current = null,
    origin = "",
    bundled = false,
    generation = 0,
    reader = null,
    opening = false;
  let view = "findings",
    page = 0,
    detailTrail = [],
    returnFocus = null;
  const PAGE_SIZE = 25;
  const node = (tag, text, className) => {
    if (renderBudget) {
      renderBudget.nodes++;
      renderBudget.text += text === undefined ? 0 : String(text).length;
      if (renderBudget.nodes > MAX_RENDER_NODES || renderBudget.text > MAX_RENDER_TEXT)
        throw new contract.ImportError(
          "This view exceeds the display budget. Inspect the remaining data in the original export."
        );
    }
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    return el;
  };
  const count = (n, word, plural = `${word}s`) =>
    `${n.toLocaleString()} ${n === 1 ? word : plural}`;
  const bytes = (n) => {
    if (n === null || n === undefined) return "Unknown";
    if (n < 1024) return `${n} B`;
    for (const [size, unit] of [
      [1024 ** 4, "TiB"],
      [1024 ** 3, "GiB"],
      [1024 ** 2, "MiB"],
      [1024, "KiB"],
    ])
      if (n >= size) return `${(n / size).toFixed(2)} ${unit}`;
    return `${n} B`;
  };
  function timestamp(value) {
    if (value === null) return "Unknown";
    const milliseconds = typeof value === "bigint" ? Number(value / 1000000n) : value / 1e6;
    return Number.isFinite(milliseconds) && Math.abs(milliseconds) <= 8640000000000000
      ? `${new Date(milliseconds).toLocaleString()} (approximate; not last use)`
      : "Outside this viewer's date range; raw observation remains in the export.";
  }
  const words = (value) => String(value).replaceAll("_", " ");
  const labelKind = (kind) =>
    ({
      directory_role: "Possible folder purpose",
      version_like_names: "Possible versions or exports",
      identical_content: "Matching content observations",
      hard_link_paths: "Paths to one observed file",
      largest_observed_files: "Largest observed files",
      older_modification_times: "Older modification times",
      incomplete_inventory: "Gaps in the snapshot",
      same_observed_file_object: "Observed object identity",
      project_marker_names: "Project marker names",
      directory_name: "Directory label",
      matching_full_hashes: "Full-file hash observations",
    }[kind] || words(kind));
  const confidenceLabel = (confidence) =>
    ({
      observed: "Recorded observation",
      hypothesis: "Hypothesis · check the evidence",
      unknown: "Unknown · insufficient evidence",
    }[confidence]);
  const badge = (confidence) => node("span", confidenceLabel(confidence), `badge ${confidence}`);
  const focus = (element) => element?.focus({ preventScroll: false });
  const status = (message, kind = "info") => {
    $("map-status").textContent = message;
    $("map-status").dataset.kind = kind;
  };
  const pathLabel = (entry) =>
    `${
      current.roots.size > 1
        ? `${current.model.scan.roots.findIndex((r) => r.id === entry.root_id) + 1}: `
        : ""
    }${entry.relative_path}`;
  function button(text, action, secondary = true) {
    const b = node("button", text, secondary ? "secondary" : "");
    b.type = "button";
    b.onclick = action;
    return b;
  }
  function limitedNotice(shown, total, label = "items") {
    return node(
      "p",
      `Showing ${shown} of ${total} ${label}. The remaining records are in the original export; no absence is implied.`,
      "notice"
    );
  }
  function list(values, empty = "None recorded.", total = values.length) {
    const ul = node("ul");
    if (!total) ul.append(node("li", empty));
    else values.slice(0, LIST_LIMIT).forEach((value) => ul.append(node("li", value)));
    if (total > LIST_LIMIT)
      ul.append(
        node(
          "li",
          `Showing ${Math.min(
            LIST_LIMIT,
            values.length
          )} of ${total} items. Remaining items are in the original export; they are not known to be absent.`,
          "muted"
        )
      );
    return ul;
  }
  function factPairs(values) {
    const wrapper = node("div"),
      dl = node("dl");
    for (const [key, value] of values.slice(0, PAIR_LIMIT))
      dl.append(node("dt", key), node("dd", value));
    wrapper.append(dl);
    if (values.length > PAIR_LIMIT)
      wrapper.append(limitedNotice(PAIR_LIMIT, values.length, "fields"));
    return wrapper;
  }
  function budgeted(work) {
    if (renderBudget) return work();
    renderBudget = { nodes: 0, text: 0 };
    try {
      return work();
    } finally {
      renderBudget = null;
    }
  }
  function checkDOM(root) {
    if (root.querySelectorAll("*").length > MAX_DOM_NODES || root.textContent.length > MAX_DOM_TEXT)
      throw new contract.ImportError(
        "This model exceeds the total display budget. The current view has been kept."
      );
  }
  function commitContents(id, prepared) {
    const target = $(id),
      map = $("map-content");
    const nodes =
      map.querySelectorAll("*").length -
      target.querySelectorAll("*").length +
      prepared.querySelectorAll("*").length;
    const text = map.textContent.length - target.textContent.length + prepared.textContent.length;
    if (nodes > MAX_DOM_NODES || text > MAX_DOM_TEXT)
      throw new contract.ImportError(
        "This view exceeds the total display budget. Inspect the original export for the remaining data."
      );
    target.replaceChildren(...prepared.childNodes);
  }
  function prepareSnapshot(accepted, name, isBundled) {
    const saved = { current, origin, bundled, view, page, detailTrail, returnFocus, renderRoot };
    const staging = mapTemplate.cloneNode(true);
    try {
      renderRoot = staging;
      current = accepted;
      origin = name;
      bundled = isBundled;
      view = "findings";
      page = 0;
      detailTrail = [];
      returnFocus = null;
      budgeted(() => renderModel());
      bindMapControls();
      checkDOM(staging);
      return staging;
    } finally {
      ({ current, origin, bundled, view, page, detailTrail, returnFocus, renderRoot } = saved);
    }
  }
  function validateInWorker(input, ticket) {
    return new Promise((resolve, reject) => {
      let local;
      try {
        local = new Worker("disk-map-worker.js");
      } catch (_) {
        reject(
          new contract.ImportError(
            "This browser could not start local validation. No model was replaced."
          )
        );
        return;
      }
      worker = local;
      settleCancelledWorker = () => resolve(null);
      const finish = () => {
        local.terminate();
        if (worker === local) {
          worker = null;
          settleCancelledWorker = null;
        }
      };
      local.onmessage = (event) => {
        if (ticket !== generation || event.data.ticket !== ticket) return;
        finish();
        if (event.data.error) reject(new contract.ImportError(event.data.error));
        else resolve(event.data.accepted);
      };
      local.onerror = () => {
        finish();
        reject(
          new contract.ImportError("Local validation stopped unexpectedly. No model was replaced.")
        );
      };
      if (typeof input === "string") local.postMessage({ ticket, text: input });
      else local.postMessage({ ticket, bytes: input }, [input]);
    });
  }
  function cancelRead(message) {
    generation++;
    if (worker) worker.terminate();
    worker = null;
    settleCancelledWorker?.();
    settleCancelledWorker = null;
    const previous = reader;
    reader = null;
    if (previous?.readyState === 1) previous.abort();
    opening = false;
    $("cancel-import").hidden = true;
    $("clear-model").disabled = !current;
    if (message) status(message);
  }
  function begin() {
    cancelRead();
    opening = true;
    $("cancel-import").hidden = false;
    $("clear-model").disabled = false;
    status(
      "Opening and checking the export locally. The current view stays until the new model is accepted."
    );
    return generation;
  }
  async function acceptText(text, name, isBundled, ticket) {
    if (ticket !== generation) return;
    let committed = false;
    try {
      const accepted = await validateInWorker(text, ticket);
      if (!accepted || ticket !== generation) return;
      await new Promise((resolve) => setTimeout(resolve, 0));
      if (ticket !== generation) return;
      const staging = prepareSnapshot(accepted, name, isBundled);
      if (ticket !== generation) return;
      $("map-content").replaceWith(staging);
      current = accepted;
      origin = name;
      bundled = isBundled;
      view = "findings";
      page = 0;
      detailTrail = [];
      returnFocus = null;
      committed = true;
      opening = false;
      reader = null;
      $("cancel-import").hidden = true;
      $("clear-model").disabled = false;
      $("empty-guidance").hidden = true;
      status(
        `${
          isBundled ? "Synthetic example" : "Export"
        } opened. Structure, references and displayed accounting checked; no file contents or current disk state were verified.`
      );
      focus($("map-title"));
    } catch (error) {
      if (ticket !== generation) return;
      opening = false;
      reader = null;
      $("cancel-import").hidden = true;
      $("clear-model").disabled = !current;
      status(
        `${
          error instanceof contract.ImportError ? error.message : "The export could not be opened."
        } ${
          committed
            ? "The new model was opened, but the view did not finish. Clear this tab before trying again."
            : current
            ? "Your previous accepted view is unchanged."
            : "No model has been opened."
        }`,
        "error"
      );
    }
  }
  $("example").onclick = () => {
    const ticket = begin();
    acceptText(assets.exampleText, "Bundled synthetic example", true, ticket);
  };
  $("model-file").onchange = (event) => {
    const file = event.target.files[0];
    event.target.value = "";
    if (!file) return;
    const ticket = begin();
    if (file.size > contract.MAX_BYTES) {
      opening = false;
      $("cancel-import").hidden = true;
      $("clear-model").disabled = !current;
      status(
        "This export exceeds the 8 MiB viewer limit and was not read. The previous accepted view is unchanged.",
        "error"
      );
      return;
    }
    const localReader = new FileReader();
    reader = localReader;
    localReader.onload = () => {
      if (ticket !== generation) return;
      acceptText(localReader.result, file.name.slice(0, 240), false, ticket);
    };
    localReader.onerror = () => {
      if (ticket !== generation) return;
      cancelRead();
      status("The file could not be read. The previous accepted view is unchanged.", "error");
    };
    localReader.onabort = () => {
      if (ticket !== generation) return;
      cancelRead("Opening cancelled. The previous accepted view is unchanged.");
    };
    localReader.readAsArrayBuffer(file);
  };
  $("cancel-import").onclick = () => {
    cancelRead("Opening cancelled. The previous accepted view is unchanged.");
    focus($("example"));
  };
  $("clear-model").onclick = () => {
    cancelRead();
    current = null;
    origin = "";
    bundled = false;
    detailTrail = [];
    returnFocus = null;
    page = 0;
    for (const id of [
      "scope-content",
      "storage-summary",
      "coverage-banner",
      "map-results",
      "detail-content",
    ])
      $(id).replaceChildren();
    $("model-origin").textContent = "";
    $("map-title").textContent = "Storage snapshot";
    $("result-count").textContent = "";
    $("map-search").value = "";
    $("detail-title").textContent = "";
    $("model-file").value = "";
    $("map-content").hidden = true;
    $("map-detail").hidden = true;
    $("empty-guidance").hidden = false;
    $("clear-model").disabled = true;
    status(
      "This tab's imported model has been cleared. The original export and your files are unchanged."
    );
    focus($("example"));
  };
  function metric(title, value, note) {
    const item = node("article", undefined, "metric");
    item.append(node("h3", title), node("strong", value), node("p", note));
    return item;
  }
  function renderModel() {
    const m = current.model,
      a = m.aggregates,
      scan = m.scan;
    $("map-content").hidden = false;
    $("model-origin").textContent = bundled
      ? "FABRICATED EXAMPLE · NO DRIVE WAS SCANNED"
      : "LOCALLY OPENED EXPORT · NOT A LIVE SCAN";
    $("map-title").textContent = origin;
    const banner = $("coverage-banner");
    banner.replaceChildren();
    banner.className = `notice${scan.status === "complete" ? " calm" : ""}`;
    banner.append(
      node(
        "strong",
        scan.status === "cancelled"
          ? "The recorded scan was cancelled. This view is incomplete."
          : scan.status === "partial"
          ? "Partial snapshot. Some storage was not characterised."
          : "The export reports completion within its selected scope and limits."
      )
    );
    const gaps = Object.entries(scan.coverage.status_counts)
      .filter(([key, value]) => key !== "observed" && value > 0)
      .map(([key, value]) => `${value} ${words(key)}`);
    banner.append(
      node(
        "p",
        `${count(m.entries.length, "entry", "entries")} recorded across ${count(
          scan.roots.length,
          "root"
        )}.${
          gaps.length ? ` Coverage gaps: ${gaps.join(", ")}.` : ""
        } This is not an atomic snapshot or a whole-drive total.`
      )
    );
    if (scan.coverage.stop_reason)
      banner.append(node("p", `Recording stopped: ${words(scan.coverage.stop_reason)}.`));
    if (m.analysis_coverage.findings_omitted || m.analysis_coverage.relationships_omitted)
      banner.append(
        node(
          "p",
          `Analysis limits omitted ${m.analysis_coverage.findings_omitted} findings and ${m.analysis_coverage.relationships_omitted} relationships. No absence can be inferred from this limited list.`
        )
      );
    $("storage-summary").replaceChildren(
      metric(
        "Logical size across observed paths",
        bytes(a.logical_bytes_by_path),
        `${count(
          a.observed_regular_files,
          "observed regular file"
        )}. Multiple hard-link paths are counted more than once.`
      ),
      metric(
        "Logical size by observed object",
        bytes(a.logical_bytes_by_observed_object),
        a.object_identity_unknown_paths
          ? `${count(
              a.object_identity_unknown_paths,
              "path"
            )} lack object identity; deduplicated accounting is unknown.`
          : `${count(a.distinct_observed_file_objects, "observed object")}; ${count(
              a.hard_link_alias_paths,
              "additional hard-link path"
            )}. Not physical storage.`
      ),
      metric(
        "Known allocated bytes",
        bytes(a.known_allocated_bytes_by_observed_object),
        a.allocation_unknown_objects === null
          ? "Object identities are incomplete; allocation cannot be totalled reliably."
          : `${count(
              a.allocation_unknown_objects,
              "object"
            )} have unknown allocation. Shared extents and compression may affect accounting.`
      ),
      metric(
        "Physical / recoverable space",
        "Unknown",
        "This model cannot determine unique physical usage, safe deletion or recoverable space."
      )
    );
    const scope = $("scope-content");
    scope.replaceChildren();
    const captured = new Date(scan.started_at),
      age = Date.now() - captured.getTime();
    scope.append(
      factPairs([
        ["Recorded", `${captured.toLocaleString(undefined, { timeZone: "UTC" })} UTC`],
        [
          "Freshness",
          age < 0
            ? "Recorded time is in the future; verify the source clock. Freshness is unknown."
            : `${Math.floor(
                age / 86400000
              )} days since recording. Files may have changed; this viewer does not rescan.`,
        ],
        [
          "Read policy",
          scan.hash_policy === "metadata_only"
            ? "Metadata only; content hashing was off."
            : "The producer used bounded SHA-256 reads. Per-file hash states remain historical observations.",
        ],
        [
          "Record limits",
          `${scan.limits.max_entries.toLocaleString()} entries, depth ${scan.limits.max_depth}, ${
            scan.limits.max_seconds
          } cooperative seconds`,
        ],
        [
          "Root boundary",
          scan.limits.cross_filesystems
            ? "The producer allowed child filesystem boundaries."
            : "The producer did not cross child filesystem boundaries.",
        ],
        [
          "Import validation",
          "Structure, references and displayed accounting checked. No path, hash or observation is authenticated against a drive.",
        ],
      ])
    );
    scope.append(
      node("h3", "Selected roots in this export"),
      list(scan.roots.map((root) => `${root.path} · ${words(root.status)}`))
    );
    if (!bundled && m.synthetic)
      scope.append(
        node(
          "p",
          "The imported file marks itself as synthetic. That label is supplied by the file, not independently verified.",
          "notice"
        )
      );
    scope.append(
      node("h3", "What remains uncertain"),
      list([...scan.uncertainties, ...a.uncertainties])
    );
    scope.append(
      node(
        "p",
        "File timestamps are shown as approximate dates. Nanosecond precision and opaque device/inode numbers are not used as file identity or action authority in this viewer.",
        "muted"
      )
    );
    if (scan.errors.length || scan.exclusions.length) {
      const details = node("details");
      details.append(node("summary", "Recorded exclusions and read errors"));
      details.append(
        list(
          [
            ...scan.errors
              .slice(0, LIST_LIMIT)
              .map(
                (e) =>
                  `${pathLabel(current.entries.get(e.entry_id))}: ${e.kind}${
                    e.errno === null ? "" : ` (code ${e.errno})`
                  }`
              ),
            ...scan.exclusions
              .slice(0, LIST_LIMIT)
              .map((e) => `${pathLabel(current.entries.get(e.entry_id))}: ${words(e.reason)}`),
          ],
          "None recorded.",
          scan.errors.length + scan.exclusions.length
        )
      );
      scope.append(details);
    }
    if (m.changes.previous_scan_id)
      scope.append(
        node("h3", "Reported change comparison"),
        node(
          "p",
          `${
            m.changes.comparable
              ? "Comparable metadata snapshots"
              : "Snapshots are not fully comparable"
          }: ${m.changes.added.length} added addresses, ${
            m.changes.changed.length
          } changed observations, ${m.changes.no_longer_observed.length} no longer observed, ${
            m.changes.unverified_absent.length
          } unverified absences. These are not deletion or rename records.`
        ),
        list(m.changes.uncertainties)
      );
    configureView();
    renderResults();
  }
  const filters = {
    findings: [
      ["all", "All questions"],
      ["hypothesis", "Hypotheses"],
      ["observed", "Recorded observations"],
      ["unknown", "Unknowns"],
    ],
    directories: [
      ["all", "All folders"],
      ["project", "Possible projects"],
      ["archive", "Possible archives"],
      ["inbox", "Possible inboxes"],
      ["cache", "Possible caches"],
      ["unknown", "Unclassified folders"],
      ["incomplete", "Incomplete coverage"],
    ],
    relationships: [
      ["all", "All relationships"],
      ["hypothesis", "Hypotheses"],
      ["observed", "Recorded observations"],
      ["unknown", "Unknowns"],
    ],
    entries: [
      ["all", "All entries"],
      ["file", "Files"],
      ["directory", "Folders"],
      ["unobserved", "Unreadable / stale / excluded"],
      ["unknown-size", "Unknown logical size"],
    ],
    plans: [["all", "All review choices"]],
  };
  function configureView() {
    $("map-content")
      .querySelectorAll('[role="tab"]')
      .forEach((tab) => {
        const selected = tab.dataset.view === view;
        tab.setAttribute("aria-selected", String(selected));
        tab.tabIndex = selected ? 0 : -1;
      });
    $("map-results").setAttribute("aria-labelledby", `tab-${view}`);
    $("map-filter").replaceChildren(
      ...filters[view].map(([value, label]) => {
        const option = node("option", label);
        option.value = value;
        return option;
      })
    );
    $("view-explanation").textContent = {
      findings:
        "Open a question to see the observed facts, related paths and limits behind it. Hypotheses are not confirmed classifications.",
      directories:
        "Possible roles come from names and marker files. A folder can have several roles; unclassified and incomplete folders remain visible.",
      relationships:
        "Matching hashes, hard-link paths and name families mean different things. None establishes a preferred version, backup sufficiency or permission to delete.",
      entries:
        "A neutral path view of the imported observations. Search and filters do not change the snapshot or its totals.",
      plans:
        "These are non-executable review choices: retain the layout, inspect evidence or clarify intent. They are not coherent reorganisation plans and cannot change files.",
    }[view];
  }
  function itemPathIds(kind, item) {
    return kind === "directories"
      ? [item.entry_id, ...item.direct_member_ids]
      : kind === "entries"
      ? [item.id]
      : kind === "plans"
      ? item.scope_member_ids
      : item.member_ids;
  }
  function titleFor(kind, item) {
    if (kind === "entries") return pathLabel(item);
    if (kind === "directories") return pathLabel(current.entries.get(item.entry_id));
    if (kind === "findings") return item.title;
    if (kind === "plans")
      return (
        (item.reasons[0] || "Read-only review choices") +
        (item.reasons.length > 1 ? ` (+${item.reasons.length - 1} more reasons)` : "")
      );
    return labelKind(item.kind);
  }
  function renderResults() {
    if (!current) return;
    return budgeted(() => {
      const query = $("map-search").value.trim().toLocaleLowerCase(),
        filter = $("map-filter").value;
      const source = view === "plans" ? current.model.plan_alternatives : current.model[view];
      const pathMatches = new Set();
      if (query)
        for (const [id, text] of current.searchPaths) if (text.includes(query)) pathMatches.add(id);
      const matches = source.filter((item) => {
        if (
          query &&
          !titleFor(view, item).toLocaleLowerCase().includes(query) &&
          !itemPathIds(view, item).some((id) => pathMatches.has(id))
        )
          return false;
        if (filter === "all") return true;
        if (view === "directories")
          return filter === "unknown"
            ? !item.role_hypotheses.length
            : filter === "incomplete"
            ? !item.coverage.complete
            : item.role_hypotheses.some((r) => r.role === filter);
        if (view === "entries")
          return filter === "unobserved"
            ? item.status !== "observed"
            : filter === "unknown-size"
            ? item.logical_bytes === null
            : item.kind === filter;
        return item.confidence === filter;
      });
      page = Math.min(page, Math.max(0, Math.ceil(matches.length / PAGE_SIZE) - 1));
      const start = page * PAGE_SIZE;
      const countText = matches.length
        ? `Showing ${start + 1}–${Math.min(
            start + PAGE_SIZE,
            matches.length
          )} of ${matches.length.toLocaleString()} matches (${source.length.toLocaleString()} in this view). Snapshot totals above are unchanged.`
        : `No matches in this view (${source.length.toLocaleString()} records). Try another search or filter. Snapshot totals are unchanged.`;
      const target = node("div");
      if (!matches.length)
        target.append(
          node(
            "p",
            source.length
              ? "Nothing matches this filter."
              : "No records of this kind were included. This does not prove that no such material exists.",
            "muted"
          )
        );
      matches.slice(start, start + PAGE_SIZE).forEach((item) => {
        const card = node("article", undefined, "result-card");
        if (item.confidence) card.append(badge(item.confidence));
        if (view === "plans")
          card.append(node("span", "Non-executable review choices", "badge unknown"));
        card.append(node("h3", titleFor(view, item)));
        if (view === "directories")
          card.append(
            node(
              "p",
              `${
                item.role_hypotheses.length
                  ? `Possible ${item.role_hypotheses.map((r) => r.role).join(" / ")}`
                  : "Unclassified folder"
              } · ${
                item.coverage.complete ? "Coverage complete within policy" : "Incomplete coverage"
              }`
            ),
            node(
              "p",
              `${bytes(item.logical_bytes)} across ${count(
                item.observed_files,
                "observed file"
              )} below this folder; path-based logical size. ${count(
                item.uncertain_entries,
                "uncertain entry",
                "uncertain entries"
              )}.`
            )
          );
        else if (view === "entries")
          card.append(
            node(
              "p",
              `${words(item.kind)} · ${words(item.status)} · ${bytes(
                item.logical_bytes
              )} logical size`
            )
          );
        else {
          const ids = itemPathIds(view, item);
          card.append(
            node(
              "p",
              `${ids
                .slice(0, 3)
                .map((id) => pathLabel(current.entries.get(id)))
                .join(" · ")}${ids.length > 3 ? ` · +${ids.length - 3} more` : ""}`,
              "path"
            )
          );
        }
        const ref = { kind: view, id: view === "directories" ? item.entry_id : item.id };
        const inspect = button(
          view === "plans"
            ? "Compare review choices"
            : view === "entries"
            ? "Inspect observation"
            : "Inspect evidence",
          () => openDetail(ref, inspect)
        );
        card.append(inspect);
        target.append(card);
      });
      commitContents("map-results", target);
      $("result-count").textContent = countText;
      $("previous-page").disabled = page === 0;
      $("next-page").disabled = start + PAGE_SIZE >= matches.length;
      $("previous-page").parentElement.hidden = matches.length <= PAGE_SIZE;
    });
  }
  function switchView(next, keyboard = false) {
    view = next;
    page = 0;
    $("map-search").value = "";
    configureView();
    renderResults();
    if (keyboard) focus($(`tab-${next}`));
  }
  function safely(work) {
    try {
      work();
    } catch (error) {
      status(
        error instanceof contract.ImportError
          ? error.message
          : "This view could not be displayed. No files changed.",
        "error"
      );
    }
  }
  function bindMapControls() {
    const tabs = [...$("map-content").querySelectorAll('[role="tab"]')];
    tabs.forEach((tab, index) => {
      tab.onclick = () => {
        if (current) safely(() => switchView(tab.dataset.view));
      };
      tab.onkeydown = (event) => {
        const next =
          event.key === "ArrowRight"
            ? (index + 1) % tabs.length
            : event.key === "ArrowLeft"
            ? (index + tabs.length - 1) % tabs.length
            : event.key === "Home"
            ? 0
            : event.key === "End"
            ? tabs.length - 1
            : null;
        if (next !== null) {
          event.preventDefault();
          if (current) safely(() => switchView(tabs[next].dataset.view, true));
        }
      };
    });
    $("map-search").oninput = () => {
      page = 0;
      safely(renderResults);
    };
    $("map-filter").onchange = () => {
      page = 0;
      safely(renderResults);
    };
    $("previous-page").onclick = () => {
      page--;
      safely(renderResults);
      focus($("map-results"));
    };
    $("next-page").onclick = () => {
      page++;
      safely(renderResults);
      focus($("map-results"));
    };
    $("detail-back").onclick = () => {
      if (detailTrail.length > 1) {
        const saved = detailTrail.slice();
        detailTrail.pop();
        try {
          renderDetail();
        } catch (error) {
          detailTrail = saved;
          safely(() => {
            throw error;
          });
        }
      }
    };
    $("detail-close").onclick = () => {
      detailTrail = [];
      $("map-detail").hidden = true;
      $("detail-content").replaceChildren();
      focus(returnFocus?.isConnected ? returnFocus : $("browse-title"));
    };
  }
  function members(ids) {
    const wrapper = node("div");
    let offset = 0;
    const contents = node("ul", undefined, "member-list"),
      progress = node("p", undefined, "muted");
    progress.setAttribute("role", "status");
    progress.tabIndex = -1;
    const more = button("Show next 25 members", () => {
      offset += PAGE_SIZE;
      safely(() => budgeted(render));
      focus(progress);
    });
    function render() {
      contents.replaceChildren();
      ids.slice(offset, offset + PAGE_SIZE).forEach((id) => {
        const entry = current.entries.get(id),
          li = node("li");
        li.append(
          node("strong", pathLabel(entry)),
          node(
            "p",
            `${words(entry.kind)} · ${words(entry.status)} · ${bytes(entry.logical_bytes)} logical`,
            "muted"
          )
        );
        li.append(
          button("Inspect this observation", () => openDetail({ kind: "entries", id }, null, true))
        );
        contents.append(li);
      });
      progress.textContent = ids.length
        ? `${offset + 1}–${Math.min(offset + PAGE_SIZE, ids.length)} of ${count(
            ids.length,
            "member"
          )}`
        : "No members recorded.";
      more.hidden = offset + PAGE_SIZE >= ids.length;
      previous.disabled = offset === 0;
    }
    const previous = button("Previous members", () => {
      offset = Math.max(0, offset - PAGE_SIZE);
      safely(() => budgeted(render));
      focus(progress);
    });
    previous.hidden = ids.length <= PAGE_SIZE;
    wrapper.append(progress, contents, previous, more);
    render();
    return wrapper;
  }
  function observation(value) {
    const parts = [];
    let chars = 0,
      visits = 0,
      omitted = false;
    function append(text) {
      const room = 1024 - chars;
      if (room <= 0) {
        omitted = true;
        return;
      }
      const s = String(text);
      parts.push(s.slice(0, room));
      chars += Math.min(s.length, room);
      if (s.length > room) omitted = true;
    }
    function walk(v, depth) {
      if (++visits > 64 || depth > 3 || chars >= 1024) {
        omitted = true;
        return;
      }
      if (v === null) append("Unknown");
      else if (typeof v !== "object") append(v);
      else {
        const total = Array.isArray(v) ? v.length : Object.keys(v).length;
        const items = Array.isArray(v)
          ? v.slice(0, 6).map((item, index) => [index, item])
          : Object.entries(v).slice(0, 6);
        for (const [key, item] of items) {
          if (chars) append("; ");
          if (!Array.isArray(v))
            append(
              `${current.entries.has(key) ? pathLabel(current.entries.get(key)) : words(key)}: `
            );
          walk(item, depth + 1);
        }
        if (total > 6) omitted = true;
      }
    }
    walk(value, 0);
    return parts.join("") + (omitted ? " … [summary limited; inspect the original export]" : "");
  }
  function evidence(ids, target) {
    target.append(node("h3", "Why this appears"));
    if (!ids.length) {
      target.append(
        node("p", "No supporting evidence is included. Treat this as unverified.", "notice")
      );
      return;
    }
    ids.slice(0, EVIDENCE_LIMIT).forEach((id) => {
      const item = current.evidence.get(id),
        card = node("article", undefined, "fact");
      card.append(
        node("h4", labelKind(item.kind)),
        badge("observed"),
        factPairs(
          Object.entries(item.observations)
            .slice(0, PAIR_LIMIT)
            .map(([key, value]) => [words(key), observation(value)])
        )
      );
      if (Object.keys(item.observations).length > PAIR_LIMIT)
        card.append(
          limitedNotice(PAIR_LIMIT, Object.keys(item.observations).length, "evidence fields")
        );
      card.append(
        node(
          "p",
          `Evidence refers to ${count(
            item.member_ids.length,
            "recorded member"
          )}. These are statements in the export; no file was read by this viewer.`,
          "muted"
        )
      );
      target.append(card);
    });
    if (ids.length > EVIDENCE_LIMIT)
      target.append(
        node(
          "p",
          `Showing ${EVIDENCE_LIMIT} of ${ids.length} evidence records. Remaining evidence is in the original export.`,
          "notice"
        )
      );
  }
  function resolve(ref) {
    return current[ref.kind].get(ref.id);
  }
  function openDetail(ref, trigger, nested = false) {
    if (!current) return;
    const savedTrail = detailTrail.slice(),
      savedFocus = returnFocus;
    if (!nested) {
      detailTrail = [];
      returnFocus = trigger;
    }
    if (detailTrail.length >= 20) detailTrail.shift();
    detailTrail.push(ref);
    try {
      renderDetail();
    } catch (error) {
      detailTrail = savedTrail;
      returnFocus = savedFocus;
      safely(() => {
        throw error;
      });
    }
  }
  function renderDetail() {
    return budgeted(() => {
      const ref = detailTrail[detailTrail.length - 1],
        item = resolve(ref),
        target = node("div");
      if (!item) return;
      const title = titleFor(ref.kind, item);
      if (item.confidence) target.append(badge(item.confidence));
      if (ref.kind === "entries") {
        const root = current.roots.get(item.root_id);
        target.append(
          factPairs([
            ["Root", root.path],
            ["Relative path", item.relative_path],
            ["Observation", `${words(item.kind)} · ${words(item.status)}`],
            ["Logical bytes", bytes(item.logical_bytes)],
            ["Allocated bytes", bytes(item.allocated_bytes)],
            ["Allocation source", words(item.allocation_source)],
            ["Hash state", words(item.hash.status)],
            ["Modification time", timestamp(item.mtime_ns)],
          ])
        );
        if (item.hash.value) {
          const d = node("details");
          d.append(node("summary", "Recorded SHA-256 digest"), node("p", item.hash.value, "path"));
          target.append(d);
        }
        target.append(
          node("h3", "Limits of this observation"),
          list(
            item.uncertainties,
            "No entry-specific uncertainty was recorded. This still is not a live verification."
          )
        );
        const related = current.model.relationships.filter((r) => r.member_ids.includes(item.id));
        if (related.length) {
          target.append(node("h3", "Related observations"));
          related
            .slice(0, 25)
            .forEach((r) =>
              target.append(
                button(labelKind(r.kind), () =>
                  openDetail({ kind: "relationships", id: r.id }, null, true)
                )
              )
            );
          if (related.length > 25)
            target.append(limitedNotice(25, related.length, "related observations"));
        }
      } else if (ref.kind === "plans") {
        target.append(
          node(
            "p",
            "Read-only questions, not an organisation plan. These alternatives cannot be applied and request no additional content reads.",
            "notice"
          )
        );
        target.append(
          node("h3", "Why consider this?"),
          list(item.reasons),
          node("h3", "Uncertainties"),
          list(item.uncertainties)
        );
        item.alternatives.forEach((alternative) => {
          const card = node("article", undefined, "fact");
          card.append(node("h3", alternative.label));
          card.append(
            node(
              "p",
              `${count(alternative.unchanged_member_ids.length, "scoped member")} retained; ${count(
                alternative.uncertain_member_ids.length,
                "member observation"
              )} uncertain. Relationship confidence is separate and remains on the originating finding.`
            )
          );
          const steps = node("ol");
          alternative.steps.forEach((step) =>
            steps.append(
              node(
                "li",
                `${
                  {
                    keep_unchanged: "Retain the current structure",
                    inspect_evidence: "Inspect the recorded evidence",
                    ask_about_intent: "Clarify whether these files belong together",
                  }[step.type]
                }${step.depends_on.length ? " (after the earlier evidence step)" : ""}.`
              )
            )
          );
          card.append(steps);
          target.append(card);
        });
        target.append(
          node("p", item.outside_scope),
          node("h3", "Scope stays unchanged"),
          members(item.scope_member_ids)
        );
        item.finding_ids
          .slice(0, LIST_LIMIT)
          .forEach((id) =>
            target.append(
              button("Return to the underlying finding", () =>
                openDetail({ kind: "findings", id }, null, true)
              )
            )
          );
        if (item.finding_ids.length > LIST_LIMIT)
          target.append(limitedNotice(LIST_LIMIT, item.finding_ids.length, "finding links"));
      } else {
        const ids =
          ref.kind === "directories"
            ? [...new Set(item.role_hypotheses.flatMap((r) => r.evidence_ids))]
            : item.evidence_ids;
        if (ref.kind === "directories")
          target.append(
            node(
              "p",
              `${
                item.coverage.complete
                  ? "Complete within recorded policy"
                  : "Incomplete directory coverage"
              } · ${bytes(item.logical_bytes)} path-based logical size.`
            ),
            list(item.coverage.reasons, "No directory-specific coverage gap was recorded.")
          );
        evidence(ids, target);
        target.append(
          node("h3", "What this does not establish"),
          list(
            item.uncertainties,
            "No uncertainty text was included. This remains an imported observation, not action authority."
          )
        );
        if (item.counter_evidence?.length)
          target.append(node("h3", "Counter-evidence"), list(item.counter_evidence));
        target.append(node("h3", "Underlying paths"), members(itemPathIds(ref.kind, item)));
        if (ref.kind === "findings") {
          const matchingPlans = current.model.plan_alternatives.filter((p) =>
            p.finding_ids.includes(item.id)
          );
          if (matchingPlans.length > LIST_LIMIT)
            target.append(limitedNotice(LIST_LIMIT, matchingPlans.length, "review-choice links"));
          matchingPlans
            .slice(0, LIST_LIMIT)
            .forEach((p) =>
              target.append(
                button("Compare read-only review choices", () =>
                  openDetail({ kind: "plans", id: p.id }, null, true)
                )
              )
            );
        }
      }
      target.append(
        node(
          "p",
          "Nothing here can move, rename, delete or recover files. Similarity and hashes do not prove which version to keep or that a backup is sufficient.",
          "muted"
        )
      );
      commitContents("detail-content", target);
      $("detail-title").textContent = title;
      $("map-detail").hidden = false;
      $("detail-back").hidden = detailTrail.length < 2;
      focus($("detail-title"));
    });
  }
  bindMapControls();
})();
