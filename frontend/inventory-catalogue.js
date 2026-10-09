/* Local historical catalogue. Imported paths stay text, never filesystem capabilities. */
(() => {
  "use strict";
  const C = window.InventoryCatalogue,
    M = window.ManualPlanningModel;
  const $ = (id) => document.getElementById(id);
  const el = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };
  if (!C || !M) {
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
    origin = null;
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
    generation++;
    $("catalogue-dialog").close();
    action = null;
    if (origin?.isConnected) origin.focus();
  }
  function dialog(title, intro, build, submit, label) {
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
          "Location label updated · save the catalogue to keep it"
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
        status("Project selection updated · export a manual plan to keep these choices");
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
    $("prepare-plan").disabled = !selections.length;
    $("clear-selection").disabled = !selections.length;
    $("selected-scopes").replaceChildren();
    selections.forEach((s) => {
      const r = catalogue.records.find((x) => x.id === s.source_id);
      $("selected-scopes").append(el("p", `${r.label}: ${s.path}`, "selected-scope"));
    });
  }
  function render() {
    const loaded = catalogue.records.length > 0;
    $("empty-catalogue").hidden = loaded;
    $("loaded-catalogue").hidden = !loaded;
    $("save-catalogue").disabled = !loaded;
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
  }
  $("open-inventory").addEventListener("click", () => {
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
            changed(
              C.add(catalogue, parsed, input.value),
              "Snapshot record added · save the catalogue to keep it"
            );
          },
          "Add separate snapshot record"
        );
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
