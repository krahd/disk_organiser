// Fabricated metadata only. No file trees are accessed.
const assets = require("../model-assets/bundled.js");
function flatModel(count = 0) {
  const model = JSON.parse(assets.exampleText);
  const root = model.entries.find((entry) => entry.parent_id === null);
  const sample = model.entries.find(
    (entry) => entry.kind === "file" && entry.status === "observed"
  );
  const files = Array.from({ length: count }, (_, index) => ({
    ...sample,
    id: `entry-test-${index}`,
    parent_id: root.id,
    relative_path: `File-${index}.txt`,
    object_id: `object-test-${index}`,
    logical_bytes: 1,
    allocated_bytes: 0,
    allocation_source: "stat_blocks_512",
    link_count: 1,
    fingerprint: { ...sample.fingerprint, size: 1, inode: index + 100, link_count: 1 },
    hash: { status: "disabled", algorithm: null, value: null },
    uncertainties: [],
  }));
  const ids = files.map((entry) => entry.id);
  model.entries = [root, ...files];
  model.scan.status = "complete";
  model.scan.errors = [];
  model.scan.exclusions = [];
  model.scan.hash_policy = "metadata_only";
  model.scan.limits.hash_files = false;
  model.scan.coverage = {
    ...model.scan.coverage,
    entries_observed: count + 1,
    status_counts: { observed: count + 1 },
    hashed_files: 0,
    hash_attempts: 0,
    hashed_bytes: 0,
    hash_status_counts: count ? { disabled: count } : {},
    complete_within_policy: true,
    stop_reason: null,
  };
  model.directories = [
    {
      ...model.directories.find((d) => d.entry_id === root.id),
      direct_member_ids: ids,
      logical_bytes: count,
      observed_files: count,
      uncertain_entries: 0,
      coverage: { complete: true, reasons: [] },
      role_hypotheses: [],
      confidence: "unknown",
    },
  ];
  Object.assign(model.aggregates, {
    logical_bytes_by_path: count,
    logical_bytes_by_observed_object: count,
    known_allocated_bytes_by_observed_object: count ? 0 : null,
    allocation_unknown_objects: 0,
    object_identity_unknown_paths: 0,
    observed_regular_files: count,
    distinct_observed_file_objects: count,
    hard_link_alias_paths: 0,
    status_counts: { observed: count + 1 },
    by_extension_category: count ? { documents: { entry_count: count, logical_bytes: count } } : {},
    partial: false,
  });
  model.evidence = count
    ? [
        {
          id: "evidence-test",
          kind: "synthetic_observations",
          confidence: "observed",
          member_ids: ids,
          observations: { count },
        },
      ]
    : [];
  model.findings = count
    ? [
        {
          id: "finding-test",
          kind: "synthetic_observations",
          title: "Synthetic member observations",
          confidence: "observed",
          member_ids: ids,
          evidence_ids: ["evidence-test"],
          uncertainties: ["Fabricated test observations, not a real disk."],
          counter_evidence: [],
        },
      ]
    : [];
  model.relationships = [];
  model.plan_alternatives = [];
  model.changes = {
    ...model.changes,
    previous_scan_id: null,
    comparable: false,
    added: [root.id, ...ids],
    changed: [],
    unchanged_metadata: [],
    no_longer_observed: [],
    unverified_absent: [],
  };
  return model;
}
module.exports = { flatModel };
