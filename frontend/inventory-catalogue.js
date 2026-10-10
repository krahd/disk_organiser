/* Local historical catalogue. Imported paths stay text, never filesystem capabilities. */
(() => {
  "use strict";
  const C = window.InventoryCatalogue,
    M = window.ManualPlanningModel,
    X = window.InventoryComparison;
  const $ = (id) => document.getElementById(id);
  const el = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };
  if (!C || !M || !X) {
    $("catalogue-status").textContent =
      "Catalogue files could not load. Keep the HTML, styles and JavaScript files together.";
    return;
  }
  let catalogue = C.empty(),
    selections = [],
    page = 0,
    details = false,
    dirty = false,
    generation = 0,
    revision = 0,
    downloadedRevision = null,
    action = null,
    origin = null,
    comparison = null,
    comparisonPage = 0;
  const embedded = window.DiskCatalogueEmbedded === true;
  const BRIDGE_VERSION = "catalogue-data-bridge/v2";
  const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
  let nativeSession = null,
    nativePending = null,
    nativeRetired = null,
    nativeInvalidated = false,
    nativeMode = "temporary",
    nativeProtocol = null,
    nativeEpoch = 0,
    nativeDialog = "none";
  let fencedControls = null,
    fencedFocus = null;
  const nativeUsed = new Set();
  function dismissNativePreview() {
    if (nativePending?.phase === "staged") nativePending.phase = "dismissed";
  }
  const persistenceOperations = [
    "status",
    "exportCatalogue",
    "acknowledgeSaved",
    "savedResult",
    "prepareClose",
    "releaseClose",
    "prepareOpen",
    "prepareReplacement",
    "retireCandidate",
    "commitReplacement",
    "replacementResult",
    "cancelOpen",
  ];
  function requireMutable() {
    nativeProtocol?.requireMutable();
  }
  function advanceEpoch() {
    if (!embedded || nativeInvalidated) return;
    if (!Number.isSafeInteger(nativeEpoch) || nativeEpoch >= Number.MAX_SAFE_INTEGER)
      throw Error("This preview has reached its interaction limit. Current data is retained.");
    nativeEpoch++;
  }
  function requireRevisionSpace() {
    if (
      embedded &&
      (!Number.isSafeInteger(revision) ||
        revision >= Number.MAX_SAFE_INTEGER ||
        nativeEpoch >= Number.MAX_SAFE_INTEGER)
    )
      throw Error("This preview has reached its revision limit. Current data is retained.");
  }
  function setPageFence(enabled) {
    if (enabled) {
      if (!fencedControls) {
        fencedControls = new Map();
        fencedFocus = document.activeElement;
      }
      document.querySelectorAll("button,input,select,textarea").forEach((control) => {
        if (!fencedControls.has(control)) fencedControls.set(control, control.disabled);
        control.disabled = true;
      });
      document.body.setAttribute("aria-busy", "true");
    } else if (fencedControls) {
      fencedControls.forEach((disabled, control) => {
        if (control.isConnected) control.disabled = disabled;
      });
      fencedControls = null;
      document.body.removeAttribute("aria-busy");
      if (fencedFocus?.isConnected) fencedFocus.focus();
      fencedFocus = null;
    }
  }
  if (embedded) {
    ["click", "keydown", "beforeinput", "input", "change", "submit", "cancel"].forEach((type) => {
      document.addEventListener(
        type,
        (event) => {
          if (nativeProtocol?.fenced) {
            event.preventDefault();
            event.stopImmediatePropagation();
            return;
          }
          if (type === "beforeinput" && nativeEpoch >= Number.MAX_SAFE_INTEGER) {
            event.preventDefault();
            event.stopImmediatePropagation();
            return;
          }
          if (["click", "input", "change", "submit", "cancel"].includes(type)) {
            try {
              advanceEpoch();
            } catch {
              event.preventDefault();
              event.stopImmediatePropagation();
            }
          }
        },
        true
      );
    });
  }
  function makePersistenceProtocol() {
    return window.NativeLibraryProtocol.create({
      check: nativeEnvelope,
      mode: () => nativeMode,
      state: () => ({
        revision: String(revision),
        epoch: String(nativeEpoch),
        dirty: dirty ? "dirty" : "clean",
        selections: String(selections.length),
        dialog: $("catalogue-dialog").open ? nativeDialog : "none",
        draft: $("catalogue-dialog").open ? "uncommitted" : "none",
        busy: nativePending !== null,
      }),
      export: () => C.exportCatalogue(catalogue),
      fence: setPageFence,
      clean: (captured) => {
        if (captured !== String(revision)) throw Error("Revision changed.");
        dirty = false;
      },
      parse: (text) => {
        const parsed = C.parse(text);
        if (parsed.schema_version !== C.CATALOGUE) throw Error("A catalogue is required.");
        return parsed;
      },
      commit: (parsed) => {
        // All validation/counter checks precede these local assignments. DOM work
        // is deliberately in render, after the protocol records the commit fact.
        catalogue = parsed;
        revision++;
        nativeEpoch++;
        dirty = false;
        selections = [];
        comparison = null;
        comparisonPage = 0;
        page = 0;
        downloadedRevision = null;
      },
      render: () => {
        $("catalogue-search").value = "";
        $("catalogue-filter").value = "";
        $("comparison-filter").value = "";
        $("catalogue-saved").hidden = true;
        render();
        setPageFence(true);
        status(
          "Saved library opened from temporary test storage. Source history remains unverified."
        );
      },
    });
  }
  function nativePersistenceCall(name, request) {
    if (!nativeProtocol) throw Error("Native library session is unavailable.");
    const reply = nativeProtocol[name](request);
    if (name === "acknowledgeSaved")
      status(
        reply.state === "current-saved"
          ? "Library revision saved in temporary test storage. Project selections remain temporary."
          : "An earlier library revision was saved. Your newer edits are still unsaved."
      );
    return reply;
  }
  const PAGE_SIZE = 50;
  const status = (text) => {
    $("catalogue-status").textContent = text;
  };
  const count = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
  function selectionWords(chosen) {
    let files = 0,
      folders = 0;
    chosen.forEach((s) => {
      const record = catalogue.records.find((r) => r.id === s.source_id),
        entry = record.snapshot.entries.find((e) => e.path === s.path);
      if (entry.kind === "file") files++;
      else if (entry.kind === "directory") folders++;
    });
    return (
      [files ? count(files, "file") : "", folders ? count(folders, "folder") : ""]
        .filter(Boolean)
        .join(" and ") || "0 files or folders"
    );
  }
  const observationDate = (tag, label, value, cls) => {
    const line = el(tag, label, cls),
      time = el("time", C.formatObservationDate(value));
    time.dateTime = value;
    line.append(time);
    return line;
  };
  function bytes(value) {
    const n = BigInt(value);
    const units = [
      [1024n ** 4n, "TiB"],
      [1024n ** 3n, "GiB"],
      [1024n ** 2n, "MiB"],
      [1024n, "KiB"],
    ];
    for (const [base, unit] of units)
      if (n >= base) return `${n / base}.${((n % base) * 10n) / base} ${unit}`;
    return `${n} B`;
  }
  const key = (s) => JSON.stringify([s.source_id, s.path]);
  const selected = (id, path) => selections.some((s) => s.source_id === id && s.path === path);
  const overlaps = (id, path) =>
    selections.some(
      (s) => s.source_id === id && (s.path.startsWith(path + "/") || path.startsWith(s.path + "/"))
    );
  const button = (text, callback, cls = "secondary-button") => {
    const b = el("button", text, cls);
    b.type = "button";
    b.addEventListener("click", callback);
    return b;
  };
  function changed(next, message) {
    requireMutable();
    requireRevisionSpace();
    advanceEpoch();
    dismissNativePreview();
    generation++;
    catalogue = next;
    revision++;
    dirty = true;
    downloadedRevision = null;
    $("catalogue-saved").hidden = true;
    render();
    status(message);
  }
  function close() {
    if (!nativeInvalidated) requireMutable();
    advanceEpoch();
    nativeDialog = "none";
    dismissNativePreview();
    generation++;
    $("catalogue-dialog").close();
    action = null;
    if (origin?.isConnected) origin.focus();
  }
  function dialog(title, intro, build, submit, label) {
    requireMutable();
    advanceEpoch();
    nativeDialog =
      title === "Name this saved location"
        ? "label-edit"
        : title === "Review this folder snapshot"
        ? "snapshot-review"
        : title === "Replace with saved catalogue?"
        ? "catalogue-review"
        : "other-edit";
    dismissNativePreview();
    generation++;
    origin = document.activeElement;
    action = submit;
    $("catalogue-dialog-title").textContent = title;
    $("catalogue-dialog-intro").textContent = intro;
    $("catalogue-dialog-body").replaceChildren();
    $("catalogue-error").hidden = true;
    $("catalogue-confirm").textContent = label;
    $("catalogue-confirm").disabled = false;
    build($("catalogue-dialog-body"));
    $("catalogue-dialog").showModal();
    ($("catalogue-dialog-body").querySelector("input,button") || $("catalogue-close")).focus();
  }
  function field(parent, label, value) {
    const l = el("label", label),
      i = el("input");
    i.id = "catalogue-name";
    i.value = value;
    i.maxLength = 240;
    i.required = true;
    i.autocomplete = "off";
    l.htmlFor = i.id;
    parent.append(l, i);
    return i;
  }
  function download(text, filename) {
    if (embedded) throw Error("File export is unavailable in this native test preview.");
    let url, anchor;
    try {
      const blob = new Blob([text], { type: "application/json;charset=utf-8" });
      url = URL.createObjectURL(blob);
      anchor = el("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.append(anchor);
      anchor.click();
    } finally {
      anchor?.remove();
      if (url) window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  }
  function rename(record) {
    let input;
    const before = catalogue;
    dialog(
      "Name this saved location",
      "Use a name you can recognise on the physical storage. This does not verify its identity or change the historical source label.",
      (body) => {
        input = field(body, "Your location label", record.label);
        body.append(
          el("p", `Original selected-folder label: ${record.snapshot.source.label}`, "small muted")
        );
      },
      () => {
        if (catalogue !== before) throw Error("Catalogue changed. Open this edit again.");
        changed(
          C.rename(catalogue, record.id, input.value),
          embedded
            ? nativeMode === "owned-storage"
              ? "Location label updated · save a new library version in the native window"
              : "Location label updated in this temporary native preview · nothing saved"
            : "Location label updated · save the catalogue to keep it"
        );
      },
      "Save label"
    );
  }
  function renderCards() {
    $("source-cards").replaceChildren();
    catalogue.records.forEach((record) => {
      const s = record.snapshot,
        sum = C.summary(s),
        card = el("article", undefined, "source-card"),
        icon = el("span", undefined, "source-icon");
      icon.setAttribute("aria-hidden", "true");
      card.append(
        icon,
        el("h3", record.label),
        observationDate("p", "Snapshot date (claimed): ", s.source.observed_at, "source-date"),
        el("p", bytes(sum.bytes), "source-stat"),
        el("p", `Listed observed file sizes · ${count(sum.files, "file path")}`, "small muted"),
        el(
          "span",
          s.source.coverage === "partial"
            ? "Partial folder record · gaps remain"
            : "Complete within the recorded folder policy",
          `coverage-label ${s.source.coverage === "partial" ? "partial" : ""}`
        )
      );
      const groups = [...sum.groups].sort((a, b) =>
          a.bytes === b.bytes ? a.path.localeCompare(b.path) : a.bytes > b.bytes ? -1 : 1
        ),
        shown = groups.slice(0, 4);
      if (groups.length > 4)
        shown.push({
          path: `${groups.length - 4} other groups`,
          bytes: groups.slice(4).reduce((a, g) => a + g.bytes, 0n),
        });
      const bar = el("div", undefined, "composition");
      bar.setAttribute("aria-hidden", "true");
      shown.forEach((g) => {
        const part = el("span");
        part.style.flexGrow = sum.bytes ? String(Number((g.bytes * 10000n) / sum.bytes)) : "1";
        bar.append(part);
      });
      const list = el("ul", undefined, "group-list");
      shown.forEach((g) => {
        const row = el("li");
        row.append(
          el("span", g.path || "Files directly in the folder"),
          el("span", bytes(g.bytes))
        );
        list.append(row);
      });
      card.append(
        bar,
        list,
        el(
          "p",
          "Logical sizes by path, not used/free disk space. Links may count the same bytes again.",
          "small muted"
        )
      );
      if (sum.uncertain || s.source.coverage === "partial")
        card.append(
          el(
            "p",
            `${count(
              sum.uncertain,
              "listed entry"
            )} with uncertain status; other entries may be absent.`,
            "small muted"
          )
        );
      const chosen = selections.filter((x) => x.source_id === record.id);
      card.append(el("p", `${selectionWords(chosen)} in your project selection`, "small"));
      const actions = el("div", undefined, "source-actions");
      actions.append(
        button("Browse record", () => {
          $("catalogue-filter").value = record.id;
          $("catalogue-search").value = "";
          page = 0;
          renderResults();
          $("catalogue-search").focus();
        }),
        button("Rename label", () => rename(record), "text-button")
      );
      card.append(actions);
      $("source-cards").append(card);
    });
  }
  function renderDetails() {
    $("catalogue-precision").hidden = !details;
    $("source-details").replaceChildren();
    if (!details) return;
    $("source-details").append(
      el(
        "p",
        "Bridge policy: metadata only; at most 2,000 entries, 500 entries per directory, depth 8 and 5 cooperative seconds; no filesystem crossing or content hashing. These are producer limits, not authentication of an imported file."
      )
    );
    catalogue.records.forEach((r) => {
      const s = r.snapshot,
        box = el("div", undefined, "source-detail");
      box.append(
        el("h3", r.label),
        el("p", `Original folder label: ${s.source.label}`),
        el("p", `Original claimed date (ISO): ${s.source.observed_at}`),
        el("p", `Source reference: ${s.source.scan_id}`),
        el("p", `Saved record key: ${r.id}`),
        el(
          "p",
          `Coverage: ${s.source.coverage}; ${s.entries.length} listed records including the selected-folder record.`
        ),
        el(
          "p",
          `Reported errors: ${s.gaps.error_count}. Stop reason: ${
            s.gaps.stop_reason || "none recorded"
          }.`
        )
      );
      s.gaps.exclusions.forEach((g) => box.append(el("p", `Exclusion: ${g.reason} (${g.count})`)));
      $("source-details").append(box);
    });
  }
  function renderResults() {
    const query = $("catalogue-search").value.toLocaleLowerCase(),
      filter = $("catalogue-filter").value,
      rows = [];
    catalogue.records.forEach((record) => {
      if (filter && record.id !== filter) return;
      record.snapshot.entries.forEach((entry) => {
        if (
          entry.path !== "." &&
          `${record.label}\n${record.snapshot.source.label}\n${entry.path}`
            .toLocaleLowerCase()
            .includes(query)
        )
          rows.push({ record, entry });
      });
    });
    const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
    page = Math.min(page, pages - 1);
    $("result-count").textContent = `${count(
      rows.length,
      "matching record"
    )}. Historical entries only; missing results do not prove absence.`;
    $("catalogue-results").replaceChildren();
    rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE).forEach(({ record, entry }) => {
      const row = el("label", undefined, "catalogue-entry"),
        input = el("input"),
        content = el("span", undefined, "entry-text");
      input.type = "checkbox";
      input.dataset.selectionKey = key({ source_id: record.id, path: entry.path });
      input.checked = selected(record.id, entry.path);
      input.disabled = !C.selectable(entry) || overlaps(record.id, entry.path);
      input.setAttribute("aria-label", `Select ${entry.path} from ${record.label}`);
      content.append(
        el("strong", entry.path),
        el("small", record.label),
        el(
          "small",
          `${entry.kind} · ${entry.status}${
            entry.kind === "file" ? ` · ${bytes(entry.logical_bytes)} logical` : ""
          }`,
          "entry-kind"
        ),
        observationDate(
          "small",
          "Historical source date: ",
          record.snapshot.source.observed_at,
          "muted"
        )
      );
      if (!C.selectable(entry))
        content.append(
          el(
            "small",
            "Unavailable for planning: only observed plain files and folders can be selected.",
            "muted"
          )
        );
      else if (overlaps(record.id, entry.path))
        content.append(
          el(
            "small",
            "Overlaps a selected folder or contained entry. Clear that selection first.",
            "muted"
          )
        );
      input.addEventListener("change", () => {
        requireMutable();
        advanceEpoch();
        generation++;
        if (input.checked) {
          if (selections.length >= 2000) {
            input.checked = false;
            status("Selection limit is 2,000 files or folders; existing choices are unchanged.");
            return;
          }
          selections = [...selections, { source_id: record.id, path: entry.path }];
        } else
          selections = selections.filter(
            (s) => key(s) !== key({ source_id: record.id, path: entry.path })
          );
        renderCards();
        renderSelection();
        renderResults();
        const replacement = [...$("catalogue-results").querySelectorAll("input")].find(
          (n) => n.dataset.selectionKey === input.dataset.selectionKey
        );
        replacement?.focus();
        status(
          embedded
            ? "Project selection is temporary and is not included in library saving. Manual-plan export is unavailable here."
            : "Project selection updated · export a manual plan to keep these choices"
        );
      });
      row.append(input, content);
      $("catalogue-results").append(row);
    });
    if (!rows.length)
      $("catalogue-results").append(
        el(
          "p",
          catalogue.records.every((r) => r.snapshot.entries.length === 1)
            ? "Only selected-folder records are listed. No file entries are recorded; partial snapshots may omit contents."
            : "No recorded matches. Try another name or saved location; live storage has not been checked.",
          "boundary-card"
        )
      );
    $("previous-results").disabled = page === 0;
    $("next-results").disabled = page + 1 >= pages;
    $("result-page").textContent = `Page ${page + 1} of ${pages} · up to ${PAGE_SIZE} per page`;
  }
  function renderSelection() {
    $("selection-count").textContent = `${selectionWords(selections)} selected`;
    $("prepare-plan").disabled = embedded || !selections.length;
    $("clear-selection").disabled = !selections.length;
    $("selected-scopes").replaceChildren();
    selections.forEach((s) => {
      const r = catalogue.records.find((x) => x.id === s.source_id);
      $("selected-scopes").append(el("p", `${r.label}: ${s.path}`, "selected-scope"));
    });
  }
  const comparisonLabels = {
    matching: "Matching listed details",
    different: "Different recorded details",
    left: "Only listed in Left",
    right: "Only listed in Right",
    uncertain: "Needs a closer look",
  };
  function renderComparison() {
    $("choose-comparison").disabled = catalogue.records.length < 2;
    $("comparison-hint").textContent =
      catalogue.records.length < 2
        ? "Add a second saved record to compare locations."
        : "You choose the pair. Similar labels never mean the same physical drive.";
    $("comparison-view").hidden = !comparison;
    if (!comparison) return;
    const result = X.compare(catalogue, comparison[0], comparison[1]);
    $("comparison-sources").replaceChildren();
    $("comparison-source-details").replaceChildren();
    [result.left, result.right].forEach((record, index) => {
      const side = index ? "Right" : "Left",
        card = el("article", undefined, "comparison-source"),
        source = record.source;
      card.append(
        el("p", side, "eyebrow"),
        el("h3", record.label),
        observationDate("p", "Snapshot date (claimed): ", source.observed_at, "small"),
        el("p", `Original folder: ${source.label}`, "small muted"),
        el(
          "p",
          source.coverage === "partial"
            ? "Partial picture · some entries may not be listed"
            : "Folder listing completed · live storage not checked",
          "small"
        )
      );
      $("comparison-sources").append(card);
      const details = el("div");
      details.append(
        el("h3", `${side}: ${record.label}`),
        el("p", `Saved record key: ${record.id}`),
        el("p", `Original claimed date (ISO): ${source.observed_at}`),
        el("p", `Source reference: ${source.scan_id}`),
        el(
          "p",
          `Reported errors: ${record.gaps.error_count}; stop reason: ${
            record.gaps.stop_reason || "none recorded"
          }.`
        )
      );
      record.gaps.exclusions.forEach((gap) =>
        details.append(el("p", `Exclusion: ${gap.reason} (${gap.count})`))
      );
      $("comparison-source-details").append(details);
    });
    $("comparison-counts").replaceChildren();
    ["left", "right", "different", "uncertain", "matching"].forEach((category) => {
      const box = el("div", undefined, "comparison-count");
      box.append(el("strong", result.counts[category]), el("span", comparisonLabels[category]));
      $("comparison-counts").append(box);
    });
    const filter = $("comparison-filter").value,
      rows = result.rows.filter((row) => !filter || row.category === filter),
      pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
    comparisonPage = Math.min(comparisonPage, pages - 1);
    $("comparison-result-count").textContent = `${count(
      rows.length,
      "recorded path"
    )} shown in this group out of ${
      result.rows.length
    } across the pair. Folder roots are shown above, not counted here.`;
    $("comparison-results").replaceChildren();
    rows.slice(comparisonPage * PAGE_SIZE, (comparisonPage + 1) * PAGE_SIZE).forEach((row) => {
      const box = el("article", undefined, "comparison-row"),
        cells = el("div", undefined, "comparison-cells");
      box.append(el("h3", row.path), el("p", comparisonLabels[row.category]));
      [row.left, row.right].forEach((entry, index) => {
        const cell = el("p"),
          side = index ? "Right" : "Left";
        cell.append(el("strong", side));
        cell.append(
          el(
            "span",
            !entry
              ? "Not listed in this snapshot"
              : `${entry.kind === "directory" ? "folder" : entry.kind} · ${
                  entry.status === "observed" ? "recorded" : entry.status
                }${entry.kind === "file" ? ` · ${bytes(entry.logical_bytes)} listed size` : ""}`
          )
        );
        cells.append(cell);
      });
      box.append(cells);
      if (row.left?.kind === "file" || row.right?.kind === "file") {
        const exact = el("details", undefined, "comparison-exact");
        exact.append(el("summary", "Exact recorded sizes"));
        [row.left, row.right].forEach((entry, index) =>
          exact.append(
            el(
              "p",
              `${index ? "Right" : "Left"}: ${
                entry?.kind === "file"
                  ? entry.logical_bytes + " logical bytes"
                  : "no file-size record"
              }`
            )
          )
        );
        box.append(exact);
      }
      if (row.category === "uncertain")
        box.append(
          el(
            "p",
            "An entry or its containing folder has an uncertain or unsupported record. Reconnect and inspect the source before relying on it.",
            "small muted"
          )
        );
      if (row.category === "matching")
        box.append(
          el(
            "p",
            row.left.kind === "directory"
              ? "Same listed folder kind; its contents may differ."
              : "Same listed path and size; file contents have not been compared.",
            "small muted"
          )
        );
      $("comparison-results").append(box);
    });
    if (!rows.length)
      $("comparison-results").append(
        el(
          "p",
          result.rows.length
            ? "No recorded paths in this group. This does not verify live storage."
            : "Only the selected-folder roots are recorded. There are no listed child paths to compare; gaps may hide contents.",
          "boundary-card"
        )
      );
    $("comparison-previous").disabled = comparisonPage === 0;
    $("comparison-next").disabled = comparisonPage + 1 >= pages;
    $("comparison-page").textContent = `Page ${
      comparisonPage + 1
    } of ${pages} · up to ${PAGE_SIZE} per page`;
  }
  $("choose-comparison").addEventListener("click", () => {
    const before = catalogue;
    let left, right;
    dialog(
      "Choose two recorded locations",
      "Compare their saved folder pictures. This does not identify drives or check file contents. Your project selection stays unchanged.",
      (body) => {
        ["Left", "Right"].forEach((side, index) => {
          const label = el("label", `${side} saved record`),
            select = el("select");
          select.id = `comparison-${side.toLowerCase()}-choice`;
          label.htmlFor = select.id;
          catalogue.records.forEach((record, n) =>
            select.append(new Option(`Record ${n + 1}: ${record.label}`, record.id))
          );
          select.value = comparison?.[index] || catalogue.records[index]?.id || "";
          body.append(label, select);
          if (index) right = select;
          else left = select;
        });
        body.append(
          el(
            "p",
            "Record numbers distinguish repeated labels. Left and Right do not mean older and newer.",
            "small muted"
          )
        );
      },
      () => {
        if (catalogue !== before) throw Error("Catalogue changed; choose the pair again.");
        X.compare(catalogue, left.value, right.value);
        comparison = [left.value, right.value];
        comparisonPage = 0;
        $("comparison-filter").value = "";
        renderComparison();
        status(
          "Recorded locations compared · reconnect the named sources to check live contents. Project selection unchanged."
        );
      },
      "Compare saved records"
    );
  });
  $("clear-comparison").addEventListener("click", () => {
    comparison = null;
    comparisonPage = 0;
    renderComparison();
    $("choose-comparison").focus();
    status("Comparison closed; saved records and project selection unchanged.");
  });
  $("comparison-filter").addEventListener("change", () => {
    comparisonPage = 0;
    renderComparison();
  });
  ["previous", "next"].forEach((direction) => {
    $(`comparison-${direction}`).addEventListener("click", () => {
      comparisonPage += direction === "next" ? 1 : -1;
      renderComparison();
      $("comparison-filter").focus();
    });
  });
  function render() {
    const loaded = catalogue.records.length > 0;
    $("empty-catalogue").hidden = loaded;
    $("loaded-catalogue").hidden = !loaded;
    $("save-catalogue").disabled = embedded || !loaded;
    $("catalogue-count").textContent = `${count(
      catalogue.records.length,
      "snapshot record"
    )} · physical drives unverified`;
    const prior = $("catalogue-filter").value;
    $("catalogue-filter").replaceChildren(new Option("All saved locations", ""));
    catalogue.records.forEach((r) => $("catalogue-filter").append(new Option(r.label, r.id)));
    if (catalogue.records.some((r) => r.id === prior)) $("catalogue-filter").value = prior;
    renderCards();
    renderSelection();
    renderResults();
    renderDetails();
    renderComparison();
  }
  function previewSnapshot(parsed, before, admit = () => {}) {
    let input;
    dialog(
      "Review this folder snapshot",
      "Imported history is unauthenticated. This adds a separate record; matching names or paths never merge locations.",
      (body) => {
        body.append(
          el("p", `Source label: ${parsed.source.label}`),
          observationDate("p", "Snapshot date (claimed): ", parsed.source.observed_at),
          el(
            "p",
            `${parsed.entries.length} entry records · ${parsed.source.coverage} within the selected folder`
          ),
          el(
            "p",
            "The file can contain private names and paths. No physical drive, current availability or backup is verified.",
            "small muted"
          )
        );
        input = field(body, "Your location label", parsed.source.label);
      },
      () => {
        if (catalogue !== before) throw Error("Catalogue changed; review the file again.");
        const next = C.add(catalogue, parsed, input.value);
        admit();
        changed(
          next,
          embedded
            ? nativeMode === "owned-storage"
              ? "Snapshot record added · save a new library version in the native window"
              : "Snapshot record added to this temporary native preview · nothing saved"
            : "Snapshot record added · save the catalogue to keep it"
        );
      },
      "Add separate snapshot record"
    );
    return generation;
  }
  // Data-only ingress exists only in the isolated embedded preview. The marker and
  // echoed IDs are not source authority; the native host owns its current view/session.
  function nativeEnvelope(version, session) {
    if (
      !embedded ||
      nativeInvalidated ||
      window.top !== window ||
      version !== BRIDGE_VERSION ||
      typeof session !== "string" ||
      !UUID.test(session) ||
      session !== nativeSession
    )
      throw Error("Native preview session is unavailable.");
  }
  if (embedded) {
    Object.defineProperty(window, "DiskCatalogueNativeBridge", {
      configurable: false,
      writable: false,
      value: Object.freeze({
        ...Object.fromEntries(
          persistenceOperations.map((name) => [
            name,
            (request) => nativePersistenceCall(name, request),
          ])
        ),
        initialise(version, session, mode) {
          if (
            arguments.length !== 3 ||
            !["temporary", "owned-storage"].includes(mode) ||
            !window.NativeLibraryProtocol ||
            nativeSession !== null ||
            nativeInvalidated ||
            window.top !== window ||
            version !== BRIDGE_VERSION ||
            typeof session !== "string" ||
            !UUID.test(session)
          )
            throw Error("Native preview session cannot initialise.");
          nativeSession = session;
          nativeMode = mode;
          nativeProtocol = makePersistenceProtocol();
          if (mode === "owned-storage") {
            $("native-preview-note").textContent =
              "Development preview · temporary test library storage. Native Save/Open keep catalogue versions here; real folders and manual-plan export remain unavailable.";
            $("empty-catalogue").querySelector("p").textContent =
              "Explore sample folders, then save and reopen a library version using the native window. No real source drive is connected.";
          }
          return Object.freeze({ version, session, mode, state: "ready" });
        },
        stage(version, session, delivery, text) {
          nativeEnvelope(version, session);
          requireMutable();
          if (typeof delivery !== "string" || !UUID.test(delivery) || nativeUsed.has(delivery))
            throw Error("Native preview delivery is invalid or already used.");
          if (nativePending || $("catalogue-dialog").open || action)
            throw Error("Finish the current preview or edit before another delivery.");
          // Bounded replay history is per view, never persisted or silently evicted.
          if (nativeUsed.size >= 128)
            throw Error("Native preview session is full. Recreate the view.");
          if (
            typeof text !== "string" ||
            !text.length ||
            text.length > C.LIMITS.snapshotBytes ||
            new TextEncoder().encode(text).length > C.LIMITS.snapshotBytes
          )
            throw Error("Native preview accepts at most 1 MiB of snapshot JSON.");
          const parsed = C.parse(text);
          if (parsed.schema_version !== C.VERSION)
            throw Error("Native delivery requires a folder snapshot.");
          const pending = { delivery, phase: "staged", generation: null };
          pending.generation = previewSnapshot(parsed, catalogue, () => {
            nativeEnvelope(version, session);
            if (
              nativePending !== pending ||
              pending.phase !== "staged" ||
              generation !== pending.generation
            )
              throw Error("Native preview was retired. Request it again.");
            pending.phase = "committed";
          });
          nativePending = pending;
          nativeRetired = null;
          nativeUsed.add(delivery);
          return Object.freeze({ version, session, delivery, state: "staged" });
        },
        retire(version, session, delivery) {
          nativeEnvelope(version, session);
          if (typeof delivery !== "string" || !UUID.test(delivery))
            throw Error("Invalid retirement.");
          if (!nativePending && nativeRetired?.delivery === delivery) return nativeRetired;
          if (!nativePending || nativePending.delivery !== delivery)
            throw Error("Unknown native preview delivery.");
          const pending = nativePending,
            matching =
              pending.phase === "staged" &&
              generation === pending.generation &&
              $("catalogue-dialog").open,
            outcome =
              pending.phase === "committed" ? "committed" : matching ? "cancelled" : "dismissed";
          pending.phase = "retired";
          nativePending = null;
          if (matching) close();
          nativeRetired = Object.freeze({ version, session, delivery, state: "retired", outcome });
          return nativeRetired;
        },
      }),
    });
    [
      "open-inventory",
      "save-catalogue",
      "inventory-file",
      "prepare-plan",
      "catalogue-saved",
    ].forEach((id) => {
      $(id).hidden = true;
      $(id).disabled = true;
    });
    document.querySelector(".skip-link").addEventListener("click", (event) => {
      event.preventDefault();
      $("catalogue").focus();
      $("catalogue").scrollIntoView({ block: "start" });
    });
    const note = el(
      "p",
      "Development native preview · temporary only. Open, Save and manual-plan export are unavailable in this preview.",
      "boundary-card"
    );
    note.id = "native-preview-note";
    $("catalogue").prepend(note);
    $("empty-catalogue").querySelector("p").textContent =
      "Waiting for an example snapshot from the native window. No user folder picker, drive connection or saved catalogue is available here.";
    document.querySelectorAll('a[href]:not([href^="#"])').forEach((link) => {
      link.closest("p").textContent =
        "Project selection is temporary. Manual-plan export is unavailable in this native test preview.";
    });
  }
  $("open-inventory").addEventListener("click", () => {
    if (embedded) return;
    generation++;
    if ($("catalogue-dialog").open) close();
    $("inventory-file").value = "";
    $("inventory-file").click();
  });
  $("inventory-file").addEventListener("cancel", () => {
    generation++;
    status("File selection cancelled; catalogue unchanged.");
  });
  $("inventory-file").addEventListener("change", async () => {
    if (embedded) return;
    const token = ++generation,
      before = catalogue,
      file = $("inventory-file").files?.[0];
    if (!file) {
      status("No file selected; catalogue unchanged.");
      return;
    }
    try {
      if (!Number.isSafeInteger(file.size) || file.size < 1 || file.size > C.LIMITS.bytes)
        throw Error("Choose one JSON file of at most 4 MiB.");
      const data = await file.arrayBuffer();
      if (token !== generation || catalogue !== before) return;
      if (data.byteLength !== file.size || data.byteLength > C.LIMITS.bytes)
        throw Error("File changed while reading; catalogue unchanged.");
      const text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(data),
        parsed = C.parse(text);
      if (parsed.schema_version === C.VERSION) {
        previewSnapshot(parsed, before);
      } else {
        dialog(
          "Replace with saved catalogue?",
          "This replaces the current catalogue and clears temporary project selections. Save the current catalogue first if needed. Imported history stays unauthenticated.",
          (body) => {
            body.append(
              el(
                "p",
                `${count(parsed.records.length, "saved location record")} · ${count(
                  parsed.records.reduce((n, r) => n + r.snapshot.entries.length, 0),
                  "entry"
                )}`
              )
            );
            parsed.records.forEach((r) =>
              body.append(
                el(
                  "p",
                  `${r.label} · ${C.formatObservationDate(r.snapshot.source.observed_at)} · ${
                    r.snapshot.source.coverage
                  }`
                )
              )
            );
          },
          () => {
            if (catalogue !== before) throw Error("Catalogue changed; review the file again.");
            catalogue = parsed;
            comparison = null;
            comparisonPage = 0;
            selections = [];
            page = 0;
            revision++;
            dirty = false;
            downloadedRevision = null;
            $("catalogue-saved").hidden = true;
            render();
            status("Saved catalogue reopened · current presence and protection remain unknown");
          },
          "Replace catalogue and open"
        );
      }
    } catch (error) {
      if (token === generation && catalogue === before)
        status(`Could not open file: ${error.message}`);
    }
  });
  $("save-catalogue").addEventListener("click", () => {
    if (embedded) return;
    const before = catalogue,
      rev = revision;
    dialog(
      "Save a private catalogue",
      "This plaintext JSON includes location labels, relative paths, sizes and historical source details. Store it privately. Project selections are saved separately as a manual plan.",
      (body) =>
        body.append(
          el("p", `${count(catalogue.records.length, "snapshot record")} will be included.`)
        ),
      () => {
        if (catalogue !== before || revision !== rev)
          throw Error("Catalogue changed; prepare the download again.");
        download(C.exportCatalogue(catalogue), "disk-organiser-catalogue.json");
        downloadedRevision = rev;
        $("catalogue-saved").hidden = false;
        status("Catalogue download requested; confirm it in Downloads, then acknowledge saving.");
      },
      "Download catalogue"
    );
  });
  $("catalogue-saved").addEventListener("click", () => {
    if (downloadedRevision === revision) {
      dirty = false;
      $("catalogue-saved").hidden = true;
      status("You confirmed saving this catalogue revision. Project selection remains temporary.");
    }
  });
  $("prepare-plan").addEventListener("click", () => {
    if (embedded) return;
    let input;
    const before = catalogue,
      chosen = selections.map((s) => ({ ...s }));
    dialog(
      "Create a manual project plan",
      "The selected historical paths become your manual planning records, with source notes preserved. Intended homes are unset and protection remains unknown.",
      (body) => {
        body.append(
          el(
            "p",
            `${selectionWords(chosen)} across ${count(
              new Set(chosen.map((s) => s.source_id)).size,
              "labelled location"
            )}. No file action will occur.`
          )
        );
        input = field(body, "Project name", "My selected project");
        body.append(
          el(
            "p",
            "Download the plan, then open it in the manual workspace. This does not change any existing plan.",
            "small muted"
          )
        );
      },
      () => {
        if (catalogue !== before || JSON.stringify(chosen) !== JSON.stringify(selections))
          throw Error("Selection changed; review the plan again.");
        const plan = C.buildPlan(catalogue, chosen, input.value, new Date().toISOString());
        download(M.exportPlan(plan), "disk-organiser-selected-plan.json");
        status(
          "Manual plan download requested. Confirm it in Downloads, then open it in the manual workspace."
        );
      },
      "Download manual plan"
    );
  });
  $("clear-selection").addEventListener("click", () => {
    requireMutable();
    advanceEpoch();
    generation++;
    selections = [];
    renderCards();
    renderSelection();
    renderResults();
    status("Temporary project selection cleared; catalogue unchanged.");
  });
  $("catalogue-search").addEventListener("input", () => {
    page = 0;
    renderResults();
  });
  $("catalogue-filter").addEventListener("change", () => {
    page = 0;
    renderResults();
  });
  $("previous-results").addEventListener("click", () => {
    page--;
    renderResults();
    $("catalogue-search").focus();
  });
  $("next-results").addEventListener("click", () => {
    page++;
    renderResults();
    $("catalogue-search").focus();
  });
  $("catalogue-details").addEventListener("click", () => {
    details = !details;
    $("catalogue-details").textContent = details ? "Hide details" : "Show details";
    $("catalogue-details").setAttribute("aria-pressed", String(details));
    renderDetails();
  });
  $("catalogue-close").addEventListener("click", close);
  $("catalogue-cancel").addEventListener("click", close);
  $("catalogue-dialog").addEventListener("cancel", (e) => {
    e.preventDefault();
    close();
  });
  $("catalogue-form").addEventListener("submit", (e) => {
    e.preventDefault();
    if (!action || $("catalogue-confirm").disabled) return;
    $("catalogue-confirm").disabled = true;
    try {
      action();
      close();
    } catch (error) {
      $("catalogue-error").textContent = error.message;
      $("catalogue-error").hidden = false;
      $("catalogue-confirm").disabled = false;
    }
  });
  window.addEventListener("pagehide", () => {
    nativeInvalidated = true;
    dismissNativePreview();
    generation++;
    if ($("catalogue-dialog").open) close();
    else action = null;
  });
  window.addEventListener("beforeunload", (e) => {
    if (dirty || selections.length) {
      e.preventDefault();
      e.returnValue = "";
    }
  });
  render();
})();
