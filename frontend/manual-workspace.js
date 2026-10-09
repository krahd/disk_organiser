/* Local manual planning UI. No filesystem paths are resolved and no service is contacted. */
(() => {
  "use strict";
  const M = window.ManualPlanningModel;
  const $ = (id) => document.getElementById(id);
  const el = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined && text !== null) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };
  const now = () => new Date().toISOString();
  const countLabel = (count, singular, plural = `${singular}s`) =>
    `${count} ${count === 1 ? singular : plural}`;
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const labelOf = (collection, id) =>
    state[collection].find((r) => r.id === id)?.label || "Not recorded";
  const find = (collection, id) => state[collection].find((r) => r.id === id);
  const steps = ["members", "arrange", "protect", "review"];
  const stepLabels = ["What belongs", "Where it lives", "How to protect it", "Review your plan"];
  const kindLabels = {
    file: "File",
    folder: "Folder",
    whole_drive: "Whole named drive",
    unspecified: "Type not specified",
    local_storage: "Local storage",
    network_storage: "Network storage",
    object_storage: "Object storage",
    managed_backup: "Backup service",
    sync_service: "Sync service",
    other: "Other",
    internal_drive: "Internal drive",
    external_drive: "External drive",
    cloud_location: "Cloud location",
  };
  const reportLabels = {
    reports_pass: "You reported that this check passed",
    reports_fail: "You reported that this check failed",
    inconclusive: "You reported an inconclusive result",
    not_applicable: "You reported this check not applicable",
  };
  let pendingImport = null;
  let state,
    selectedProject = null,
    selectedProtection = null,
    step = "members",
    details = false,
    dirty = false,
    downloadRevision = null,
    formAction = null,
    dialogOrigin = null,
    submitting = false,
    importSequence = 0;
  if (!M) {
    $("workspace").append(
      el(
        "p",
        "The planning model could not be loaded. Keep the workspace HTML, CSS and both JavaScript files together and reopen this page."
      )
    );
    return;
  }
  try {
    state = M.createEmptyPlan({
      title: "My storage plan",
      document_id: M.newId("plan"),
      now: now(),
    });
  } catch (error) {
    $("workspace").append(el("p", error.message));
    return;
  }
  const currentProject = () => find("projects", selectedProject);
  const members = () => state.items.filter((i) => currentProject()?.member_item_ids.includes(i.id));
  const currentProtection = () => find("protection_plans", selectedProtection);
  const projectProtections = () =>
    state.protection_plans.filter((p) => p.project_id === selectedProject);
  const status = (message) => {
    $("status").textContent = message;
  };
  const button = (text, action, cls = "secondary-button") => {
    const b = el("button", text, cls);
    b.type = "button";
    b.addEventListener("click", action);
    return b;
  };
  const small = (text) => el("p", text, "small muted");
  const titleRow = (title, action) => {
    const row = el("div", null, "section-title");
    row.append(el("h3", title));
    if (action) row.append(action);
    return row;
  };
  const icon = (cls) => {
    const n = el("span", null, cls);
    n.setAttribute("aria-hidden", "true");
    return n;
  };
  const tag = (text, cls = "") => el("span", text, `tag ${cls}`);
  const appendOptional = (obj, key, value) => {
    if (typeof value === "string" && value.trim()) obj[key] = value;
    else delete obj[key];
  };
  const recordEdit = (collection, record) => ({ type: "replaceRecord", collection, record });
  function mutate(action, message = "Plan updated · unsaved changes") {
    importSequence += 1;
    const next = M.reduce(state, { ...action, expected_revision: state.revision, now: now() });
    if (next === state) {
      status("No planning changes to save.");
      return state;
    }
    state = next;
    dirty = true;
    downloadRevision = null;
    $("acknowledge-save").hidden = true;
    render();
    status(message);
    return state;
  }
  function batch(edits, message) {
    return mutate({ type: "batch", edits }, message);
  }
  function setStep(next) {
    step = next;
    render();
    $("step-heading")?.focus();
  }
  function selectProject(id) {
    selectedProject = id;
    selectedProtection = projectProtections()[0]?.id || null;
    step = "members";
    render();
    $("project-title")?.focus();
  }
  function openDialog(title, intro, build, onSubmit, submitLabel = "Save change") {
    importSequence += 1;
    if (pendingImport) {
      M.cancelImport(pendingImport);
      pendingImport = null;
    }
    dialogOrigin = document.activeElement;
    formAction = onSubmit;
    submitting = false;
    $("dialog-title").textContent = title;
    $("dialog-intro").textContent = intro;
    $("dialog-body").replaceChildren();
    $("dialog-error").hidden = true;
    $("submit-dialog").textContent = submitLabel;
    $("submit-dialog").disabled = false;
    build($("dialog-body"));
    $("editor-dialog").showModal();
    const first = $("dialog-body").querySelector(
      "input:not([type=checkbox]), select, textarea, button"
    );
    (first || $("close-dialog")).focus();
  }
  function closeDialog() {
    importSequence += 1;
    $("editor-dialog").close();
    formAction = null;
    submitting = false;
    if (pendingImport) {
      M.cancelImport(pendingImport);
      pendingImport = null;
    }
    if (dialogOrigin?.isConnected) dialogOrigin.focus();
    else $("project-title")?.focus();
  }
  function field(parent, label, value = "", options = {}) {
    const wrap = el("div", null, "field"),
      id = `field-${++field.count}`,
      lab = el("label", label),
      input = el(options.multiline ? "textarea" : options.choices ? "select" : "input");
    input.id = id;
    lab.htmlFor = id;
    if (options.choices) for (const [v, t] of options.choices) input.append(new Option(t, v));
    else {
      if (!options.multiline) input.type = options.type || "text";
      input.maxLength = options.max || 240;
      if (options.type === "number") {
        input.min = options.min || 1;
        input.max = options.max;
        input.step = 1;
      }
    }
    input.value = value ?? "";
    input.required = !!options.required;
    if (options.required)
      input.addEventListener("input", () =>
        input.setCustomValidity(
          input.value.trim() ? "" : "Enter a name or description, not only spaces."
        )
      );
    input.autocomplete = "off";
    if (options.path) input.spellcheck = false;
    wrap.append(lab, input);
    if (options.help) {
      const h = small(options.help);
      h.id = `${id}-help`;
      input.setAttribute("aria-describedby", h.id);
      wrap.append(h);
    }
    parent.append(wrap);
    return input;
  }
  field.count = 0;
  function checkbox(parent, label, checked, help) {
    const row = el("label", null, "selection-row"),
      input = el("input");
    input.type = "checkbox";
    input.checked = checked;
    const text = el("span", label);
    if (help) text.append(small(help));
    row.append(input, text);
    parent.append(row);
    return input;
  }
  function optionBox(parent, summary) {
    const box = el("details");
    box.open = details;
    box.append(el("summary", summary));
    parent.append(box);
    return box;
  }
  function chooseRecords(parent, legend, records, selected, hint) {
    const fs = el("fieldset");
    fs.append(el("legend", legend));
    if (hint) fs.append(small(hint));
    const fields = records.map((r) => ({
      id: r.id,
      input: checkbox(
        fs,
        r.label + (r.archived ? " (archived record)" : ""),
        selected.includes(r.id)
      ),
    }));
    if (!records.length) fs.append(small("No records yet. You can save this as a draft."));
    parent.append(fs);
    return () => fields.filter((x) => x.input.checked).map((x) => x.id);
  }
  function driveChoices(includeNew = false) {
    return [
      ["", "Not recorded yet"],
      ...state.drives.map((d) => [d.id, d.label + (d.archived ? " (archived)" : "")]),
      ...(includeNew ? [["__new__", "+ Name a new location"]] : []),
    ];
  }
  function locationFields(parent, location, options = {}) {
    const drive = field(parent, options.label || "Named location", location?.drive_id, {
      choices: driveChoices(options.newDrive),
    });
    let newName, newWrap;
    if (options.newDrive) {
      newWrap = el("div");
      parent.append(newWrap);
      newName = field(newWrap, "Name the new location", "", {
        help: "For example, Laptop or Old photo drive. No hardware is detected.",
      });
      newWrap.hidden = true;
      drive.addEventListener("change", () => {
        newWrap.hidden = drive.value !== "__new__";
        newName.required = drive.value === "__new__";
      });
    }
    const path = field(parent, "Folder name or path (optional)", location?.path_text, {
      max: 2048,
      path: true,
      help: "A text note only. The app cannot open, inspect or follow it.",
    });
    return {
      drive,
      path,
      read: () => {
        const edits = [];
        let driveId = drive.value;
        if (driveId === "__new__") {
          if (!newName.value.trim()) throw new Error("Give the new location a name.");
          driveId = M.newId("drive");
          edits.push({
            type: "addRecord",
            collection: "drives",
            record: { id: driveId, label: newName.value },
          });
        }
        if (!driveId && path.value.trim())
          throw new Error("Choose or name a location before adding a path.");
        return {
          edits,
          location: driveId
            ? { drive_id: driveId, ...(path.value.trim() ? { path_text: path.value } : {}) }
            : undefined,
        };
      },
    };
  }
  function editProject(project) {
    let name, notes;
    openDialog(
      project ? "Edit this project" : "What do you want to look after?",
      "A project groups the folders or files that matter to you, even when they are on different drives.",
      (body) => {
        name = field(body, "Project name", project?.label, {
          required: true,
          help: "For example, Family photos, Studio work or Tax records.",
        });
        notes = field(optionBox(body, "Add a note (optional)"), "Project note", project?.notes, {
          multiline: true,
          max: 2000,
          help: "Do not enter passwords, recovery keys or tokens.",
        });
      },
      () => {
        const p = project ? clone(project) : { id: M.newId("project"), member_item_ids: [] };
        p.label = name.value;
        appendOptional(p, "notes", notes.value);
        if (project) mutate(recordEdit("projects", p));
        else {
          const protection = {
            id: M.newId("protect"),
            label: `Protection for ${p.label}`.slice(0, 240),
            project_id: p.id,
            target_ids: [],
            excluded_item_ids: [],
            policy: {},
          };
          selectedProject = p.id;
          selectedProtection = protection.id;
          step = "members";
          batch(
            [
              { type: "addRecord", collection: "projects", record: p },
              { type: "addRecord", collection: "protection_plans", record: protection },
            ],
            "Project added. Next, list a folder or file."
          );
        }
      },
      project ? "Save project" : "Create project"
    );
  }
  function editItem(item) {
    let name, kind, location, version, notes;
    openDialog(
      item ? "Edit your recorded item" : "What belongs to this project?",
      "Record a meaningful folder or file. Its contents, size and actual version remain unknown.",
      (body) => {
        name = field(body, "Folder or file name", item?.label, {
          required: true,
          help: "Use a name you recognise. An exact path is optional.",
        });
        kind = field(body, "What is it?", item?.kind || "folder", {
          choices: ["folder", "file", "whole_drive", "unspecified"].map((k) => [k, kindLabels[k]]),
        });
        location = locationFields(body, item?.location, {
          newDrive: true,
          label: "Where is it now, according to your records?",
        });
        const sync = () => {
          location.path.disabled = kind.value === "whole_drive";
          location.path.parentElement.hidden = kind.value === "whole_drive";
        };
        kind.addEventListener("change", sync);
        sync();
        const more = optionBox(body, "Version description and notes");
        version = field(more, "Your version description (optional)", item?.described_version, {
          help: "For example, final export. This does not authenticate a file version.",
        });
        notes = field(more, "Notes (optional)", item?.notes, { multiline: true, max: 2000 });
      },
      () => {
        const pathValue = location.path.value;
        if (kind.value === "whole_drive") location.path.value = "";
        let loc;
        try {
          loc = location.read();
        } finally {
          location.path.value = pathValue;
        }
        if (kind.value === "whole_drive" && !loc.location)
          throw new Error("A whole-drive scope needs a named location.");
        const record = item ? clone(item) : { id: M.newId("item") };
        record.label = name.value;
        record.kind = kind.value;
        if (loc.location) record.location = loc.location;
        else delete record.location;
        appendOptional(record, "described_version", version.value);
        appendOptional(record, "notes", notes.value);
        batch(
          [
            ...loc.edits,
            item
              ? recordEdit("items", record)
              : { type: "addItemToProject", project_id: selectedProject, item: record },
          ],
          item
            ? "Recorded item corrected · unsaved changes"
            : "Item added to the project · no files inspected"
        );
      },
      item ? "Save recorded item" : "Add to project"
    );
  }
  function editMembership() {
    let selection;
    openDialog(
      "Choose what belongs",
      "Removing an item from this project leaves its record and historical checklists intact.",
      (body) => {
        selection = chooseRecords(
          body,
          "Items in this document",
          state.items,
          currentProject().member_item_ids
        );
      },
      () => {
        const project = clone(currentProject());
        project.member_item_ids = selection();
        mutate(recordEdit("projects", project));
      },
      "Save project members"
    );
  }
  function editDrive(drive) {
    let name, kind, notes, purposes, availability, availabilityNote;
    openDialog(
      drive ? "Edit a named location" : "Name a drive or location",
      "This creates a record in your plan. It does not identify, connect to or inspect a device.",
      (body) => {
        name = field(body, "Location name", drive?.label, { required: true });
        kind = field(body, "Kind (optional)", drive?.kind || "", {
          choices: [
            ["", "Not recorded"],
            ...[
              "internal_drive",
              "external_drive",
              "network_storage",
              "cloud_location",
              "other",
              "unspecified",
            ].map((k) => [k, kindLabels[k]]),
          ],
        });
        const fs = el("fieldset");
        fs.append(el("legend", "How you intend to use it (optional)"));
        purposes = ["working", "archive", "backup", "other"].map((p) => ({
          value: p,
          input: checkbox(
            fs,
            { working: "Working", archive: "Archive", backup: "Intended backup", other: "Other" }[
              p
            ],
            drive?.purposes?.includes(p)
          ),
        }));
        body.append(fs);
        const more = optionBox(body, "Availability report and notes");
        availability = field(more, "Your availability report", "", {
          choices: [
            ["", drive?.availability_report ? "Keep the existing report" : "Not checked"],
            ["available", "I report it available now"],
            ["unavailable", "I report it unavailable now"],
            ["unsure", "I am unsure now"],
          ],
        });
        availabilityNote = field(more, "Availability note (optional)", "", { max: 1000 });
        if (drive?.availability_report)
          more.append(
            small(
              `Existing report: ${drive.availability_report.status} · ${drive.availability_report.recorded_at}`
            )
          );
        notes = field(more, "Notes (optional)", drive?.notes, { multiline: true, max: 2000 });
      },
      () => {
        const d = drive ? clone(drive) : { id: M.newId("drive") };
        d.label = name.value;
        appendOptional(d, "kind", kind.value);
        d.purposes = purposes.filter((p) => p.input.checked).map((p) => p.value);
        appendOptional(d, "notes", notes.value);
        if (availability.value)
          d.availability_report = {
            status: availability.value,
            recorded_at: now(),
            ...(availabilityNote.value.trim() ? { note: availabilityNote.value } : {}),
          };
        mutate(
          drive ? recordEdit("drives", d) : { type: "addRecord", collection: "drives", record: d }
        );
      },
      drive ? "Save location record" : "Add named location"
    );
  }
  function editHome() {
    let location;
    openDialog(
      "Where should this project live?",
      "This is an intended home. Recorded locations stay unchanged and no files are moved.",
      (body) => {
        location = locationFields(body, currentProject().intended_home, { newDrive: true });
      },
      () => {
        const result = location.read(),
          project = clone(currentProject());
        if (result.location) project.intended_home = result.location;
        else delete project.intended_home;
        batch(
          [...result.edits, recordEdit("projects", project)],
          result.location
            ? "Intended home updated · recorded locations unchanged"
            : "Intended home cleared · recorded locations unchanged"
        );
      },
      "Set intended home"
    );
  }
  function editTarget(target) {
    let name, kind, drive, provider, nickname, region, independence, notes;
    openDialog(
      target ? "Edit a planned target" : "Where would you like a backup copy?",
      "Name an intended destination. This does not create a backup or connect to a service.",
      (body) => {
        name = field(body, "Target name", target?.label, {
          required: true,
          help: "For example, Backup drive at home or Cloud backup to choose.",
        });
        kind = field(body, "Destination kind", target?.kind || "local_storage", {
          choices: [
            "local_storage",
            "network_storage",
            "managed_backup",
            "object_storage",
            "sync_service",
            "other",
            "unspecified",
          ].map((k) => [k, kindLabels[k]]),
        });
        drive = field(body, "Named storage location (optional)", target?.storage_drive_id, {
          choices: driveChoices(),
        });
        const more = optionBox(body, "Service and independence notes (optional)");
        provider = field(more, "Provider name", target?.provider_name, { max: 120 });
        nickname = field(more, "Non-secret account nickname", target?.account_nickname, {
          max: 120,
          help: "No passwords, keys, tokens or account credentials.",
        });
        region = field(more, "Region note", target?.region_note);
        independence = field(
          more,
          "How you intend to keep this separate",
          target?.independence_note,
          {
            multiline: true,
            max: 1000,
            help: "Different names do not establish independent copies.",
          }
        );
        notes = field(more, "Notes", target?.notes, { multiline: true, max: 2000 });
      },
      () => {
        const t = target ? clone(target) : { id: M.newId("target") };
        t.label = name.value;
        t.kind = kind.value;
        for (const [key, input] of [
          ["storage_drive_id", drive],
          ["provider_name", provider],
          ["account_nickname", nickname],
          ["region_note", region],
          ["independence_note", independence],
          ["notes", notes],
        ])
          appendOptional(t, key, input.value);
        if (target) mutate(recordEdit("backup_targets", t));
        else {
          const protection = clone(currentProtection());
          protection.target_ids.push(t.id);
          batch(
            [
              { type: "addRecord", collection: "backup_targets", record: t },
              recordEdit("protection_plans", protection),
            ],
            "Target planned · backup coverage remains unknown"
          );
        }
      },
      target ? "Save target record" : "Add planned target"
    );
  }
  function chooseTargets() {
    let selection;
    openDialog(
      "Choose planned backup targets",
      "These choices express your intent. No backup settings are applied.",
      (body) => {
        selection = chooseRecords(
          body,
          "Targets in this document",
          state.backup_targets,
          currentProtection().target_ids
        );
      },
      () => {
        const p = clone(currentProtection());
        p.target_ids = selection();
        mutate(recordEdit("protection_plans", p));
      },
      "Save target choices"
    );
  }
  function chooseScope() {
    let selection;
    const p = currentProtection();
    openDialog(
      "Choose the protection scope",
      "Unticked items are explicitly excluded in this plan. Excluding a listed file does not exclude it from a parent folder in a backup tool.",
      (body) => {
        selection = chooseRecords(
          body,
          "Include these named scopes",
          members(),
          members()
            .filter((i) => !p.excluded_item_ids.includes(i.id))
            .map((i) => i.id)
        );
        const historical = p.excluded_item_ids.filter(
          (id) => !currentProject().member_item_ids.includes(id)
        );
        if (historical.length)
          body.append(
            small(`${historical.length} historical exclusions for former members will be retained.`)
          );
      },
      () => {
        const record = clone(p),
          included = selection();
        record.excluded_item_ids = [
          ...p.excluded_item_ids.filter((id) => !currentProject().member_item_ids.includes(id)),
          ...members()
            .filter((i) => !included.includes(i.id))
            .map((i) => i.id),
        ];
        mutate(recordEdit("protection_plans", record));
      },
      "Save scope choices"
    );
  }
  function editPolicy() {
    let frequency, frequencyNote, retention, copies, age, review, checks, checkNote, name, notes;
    const protection = currentProtection(),
      policy = protection.policy;
    openDialog(
      "How would you like protection to work?",
      "These are preferences only. No backup schedule, task or notification is created.",
      (body) => {
        frequency = field(body, "Desired frequency", policy.desired_frequency, {
          choices: [
            ["", "Not decided"],
            ["daily", "Daily"],
            ["weekly", "Weekly"],
            ["monthly", "Monthly"],
            ["after_changes", "After changes"],
            ["before_drive_retirement", "Before retiring a drive"],
            ["custom", "Custom"],
          ],
        });
        retention = field(body, "Desired retention (optional)", policy.desired_retention, {
          max: 500,
          help: "For example, keep previous versions for one year.",
        });
        const more = optionBox(body, "More precise preferences");
        copies = field(
          more,
          "Desired independent copies (optional)",
          policy.desired_independent_copies,
          { type: "number", max: 10, help: "A preference. Independence is not established." }
        );
        age = field(
          more,
          "Maximum acceptable backup age, days (optional)",
          policy.max_acceptable_backup_age_days,
          { type: "number", max: 3650 }
        );
        frequencyNote = field(more, "Frequency note (optional)", policy.frequency_note);
        review = field(more, "Next review date (optional)", policy.next_review_on, {
          type: "date",
          max: 10,
        });
        const fs = el("fieldset");
        fs.append(el("legend", "Desired restore checks"));
        checks = [
          "file_readability",
          "byte_comparison",
          "metadata",
          "application_opening",
          "other",
        ].map((k) => ({
          kind: k,
          input: checkbox(
            fs,
            {
              file_readability: "Open sample files",
              byte_comparison: "Compare bytes",
              metadata: "Check metadata",
              application_opening: "Open in the required application",
              other: "Other",
            }[k],
            policy.desired_restore_checks?.includes(k)
          ),
        }));
        more.append(fs);
        checkNote = field(more, "Restore-check note (optional)", policy.restore_check_note, {
          max: 500,
        });
        name = field(more, "Protection plan name", protection.label, { required: true });
        notes = field(more, "Plan notes (optional)", protection.notes, {
          multiline: true,
          max: 2000,
        });
      },
      () => {
        const record = clone(protection),
          p = clone(policy);
        for (const [key, input] of [
          ["desired_frequency", frequency],
          ["frequency_note", frequencyNote],
          ["desired_retention", retention],
          ["next_review_on", review],
          ["restore_check_note", checkNote],
        ])
          appendOptional(p, key, input.value);
        for (const [key, input] of [
          ["desired_independent_copies", copies],
          ["max_acceptable_backup_age_days", age],
        ]) {
          if (input.value) p[key] = Number(input.value);
          else delete p[key];
        }
        p.desired_restore_checks = checks.filter((c) => c.input.checked).map((c) => c.kind);
        record.policy = p;
        record.label = name.value;
        appendOptional(record, "notes", notes.value);
        mutate(recordEdit("protection_plans", record));
      },
      "Save preferences"
    );
  }
  const defaultChecks = [
    ["locate_snapshot", "Locate the intended snapshot."],
    ["confirm_scope", "Check whether the chosen scopes are listed."],
    ["confirm_destination", "Choose a separate, empty destination in your restore tool."],
    ["confirm_capacity", "Check temporary space and destination capacity."],
    ["confirm_access", "Check that you can access the backup without recording secrets here."],
    ["file_readability", "Use your backup tool yourself, then open the restored samples."],
    ["metadata", "Check required dates and other metadata."],
    ["application_opening", "Check behaviour in the required application."],
  ];
  function editRestore(restore, asNew = false) {
    let name,
      target,
      selection,
      scope,
      scopeNote,
      snapshot,
      destination,
      capacity,
      access,
      checks,
      notes;
    const source = restore;
    openDialog(
      asNew
        ? "Prepare a new exercise from this one"
        : restore
        ? "Edit the restore-check plan"
        : "Prepare a restore check",
      "Describe what you will try in your own backup tool. You can save an incomplete checklist now.",
      (body) => {
        name = field(
          body,
          "Checklist name",
          source?.label || `Check ${currentProject().label}`.slice(0, 240),
          { required: true }
        );
        target = field(body, "Which planned target?", source?.target_id, {
          choices: [["", "Still to decide"], ...state.backup_targets.map((t) => [t.id, t.label])],
          help: "A target record is not evidence that a backup exists.",
        });
        const ownMembers = members(),
          historical = (source?.item_ids || [])
            .filter((id) => !ownMembers.some((i) => i.id === id))
            .map((id) => find("items", id));
        selection = chooseRecords(
          body,
          "Choose the named scopes to exercise",
          [...ownMembers, ...historical],
          source?.item_ids || [],
          "Folder descendants and exact versions are unknown."
        );
        scope = field(body, "What do you intend to try?", source?.intended_scope || "undecided", {
          choices: [
            ["undecided", "Still to decide"],
            ["sample", "A sample"],
            ["whole_planned_scope", "The whole selected scope (intent only)"],
          ],
        });
        scopeNote = field(
          body,
          "Describe the actual sample or scope",
          source?.exercise_scope_note,
          {
            multiline: true,
            max: 1000,
            help: "For example, three images selected from Recent photos; exact versions unknown. Required before recording results.",
          }
        );
        const more = optionBox(body, "Snapshot, destination and checklist details");
        snapshot = field(more, "Snapshot reference (optional)", source?.snapshot_reference_text, {
          max: 500,
          help: "Plain text, not a provider link or verified snapshot identity.",
        });
        destination = locationFields(more, source?.destination, {
          label: "Proposed separate restore destination (optional)",
        });
        capacity = field(more, "Capacity note (optional)", source?.capacity_note, { max: 1000 });
        access = field(more, "Access note (optional)", source?.access_note, {
          max: 1000,
          help: "Describe how to obtain access; never enter passwords, recovery keys or tokens.",
        });
        const fs = el("fieldset");
        fs.append(el("legend", "Checks to prepare"));
        checks = [];
        function addCheck(c) {
          const row = el("div", null, "draft-check");
          const include = checkbox(row, c.label || "New custom check", true);
          const editor = el("details");
          editor.open = !c.label;
          editor.append(el("summary", "Edit this check"));
          const description = field(editor, "Check description", c.label, {
            required: true,
            max: 500,
          });
          const checkKind = field(editor, "Check kind", c.kind, {
            choices: [
              "locate_snapshot",
              "confirm_scope",
              "confirm_destination",
              "confirm_capacity",
              "confirm_access",
              "file_readability",
              "byte_comparison",
              "metadata",
              "application_opening",
              "other",
            ].map((k) => [k, k.replaceAll("_", " ")]),
          });
          include.addEventListener("change", () => {
            description.required = include.checked;
            description.disabled = !include.checked;
            checkKind.disabled = !include.checked;
          });
          row.append(editor);
          fs.append(row);
          checks.push({ source: c, input: include, description, checkKind });
        }
        (source?.checks || defaultChecks.map(([kind, label]) => ({ kind, label }))).forEach(
          addCheck
        );
        fs.append(
          button(
            "+ Add a custom check",
            () => addCheck({ kind: "other", label: "" }),
            "text-button"
          )
        );
        more.append(fs);
        notes = field(more, "Exercise notes (optional)", source?.notes, {
          multiline: true,
          max: 2000,
        });
      },
      () => {
        const r =
          source && !asNew
            ? clone(source)
            : {
                id: M.newId("restore"),
                protection_plan_id: currentProtection().id,
                lifecycle: "draft",
              };
        r.label = name.value;
        r.intended_scope = scope.value;
        r.item_ids = selection();
        appendOptional(r, "target_id", target.value);
        appendOptional(r, "exercise_scope_note", scopeNote.value);
        appendOptional(r, "snapshot_reference_text", snapshot.value);
        appendOptional(r, "capacity_note", capacity.value);
        appendOptional(r, "access_note", access.value);
        appendOptional(r, "notes", notes.value);
        const loc = destination.read();
        if (loc.location) r.destination = loc.location;
        else delete r.destination;
        r.checks = checks
          .filter((c) => c.input.checked)
          .map((c) => ({
            ...clone(c.source),
            label: c.description.value,
            kind: c.checkKind.value,
            id: !source || asNew || !c.source.id ? M.newId("check") : c.source.id,
          }));
        if (asNew) {
          r.checks.forEach((c) => delete c.user_reports);
          delete r.reported_context;
        }
        mutate(
          source && !asNew
            ? recordEdit("restore_plans", r)
            : { type: "addRecord", collection: "restore_plans", record: r },
          "Restore checklist saved · no restore has been run"
        );
      },
      "Save checklist"
    );
  }
  function recordReport(restore, check) {
    if (
      !restore.target_id ||
      !restore.item_ids.length ||
      restore.intended_scope === "undecided" ||
      !restore.exercise_scope_note?.trim()
    ) {
      status("Describe the target, selected scopes and exact sample before recording a result.");
      editRestore(restore);
      return;
    }
    let result, notes, performed;
    openDialog(
      "Record what you did",
      "This adds your self-report. It does not verify recovery. The target, sample and check definitions become fixed after the first report.",
      (body) => {
        const summary = el("div", null, "modal-summary");
        summary.append(
          el(
            "p",
            `Target: ${
              restore.reported_context?.target.label || labelOf("backup_targets", restore.target_id)
            }`
          ),
          el("p", `Scope: ${restore.exercise_scope_note}`),
          el("p", `Check: ${check.label}`),
          small(
            "Exact versions and folder descendants remain unknown. A sample pass does not cover the whole project."
          )
        );
        body.append(summary);
        result = field(body, "Your result for this check", "", {
          required: true,
          choices: [
            ["", "Choose a result"],
            ["reports_pass", "I report a pass"],
            ["reports_fail", "I report a failure"],
            ["inconclusive", "Inconclusive"],
            ["not_applicable", "Not applicable"],
          ],
        });
        notes = field(body, "What happened? (optional)", "", { multiline: true, max: 2000 });
        performed = field(
          optionBox(body, "Record a different performed time (optional)"),
          "When you performed the check (with timezone)",
          "",
          {
            max: 40,
            help: "Example: 2026-10-09T10:30:00-03:00. Leave blank if unknown; the app still records when you enter this report.",
          }
        );
      },
      () => {
        const report = { id: M.newId("report"), result: result.value };
        appendOptional(report, "notes", notes.value);
        appendOptional(report, "performed_at", performed.value);
        mutate(
          { type: "appendReport", restore_plan_id: restore.id, check_id: check.id, report },
          "Your result was recorded. Backup coverage remains unknown."
        );
      },
      "Add my self-report"
    );
  }
  function archiveRecord(collection, record) {
    openDialog(
      record.archived ? "Return this record to active use?" : "Archive this record?",
      "The record stays in this document. References, project membership, planned targets and historical reports are retained.",
      (body) => {
        body.append(el("p", record.label, "modal-summary"));
      },
      () =>
        mutate({ type: "archiveRecord", collection, id: record.id, archived: !record.archived }),
      record.archived ? "Make record active" : "Archive record"
    );
  }
  function locationText(location) {
    return location
      ? `${labelOf("drives", location.drive_id)} · ${location.path_text || "Path not recorded"}`
      : "Location not recorded";
  }
  function driveStatus(drive) {
    const r = drive.availability_report;
    return r ? `You marked ${r.status} · ${r.recorded_at}` : "Availability not checked";
  }
  function renderDriveLibrary(parent) {
    const section = el("section", null, "drive-library");
    section.append(
      titleRow(
        "Your named locations",
        button("+ Name a location", () => editDrive())
      )
    );
    if (!state.drives.length)
      section.append(
        small(
          "Name your laptop, archive or backup drive when you need it. Exact hardware details are optional."
        )
      );
    const cards = el("div", null, "drive-cards");
    for (const d of state.drives) {
      const card = el("article", null, "drive-card"),
        h = el("h4");
      h.append(icon("drive-icon"), el("span", d.label));
      card.append(h);
      (d.purposes || []).forEach((p) =>
        card.append(
          tag(
            { working: "Working", archive: "Archive", backup: "Intended backup", other: "Other" }[p]
          )
        )
      );
      if (d.archived) card.append(tag("Archived record", "neutral"));
      card.append(
        el("p", driveStatus(d), "drive-state"),
        button("Edit location", () => editDrive(d), "text-button")
      );
      if (details)
        card.append(
          button(
            d.archived ? "Make active" : "Archive record",
            () => archiveRecord("drives", d),
            "text-button"
          )
        );
      cards.append(card);
    }
    section.append(cards);
    parent.append(section);
  }
  function renderRecorded(parent, compact = false) {
    const list = members(),
      grouped = new Map();
    for (const item of list) {
      const key = item.location?.drive_id || "";
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key).push(item);
    }
    if (!list.length) {
      const empty = el("div", null, "empty-card");
      empty.append(
        el("h3", "Start with one folder"),
        small("Use the name you know. You can record its location later."),
        button("Add folder or file", () => editItem(), "primary-button")
      );
      parent.append(empty);
    }
    for (const [driveId, items] of grouped) {
      const group = el("section", null, "drive-group"),
        heading = el("h4", null, "drive-heading");
      heading.append(
        icon("drive-icon"),
        el("span", driveId ? labelOf("drives", driveId) : "Location not recorded")
      );
      group.append(heading);
      if (driveId) group.append(el("p", driveStatus(find("drives", driveId)), "drive-state"));
      const cards = el("div", null, compact ? "" : "item-cards");
      for (const item of items) {
        const card = el("article", null, compact ? "source-folder" : "item-card"),
          content = el("div"),
          h = el(compact ? "strong" : "h4", item.label);
        if (!compact) h.prepend(icon("folder-icon"));
        content.append(
          h,
          small(
            `${kindLabels[item.kind]} · ${
              item.kind === "file" ? "version unknown" : "contents unknown"
            }`
          )
        );
        if (details || compact)
          content.append(small(item.location?.path_text || "Path not recorded"));
        if (item.archived) content.append(tag("Archived record", "neutral"));
        if (!compact)
          content.append(button("Edit recorded item", () => editItem(item), "text-button"));
        if (compact) card.append(icon("folder-icon"));
        card.append(content);
        cards.append(card);
      }
      group.append(cards);
      parent.append(group);
    }
  }
  function renderMembers(pane) {
    pane.append(
      titleRow(
        "Folders and files you listed",
        button("+ Add folder or file", () => editItem(), "primary-button")
      )
    );
    renderRecorded(pane);
    if (state.items.length)
      pane.append(button("Choose project members", editMembership, "text-button"));
    pane.append(
      small(
        "These are items you named, not a scanned file list. Grouping them here leaves their recorded locations unchanged."
      )
    );
    renderDriveLibrary(pane);
  }
  function renderArrange(pane) {
    const layout = el("div", null, "arrangement"),
      recorded = el("section", null, "recorded-lane"),
      intended = el("section", null, "intended-lane");
    for (const [parent, label, cls] of [
      [recorded, "Locations you recorded", "solid"],
      [intended, "Intended arrangement", "dashed"],
    ]) {
      const h = el("div", null, "lane-heading");
      h.append(icon(`line-key ${cls}`), el("h3", label));
      parent.append(h);
    }
    renderRecorded(recorded, true);
    const connector = el("div", null, "intention-connector");
    connector.setAttribute("aria-hidden", "true");
    connector.append(el("span", "Planned"), el("div", "→"));
    const home = el("div", null, "project-envelope planned");
    home.append(
      icon("folder-tab"),
      el("p", "PROPOSED PROJECT HOME", "eyebrow"),
      el("h3", currentProject().label),
      el(
        "p",
        currentProject().intended_home
          ? locationText(currentProject().intended_home)
          : "Still to choose",
        currentProject().intended_home ? "home-address" : "empty-home"
      )
    );
    const names = el("div", null, "mini-members");
    members().forEach((i) => names.append(el("div", i.label, "mini-member")));
    home.append(names);
    intended.append(
      home,
      small(
        "A planned home only. Exact destinations and application dependencies have not been checked."
      ),
      button(
        currentProject().intended_home ? "Change intended home" : "Set intended home",
        editHome,
        "primary-button"
      )
    );
    layout.append(recorded, connector, intended);
    pane.append(layout);
    const summary = el("details");
    summary.append(el("summary", "Read this arrangement as a list"));
    const ul = el("ul", null, "help-list");
    members().forEach((i) =>
      ul.append(el("li", `${i.label}: recorded at ${locationText(i.location)}`))
    );
    ul.append(
      el(
        "li",
        `Intended project home: ${
          currentProject().intended_home
            ? locationText(currentProject().intended_home)
            : "Not chosen"
        }`
      )
    );
    summary.append(ul);
    pane.append(summary);
  }
  function renderProtection(pane) {
    const choices = projectProtections();
    if (choices.length > 1) {
      const selection = field(pane, "Protection plan", selectedProtection, {
        choices: choices.map((p) => [p.id, p.label]),
      });
      selection.addEventListener("change", () => {
        selectedProtection = selection.value;
        render();
      });
    }
    const p = currentProtection();
    if (!p) {
      const b = button(
        "Start a protection plan",
        () => {
          const record = {
            id: M.newId("protect"),
            label: `Protection for ${currentProject().label}`.slice(0, 240),
            project_id: selectedProject,
            target_ids: [],
            excluded_item_ids: [],
            policy: {},
          };
          selectedProtection = record.id;
          mutate({ type: "addRecord", collection: "protection_plans", record });
        },
        "primary-button"
      );
      pane.append(small("No protection intent has been recorded for this project."), b);
      return;
    }
    pane.append(
      titleRow(
        "Planned backup targets",
        button("+ Add a target", () => editTarget(), "primary-button")
      )
    );
    if (!p.target_ids.length) {
      const empty = el("div", null, "empty-card");
      empty.append(
        el("h3", "Where would you like a backup copy?"),
        small("Start with a drive or a service name. You do not need account details.")
      );
      pane.append(empty);
    }
    const grid = el("div", null, "item-cards");
    for (const id of p.target_ids) {
      const t = find("backup_targets", id),
        card = el("article", null, "target-row");
      const h = el("h4", t.label);
      card.append(h, tag("Target planned"), small(kindLabels[t.kind]));
      if (t.archived) card.append(tag("Archived record", "neutral"));
      if (t.storage_drive_id) card.append(small(labelOf("drives", t.storage_drive_id)));
      if (t.kind === "sync_service")
        card.append(
          el("p", "Sync alone does not establish versioned backup or retention.", "inline-warning")
        );
      card.append(
        small("Backup coverage unknown"),
        button("Edit target record", () => editTarget(t), "text-button")
      );
      if (details && t.independence_note) card.append(small(t.independence_note));
      grid.append(card);
    }
    pane.append(grid);
    if (state.backup_targets.length)
      pane.append(button("Choose or remove planned targets", chooseTargets, "text-button"));
    pane.append(small("Different target names do not establish independent backup copies."));
    const scope = el("section", null, "check-card"),
      included = members().filter((i) => !p.excluded_item_ids.includes(i.id)),
      excluded = members().filter((i) => p.excluded_item_ids.includes(i.id));
    scope.append(
      titleRow(
        "What this protection plan includes",
        button("Choose included items", chooseScope, "text-button")
      ),
      small(
        `${countLabel(included.length, "item")} included · ${countLabel(
          excluded.length,
          "item"
        )} excluded by you`
      )
    );
    const list = el("ul", null, "plain-list");
    included.forEach((i) => list.append(el("li", i.label)));
    excluded.forEach((i) => list.append(el("li", `${i.label} · excluded by you`, "excluded")));
    scope.append(list);
    pane.append(scope);
    const preferences = el("section", null, "check-card");
    preferences.append(
      titleRow("Timing and retention", button("Edit preferences", editPolicy, "text-button")),
      small(
        `Desired frequency: ${p.policy.desired_frequency?.replaceAll("_", " ") || "Not decided"}`
      ),
      small(`Desired retention: ${p.policy.desired_retention || "Not decided"}`)
    );
    if (details) {
      preferences.append(
        small(
          `Desired independent copies: ${
            p.policy.desired_independent_copies ?? "Not decided"
          } · independence unknown`
        ),
        small(
          `Maximum acceptable age: ${p.policy.max_acceptable_backup_age_days ?? "Not decided"} days`
        ),
        small(`Next review: ${p.policy.next_review_on || "Not decided"} · no reminder scheduled`)
      );
    }
    pane.append(preferences);
    const heading = el("div", null, "restore-heading");
    heading.append(
      el("p", "CHECK RECOVERY, ONE STEP AT A TIME", "eyebrow"),
      titleRow(
        "Your restore-check plans",
        button("Prepare a restore checklist", () => editRestore())
      )
    );
    pane.append(
      heading,
      small("Use your own backup tool for the exercise. Record results here afterward.")
    );
    const restores = state.restore_plans.filter((r) => r.protection_plan_id === p.id);
    if (!restores.length) pane.append(small("No restore exercise has been described yet."));
    restores.forEach((r) => renderRestore(pane, r));
  }

  function contextChanged(restore) {
    const c = restore.reported_context;
    if (!c) return false;
    const p = find("protection_plans", restore.protection_plan_id),
      project = find("projects", p.project_id),
      t = find("backup_targets", restore.target_id);
    if (c.protection_plan.label !== p.label || c.protection_plan.project_label !== project.label)
      return true;
    for (const key of [
      "label",
      "kind",
      "storage_drive_id",
      "provider_name",
      "account_nickname",
      "region_note",
      "independence_note",
    ])
      if (c.target[key] !== t[key]) return true;
    if (c.destination && c.destination.drive_label !== labelOf("drives", c.destination.drive_id))
      return true;
    if (
      c.target.storage_drive_label !==
      (t.storage_drive_id ? labelOf("drives", t.storage_drive_id) : undefined)
    )
      return true;
    return c.items.some((saved) => {
      const item = find("items", saved.id);
      if (
        saved.label !== item.label ||
        saved.kind !== item.kind ||
        saved.described_version !== item.described_version
      )
        return true;
      if (!saved.location || !item.location) return !!saved.location !== !!item.location;
      return (
        saved.location.drive_id !== item.location.drive_id ||
        saved.location.path_text !== item.location.path_text ||
        saved.location.drive_label !== labelOf("drives", item.location.drive_id)
      );
    });
  }

  function renderRestore(parent, restore) {
    const reports = restore.checks.flatMap((c) => c.user_reports || []),
      context = restore.reported_context,
      card = el("article", null, "check-card");
    card.append(
      el("h4", restore.label),
      tag(
        reports.length ? `${countLabel(reports.length, "self-report")} recorded` : "Checklist only",
        "neutral"
      )
    );
    if (restore.archived) card.append(tag("Archived record", "neutral"));
    card.append(
      small(
        `Target${context ? " recorded at first report" : ""}: ${
          context?.target.label ||
          (restore.target_id ? labelOf("backup_targets", restore.target_id) : "Still to decide")
        }`
      ),
      small(
        `Selected${context ? " at first report" : ""}: ${
          context
            ? context.items.map((i) => i.label).join(", ")
            : restore.item_ids.map((id) => labelOf("items", id)).join(", ") || "No scope selected"
        }`
      ),
      small(`Sample: ${restore.exercise_scope_note || "Still to describe"}`),
      small("Exact versions and folder descendants remain unknown.")
    );
    const contextDrift = context && contextChanged(restore);
    if (contextDrift)
      card.append(
        el(
          "p",
          "Current descriptions differ from this exercise’s saved record. The target and scope shown here are the descriptions retained at its first report.",
          "inline-warning"
        )
      );
    const mismatch =
      restore.item_ids.some((id) => !currentProject().member_item_ids.includes(id)) ||
      (restore.target_id && !currentProtection().target_ids.includes(restore.target_id));
    if (mismatch)
      card.append(
        el(
          "p",
          "This historical exercise differs from the current project membership or chosen targets. Its original references are retained.",
          "inline-warning"
        )
      );
    const actions = el("div", null, "card-actions");
    actions.append(
      button(
        reports.length ? "Prepare a new exercise" : "Edit checklist",
        () => editRestore(restore, !!reports.length),
        "text-button"
      )
    );
    if (details)
      actions.append(
        button(
          restore.archived ? "Make active" : "Archive checklist",
          () => archiveRecord("restore_plans", restore),
          "text-button"
        )
      );
    card.append(actions);
    if (reports.length)
      card.append(
        small(
          "This exercise’s target, sample and check definitions are fixed. New attempts append reports; earlier failures remain."
        )
      );
    const checks = el("details");
    checks.open = details || reports.length > 0;
    checks.append(
      el("summary", `Checklist and result history · ${countLabel(restore.checks.length, "check")}`)
    );
    if (details && context) {
      checks.append(
        small(
          `Recorded project: ${context.protection_plan.project_label} · recorded plan: ${context.protection_plan.label}`
        ),
        small(
          `Context captured: ${context.captured_at} · imported snapshots and timestamps remain unverified claims.`
        )
      );
      context.items.forEach((i) =>
        checks.append(
          small(
            `Recorded scope: ${i.label} · ${
              i.location
                ? i.location.drive_label + " · " + (i.location.path_text || "Path not recorded")
                : "Location not recorded"
            } · described version: ${i.described_version || "Not recorded"}`
          )
        )
      );
      checks.append(
        small(
          `Recorded target kind: ${kindLabels[context.target.kind]} · storage: ${
            context.target.storage_drive_label || "Not recorded"
          } · provider: ${context.target.provider_name || "Not recorded"}`
        ),
        small(
          `Recorded account nickname: ${
            context.target.account_nickname || "Not recorded"
          } · region: ${context.target.region_note || "Not recorded"} · independence note: ${
            context.target.independence_note || "Not recorded"
          }`
        )
      );
      if (contextDrift)
        checks.append(
          small(
            `Current target name: ${labelOf(
              "backup_targets",
              restore.target_id
            )} · current selected names: ${restore.item_ids
              .map((id) => labelOf("items", id))
              .join(", ")}`
          )
        );
    }
    if (details) {
      checks.append(
        small(`Snapshot: ${restore.snapshot_reference_text || "Not recorded"}`),
        small(
          `Proposed destination${context ? " recorded at first report" : ""}: ${
            context?.destination
              ? context.destination.drive_label +
                " · " +
                (context.destination.path_text || "Path not recorded")
              : locationText(restore.destination)
          }`
        ),
        small(`Capacity: ${restore.capacity_note || "Unknown"}`),
        small(`Access: ${restore.access_note || "Not recorded"}`)
      );
    }
    restore.checks.forEach((check, index) => {
      const row = el("section", null, "check-row");
      row.append(el("h5", `${index + 1}. ${check.label}`));
      const list = el("ul", null, "report-list");
      (check.user_reports || []).forEach((report) => {
        const li = el("li", null, report.result === "reports_fail" ? "failed" : "");
        li.append(
          el("strong", reportLabels[report.result]),
          el("span", `Recorded ${report.recorded_at}`)
        );
        if (report.performed_at)
          li.append(el("span", `You gave performed time: ${report.performed_at}`));
        if (report.notes) li.append(el("span", report.notes));
        if (details) li.append(el("span", `Report key: ${report.id}`));
        list.append(li);
      });
      row.append(
        list,
        button("Record my result", () => recordReport(restore, check), "text-button")
      );
      checks.append(row);
    });
    card.append(checks);
    parent.append(card);
  }
  function renderReview(pane) {
    const p = currentProtection(),
      data = M.derive(state),
      checklistCount = state.restore_plans.filter((r) => r.protection_plan_id === p?.id).length,
      stats = el("div", null, "summary-stats");
    for (const [count, label] of [
      [members().length, members().length === 1 ? "item listed" : "items listed"],
      [
        p?.target_ids.length || 0,
        p?.target_ids.length === 1 ? "target planned" : "targets planned",
      ],
      [checklistCount, checklistCount === 1 ? "checklist" : "checklists"],
    ]) {
      const s = el("div", null, "summary-stat");
      s.append(el("strong", String(count)), el("span", label));
      stats.append(s);
    }
    pane.append(stats);
    const rows = [
      [
        "Your project",
        members()
          .map((i) => i.label)
          .join(", ") || "No items listed",
        "members",
      ],
      [
        "Intended home",
        currentProject().intended_home
          ? locationText(currentProject().intended_home)
          : "Not chosen",
        "arrange",
      ],
      [
        "Planned protection",
        p?.target_ids.map((id) => labelOf("backup_targets", id)).join(", ") || "No target chosen",
        "protect",
      ],
    ];
    rows.forEach(([title, text, target], i) => {
      const row = el("div", null, "review-row"),
        body = el("div");
      body.append(el("h3", title), el("p", text));
      row.append(
        el("span", `0${i + 1}`, "review-number"),
        body,
        button("Edit", () => setStep(target), "text-button")
      );
      pane.append(row);
    });
    const next = !members().length
      ? ["List one folder or file", "members"]
      : !p?.target_ids.length
      ? ["Choose a planned backup target", "protect"]
      : !currentProject().intended_home
      ? ["Choose an intended project home", "arrange"]
      : ["Describe a sample restore check in your own backup tool", "protect"];
    const decision = el("section", null, "next-decisions");
    decision.append(
      el("h3", "A useful next decision"),
      el("p", next[0]),
      button("Go to this step", () => setStep(next[1]), "text-button"),
      small("You can save now, even with decisions still open.")
    );
    pane.append(decision);
    const warnings = el("details");
    warnings.append(el("summary", `Planning gaps and cautions · ${data.warnings.length}`));
    const ul = el("ul", null, "warning-list");
    data.warnings.forEach((w) => ul.append(el("li", w.message)));
    warnings.append(
      ul,
      small("A completed form still does not establish actual backup or restore coverage.")
    );
    pane.append(warnings);
    const save = el("div", null, "save-preview"),
      desc = el("div");
    desc.append(
      el("h3", "Keep your plan privately"),
      small(
        "Save one plaintext plan file and deliberately reopen it later. It includes the names, paths and notes you entered."
      )
    );
    save.append(desc, button("Save plan", savePlan, "primary-button"));
    pane.append(save);
  }
  function renderDetails(parent) {
    const panel = el("section", null, "precision-panel");
    panel.append(
      el("p", "DETAILS / SAME PLAN", "eyebrow"),
      el("h2", "Precise records and evidence limits"),
      small(`Revision ${state.revision} · ${state.document_id}`),
      small(
        "These keys identify records only. Imported reports are unverified claims, including their timestamps."
      )
    );
    for (const i of members()) {
      const row = el("div", null, "detail-entry"),
        content = el("div");
      content.append(
        el("p", locationText(i.location), "path"),
        small(
          `Version description: ${i.described_version || "Not recorded"} · actual version unknown`
        ),
        small(`Key: ${i.id}`),
        button("Edit record", () => editItem(i), "text-button"),
        button(
          i.archived ? "Make active" : "Archive record",
          () => archiveRecord("items", i),
          "text-button"
        )
      );
      if (i.notes) content.append(small(i.notes));
      row.append(el("strong", i.label), content);
      panel.append(row);
    }
    if (state.backup_targets.length) {
      const library = el("section", null, "target-library");
      library.append(
        el("h3", "All target records in this document"),
        small(
          "Unchosen and archived targets remain available for correction and historical references."
        )
      );
      state.backup_targets.forEach((t) => {
        const row = el("div", null, "detail-entry"),
          actions = el("div");
        actions.append(
          small(`${kindLabels[t.kind]}${t.archived ? " · archived record" : ""}`),
          button("Edit target record", () => editTarget(t), "text-button"),
          button(
            t.archived ? "Make target active" : "Archive target record",
            () => archiveRecord("backup_targets", t),
            "text-button"
          )
        );
        row.append(el("strong", t.label), actions);
        library.append(row);
      });
      panel.append(library);
    }
    const text = el("details");
    text.append(el("summary", "Inspect the full plan JSON (read-only)"));
    const pre = el("pre");
    pre.tabIndex = 0;
    pre.setAttribute("aria-label", "Read-only complete plan JSON");
    pre.textContent = JSON.stringify(state, null, 2);
    text.append(pre);
    panel.append(text);
    parent.append(panel);
  }
  function render() {
    if (selectedProject && !currentProject()) selectedProject = state.projects[0]?.id || null;
    if (!selectedProject && state.projects.length) selectedProject = state.projects[0].id;
    if (!currentProtection() || currentProtection()?.project_id !== selectedProject)
      selectedProtection = projectProtections()[0]?.id || null;
    $("detail-toggle").setAttribute("aria-pressed", String(details));
    $("detail-toggle").textContent = details ? "Hide details" : "Show details";
    const root = $("workspace");
    root.replaceChildren();
    const overview = el("div", null, "overview-heading");
    overview.append(
      el("h2", state.title),
      button(
        "Rename plan",
        () => {
          let input;
          openDialog(
            "Name this plan file",
            "This is a title inside the saved document.",
            (body) => {
              input = field(body, "Plan title", state.title, { required: true });
            },
            () => mutate({ type: "setTitle", title: input.value }),
            "Save title"
          );
        },
        "text-button"
      )
    );
    root.append(overview);
    if (!state.projects.length) {
      const blank = el("section", null, "blank-workspace"),
        content = el("div");
      content.append(
        el("p", "YOUR DRIVES. YOUR PROJECTS. A CLEARER PLAN.", "eyebrow"),
        el("h1", "What do you want to look after?"),
        el(
          "p",
          "Start with one project. Name where its folders live, choose a home, then plan how you would like to protect it.",
          "muted"
        ),
        button("Name your first project", () => editProject(), "primary-button"),
        small("No scanning or account connection. Exact paths are optional.")
      );
      const art = el("div", null, "blank-illustration"),
        folder = el("div", null, "project-envelope planned");
      folder.append(
        icon("folder-tab"),
        el("h3", "Your project"),
        el("p", "Recorded locations → intended home → planned protection")
      );
      art.append(folder, small("A plan you can save and return to."));
      blank.append(content, art);
      root.append(blank);
      if (details) renderDetails(root);
      return;
    }
    const rail = el("nav", null, "project-rail");
    rail.setAttribute("aria-label", "Your projects");
    state.projects.forEach((project) => {
      const b = button("", () => selectProject(project.id), "project-card"),
        name = el("span");
      name.append(
        el("strong", project.label),
        el(
          "small",
          `${countLabel(project.member_item_ids.length, "item")} listed${
            project.archived ? " · archived" : ""
          }`
        )
      );
      b.append(icon("folder-icon"), name);
      if (project.id === selectedProject) b.setAttribute("aria-current", "true");
      rail.append(b);
    });
    rail.append(button("+ New project", () => editProject(), "project-card"));
    root.append(rail);
    const project = currentProject(),
      header = el("div", null, "project-header"),
      heading = el("div");
    const title = el("h1", project.label);
    title.id = "project-title";
    title.tabIndex = -1;
    heading.append(
      el("p", "YOUR PROJECT", "eyebrow"),
      title,
      el("p", "See the arrangement. Make one decision at a time.", "project-description")
    );
    const controls = el("div", null, "inline-actions");
    controls.append(button("Edit project", () => editProject(project), "text-button"));
    if (details)
      controls.append(
        button(
          project.archived ? "Make active" : "Archive project",
          () => archiveRecord("projects", project),
          "text-button"
        )
      );
    header.append(heading, controls);
    root.append(header);
    const nav = el("nav", null, "steps");
    nav.setAttribute("aria-label", "Planning steps");
    steps.forEach((s, i) => {
      const b = button("", () => setStep(s));
      b.append(el("span", String(i + 1), "step-number"), el("span", stepLabels[i]));
      if (s === step) b.setAttribute("aria-current", "step");
      nav.append(b);
    });
    root.append(nav);
    const evidence = el("div", null, "evidence-strip");
    evidence.append(
      el("strong", "Backup coverage unknown"),
      el("p", "These are manual records. No drive has been inspected.")
    );
    root.append(evidence);
    const pane = el("section", null, "step-pane"),
      sh = el("div", null, "step-heading");
    const texts = {
      members: [
        "What belongs to this project?",
        "List meaningful folders or files, wherever you keep them.",
      ],
      arrange: [
        "Where should this project live?",
        "Compare the locations you recorded with the home you intend.",
      ],
      protect: [
        "Where would you like backup copies?",
        "Plan destinations and prepare your own recovery checks.",
      ],
      review: [
        "A clear plan, with the gaps visible",
        "Keep an unfinished plan and return to the remaining decisions.",
      ],
    };
    const h = el("h2", texts[step][0]);
    h.id = "step-heading";
    h.tabIndex = -1;
    sh.append(
      el("p", `STEP ${steps.indexOf(step) + 1} OF 4`, "eyebrow"),
      h,
      el("p", texts[step][1])
    );
    pane.append(sh);
    ({
      members: renderMembers,
      arrange: renderArrange,
      protect: renderProtection,
      review: renderReview,
    })[step](pane);
    root.append(pane);
    if (details) renderDetails(root);
    const bottom = el("div", null, "bottom-actions");
    bottom.append(
      small(dirty ? "Unsaved plan changes in this tab" : "Manual planning information only")
    );
    if (step !== "review")
      bottom.append(
        button(
          `Next: ${stepLabels[steps.indexOf(step) + 1].toLowerCase()} →`,
          () => setStep(steps[steps.indexOf(step) + 1]),
          "primary-button"
        )
      );
    root.append(bottom);
  }
  function savePlan() {
    let serialised;
    try {
      serialised = M.exportPlan(state);
    } catch (error) {
      status(`The plan could not be exported: ${error.message}`);
      return;
    }
    openDialog(
      "Save your private plan",
      "The download contains your manually entered labels, paths, notes and self-reports. It is plaintext, not encrypted. Store it somewhere appropriate for this information.",
      (body) => {
        body.append(
          el(
            "p",
            `“${state.title}” · ${countLabel(state.projects.length, "project")} · revision ${
              state.revision
            }`,
            "modal-summary"
          ),
          small(
            "This requests a local browser download. It does not upload, sync or back up the files described in your plan."
          )
        );
      },
      () => {
        const blob = new Blob([serialised], { type: "application/json;charset=utf-8" });
        const url = URL.createObjectURL(blob),
          link = el("a");
        link.href = url;
        link.download = "disk-organiser-plan.json";
        document.body.append(link);
        try {
          link.click();
        } finally {
          link.remove();
          setTimeout(() => URL.revokeObjectURL(url), 1000);
        }
        downloadRevision = state.revision;
        $("acknowledge-save").hidden = false;
        status("Plan download requested; confirm it in Downloads.");
      },
      "Download plan file"
    );
  }
  function importText(text, sequence) {
    if (sequence !== importSequence || $("editor-dialog").open) return;
    let token;
    try {
      token = M.stageImport(text, state);
    } catch (error) {
      status(
        `Plan not opened. ${error.path ? `${error.path}: ` : ""}${
          error.message
        } Current plan unchanged.`
      );
      return;
    }
    const doc = token.document,
      warnings = M.validatePlan(doc).warnings;
    openDialog(
      "Review the plan before opening",
      "This file may contain private labels, paths, notes and self-reported results. Its claims are unverified. Opening it replaces the current in-memory plan.",
      (body) => {
        const summary = el("div", null, "modal-summary");
        summary.append(
          el("strong", doc.title),
          el(
            "p",
            `${countLabel(doc.projects.length, "project")} · ${countLabel(
              doc.drives.length,
              "named location"
            )} · ${countLabel(doc.items.length, "item")} listed · ${countLabel(
              doc.backup_targets.length,
              "target"
            )} · ${countLabel(doc.restore_plans.length, "checklist")}`
          )
        );
        body.append(summary);
        if (dirty)
          body.append(
            el(
              "p",
              "You have unsaved changes in the current plan. Cancel and save them first if you want to keep them.",
              "inline-warning"
            )
          );
        body.append(
          small(`${warnings.length} planning gaps or cautions. Backup coverage remains unknown.`)
        );
        const more = el("details");
        more.append(el("summary", "Review planning cautions"));
        const list = el("ul", null, "warning-list");
        warnings.forEach((w) => list.append(el("li", w.message)));
        more.append(list);
        body.append(more);
      },
      () => {
        state = M.replaceImport(state, token, { confirm: true });
        selectedProject = state.projects[0]?.id || null;
        selectedProtection = null;
        step = "members";
        dirty = false;
        downloadRevision = null;
        $("acknowledge-save").hidden = true;
        render();
        status(`Opened plan: ${state.title}. Manual records only; backup coverage unknown.`);
      },
      "Replace current plan and open"
    );
    pendingImport = token;
  }
  $("editor-form").addEventListener("submit", (event) => {
    event.preventDefault();
    if (submitting || !formAction) return;
    for (const input of $("editor-form").querySelectorAll("[required]")) {
      if (!input.disabled)
        input.setCustomValidity(
          input.value.trim() ? "" : "Enter a name or description, not only spaces."
        );
    }
    if (!$("editor-form").reportValidity()) return;
    submitting = true;
    $("submit-dialog").disabled = true;
    try {
      formAction();
      closeDialog();
    } catch (error) {
      $("dialog-error").textContent = `${error.path ? `${error.path}: ` : ""}${error.message}`;
      $("dialog-error").hidden = false;
      $("dialog-error").tabIndex = -1;
      $("dialog-error").focus();
      submitting = false;
      $("submit-dialog").disabled = false;
    }
  });
  $("close-dialog").addEventListener("click", closeDialog);
  $("cancel-dialog").addEventListener("click", closeDialog);
  $("editor-dialog").addEventListener("cancel", (event) => {
    event.preventDefault();
    closeDialog();
  });
  $("detail-toggle").addEventListener("click", () => {
    details = !details;
    render();
  });
  $("save-plan").addEventListener("click", savePlan);
  $("acknowledge-save").addEventListener("click", () => {
    if (downloadRevision === state.revision) {
      dirty = false;
      $("acknowledge-save").hidden = true;
      render();
      status("You confirmed saving this plan file. Keep it for reopening later.");
    }
  });
  $("open-plan").addEventListener("click", () => {
    importSequence += 1;
    $("open-file").value = "";
    $("open-file").click();
  });
  $("open-file").addEventListener("cancel", () => {
    importSequence += 1;
  });
  $("open-file").addEventListener("change", async () => {
    const file = $("open-file").files?.[0];
    if (!file) return;
    const sequence = ++importSequence;
    if (file.size > M.LIMITS.bytes) {
      status("Plan not opened: the file exceeds the 1 MiB limit. Current plan unchanged.");
      return;
    }
    try {
      const buffer = await file.arrayBuffer();
      const text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(buffer);
      importText(text, sequence);
    } catch (error) {
      if (sequence === importSequence)
        status(
          "Plan not opened: the selected file could not be read as valid UTF-8. Current plan unchanged."
        );
    }
  });
  window.addEventListener("beforeunload", (event) => {
    if (dirty) {
      event.preventDefault();
      event.returnValue = "";
    }
  });
  render();
})();
