/** @jest-environment node */
const C = require("../inventory-snapshot-model.js");
const X = require("../inventory-comparison-model.js");
const original = require("../../prototypes/inventory_catalogue/owned-creative.example.json");
const clone = (x) => JSON.parse(JSON.stringify(x));
const id = (n) => `source_00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const entry = (path, kind = "file", logical_bytes = "3", status = "observed") => ({
  path,
  kind,
  status,
  logical_bytes: kind === "file" ? logical_bytes : null,
});
function snapshot(entries = [], partial = false) {
  const s = clone(original);
  s.entries = [entry(".", "directory"), ...entries];
  s.source.coverage = partial ? "partial" : "complete";
  return s;
}
function pair(a = snapshot(), b = snapshot()) {
  return C.add(C.add(C.empty(), a, "Same visible label", id(1)), b, "Same visible label", id(2));
}
const compare = (a, b) => X.compare(pair(a, b), id(1), id(2));
test("empty roots are context, not matching child contents", () => {
  const r = compare();
  expect(r.rows).toEqual([]);
  expect(Object.values(r.counts)).toEqual([0, 0, 0, 0, 0]);
  expect(r.left.id).not.toBe(r.right.id);
  expect(r.left.label).toBe(r.right.label);
});
test("complete bounded exact-path union has disjoint truthful groups", () => {
  const r = compare(
    snapshot([entry("same"), entry("changed", "file", "4"), entry("left")]),
    snapshot([entry("same"), entry("changed", "file", "5"), entry("right")])
  );
  expect(r.counts).toEqual({
    matching: 1,
    different: 1,
    left: 1,
    right: 1,
    uncertain: 0,
  });
  expect(r.rows.map((x) => x.path)).toEqual(["changed", "left", "right", "same"]);
  expect(r.rows[1].right).toBeNull();
  expect(r.rows[2].left).toBeNull();
});
test.each(["Case", "café", "cafe\u0301", "x😀", "x😁", "__proto__", "constructor"])(
  "path %s remains exact and inert",
  (path) => {
    const r = compare(snapshot([entry(path)]), snapshot([entry(path + "z")]));
    expect(r.counts.left).toBe(1);
    expect(r.counts.right).toBe(1);
    expect(r.counts.matching).toBe(0);
    expect(r.rows.map((x) => x.path)).toContain(path);
  }
);
test("canonically equivalent and case-different names never collapse", () => {
  const r = compare(
    snapshot([entry("café"), entry("FILE")]),
    snapshot([entry("cafe\u0301"), entry("file")])
  );
  expect(r.rows).toHaveLength(4);
  expect(r.counts.matching).toBe(0);
});
test("directories only match their recorded kind; children are compared separately", () => {
  const r = compare(
    snapshot([entry("Project", "directory"), entry("Project/left")]),
    snapshot([entry("Project", "directory"), entry("Project/right")])
  );
  expect(r.counts).toEqual({
    matching: 1,
    different: 0,
    left: 1,
    right: 1,
    uncertain: 0,
  });
});
test("file/directory disagreement is not treated as matching", () => {
  expect(
    compare(snapshot([entry("thing")]), snapshot([entry("thing", "directory")])).rows[0].category
  ).toBe("different");
});
test.each(["stale", "disappeared", "unreadable", "unsupported", "excluded"])(
  "%s entry cannot be promoted to a matching observation",
  (status) => {
    const r = compare(snapshot([entry("a", "file", "3", status)], true), snapshot([entry("a")]));
    expect(r.rows[0].category).toBe("uncertain");
    expect(r.rows[0].left.status).toBe(status);
  }
);
test.each(["symlink", "special", "unknown"])(
  "%s kinds cannot imply comparable contents",
  (kind) => {
    const r = compare(snapshot([entry("a", kind, null, "unsupported")], true), snapshot());
    expect(r.rows[0].category).toBe("uncertain");
    expect(r.rows[0].right).toBeNull();
  }
);
test("uncertain ancestor prevents promotion of a listed observed child", () => {
  const a = snapshot([entry("P", "directory", null, "stale"), entry("P/a")], true);
  const b = snapshot([entry("P", "directory"), entry("P/a")]);
  expect(compare(a, b).rows.every((r) => r.category === "uncertain")).toBe(true);
});
test("partial and empty snapshots retain their gaps, not live absence claims", () => {
  const b = snapshot([], true);
  b.gaps.stop_reason = "entry_limit";
  const r = compare(snapshot([entry("a")]), b);
  expect(r.counts.left).toBe(1);
  expect(r.right.source.coverage).toBe("partial");
  expect(r.right.gaps.stop_reason).toBe("entry_limit");
  expect(Object.keys(r)).toEqual(["left", "right", "counts", "rows"]);
});
test("decimal sizes are compared exactly without floating-point conversion", () => {
  const a = "9007199254740991",
    b = "9007199254740992";
  const r = compare(snapshot([entry("a", "file", a)]), snapshot([entry("a", "file", b)]));
  expect(r.rows[0].category).toBe("different");
  expect(r.rows[0].left.logical_bytes).toBe(a);
});
test("maximum source pair includes all 3998 children, no first-page truncation", () => {
  const make = (prefix) =>
    snapshot(Array.from({ length: 1999 }, (_, n) => entry(prefix + String(n).padStart(4, "0"))));
  const r = compare(make("a"), make("b"));
  expect(r.rows).toHaveLength(3998);
  expect(r.counts.left).toBe(1999);
  expect(r.counts.right).toBe(1999);
});
test("same record, missing records and invalid source are rejected", () => {
  const c = pair();
  expect(() => X.compare(c, id(1), id(1))).toThrow(/different/);
  expect(() => X.compare(c, id(1), id(3))).toThrow(/current/);
  const invalid = clone(c);
  invalid.records[0].snapshot.source.trusted = true;
  expect(() => X.compare(invalid, id(1), id(2))).toThrow();
});
test("comparison leaves caller state and saved format unchanged and freezes only its own result", () => {
  const c = clone(pair(snapshot([entry("a")]), snapshot([entry("a")]))),
    before = JSON.stringify(c);
  const r = X.compare(c, id(1), id(2));
  expect(JSON.stringify(c)).toBe(before);
  expect(Object.isFrozen(c)).toBe(false);
  expect(Object.isFrozen(c.records[0].snapshot.entries[1])).toBe(false);
  expect(Object.isFrozen(r.rows[0].left)).toBe(true);
  c.records[0].snapshot.entries[1].logical_bytes = "99";
  expect(r.rows[0].left.logical_bytes).toBe("3");
  expect(C.parse(C.exportCatalogue(pair())).schema_version).toBe(C.CATALOGUE);
});
test("source dates remain verbatim, and swapping sides does not infer time order", () => {
  const a = snapshot([entry("a")]),
    b = snapshot([entry("b")]);
  a.source.observed_at = "2026-10-09T00:05:00+05:30";
  b.source.observed_at = "2025-01-01T00:00:00-00:00";
  const c = pair(a, b),
    r = X.compare(c, id(2), id(1));
  expect(r.left.source.observed_at).toBe(b.source.observed_at);
  expect(r.right.source.observed_at).toBe(a.source.observed_at);
  expect(r.rows.find((x) => x.path === "b").category).toBe("left");
});
