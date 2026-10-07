(function () {
  "use strict";

  const GAPS = {
    physical_volume_identity_unestablished:
      "Physical drive identity: Unknown. Recorded roots do not establish physical volumes.",
    volume_name_semantics_unknown: "Case and Unicode naming rules: Unknown.",
    current_root_availability_unverified:
      "Current root availability: Unknown. Recorded status is not a connection check.",
    content_version_unverified:
      "Current content versions: Unknown. Recorded hashes are export assertions.",
    project_dependencies_unknown:
      "Application dependencies: Unknown. A usable relocation has not been established.",
    backup_evidence_unavailable:
      "Backup configuration and coverage: Unknown. Independent protection is not established.",
    restore_evidence_unavailable:
      "Restore scope and usability: Unknown. No restore has been verified.",
    destination_capacity_unknown: "Available destination capacity: Unknown.",
    observation_scope_incomplete:
      "The recorded scope is partial. Unobserved members are not confirmed deletions.",
    root_not_observed: "A selected root does not have an observed state in this snapshot.",
    member_not_observed:
      "A selected member has a stale, unavailable or unsupported recorded state.",
    unsupported_member_kind: "A selected member kind is unsupported for a qualified plan.",
    placeholder_content_unavailable:
      "Placeholder content is unavailable; nothing is downloaded or hydrated.",
    link_identity_unresolved:
      "Link identity is unresolved. Alias paths are not independent copies.",
    declared_project_path_collision: "Explicit intended project paths collide or overlap.",
    observed_target_path_overlap:
      "An intended path overlaps a recorded entry. This does not establish a safe no-op.",
    membership_and_destination_need_review: "The explicit membership and destination need review.",
    observation_stale: "The recorded scan start is outside the requested fixture-time window.",
    observation_future: "The recorded scan start is future-dated against the fixture clock.",
  };

  function createObservationDemo(doc, requestFetch) {
    const byId = (id) => doc.getElementById(id);
    const token = doc.querySelector('meta[name="demo-process-token"]').content;
    const fields = byId("observation-fields");
    const reviewButton = byId("observation-review-button");
    const dismissButton = byId("observation-dismiss");
    let reference = null;
    let generation = 0;
    let controller = null;
    let pending = false;
    const controls = new Map();

    function append(parent, tag, text, className) {
      const node = doc.createElement(tag);
      if (text !== undefined) node.textContent = text;
      if (className) node.className = className;
      parent.append(node);
      return node;
    }
    function status(text) {
      byId("observation-status").textContent = text;
    }
    function error(text) {
      byId("observation-error").textContent = text || "";
      byId("observation-error").hidden = !text;
    }
    function invalidate() {
      generation += 1;
      if (controller) controller.abort();
      controller = null;
      pending = false;
      reviewButton.disabled = !reference;
      return generation;
    }
    function safe(value) {
      return (
        value &&
        value.synthetic === true &&
        value.executable === false &&
        value.execution_authority === null &&
        value.undo_available === false &&
        value.source_safe_to_erase === false
      );
    }
    function assertEnvelope(value) {
      const draft = value && value.draft;
      if (
        !safe(value) ||
        value.read_only !== true ||
        value.live_backup_verified !== false ||
        value.live_restore_verified !== false ||
        value.scenario_id !== "aurora-observation" ||
        !Number.isSafeInteger(value.source_revision) ||
        value.source_revision < 1 ||
        !/^[a-f0-9]{64}$/.test(value.observation_digest) ||
        !/^[a-f0-9]{64}$/.test(value.reference_decision_digest) ||
        ![1, 2].includes(value.decision_revision) ||
        !safe(draft) ||
        draft.read_only !== true ||
        draft.schema_version !== "disk-administration-observation-draft/v1" ||
        draft.status !== "blocked_observation_draft" ||
        draft.observation_digest !== value.observation_digest ||
        !/^[a-f0-9]{64}$/.test(draft.decision_digest) ||
        !draft.protection ||
        draft.protection.live_backup_verified !== false ||
        draft.protection.live_restore_verified !== false ||
        draft.protection.configured_target_ids !== null ||
        draft.protection.independent_copy_count !== null ||
        draft.protection.project_restore_satisfied !== null ||
        !draft.capacity ||
        draft.capacity.known_logical_copy_bytes !== null ||
        draft.capacity.required_destination_bytes !== null ||
        draft.capacity.observed_free_bytes !== null ||
        draft.capacity.physical_allocation_prediction !== null ||
        draft.capacity.reclaimed_bytes !== 0 ||
        !Array.isArray(draft.members) ||
        !Array.isArray(draft.member_ids) ||
        draft.members.length < 1 ||
        draft.members.length > 8 ||
        draft.members.length !== draft.member_ids.length ||
        draft.members.some(
          (member, index) =>
            member.entry_id !== draft.member_ids[index] ||
            member.volume_id !== null ||
            member.content_version !== null ||
            member.dependency_coverage !== "unknown" ||
            member.source_retained !== true ||
            !["current_address_requires_identity", "proposed_address_requires_review"].includes(
              member.placement
            )
        )
      ) {
        throw new Error("Unexpected observation response. Reload this page.");
      }
    }
    function sameJSON(left, right) {
      if (left === right) return true;
      if (
        !left ||
        !right ||
        typeof left !== "object" ||
        typeof right !== "object" ||
        Array.isArray(left) !== Array.isArray(right)
      )
        return false;
      const keys = Object.keys(left);
      return (
        keys.length === Object.keys(right).length &&
        keys.every(
          (key) =>
            Object.prototype.hasOwnProperty.call(right, key) && sameJSON(left[key], right[key])
        )
      );
    }
    function assertProjection(value, base) {
      const decision = value.decision;
      const choices = new Map(base.choices.map((choice) => [choice.entry.id, choice.entry]));
      if (
        !decision ||
        decision.project_id !== base.decision.project_id ||
        decision.project_label !== base.decision.project_label ||
        decision.acknowledged !== true ||
        !Array.isArray(decision.member_paths) ||
        decision.member_paths.length !== value.draft.members.length ||
        new Set(value.draft.member_ids).size !== value.draft.member_ids.length ||
        new Set(decision.member_paths.map((member) => member.entry_id)).size !==
          decision.member_paths.length ||
        !base.roots.some((root) => root.id === decision.destination_root_id)
      ) {
        throw new Error("Unexpected observation decision. Reload this page.");
      }
      const intended = new Map(
        decision.member_paths.map((member) => [member.entry_id, member.project_path])
      );
      for (const key of [
        "observed_roots",
        "project",
        "evaluated_at",
        "max_observation_age_hours",
        "recorded_scan_freshness",
        "limitations",
      ]) {
        if (!sameJSON(value.draft[key], base.draft[key]))
          throw new Error("Unexpected observation provenance. Reload this page.");
      }
      const scope = {
        ...value.draft.observation_scope,
        selected_entry_count: base.draft.observation_scope.selected_entry_count,
      };
      if (
        !sameJSON(scope, base.draft.observation_scope) ||
        value.draft.observation_scope.selected_entry_count !== value.draft.members.length
      ) {
        throw new Error("Unexpected observation scope. Reload this page.");
      }
      // Integrity checks for displayed recorded facts only; all planning rules
      // remain in the Python adapter. No identity or capacity is inferred here.
      let recordedBytes = 0;
      const unknownSizes = [];
      for (const member of value.draft.members) {
        const observed = choices.get(member.entry_id);
        if (
          !observed ||
          !intended.has(member.entry_id) ||
          !sameJSON(member.observation, observed) ||
          member.placement !==
            (member.source.root_id === member.intended.root_id &&
            member.source.relative_path === member.intended.relative_path
              ? "current_address_requires_identity"
              : "proposed_address_requires_review") ||
          member.source.root_id !== observed.root_id ||
          member.source.relative_path !== observed.relative_path ||
          member.project_path !== intended.get(member.entry_id) ||
          member.intended.root_id !== decision.destination_root_id ||
          member.intended.relative_path !==
            `${decision.destination_folder}/${intended.get(member.entry_id)}`
        ) {
          throw new Error("Unexpected observation paths. Reload this page.");
        }
        if (observed.logical_bytes === null) unknownSizes.push(member.entry_id);
        else recordedBytes += observed.logical_bytes;
      }
      if (
        value.draft.capacity.known_recorded_path_logical_bytes !== recordedBytes ||
        !sameJSON([...value.draft.capacity.unknown_size_member_ids].sort(), unknownSizes.sort())
      ) {
        throw new Error("Unexpected recorded size summary. Reload this page.");
      }
    }
    async function fetchJSON(path, options, signal) {
      const response = await requestFetch(path, {
        ...options,
        signal,
        cache: "no-store",
        credentials: "omit",
        redirect: "error",
        headers: { "X-Demo-Token": token, ...(options.headers || {}) },
      });
      const value = await response.json();
      if (!response.ok) {
        throw new Error(
          response.status === 409
            ? "The observation reference changed. Reload this page before reviewing."
            : response.status === 403
            ? "Reload this page to renew the demo session."
            : value.error || "Observation request failed. Retry or reload the reference."
        );
      }
      assertEnvelope(value);
      return value;
    }
    function bytes(value) {
      return value === null ? "Unknown" : `${value.toLocaleString("en-GB")} bytes`;
    }
    function rootName(id) {
      return reference.roots.find((root) => root.id === id)?.path || id;
    }
    function memberName(id) {
      const record = reference.recorded_paths.find((entry) => entry.entry_id === id);
      if (!record) return id;
      const outside = reference.choices.some((choice) => choice.entry.id === id)
        ? ""
        : " (outside selectable membership)";
      return `${rootName(record.root_id)} / ${record.relative_path}${outside}`;
    }
    function markMembers() {
      const included = new Set(reference.decision.member_paths.map((member) => member.entry_id));
      for (const [id, control] of controls) {
        control.path.disabled = !control.check.checked;
        control.state.textContent = control.check.checked
          ? included.has(id)
            ? "Included"
            : "Added"
          : included.has(id)
          ? "Removed"
          : "Not included";
      }
    }
    function rootFacts() {
      const root = reference.roots.find((item) => item.id === byId("observation-root").value);
      byId(
        "observation-root-facts"
      ).textContent = `${root.path}. Recorded state: ${root.status}. Physical drive, current availability, naming rules and free space: Unknown.`;
    }
    function setDecision(decision) {
      const selected = new Map(
        decision.member_paths.map((member) => [member.entry_id, member.project_path])
      );
      for (const choice of reference.choices) {
        const control = controls.get(choice.entry.id);
        control.check.checked = selected.has(choice.entry.id);
        control.path.value = selected.get(choice.entry.id) || choice.default_project_path;
      }
      byId("observation-root").value = decision.destination_root_id;
      byId("observation-folder").value = decision.destination_folder;
      markMembers();
      rootFacts();
    }
    function section(parent, title, intro) {
      const node = append(parent, "section", undefined, "review-section");
      append(node, "h3", title);
      if (intro) append(node, "p", intro);
      return node;
    }
    function renderDraft(value, isReference) {
      const draft = value.draft;
      const content = doc.createDocumentFragment();
      byId("observation-caption").textContent = isReference
        ? "Reference observation draft. Edits change intent; they cannot supply the missing evidence."
        : "Reviewed intent. Any edit invalidates this draft. It is still incomplete and non-executable.";
      const summary = append(content, "div", undefined, "attention");
      append(summary, "h3", "Evidence is still needed before a qualified plan");
      append(
        summary,
        "p",
        "These observations do not establish a copy, a no-op, a backup or a restore. No files have changed."
      );
      append(
        content,
        "p",
        `Selected: ${draft.member_ids.length}. Decision revision ${value.decision_revision}, rebuilt from source revision ${value.source_revision}.`,
        "provenance"
      );
      const layout = section(
        content,
        "Recorded paths → intended paths",
        "Intended paths express your decision only. Sources are retained; nothing is copied, moved or deleted."
      );
      for (const member of draft.members) {
        const row = append(layout, "div", undefined, "comparison");
        const source = append(row, "div");
        append(source, "strong", "RECORDED · root scope");
        append(source, "div", rootName(member.source.root_id), "path");
        append(source, "div", member.source.relative_path, "path");
        append(
          source,
          "p",
          `Recorded state: ${member.observation.status}. Recorded hash: ${member.observation.hash.status}. Current content version: Unknown.`,
          "evidence-line"
        );
        const target = append(row, "div");
        append(target, "strong", "INTENDED · identity unresolved");
        append(target, "div", rootName(member.intended.root_id), "path");
        append(target, "div", member.intended.relative_path, "path");
        append(
          target,
          "p",
          member.placement === "current_address_requires_identity"
            ? "Same recorded address; physical identity is still Unknown. No safe no-op is established."
            : "Different intended address; no copy or relocation is established.",
          "evidence-line"
        );
      }
      const capacity = section(
        content,
        "Capacity remains unverified",
        "Recorded logical sizes count selected paths, including aliases and stale records. They are not current physical space or required copy space."
      );
      const metrics = append(capacity, "dl", undefined, "metrics");
      for (const [label, value] of [
        ["Known recorded size by selected path", draft.capacity.known_recorded_path_logical_bytes],
        ["Required copy space", draft.capacity.required_destination_bytes],
        ["Available destination space", draft.capacity.observed_free_bytes],
      ]) {
        const metric = append(metrics, "div", undefined, "metric");
        append(metric, "dt", label);
        append(metric, "dd", bytes(value));
      }
      append(
        capacity,
        "p",
        `Unknown recorded sizes: ${
          draft.capacity.unknown_size_member_ids.map(memberName).join(", ") ||
          "none among selected records"
        }. Logical copy bytes: Unknown. Physical allocation: Unknown. Reclaimed: 0 bytes.`
      );
      const protection = section(
        content,
        "Identity, dependencies and protection",
        "Missing evidence stays Unknown. Matching hashes or multiple roots do not establish independent backups."
      );
      const facts = append(protection, "dl", undefined, "metrics");
      for (const label of [
        "Physical drive identity",
        "Current content versions",
        "Application dependencies",
        "Backup targets and coverage",
        "Independent copy count",
        "Restore scope and usability",
      ]) {
        const item = append(facts, "div", undefined, "metric");
        append(item, "dt", label);
        append(item, "dd", "Unknown");
      }
      append(
        protection,
        "p",
        "Live backup verified: false. Live restore verified: false. No provider is connected."
      );
      const gaps = section(
        content,
        "Evidence gaps and recorded conflicts",
        `${draft.blockers.length} issues remain visible. Changing the layout cannot clear missing identity or protection evidence.`
      );
      const list = append(gaps, "ul");
      for (const issue of draft.blockers) {
        const scope =
          issue.member_ids.length === draft.member_ids.length &&
          new Set(issue.member_ids).size === draft.member_ids.length &&
          issue.member_ids.every((id) => draft.member_ids.includes(id))
            ? "All selected members."
            : issue.member_ids.length
            ? `Members: ${issue.member_ids.map(memberName).join(", ")}.`
            : "";
        append(
          list,
          "li",
          `${GAPS[issue.code] || `Review issue: ${issue.code.replaceAll("_", " ")}.`} ${scope}`
        );
      }
      const limits = append(content, "details");
      append(limits, "summary", "Source scope, limitations and review identity");
      append(
        limits,
        "p",
        `Recorded scan: ${draft.observation_scope.scan.id}. Status: ${
          draft.observation_scope.scan.status
        }. Snapshot freshness: ${draft.recorded_scan_freshness.replaceAll(
          "_",
          " "
        )} against the fixed fixture clock, not today.`
      );
      append(
        limits,
        "p",
        `Observation records: ${draft.observation_scope.entry_count}. Recorded errors: ${draft.observation_scope.scan.errors.length}. Exclusions: ${draft.observation_scope.scan.exclusions.length}. A partial scope does not prove deletion or absence.`
      );
      const notes = append(limits, "ul");
      for (const note of draft.limitations) append(notes, "li", note);
      append(
        limits,
        "p",
        `Source revision ${value.source_revision}. Observation digest ${value.observation_digest}. Decision digest ${draft.decision_digest}. Contract ${draft.schema_version}.`,
        "provenance"
      );
      append(
        limits,
        "p",
        "Execution: false. Authority: null. Undo: false. Source safe to erase: false. Digests do not authenticate observations or authorise operations."
      );
      byId("observation-review-content").replaceChildren(content);
    }
    function renderReference() {
      byId(
        "observation-clock"
      ).textContent = `Fabricated observations as of ${reference.fixture_as_of}. Evaluation uses this fixed fixture clock, not today. Source revision ${reference.source_revision}.`;
      byId(
        "observation-scope"
      ).textContent = `${reference.choices.length} fixed selectable examples from ${reference.source_entry_count} observation records across ${reference.roots.length} recorded roots. Other records remain outside this form. Project membership is explicit, not inferred from folder roles or hashes.`;
      controls.clear();
      const members = byId("observation-members");
      members.replaceChildren();
      for (const [index, choice] of reference.choices.entries()) {
        const entry = choice.entry;
        const card = append(members, "article", undefined, "current-layout");
        const row = append(card, "div", undefined, "member-row");
        const check = append(row, "input");
        check.type = "checkbox";
        check.id = `observation-member-${index}`;
        const label = append(row, "label", entry.relative_path);
        label.htmlFor = check.id;
        append(label, "span", rootName(entry.root_id), "member-details");
        append(
          label,
          "span",
          `${entry.kind} · recorded ${entry.status} · ${bytes(entry.logical_bytes)}`,
          "member-details"
        );
        append(
          label,
          "span",
          `Recorded hash: ${entry.hash.status}. Current version and dependencies: Unknown.`,
          "member-details"
        );
        const state = append(row, "span", "", "member-state");
        const pathLabel = append(card, "label", "Intended project-relative path");
        const path = append(card, "input");
        path.type = "text";
        path.id = `observation-path-${index}`;
        path.required = true;
        path.maxLength = 240;
        path.autocomplete = "off";
        path.spellcheck = false;
        pathLabel.htmlFor = path.id;
        controls.set(entry.id, { check, path, state });
      }
      const select = byId("observation-root");
      select.replaceChildren();
      const roots = byId("observation-roots");
      roots.replaceChildren();
      for (const root of reference.roots) {
        const option = append(select, "option", `${root.path} · recorded ${root.status}`);
        option.value = root.id;
        append(roots, "p", root.path, "path");
        append(
          roots,
          "p",
          `Recorded state: ${root.status}. Current availability and physical identity: Unknown.`,
          "evidence-line"
        );
      }
      setDecision(reference.decision);
      renderDraft(reference, true);
      fields.disabled = false;
      reviewButton.disabled = false;
      dismissButton.disabled = false;
    }
    function changed() {
      if (!reference) return;
      invalidate();
      markMembers();
      rootFacts();
      error("");
      byId("observation-review-content").replaceChildren();
      byId("observation-caption").textContent =
        "Intent changed. Review again to see the current draft and evidence gaps.";
      status("Intent changed. The previous draft no longer applies.");
    }
    async function loadReference() {
      const current = invalidate();
      reference = null;
      controls.clear();
      fields.disabled = true;
      reviewButton.disabled = true;
      dismissButton.disabled = true;
      for (const id of [
        "observation-members",
        "observation-roots",
        "observation-root",
        "observation-review-content",
      ])
        byId(id).replaceChildren();
      for (const id of ["observation-clock", "observation-scope", "observation-root-facts"])
        byId(id).textContent = "";
      byId("observation-folder").value = "";
      byId("observation-caption").textContent =
        "Loading the fixed Aurora source and reference decision.";
      status("Loading Aurora observations…");
      error("");
      controller = new AbortController();
      try {
        const value = await fetchJSON("/api/observation/reference", {}, controller.signal);
        if (current !== generation) return;
        if (
          !Array.isArray(value.choices) ||
          value.choices.length !== 8 ||
          new Set(value.choices.map((choice) => choice.entry.id)).size !== 8 ||
          !Array.isArray(value.roots) ||
          value.roots.length !== 2 ||
          new Set(value.roots.map((root) => root.id)).size !== 2 ||
          value.decision_revision !== 1 ||
          value.draft.decision_digest !== value.reference_decision_digest ||
          value.fixture_as_of !== value.draft.evaluated_at ||
          !sameJSON(
            [...value.roots].sort((a, b) => a.id.localeCompare(b.id)),
            value.draft.observed_roots
          ) ||
          value.source_entry_count !== 32 ||
          !Array.isArray(value.recorded_paths) ||
          value.recorded_paths.length !== value.source_entry_count ||
          new Set(value.recorded_paths.map((entry) => entry.entry_id)).size !==
            value.source_entry_count ||
          value.recorded_paths.some(
            (entry) =>
              typeof entry.relative_path !== "string" ||
              !value.roots.some((root) => root.id === entry.root_id)
          ) ||
          value.choices.some(
            (choice) =>
              !value.recorded_paths.some(
                (entry) =>
                  entry.entry_id === choice.entry.id &&
                  entry.root_id === choice.entry.root_id &&
                  entry.relative_path === choice.entry.relative_path
              )
          )
        ) {
          throw new Error("Unexpected packaged observation reference. Reload this page.");
        }
        assertProjection(value, value);
        reference = value;
        renderReference();
        status(
          "Aurora reference loaded. Review explicit intent; identity and protection remain Unknown."
        );
      } catch (failure) {
        if (current !== generation) return;
        reference = null;
        controls.clear();
        for (const id of [
          "observation-members",
          "observation-roots",
          "observation-root",
          "observation-review-content",
        ])
          byId(id).replaceChildren();
        fields.disabled = true;
        reviewButton.disabled = true;
        dismissButton.disabled = true;
        error(failure.message || "Reference unavailable.");
        status("Reference unavailable. Reload Aurora reference to retry.");
      } finally {
        if (current === generation) controller = null;
      }
    }
    async function submit(event) {
      event.preventDefault();
      if (!reference || pending) return;
      const current = invalidate();
      const body = {
        expected_source_revision: reference.source_revision,
        expected_observation_digest: reference.observation_digest,
        expected_reference_decision_digest: reference.reference_decision_digest,
        member_paths: Array.from(controls, ([entry_id, control]) =>
          control.check.checked ? { entry_id, project_path: control.path.value } : null
        ).filter(Boolean),
        destination_root_id: byId("observation-root").value,
        destination_folder: byId("observation-folder").value,
      };
      pending = true;
      reviewButton.disabled = true;
      error("");
      byId("observation-review-content").replaceChildren();
      byId("observation-caption").textContent =
        "Reviewing this intent against the immutable synthetic observations.";
      status("Reviewing observation draft… You can still edit or dismiss it.");
      controller = new AbortController();
      try {
        const value = await fetchJSON(
          "/api/observation/review",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          },
          controller.signal
        );
        if (current !== generation) return;
        const decision = value.decision;
        if (
          value.source_revision !== reference.source_revision ||
          value.observation_digest !== reference.observation_digest ||
          value.reference_decision_digest !== reference.reference_decision_digest ||
          value.decision_revision !== 2 ||
          decision.project_id !== reference.decision.project_id ||
          decision.project_label !== reference.decision.project_label ||
          decision.acknowledged !== true ||
          decision.destination_root_id !== body.destination_root_id ||
          decision.destination_folder !== body.destination_folder ||
          !Array.isArray(decision.member_paths) ||
          decision.member_paths.length !== body.member_paths.length ||
          decision.member_paths.some(
            (member, index) =>
              member.entry_id !== body.member_paths[index].entry_id ||
              member.project_path !== body.member_paths[index].project_path
          )
        ) {
          throw new Error("Unexpected observation reference or decision. Reload this page.");
        }
        assertProjection(value, reference);
        renderDraft(value, false);
        status("Draft reviewed. Identity, capacity and protection still need evidence.");
        byId("observation-review-heading").focus();
      } catch (failure) {
        if (current !== generation) return;
        byId("observation-review-content").replaceChildren();
        error(failure.message || "Draft review unavailable.");
        byId("observation-caption").textContent = "No valid review is available for this intent.";
        status("Review unavailable. Your edits are retained. Retry or reload the reference.");
      } finally {
        if (current === generation) {
          controller = null;
          pending = false;
          reviewButton.disabled = false;
        }
      }
    }
    function dismiss() {
      if (!reference) return;
      invalidate();
      setDecision(reference.decision);
      renderDraft(reference, true);
      error("");
      status("Changes dismissed. The fixed Aurora reference is shown. No files changed.");
      reviewButton.focus();
    }
    byId("observation-form").addEventListener("submit", submit);
    fields.addEventListener("input", changed);
    fields.addEventListener("change", changed);
    byId("observation-reload").addEventListener("click", loadReference);
    dismissButton.addEventListener("click", dismiss);
    if (doc.defaultView)
      doc.defaultView.addEventListener("pageshow", (event) => {
        if (event.persisted) loadReference();
      });
    return { ready: loadReference() };
  }

  if (typeof module !== "undefined" && module.exports) module.exports = { createObservationDemo };
  else createObservationDemo(document, window.fetch.bind(window));
})();
