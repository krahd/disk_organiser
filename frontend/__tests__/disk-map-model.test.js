const fs = require("fs");
const path = require("path");
const api = require("../disk-map-model.js");
const assets = require("../model-assets/bundled.js");
const fixture = () => JSON.parse(assets.exampleText);
const check = (model) => api.validate(model, assets.schema);

test("bundled assets preserve the published contract and fabricated export", () => {
  expect(assets.schema).toEqual(
    JSON.parse(
      fs.readFileSync(path.join(__dirname, "../model-assets/disk-model-v1.schema.json"), "utf8")
    )
  );
  const gitBlob = (text) =>
    require("crypto")
      .createHash("sha1")
      .update(`blob ${Buffer.byteLength(text)}\0`)
      .update(text)
      .digest("hex");
  expect(
    gitBlob(
      fs.readFileSync(path.join(__dirname, "../model-assets/disk-model-v1.schema.json"), "utf8")
    )
  ).toBe("be2fd9b09dd864f3aeed5aaaf6807d80f61cc0a0");
  expect(gitBlob(assets.exampleText)).toBe("f844fcde2bb98dda0c1cf8eb5a1e1cb2d02f4f0a");
  expect(assets.exampleText).toBe(
    fs.readFileSync(path.join(__dirname, "../model-assets/disk-model-v1.example.json"), "utf8")
  );
  const result = api.parse(assets.exampleText, assets.schema);
  expect(result.entries.size).toBe(16);
  expect(result.model.read_only).toBe(true);
  expect(result.model.aggregates.physical_bytes).toBeNull();
  expect(result.model.aggregates.recoverable_bytes).toBeNull();
  expect(result.plans.size).toBe(8);
  expect(result.model.plan_alternatives.every((p) => p.executable === false)).toBe(true);
});
test.each(assets.schema.required)("missing required top-level field %s is rejected", (key) => {
  const data = fixture();
  delete data[key];
  expect(() => check(data)).toThrow(api.ImportError);
});
test.each([
  [
    "unknown version",
    (m) => {
      m.schema_version = "disk-model/v2";
    },
  ],
  [
    "writable model",
    (m) => {
      m.read_only = false;
    },
  ],
  [
    "executable alternative",
    (m) => {
      m.plan_alternatives[0].executable = true;
    },
  ],
  [
    "new filesystem step",
    (m) => {
      m.plan_alternatives[0].alternatives[0].steps[0].type = "move";
    },
  ],
  [
    "unknown field",
    (m) => {
      m.upload_url = "https://invalid.example/";
    },
  ],
  [
    "missing nested field",
    (m) => {
      delete m.entries[0].hash.status;
    },
  ],
  [
    "fake hash",
    (m) => {
      m.entries.find((e) => e.hash.status === "verified").hash.value = "wrong";
    },
  ],
  [
    "invented physical bytes",
    (m) => {
      m.aggregates.physical_bytes = 0;
    },
  ],
  [
    "invalid date",
    (m) => {
      m.scan.started_at = "2026-02-30T00:00:00Z";
    },
  ],
  [
    "missing timezone",
    (m) => {
      m.scan.started_at = "2026-10-06T10:00:00";
    },
  ],
  [
    "duplicate entry",
    (m) => {
      m.entries.push(m.entries[0]);
    },
  ],
  [
    "dangling evidence",
    (m) => {
      m.findings[0].evidence_ids = ["missing"];
    },
  ],
  [
    "duplicate reference",
    (m) => {
      m.findings[0].member_ids.push(m.findings[0].member_ids[0]);
    },
  ],
  [
    "self parent",
    (m) => {
      m.entries[0].parent_id = m.entries[0].id;
    },
  ],
  [
    "wrong parent path",
    (m) => {
      m.entries[1].relative_path = "Missing/Archive";
    },
  ],
  [
    "unsafe root-relative path",
    (m) => {
      m.entries[1].relative_path = "../Archive";
    },
  ],
  [
    "changed accounting",
    (m) => {
      m.aggregates.logical_bytes_by_path++;
    },
  ],
  [
    "inconsistent coverage",
    (m) => {
      m.scan.coverage.entries_observed++;
    },
  ],
  [
    "unsafe size precision",
    (m) => {
      m.aggregates.logical_bytes_by_path = Number.MAX_SAFE_INTEGER + 1;
    },
  ],
  [
    "choice discards scope",
    (m) => {
      m.plan_alternatives[0].alternatives[0].unchanged_member_ids = [];
    },
  ],
  [
    "future dependency",
    (m) => {
      m.plan_alternatives[0].alternatives[0].steps[0].depends_on = ["future"];
    },
  ],
])("rejects %s before rendering", (_, change) => {
  const data = fixture();
  change(data);
  expect(() => check(data)).toThrow(api.ImportError);
});
test("unknown object identity is kept unknown rather than estimated", () => {
  const m = fixture();
  const related = new Set(m.relationships.flatMap((r) => r.member_ids));
  const item = m.entries.find(
    (e) => e.kind === "file" && e.status === "observed" && !related.has(e.id)
  );
  item.object_id = null;
  Object.assign(m.aggregates, {
    object_identity_unknown_paths: 1,
    logical_bytes_by_observed_object: null,
    known_allocated_bytes_by_observed_object: null,
    allocation_unknown_objects: null,
    distinct_observed_file_objects: null,
    hard_link_alias_paths: null,
  });
  expect(check(m).model.aggregates.logical_bytes_by_observed_object).toBeNull();
});
test("plain JSON, nested complexity, schema vocabulary and byte limits are bounded", () => {
  expect(() => api.parse("not-json", assets.schema)).toThrow("not valid JSON");
  expect(() => api.parse(" ".repeat(api.MAX_BYTES + 1), assets.schema)).toThrow("8 MiB");
  expect(() => api.parse('"' + "💾".repeat(api.MAX_BYTES / 4) + '"', assets.schema)).toThrow(
    "8 MiB"
  );
  const m = fixture();
  let node = m.evidence[0].observations;
  for (let i = 0; i < 40; i++) {
    node.deep = {};
    node = node.deep;
  }
  expect(() => check(m)).toThrow("too complex");
  const bad = fixture();
  bad.evidence[0].observations = new Date();
  expect(() => check(bad)).toThrow("plain JSON");
  expect(() => api.auditSchema({ ...assets.schema, unsupportedRule: true })).toThrow(
    "unsupported validation rule"
  );
});
test("object keys cannot alter prototypes or become behaviour", () => {
  const m = fixture();
  m.evidence[0].observations = JSON.parse('{"__proto__":{"polluted":true}}');
  expect(() => check(m)).toThrow("unsupported object key");
  expect({}.polluted).toBeUndefined();
});

