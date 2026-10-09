/** @jest-environment node */
const { webcrypto } = require("node:crypto");
if (!globalThis.crypto) globalThis.crypto = webcrypto;
const C = require("../inventory-snapshot-model.js");
const M = require("../manual-planning-model.js");
const fixture = require("../../prototypes/inventory_catalogue/owned-creative.example.json");
const partial = require("../../prototypes/inventory_catalogue/owned-archive.example.json");
const clone = (x) => JSON.parse(JSON.stringify(x));
const id = (n) => `source_00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const cat = () => C.add(C.empty(), fixture, "Offline disk A", id(1));
const parse = (x) => C.parse(JSON.stringify(x));
const now = "2026-10-09T07:00:00Z";
const selection = (path, n = 1) => ({ source_id: id(n), path });

test.each([
  ["2026-10-09T07:00:59.123456Z", "9 Oct 2026, 07:00 UTC"],
  ["2026-10-09T07:00:00+00:00", "9 Oct 2026, 07:00 UTC"],
  ["2026-10-09T00:05:00+05:30", "9 Oct 2026, 00:05 UTC+05:30"],
  ["2026-12-31T23:59:59-03:30", "31 Dec 2026, 23:59 UTC-03:30"],
  ["2026-10-09T07:00:00-00:00", "9 Oct 2026, 07:00 UTC (local offset unknown)"],
  ["2000-02-29T00:00:00Z", "29 Feb 2000, 00:00 UTC"],
  ["0001-01-01T00:00:00Z", "1 Jan 0001, 00:00 UTC"],
  ["9999-12-31T23:59:59+23:59", "31 Dec 9999, 23:59 UTC+23:59"],
])("claimed date %s has a readable, unconverted minute display", (raw, shown) => {
  expect(C.formatObservationDate(raw)).toBe(shown);
  const snapshot = clone(fixture);
  snapshot.source.observed_at = raw;
  const catalogue = C.add(C.empty(), parse(snapshot), "Date fixture", id(1));
  expect(C.parse(C.exportCatalogue(catalogue)).records[0].snapshot.source.observed_at).toBe(raw);
  const plan = C.buildPlan(catalogue, [selection("Photos")], "Date project", now);
  expect(plan.items[0].notes).toContain(raw);
});
test.each([
  undefined,
  null,
  0,
  {},
  "",
  "2026",
  "2026-10-09",
  "2026-10-09T07:00",
  "2026-10-09T07:00:00",
  "2026-10-09T07:00:00+05",
  "2026-10-09T07:00:00.1234567Z",
  "1900-02-29T07:00:00Z",
  "2026-10-09T24:00:00Z",
  "2026-10-09T07:00:00+24:00",
])("invalid or incomplete date %p stays unavailable and cannot import", (raw) => {
  expect(C.formatObservationDate(raw)).toBe("Date unavailable");
  const snapshot = clone(fixture);
  snapshot.source.observed_at = raw;
  expect(() => parse(snapshot)).toThrow();
});
test("date display is independent of the host timezone", () => {
  const { execFileSync } = require("node:child_process"),
    modulePath = require.resolve("../inventory-snapshot-model.js"),
    script = `process.stdout.write(require(${JSON.stringify(
      modulePath
    )}).formatObservationDate("2026-12-31T23:59:59-03:30"))`;
  for (const TZ of ["UTC", "Pacific/Kiritimati", "America/Los_Angeles"])
    expect(
      execFileSync(process.execPath, ["-e", script], {
        env: { ...process.env, TZ },
        encoding: "utf8",
      })
    ).toBe("31 Dec 2026, 23:59 UTC-03:30");
});

test("owned complete and partial projections preserve exact decimal strings", () => {
  expect(parse(fixture)).toEqual(fixture);
  expect(parse(partial)).toEqual(partial);
  const s = clone(fixture);
  s.entries.find((e) => e.kind === "file").logical_bytes = "9007199254740993000000000";
  expect(C.summary(parse(s)).bytes > 9007199254740993000000000n).toBe(true);
});
test("empty catalogue roundtrips without claiming absence", () =>
  expect(C.parse(C.exportCatalogue(C.empty()))).toEqual(C.empty()));
test("same labels and snapshots remain separate records", () => {
  const c = C.add(cat(), fixture, "Offline disk A", id(2));
  expect(c.records).toHaveLength(2);
  expect(c.records[0].snapshot).toEqual(c.records[1].snapshot);
});
test("rename preserves frozen historical label, date and source", () => {
  const c = cat(),
    next = C.rename(c, id(1), "New shelf name");
  expect(next.records[0].snapshot).toEqual(c.records[0].snapshot);
  expect(c.records[0].label).toBe("Offline disk A");
  expect(Object.isFrozen(next.records[0].snapshot.entries[0])).toBe(true);
});
test("byte summary counts only observed file paths and partitions them once", () => {
  const s = clone(partial);
  const file = s.entries.find((e) => e.kind === "file");
  file.status = "stale";
  const sum = C.summary(parse(s));
  expect(sum.bytes).toBe(
    s.entries
      .filter((e) => e.kind === "file" && e.status === "observed")
      .reduce((a, e) => a + BigInt(e.logical_bytes), 0n)
  );
  expect(sum.groups.reduce((a, g) => a + g.bytes, 0n)).toBe(sum.bytes);
  expect(sum.uncertain).toBe(2);
});
test.each([
  "../escape",
  "/absolute",
  "a//b",
  "a/./b",
  "a/../b",
  "a\\b",
  "a/",
  "bad\nname",
  "bad\u0085name",
  "bad\ud800",
])("invalid relative path %p rejects", (p) => {
  const s = clone(fixture);
  s.entries[1].path = p;
  expect(() => parse(s)).toThrow();
});
test.each(["01", "-1", "+1", "1.1", "1e2", "1".repeat(31), 42, null])(
  "invalid file byte field %p rejects",
  (size) => {
    const s = clone(fixture);
    s.entries.find((e) => e.kind === "file").logical_bytes = size;
    expect(() => parse(s)).toThrow();
  }
);
test.each([
  "2026-02-30T12:00:00Z",
  "0000-01-01T00:00:00Z",
  "2026-10-09T24:00:00Z",
  "2026-10-09T07:00:60Z",
  "2026-10-09T07:00:00+24:00",
  "yesterday",
])("invalid observation time %s rejects", (t) => {
  const s = clone(fixture);
  s.source.observed_at = t;
  expect(() => parse(s)).toThrow();
});
test.each(["trusted", "synthetic", "execution_authority", "provider", "physical_volume_id"])(
  "extra authority-shaped field %s rejects",
  (key) => {
    const s = clone(fixture);
    s[key] = "claimed";
    expect(() => parse(s)).toThrow();
  }
);
test.each([
  '{"schema_version":"x","schema_version":"y"}',
  '{"a":null,"\\u0061":null}',
  '{"__proto__":null,"__proto__":null}',
  "[] trailing",
  "[null,]",
  '{"x":null,}',
  "\ufeff{}",
  "[true]",
  "[0]",
  "[1e999]",
])("strict parse rejects ambiguous or unsupported JSON %s", (s) =>
  expect(() => C.parse(s)).toThrow()
);
test("duplicate path, missing parent, wrong parent and contradictory complete coverage reject", () => {
  for (const edit of [
    (s) => s.entries.push(clone(s.entries[1])),
    (s) =>
      s.entries.splice(
        s.entries.findIndex((e) => e.path === "Photos"),
        1
      ),
    (s) => {
      s.entries.find((e) => e.path === "Photos").kind = "file";
      s.entries.find((e) => e.path === "Photos").logical_bytes = "0";
    },
    (s) => (s.entries[1].status = "stale"),
    (s) => (s.gaps.error_count = "1"),
    (s) => (s.gaps.stop_reason = "time_limit"),
    (s) => s.gaps.exclusions.push({ reason: "excluded", count: "1" }),
  ]) {
    const s = clone(fixture);
    edit(s);
    expect(() => parse(s)).toThrow();
  }
});
test("empty or non-observed selected root rejects", () => {
  for (const edit of [
    (s) => (s.entries = []),
    (s) => s.entries.shift(),
    (s) => (s.entries[0].status = "stale"),
    (s) => (s.source.coverage = "cancelled"),
  ]) {
    const s = clone(fixture);
    edit(s);
    expect(() => parse(s)).toThrow();
  }
});
test("future snapshot/catalogue version and unknown schema fields reject", () => {
  for (const x of [
    { ...clone(fixture), schema_version: "next" },
    { ...clone(C.empty()), extra: "x" },
  ])
    expect(() => parse(x)).toThrow();
});
test("32 source limit is explicit and atomic", () => {
  let c = C.empty();
  for (let n = 1; n <= 32; n++) c = C.add(c, fixture, "Source " + n, id(n));
  const before = C.exportCatalogue(c);
  expect(() => C.add(c, fixture, "Overflow", id(33))).toThrow(/32/);
  expect(C.exportCatalogue(c)).toBe(before);
});
test("aggregate entry budget rejects without changing earlier catalogue", () => {
  const s = clone(fixture);
  s.entries = [s.entries[0]];
  for (let n = 1; n < 2000; n++)
    s.entries.push({ path: `file-${n}`, kind: "file", status: "observed", logical_bytes: "0" });
  let c = C.empty();
  for (let n = 1; n <= 5; n++) c = C.add(c, s, `S${n}`, id(n));
  expect(c.records.reduce((a, r) => a + r.snapshot.entries.length, 0)).toBe(10000);
  expect(() => C.add(c, fixture, "Overflow", id(6))).toThrow(/10,000/);
  expect(c.records).toHaveLength(5);
});
test("source entry budget and input byte budget reject early", () => {
  const s = clone(fixture);
  s.entries = Array(2001).fill(s.entries[0]);
  expect(() => parse(s)).toThrow(/2,000/);
  expect(() => C.parse(" ".repeat(C.LIMITS.bytes + 1))).toThrow(/4 MiB/);
  expect(() => C.parse("é".repeat(C.LIMITS.bytes / 2 + 1))).toThrow(/4 MiB/);
});
test("depth and duplicate record keys reject", () => {
  expect(() => C.parse("[".repeat(14) + "null" + "]".repeat(14))).toThrow();
  const c = clone(cat());
  c.records.push(clone(c.records[0]));
  expect(() => parse(c)).toThrow(/repeated/);
});
test("hostile-looking inert text survives safely as text and no prototype mutation", () => {
  const s = clone(fixture);
  s.source.label = "<img src=x onerror=alert(1)>";
  s.entries.push({ path: "__proto__", kind: "file", status: "observed", logical_bytes: "0" });
  expect(parse(s).source.label).toBe(s.source.label);
  expect({}.polluted).toBeUndefined();
});
test("manual plan preserves historical origin separately from user label and future intent", () => {
  const c = C.rename(cat(), id(1), "My renamed drive");
  const p = C.buildPlan(c, [selection("Photos")], "Trip project", now);
  expect(p.drives[0].label).toBe("My renamed drive");
  expect(p.items[0].notes).toContain(fixture.source.label);
  expect(p.items[0].notes).toContain("Original relative path: Photos");
  expect(p.items[0].notes).toContain(fixture.source.observed_at);
  expect(p.items[0].notes).toContain("Imported historical snapshot claim");
  expect(p.projects[0].intended_home).toBeUndefined();
  expect(p.backup_targets).toEqual([]);
  expect(M.derive(p).coverage).toBe("unknown");
  expect(M.strictParse(M.exportPlan(p))).toEqual(p);
});
test("manual project can span distinct labelled records with same path", () => {
  const c = C.add(cat(), fixture, "Offline B", id(2)),
    p = C.buildPlan(c, [selection("Photos"), selection("Photos", 2)], "Scattered project", now);
  expect(p.drives).toHaveLength(2);
  expect(p.items).toHaveLength(2);
  expect(new Set(p.items.map((i) => i.location.drive_id)).size).toBe(2);
});
test.each(
  [
    [selection("Photos"), selection("Photos/Trip.jpg")],
    [selection("Photos/Trip.jpg"), selection("Photos")],
    [selection("Photos"), selection("Photos")],
    [selection(".")],
    [selection("missing")],
    [],
    [selection("Photos", 99)],
  ].map((choices) => ({ choices }))
)("invalid or overlapping selection rejects atomically", ({ choices }) => {
  const c = cat(),
    before = C.exportCatalogue(c);
  expect(() => C.buildPlan(c, choices, "Project", now)).toThrow();
  expect(C.exportCatalogue(c)).toBe(before);
});
test("symlinks and stale paths cannot be selected", () => {
  const c = C.add(C.empty(), partial, "Partial", id(1));
  expect(() => C.buildPlan(c, [selection("External link")], "P", now)).toThrow();
  const s = clone(partial);
  s.entries.find((e) => e.path === "Exports").status = "stale";
  const next = C.add(C.empty(), s, "Stale", id(1));
  expect(() => C.buildPlan(next, [selection("Exports")], "P", now)).toThrow();
});
test("unsupported project title and missing record rename preserve input", () => {
  const c = cat();
  expect(() => C.buildPlan(c, [selection("Photos")], " ", now)).toThrow();
  expect(() => C.rename(c, id(2), "Name")).toThrow();
  expect(() => C.rename(c, id(1), " ")).toThrow();
  expect(c.records[0].label).toBe("Offline disk A");
});
test("long Unicode filename exports a valid bounded label with full original path", () => {
  const s = clone(fixture);
  const name = "🌿".repeat(241);
  s.entries.push({ path: name, kind: "file", status: "observed", logical_bytes: "1" });
  const c = C.add(C.empty(), s, "Unicode", id(1)),
    p = C.buildPlan(c, [selection(name)], "Unicode project", now);
  expect(Array.from(p.items[0].label)).toHaveLength(240);
  expect(p.items[0].location.path_text).toBe(name);
  expect(p.items[0].notes).toContain(name);
});

test("Unicode title truncation keeps valid protection labels", () => {
  const p = C.buildPlan(cat(), [selection("Photos")], "x".repeat(219) + "🌿", now);
  expect(p.protection_plans[0].label).toBe("x".repeat(219) + "🌿 protection");
});
