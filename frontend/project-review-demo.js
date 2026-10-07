(function () {
  "use strict";

  const BLOCKERS = {
    membership_and_destination_need_review: "Review the project members and proposed home.",
    destination_not_online: "The destination is not online in this fixture.",
    destination_coverage_incomplete: "The destination inventory is incomplete.",
    destination_observation_stale_or_future:
      "The destination observation is stale or future-dated.",
    destination_name_semantics_unknown:
      "The destination’s case or Unicode naming rules are unknown.",
    source_not_online: "A source volume is not online.",
    source_coverage_incomplete: "A source inventory is incomplete.",
    source_name_semantics_unknown: "A source’s naming rules are unknown.",
    source_volume_observation_stale_or_future:
      "A source-volume observation is stale or future-dated.",
    source_observation_stale_or_future: "A member observation is stale or future-dated.",
    unsupported_placeholder: "A member is a placeholder; its actual content is unavailable.",
    hardlink_or_link_identity_unknown: "A member has a hard link or uncertain link identity.",
    source_version_unknown: "A member’s content version is unknown.",
    current_location_identity_unproven:
      "Keeping this location is unresolved because its declared identity is incomplete or uncertain.",
    project_dependencies_unknown: "A member’s application dependencies are not fully known.",
    project_dependency_not_selected: "A selected member depends on a member you removed.",
    source_ancestor_not_a_directory: "A declared source path overlaps another file-like member.",
    planned_name_or_ancestor_collision: "Two proposed paths collide or overlap.",
    occupied_name_or_ancestor_collision: "A proposed path is already occupied in this fixture.",
    nonportable_destination_name: "The proposed folder contains a name that is not portable.",
    required_capacity_unknown:
      "Required capacity cannot be established because a member’s size is unknown.",
    destination_capacity_unknown: "Available destination capacity is unknown.",
    insufficient_observed_capacity:
      "Observed free space is below the required logical data and reserve.",
    ambiguous_latest_backup_evidence: "The latest backup evidence is contradictory or ambiguous.",
    verified_independent_copy_requirement_unmet:
      "A current-version independent copy is not established by the fixture evidence.",
    unresolved_restore_evidence_requires_attention: "Unresolved restore evidence needs attention.",
    project_restore_evidence_requirement_unmet:
      "The fixture does not establish a restore of the whole selected project.",
  };
  const LEVELS = {
    declared_configuration: "Configuration only",
    provider_reported: "Fabricated provider report",
    manifest_present: "Fabricated snapshot manifest",
    content_verified: "Fabricated content verification",
  };

  function createDemo(doc, requestFetch) {
    const byId = (id) => doc.getElementById(id);
    const token = doc.querySelector('meta[name="demo-process-token"]').content;
    const form = byId("decision-form");
    const fields = byId("decision-fields");
    const reviewButton = byId("review-button");
    const dismissButton = byId("dismiss");
    let reference = null;
    let generation = 0;
    let controller = null;
    let pendingReview = false;

    function element(tag, text, className) {
      const node = doc.createElement(tag);
      if (text !== undefined) node.textContent = text;
      if (className) node.className = className;
      return node;
    }
    function append(parent, tag, text, className) {
      const node = element(tag, text, className);
      parent.append(node);
      return node;
    }
    function invalidate() {
      generation += 1;
      if (controller) controller.abort();
      controller = null;
      pendingReview = false;
      reviewButton.disabled = !reference;
      return generation;
    }
    function setStatus(text) {
      byId("status").textContent = text;
    }
    function setError(text) {
      byId("error").textContent = text || "";
      byId("error").hidden = !text;
    }
    function safety(value) {
      return (
        value &&
        value.synthetic === true &&
        value.executable === false &&
        value.execution_authority === null &&
        value.undo_available === false &&
        value.source_safe_to_erase === false &&
        value.live_backup_verified === false &&
        value.live_restore_verified === false
      );
    }
    function assertSafe(value) {
      const result = value && value.review;
      if (
        !safety(value) ||
        !result ||
        result.synthetic !== true ||
        result.executable !== false ||
        result.execution_authority !== null ||
        result.undo_available !== false ||
        result.source_safe_to_erase !== false ||
        !result.protection ||
        result.protection.live_backup_verified !== false ||
        result.protection.live_restore_verified !== false
      ) {
        throw new Error("Unexpected demo response. Reload the scenario.");
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
            ? "The fixture reference changed. Reload this scenario before reviewing."
            : value.error || "Demo request failed. Retry or reload this scenario."
        );
      }
      assertSafe(value);
      return value;
    }
    function entryName(id) {
      const entry = reference.entries.find((item) => item.id === id);
      return entry ? entry.project_path : id;
    }
    function volumeName(id) {
      const volume = reference.volumes.find((item) => item.id === id);
      return volume ? volume.label : id;
    }
    function bytes(value) {
      return value === null ? "Unknown" : `${value.toLocaleString("en-GB")} bytes`;
    }
    function markMembers() {
      const suggested = new Set(reference.project.candidate_member_ids);
      for (const input of byId("members").querySelectorAll("input")) {
        const initial = suggested.has(input.value);
        byId(`state-${input.value}`).textContent = initial
          ? input.checked
            ? "Suggested · included"
            : "Removed"
          : input.checked
          ? "Added"
          : "Not included";
      }
    }
    function destinationFacts() {
      const volume = reference.volumes.find((item) => item.id === byId("destination-volume").value);
      byId("destination-facts").textContent = `${volume.label}: ${
        volume.state
      }. Inventory coverage: ${volume.coverage}. Observed ${
        volume.observed_at
      }. Free capacity: ${bytes(volume.free_bytes)}. These are fixture assertions.`;
    }
    function setDecision(decision) {
      for (const input of byId("members").querySelectorAll("input")) {
        input.checked = decision.member_ids.includes(input.value);
      }
      byId("destination-volume").value = decision.destination_volume_id;
      byId("destination-folder").value = decision.destination_folder;
      markMembers();
      destinationFacts();
    }
    function renderReference() {
      byId(
        "fixture-date"
      ).textContent = `Fabricated observations as of ${reference.fixture_as_of}. Freshness is measured against this fixed fixture clock, not today. Reference revision ${reference.reference_revision}.`;
      const members = byId("members");
      members.replaceChildren();
      const current = byId("current-layout");
      current.replaceChildren();
      for (const entry of reference.entries) {
        const row = append(members, "div", undefined, "member-row");
        const input = append(row, "input");
        input.type = "checkbox";
        input.id = `member-${entry.id}`;
        input.value = entry.id;
        const label = append(row, "label", entry.project_path);
        label.htmlFor = input.id;
        append(
          label,
          "span",
          `${entry.kind} · ${bytes(entry.bytes)} · version ${entry.version || "unknown"}`,
          "member-details"
        );
        append(
          label,
          "span",
          entry.dependencies.length
            ? `Depends on: ${entry.dependencies.map(entryName).join(", ")}.`
            : "No dependencies declared in this fixture.",
          "member-details"
        );
        append(
          label,
          "span",
          `Dependency coverage: ${entry.dependency_coverage.replaceAll("_", " ")}.`,
          "member-details"
        );
        append(row, "span", "", "member-state").id = `state-${entry.id}`;
        const item = append(current, "li");
        append(item, "span", volumeName(entry.volume_id));
        append(item, "div", entry.path, "path");
      }
      const volumes = byId("destination-volume");
      volumes.replaceChildren();
      for (const volume of reference.volumes) {
        const option = append(volumes, "option", `${volume.label} · ${volume.state}`);
        option.value = volume.id;
      }
      setDecision(reference.decision);
      fields.disabled = false;
      reviewButton.disabled = false;
      dismissButton.disabled = false;
      renderReview(reference.review, true);
    }
    function section(parent, title, intro) {
      const node = append(parent, "section", undefined, "review-section");
      append(node, "h3", title);
      if (intro) append(node, "p", intro);
      return node;
    }
    function renderReview(result, isReference) {
      const content = byId("review-content");
      content.replaceChildren();
      byId("review-caption").textContent = isReference
        ? "Reference proposal. Edit the decision above to compare a different layout."
        : "Reviewed draft. Editing any member or destination invalidates this review.";
      const summary = append(
        content,
        "div",
        undefined,
        result.blockers.length ? "attention" : "review-summary"
      );
      append(
        summary,
        "h3",
        result.blockers.length
          ? `${result.blockers.length} review issue${
              result.blockers.length === 1 ? "" : "s"
            } need attention`
          : "No rule blockers in this synthetic proposal"
      );
      append(summary, "p", "Proposal only. No files have changed and no action can be executed.");
      if (result.blockers.length) {
        const list = append(summary, "ul");
        for (const blocker of result.blockers) {
          append(
            list,
            "li",
            `${BLOCKERS[blocker.code] || `Review issue: ${blocker.code.replaceAll("_", " ")}`}${
              blocker.member_ids.length
                ? ` Members: ${blocker.member_ids.map(entryName).join(", ")}.`
                : ""
            }`
          );
        }
      }
      const corrections = result.membership_corrections;
      append(
        content,
        "p",
        `Selected: ${result.member_ids.length}. Added: ${
          corrections.added.map(entryName).join(", ") || "none"
        }. Removed: ${corrections.removed.map(entryName).join(", ") || "none"}.`,
        "provenance"
      );
      const allKept = result.proposed_changes.every((change) => change.proposal === "keep_current");
      const hasCurrent = result.proposed_changes.some(
        (change) => change.proposal !== "copy_with_project_structure"
      );
      const layout = section(
        content,
        "Current layout → proposed paths",
        allKept
          ? "Keep current: no copies are proposed. Exact declared locations stay unchanged. Zero bytes reclaimed."
          : hasCurrent
          ? "Kept entries stay at their declared locations. Unresolved locations need review. Proposed copies retain their sources. Zero bytes reclaimed."
          : "Proposed copies retain the sources. Zero bytes reclaimed. No move or deletion is proposed."
      );
      for (const change of result.proposed_changes) {
        const row = append(layout, "div", undefined, "comparison");
        const source = append(row, "div");
        append(source, "strong", `CURRENT · ${volumeName(change.source.volume_id)}`);
        append(source, "div", change.source.relative_path, "path");
        append(source, "p", `Version: ${change.source.version || "unknown"}`, "evidence-line");
        const target = append(row, "div");
        const kept = change.proposal === "keep_current";
        const unresolved = change.proposal === "unresolved_current_location";
        const label = kept ? "KEEP CURRENT" : unresolved ? "UNRESOLVED" : "PROPOSED";
        append(target, "strong", `${label} · ${volumeName(change.destination.volume_id)}`);
        append(target, "div", change.destination.relative_path, "path");
        append(
          target,
          "p",
          kept
            ? "Same declared member, version and exact address · no copy proposed"
            : unresolved
            ? "Current-location identity unproven · no copy or no-op established"
            : "Source retained · proposal only",
          "evidence-line"
        );
      }
      const capacity = section(
        content,
        "Capacity before committing to a home",
        allKept
          ? "No additional copy space or reserve is required by this declared keep-current plan. Actual free space and physical allocation are not verified."
          : hasCurrent
          ? "Logical data counts only proposed copies. Unresolved current locations leave required capacity unknown. A fixed reserve applies unless every member is kept. Physical allocation and actual free space are not verified."
          : "Logical copy data plus a fixed reserve. Physical allocation, compression and actual free space are not verified."
      );
      const metrics = append(capacity, "dl", undefined, "metrics");
      for (const [label, value] of [
        ["Known logical copy data", result.capacity.known_logical_copy_bytes],
        ["Required including reserve", result.capacity.required_destination_bytes],
        ["Observed destination free", result.capacity.observed_free_bytes],
      ]) {
        const metric = append(metrics, "div", undefined, "metric");
        append(metric, "dt", label);
        append(metric, "dd", bytes(value));
      }
      append(
        capacity,
        "p",
        `Reserve: ${bytes(result.capacity.reserve_bytes)}. Unknown member sizes: ${
          result.capacity.unknown_size_member_ids.map(entryName).join(", ") || "none"
        }.`
      );
      const protection = section(
        content,
        "Protection by target and content version",
        "All evidence below is fabricated and read-only. Configuration, backup content checks and restore exercises are different claims."
      );
      const targets = append(protection, "div", undefined, "targets");
      for (const targetId of result.protection.configured_target_ids) {
        const target = reference.targets.find((item) => item.id === targetId);
        const card = append(targets, "article", undefined, "target");
        append(card, "h4", target.label);
        append(
          card,
          "p",
          `Type: ${target.kind.replaceAll("_", " ")}. Declared failure domain: ${
            target.failure_domain || "unknown"
          }.`,
          "evidence-line"
        );
        if (target.region) append(card, "p", `Region: ${target.region}`, "evidence-line");
        for (const member of result.protection.members) {
          const node = append(card, "div", undefined, "evidence-member");
          append(node, "h4", entryName(member.member_id));
          const observations = member.observations.filter((item) => item.target_id === targetId);
          if (!observations.length)
            append(node, "p", "No evidence for this member and target.", "evidence-line");
          for (const observed of observations) {
            append(
              node,
              "p",
              LEVELS[observed.evidence_level] || observed.evidence_level.replaceAll("_", " "),
              "evidence-line"
            );
            append(
              node,
              "p",
              `Snapshot: ${observed.snapshot_id}. Evidence: ${observed.backup_id}. Observed: ${observed.observed_at}.`,
              "evidence-line"
            );
            append(
              node,
              "p",
              `Matches current fixture version: ${
                observed.matches_current_fixture_version ? "yes" : "no"
              }. Fresh at fixture clock: ${observed.fresh ? "yes" : "no"}. Complete: ${
                observed.complete ? "yes" : "no"
              }.`,
              "evidence-line"
            );
            append(
              node,
              "p",
              `Current snapshot evidence: ${
                observed.current_snapshot_evidence ? "yes" : "no"
              }. Independent declared domain: ${
                observed.independent_declared_domain ? "yes" : "no"
              }. Counts towards fixture copy requirement: ${
                observed.counts_for_fixture_copy_requirement ? "yes" : "no"
              }.`,
              "evidence-line"
            );
          }
        }
      }
      const restores = section(
        content,
        "Restore evidence and its exact scope",
        "A sample restore does not prove a whole-project restore. Past exercises do not prove that the proposed new layout opens in its application."
      );
      append(
        restores,
        "p",
        `Whole selected project meets fixture restore requirement: ${
          result.protection.project_restore_satisfied_in_fixture
            ? "yes, in fabricated records only"
            : "no"
        }. Required method: ${
          result.protection.required_restore_check === "bytes_and_app"
            ? "bytes and application check"
            : "bytes check"
        }.`
      );
      for (const restore of result.protection.restore_observations) {
        const card = append(restores, "article", undefined, "restore-card");
        append(
          card,
          "h4",
          `${restore.scope === "project" ? "Project-scoped" : "Sample-scoped"} exercise · ${
            restore.outcome
          }`
        );
        append(
          card,
          "p",
          `Target: ${
            reference.targets.find((target) => target.id === restore.target_id).label
          }. Snapshot: ${restore.snapshot_id}.`,
          "evidence-line"
        );
        append(
          card,
          "p",
          `Completed: ${restore.completed_at}. Method: ${
            restore.check === "bytes_and_app" ? "bytes and application check" : "bytes check"
          }. Required method met: ${restore.meets_required_check ? "yes" : "no"}.`,
          "evidence-line"
        );
        append(
          card,
          "p",
          `Matching selected member versions: ${
            restore.matching_member_ids.map(entryName).join(", ") || "none"
          }. Fresh at fixture clock: ${
            restore.fresh ? "yes" : "no"
          }. Invalidated by later or ambiguous evidence: ${
            restore.invalidated_by_later_or_ambiguous_evidence ? "yes" : "no"
          }.`,
          "evidence-line"
        );
        append(
          card,
          "p",
          `Satisfies the project fixture restore requirement: ${
            restore.satisfies_project_fixture_restore ? "yes" : "no"
          }. Evidence ID: ${restore.restore_id}. Backup evidence: ${restore.backup_id}.`,
          "evidence-line"
        );
      }
      if (!result.protection.restore_observations.length)
        append(restores, "p", "No restore exercises recorded.");
      const alerts = result.protection.restore_alerts;
      append(restores, "h4", "Unresolved restore alerts");
      if (!alerts.length)
        append(
          restores,
          "p",
          "None recorded in this fixture. This is not live restore verification.",
          "evidence-line"
        );
      for (const alert of alerts) {
        append(
          restores,
          "p",
          `${alert.target_id} · ${alert.snapshot_id} · ${alert.at}. ${alert.reasons
            .join(", ")
            .replaceAll("_", " ")}. Required check: ${alert.required_check.replaceAll(
            "_",
            " "
          )}. Affected members: ${alert.member_ids
            .map(entryName)
            .join(", ")}. Events: ${alert.event_ids.join(", ")}.`,
          "attention"
        );
      }
      const limits = append(content, "details");
      append(limits, "summary", "Evidence limits and review identity");
      const limitations = append(limits, "ul");
      for (const item of result.limitations) append(limitations, "li", item);
      append(
        limits,
        "p",
        `Contract ${result.schema_version}. Proposal revision ${result.revision}. Review digest ${result.input_digest}. Reference digest ${reference.reference_digest}.`,
        "provenance"
      );
      append(
        limits,
        "p",
        "Execution: false. Authority: null. Undo: false. Source safe to erase: false. Live backup verified: false. Live restore verified: false."
      );
    }
    function changed() {
      if (!reference) return;
      invalidate();
      markMembers();
      destinationFacts();
      setError("");
      byId("review-content").replaceChildren();
      byId("review-caption").textContent =
        "Draft changed. Review the proposed layout to see current checks and evidence.";
      setStatus("Draft changed. The previous review no longer applies.");
    }
    async function loadScenario() {
      const currentGeneration = invalidate();
      const scenarioId = byId("scenario").value;
      reference = null;
      fields.disabled = true;
      reviewButton.disabled = true;
      dismissButton.disabled = true;
      for (const id of ["members", "current-layout", "destination-volume", "review-content"])
        byId(id).replaceChildren();
      byId("fixture-date").textContent = "";
      byId("destination-folder").value = "";
      byId("destination-facts").textContent = "";
      byId("review-caption").textContent = "Loading the selected reference scenario.";
      setStatus("Loading packaged scenario…");
      setError("");
      controller = new AbortController();
      try {
        const value = await fetchJSON(
          `/api/reference?scenario_id=${encodeURIComponent(scenarioId)}`,
          {},
          controller.signal
        );
        if (currentGeneration !== generation) return;
        if (value.scenario_id !== scenarioId)
          throw new Error("Unexpected scenario response. Reload the scenario.");
        reference = value;
        renderReference();
        setStatus("Reference decision loaded. Review or change its members and proposed home.");
      } catch (error) {
        if (currentGeneration !== generation) return;
        setError(error.message || "The scenario could not be loaded.");
        setStatus("Scenario unavailable. Use Reload scenario to retry.");
      } finally {
        if (currentGeneration === generation) controller = null;
      }
    }
    async function submit(event) {
      event.preventDefault();
      if (!reference || pendingReview) return;
      const currentGeneration = invalidate();
      const body = {
        scenario_id: reference.scenario_id,
        expected_revision: reference.reference_revision,
        expected_digest: reference.reference_digest,
        member_ids: Array.from(
          byId("members").querySelectorAll("input:checked"),
          (input) => input.value
        ),
        destination_volume_id: byId("destination-volume").value,
        destination_folder: byId("destination-folder").value,
      };
      pendingReview = true;
      reviewButton.disabled = true;
      setError("");
      byId("review-content").replaceChildren();
      byId("review-caption").textContent = "Checking this draft against the packaged evidence.";
      setStatus("Reviewing proposed layout… You can still edit or dismiss it.");
      controller = new AbortController();
      try {
        const value = await fetchJSON(
          "/api/review",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          },
          controller.signal
        );
        if (currentGeneration !== generation) return;
        if (
          value.scenario_id !== reference.scenario_id ||
          value.reference_digest !== reference.reference_digest ||
          value.reference_revision !== reference.reference_revision
        ) {
          throw new Error("Unexpected review reference. Reload the scenario.");
        }
        renderReview(value.review, false);
        setStatus("Draft reviewed. This is a non-executable proposal.");
        byId("review-heading").focus();
      } catch (error) {
        if (currentGeneration !== generation) return;
        setError(error.message || "Review unavailable.");
        byId("review-caption").textContent = "No valid review is available for this draft.";
        setStatus("Review unavailable. Your draft is retained. Retry or reload the scenario.");
      } finally {
        if (currentGeneration === generation) {
          controller = null;
          pendingReview = false;
          reviewButton.disabled = false;
        }
      }
    }
    function dismiss() {
      if (!reference) return;
      invalidate();
      setDecision(reference.decision);
      renderReview(reference.review, true);
      setError("");
      setStatus(
        "Proposal dismissed. The scenario’s reference decision is shown. No files changed."
      );
      reviewButton.focus();
    }
    form.addEventListener("submit", submit);
    fields.addEventListener("input", changed);
    fields.addEventListener("change", changed);
    byId("scenario").addEventListener("change", loadScenario);
    byId("reload").addEventListener("click", loadScenario);
    dismissButton.addEventListener("click", dismiss);
    // Back/forward cache must not revive a previous tab draft or pending response.
    if (doc.defaultView)
      doc.defaultView.addEventListener("pageshow", (event) => {
        if (event.persisted) loadScenario();
      });
    const ready = loadScenario();
    return { ready };
  }
  if (typeof module !== "undefined" && module.exports) module.exports = { createDemo };
  else createDemo(document, window.fetch.bind(window));
})();