test.each(["logical_bytes", "observed_files", "uncertain_entries"])(
  "rejects inconsistent recursive directory %s",
  (field) => {
    const data = fixture();
    data.directories[0][field]++;
    expect(() => check(data)).toThrow("Directory accounting");
  }
);
test("reconciles directory coverage and top-level completion with real recorded gaps", () => {
  const data = fixture(),
    root = data.directories.find((d) => !d.coverage.complete);
  root.coverage.complete = true;
  root.coverage.reasons = [];
  expect(() => check(data)).toThrow("Directory coverage");
  const complete = fixture();
  complete.scan.status = "complete";
  complete.scan.coverage.complete_within_policy = true;
  complete.aggregates.partial = false;
  expect(() => check(complete)).toThrow("Scan completion contradicts");
  const noGap = require("./disk-map-fixtures.js").flatModel(2);
  noGap.scan.status = "cancelled";
  noGap.scan.coverage.stop_reason = "cancelled";
  noGap.scan.coverage.complete_within_policy = false;
  noGap.aggregates.partial = true;
  noGap.directories[0].coverage = { complete: false, reasons: ["scan_interrupted"] };
  expect(check(noGap).model.scan.status).toBe("cancelled");
});
function aliasPair(data) {
  const group = data.relationships.find((r) => r.kind === "hard_link_paths");
  return group.member_ids.map((id) => data.entries.find((e) => e.id === id));
}
test("conflicting alias accounting is rejected in either input order", () => {
  const data = fixture(),
    [, later] = aliasPair(data);
  later.logical_bytes++;
  later.fingerprint.size++;
  data.aggregates.logical_bytes_by_path++;
  data.aggregates.by_extension_category.documents.logical_bytes++;
  let parent = later.parent_id;
  while (parent) {
    data.directories.find((d) => d.entry_id === parent).logical_bytes++;
    parent = data.entries.find((e) => e.id === parent).parent_id;
  }
  expect(() => check(data)).toThrow("Aliases of one reported object");
  data.entries.reverse();
  expect(() => check(data)).toThrow("Aliases of one reported object");
});
test("large fingerprint integers retain exact decimal values rather than rounding alias differences", () => {
  const data = fixture(),
    [first, later] = aliasPair(data);
  const original = BigInt(first.fingerprint.mtime_ns);
  later.fingerprint.mtime_ns = "REPLACE_EXACT_TIMESTAMP";
  const text = JSON.stringify(data).replace('"REPLACE_EXACT_TIMESTAMP"', String(original + 1n));
  expect(() => api.parse(text, assets.schema)).toThrow("Aliases of one reported object");
  const parsed = api.parse(assets.exampleText, assets.schema);
  expect(typeof parsed.model.entries[0].mtime_ns).toBe("bigint");
});
test("valid accounting is invariant to record and alias ordering", () => {
  const before = check(fixture()).model.aggregates;
  const reordered = fixture();
  for (const key of ["entries", "directories", "relationships", "findings", "evidence"])
    reordered[key].reverse();
  expect(check(reordered).model.aggregates).toEqual(before);
});
test("rejects excess free-text collections and long evidence keys before display", () => {
  const many = fixture();
  many.scan.uncertainties = Array(200000).fill("");
  expect(() => check(many)).toThrow("bounded presentation limit");
  const key = fixture();
  key.evidence[0].observations["k".repeat(257)] = "x";
  expect(() => check(key)).toThrow("key or total text budget");
  const text = fixture();
  text.findings[0].title = "x".repeat(4097);
  expect(() => check(text)).toThrow("field or total text budget");
});
test("repeated references have a work budget independent of path length", () => {
  let text = assets.exampleText;
  fixture().entries.forEach((entry, index) => {
    text = text.replaceAll(entry.id, `e${index}`);
  });
  const data = JSON.parse(text),
    ids = data.entries.map((e) => e.id);
  for (let i = 0; i < 7000; i++)
    data.evidence.push({
      id: `extra-${i}`,
      kind: "test",
      member_ids: ids,
      observations: {},
      confidence: "observed",
    });
  expect(() => check(data)).toThrow("reference/search work budget");
});
test("change categories and per-file hash counts cannot contradict each other", () => {
  const changes = fixture();
  changes.changes.changed = [changes.changes.added[0]];
  expect(() => check(changes)).toThrow("change categories overlap");
  const hashes = fixture();
  hashes.scan.coverage.hash_status_counts.verified++;
  expect(() => check(hashes)).toThrow("per-file hash states disagree");
});
test("JSON parsing rejects non-JSON whitespace, duplicate keys and out-of-range unsafe sizes", () => {
  expect(() => api.parse("\u00a0" + assets.exampleText, assets.schema)).toThrow("not valid JSON");
  expect(() => api.parse('{"read_only":true,"read_only":false}', assets.schema)).toThrow(
    "repeated JSON object key"
  );
  expect(() =>
    api.parse(
      assets.exampleText.replace(
        '"logical_bytes_by_path": 1896',
        '"logical_bytes_by_path": 9007199254740993'
      ),
      assets.schema
    )
  ).toThrow("too large");
});
