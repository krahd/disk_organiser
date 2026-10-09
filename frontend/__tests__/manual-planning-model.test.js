/** @jest-environment node */
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const Model = require("../manual-planning-model");
const ROOT = path.resolve(__dirname, "../../prototypes/manual_planning");
const fixture = (name = "manual-plan.example.json") =>
  JSON.parse(fs.readFileSync(path.join(ROOT, name), "utf8"));
const copy = (value) => JSON.parse(JSON.stringify(value));
const id = (kind, number) => `${kind}_10000000-0000-0000-0000-${String(number).padStart(12, "0")}`;
const NOW = "2026-10-09T06:00:00.000Z";
const empty = () =>
  Model.createEmptyPlan({ title: "My plan", document_id: id("plan", 1), now: NOW });
const run = (plan, action) =>
  Model.reduce(plan, { expected_revision: plan.revision, now: NOW, ...action });
const reports = () => fixture("manual-reported-result.example.json");
const expectError = (fn, code) => {
  let error;
  try {
    fn();
  } catch (caught) {
    error = caught;
  }
  expect(error).toBeInstanceOf(Model.PlanError);
  if (code) expect(error.code).toBe(code);
  expect(typeof error.path).toBe("string");
};
const mutate = (fn, source = fixture()) => {
  const changed = copy(source);
  fn(changed);
  return changed;
};

describe("manual planning document contract", () => {
  test("embedded schema exactly matches shipped schema", () => {
    expect(Model.schema).toEqual(
      JSON.parse(fs.readFileSync(path.join(ROOT, "manual-storage-plan.schema.json"), "utf8"))
    );
    expect(Object.isFrozen(Model.schema.$defs)).toBe(true);
  });
  test.each(["empty-plan.json", "manual-plan.example.json", "manual-reported-result.example.json"])(
    "strict round trip preserves %s",
    (name) => {
      const original = fixture(name);
      const plan = Model.strictParse(JSON.stringify(original));
      expect(plan).toEqual(original);
      expect(Model.strictParse(Model.exportPlan(plan))).toEqual(original);
      expect(Object.isFrozen(plan)).toBe(true);
      expect(Model.derive(plan).coverage).toBe("unknown");
    }
  );
  test("partial real names need no invented observations or location defaults", () => {
    let plan = empty();
    plan = run(plan, {
      type: "addRecord",
      collection: "drives",
      record: { id: id("drive", 1), label: "My old drive" },
    });
    plan = run(plan, {
      type: "addRecord",
      collection: "projects",
      record: { id: id("project", 1), label: "Archivo familiar", member_item_ids: [] },
    });
    plan = run(plan, {
      type: "addItemToProject",
      project_id: id("project", 1),
      item: { id: id("item", 1), label: "Photos", kind: "folder" },
    });
    expect(plan.items[0]).not.toHaveProperty("location");
    expect(plan.items[0]).not.toHaveProperty("bytes");
    expect(plan.drives[0]).not.toHaveProperty("availability_report");
    expect(Model.derive(plan).warnings.map((w) => w.code)).toEqual(
      expect.arrayContaining([
        "coverage_unknown",
        "identity_unknown",
        "location_missing",
        "descendants_unknown",
      ])
    );
    expect(Model.strictParse(Model.exportPlan(plan))).toEqual(plan);
  });
  test.each([
    [
      "unknown root field",
      (p) => {
        p.verified = true;
      },
    ],
    [
      "synthetic identity field",
      (p) => {
        p.synthetic = false;
      },
    ],
    [
      "future schema",
      (p) => {
        p.schema_version = "disk-organiser/manual-storage-plan/v999";
      },
    ],
    [
      "empty title",
      (p) => {
        p.title = "   ";
      },
    ],
    [
      "title newline",
      (p) => {
        p.title = "A\nB";
      },
    ],
    [
      "NUL title",
      (p) => {
        p.title = "\0bad";
      },
    ],
    [
      "null optional notes",
      (p) => {
        p.items[0].notes = null;
      },
    ],
    [
      "long name",
      (p) => {
        p.items[0].label = "x".repeat(241);
      },
    ],
    [
      "unsafe integer",
      (p) => {
        p.revision = Number.MAX_SAFE_INTEGER + 1;
      },
    ],
    [
      "fractional number",
      (p) => {
        p.revision = 1.2;
      },
    ],
    [
      "negative zero",
      (p) => {
        p.revision = -0;
      },
    ],
    [
      "NaN",
      (p) => {
        p.revision = NaN;
      },
    ],
    [
      "infinity",
      (p) => {
        p.revision = Infinity;
      },
    ],
    [
      "boolean integer",
      (p) => {
        p.revision = true;
      },
    ],
    [
      "negative integer",
      (p) => {
        p.revision = -1;
      },
    ],
    [
      "global duplicated ID",
      (p) => {
        p.drives[1].id = p.document_id;
      },
    ],
    [
      "wrong reference type",
      (p) => {
        p.items[0].location.drive_id = p.backup_targets[0].id;
      },
    ],
    [
      "dangling member",
      (p) => {
        p.projects[0].member_item_ids = [id("item", 99)];
      },
    ],
    [
      "duplicate references",
      (p) => {
        p.projects[0].member_item_ids.push(p.items[0].id);
      },
    ],
    [
      "target credentials",
      (p) => {
        p.backup_targets[0].credentials = "placeholder";
      },
    ],
    [
      "whole drive has path",
      (p) => {
        p.items[0].kind = "whole_drive";
      },
    ],
    [
      "whole drive lacks location",
      (p) => {
        p.items[0].kind = "whole_drive";
        delete p.items[0].location;
      },
    ],
    [
      "bad enum",
      (p) => {
        p.items[0].kind = "device";
      },
    ],
    [
      "unsupported capacity",
      (p) => {
        p.drives[0].capacity = 0;
      },
    ],
    [
      "empty path",
      (p) => {
        p.items[0].location.path_text = "";
      },
    ],
    [
      "bad calendar date",
      (p) => {
        p.protection_plans[0].policy.next_review_on = "2026-02-29";
      },
    ],
    [
      "missing timezone",
      (p) => {
        p.created_at = "2026-10-09T10:00:00";
      },
    ],
    [
      "impossible time",
      (p) => {
        p.created_at = "2026-10-09T25:00:00Z";
      },
    ],
    [
      "unpaired surrogate",
      (p) => {
        p.title = "\ud800";
      },
    ],
    [
      "notes control",
      (p) => {
        p.items[0].notes = "bad\x7f";
      },
    ],
    [
      "too many drives",
      (p) => {
        p.drives = Array.from({ length: 101 }, (_, i) => ({ id: id("drive", i), label: "Drive" }));
      },
    ],
    [
      "policy copies limit",
      (p) => {
        p.protection_plans[0].policy.desired_independent_copies = 11;
      },
    ],
    [
      "policy age limit",
      (p) => {
        p.protection_plans[0].policy.max_acceptable_backup_age_days = 3651;
      },
    ],
    [
      "reports lifecycle without report",
      (p) => {
        p.restore_plans[0].lifecycle = "user_recorded_results";
      },
    ],
    [
      "prepared without selection",
      (p) => {
        p.restore_plans[0].lifecycle = "prepared";
        p.restore_plans[0].item_ids = [];
      },
    ],
  ])("rejects %s without mutating input", (_, change) => {
    const plan = fixture();
    change(plan);
    expectError(() => Model.validatePlan(plan));
  });
  test.each([
    [
      "missing scope",
      (p) => {
        delete p.restore_plans[0].exercise_scope_note;
      },
    ],
    [
      "missing target",
      (p) => {
        delete p.restore_plans[0].target_id;
      },
    ],
    [
      "empty selection",
      (p) => {
        p.restore_plans[0].item_ids = [];
      },
    ],
    [
      "undecided scope",
      (p) => {
        p.restore_plans[0].intended_scope = "undecided";
      },
    ],
    [
      "draft with reports",
      (p) => {
        p.restore_plans[0].lifecycle = "draft";
      },
    ],
    [
      "duplicate check ID",
      (p) => {
        p.restore_plans[0].checks[0].id = p.document_id;
      },
    ],
    [
      "duplicate report ID",
      (p) => {
        p.restore_plans[0].checks[2].user_reports[0].id = p.document_id;
      },
    ],
    [
      "extra verified field",
      (p) => {
        p.restore_plans[0].checks[2].user_reports[0].verified = true;
      },
    ],
  ])("rejects reported exercise %s", (_, change) =>
    expectError(() => Model.validatePlan(mutate(change, reports())))
  );
  test.each([
    [
      "missing location",
      (p) => {
        delete p.items[0].location;
      },
    ],
    [
      "Windows path",
      (p) => {
        p.items[0].location.path_text = "C:\\Users\\Example\\Pictures";
      },
    ],
    [
      "relative path",
      (p) => {
        p.items[0].location.path_text = "../../Pictures";
      },
    ],
    [
      "hostile text",
      (p) => {
        p.items[0].label = "<img src=x onerror=alert(1)>";
      },
    ],
    [
      "same drive labels",
      (p) => {
        p.drives[0].label = p.drives[1].label;
      },
    ],
    [
      "archived drive",
      (p) => {
        p.drives[0].archived = true;
      },
    ],
    [
      "whole drive explicit",
      (p) => {
        p.items[0].kind = "whole_drive";
        delete p.items[0].location.path_text;
      },
    ],
    [
      "Unicode",
      (p) => {
        p.title = "📷".repeat(240);
        p.items[0].notes = "日本語\nPhoto\tproject";
      },
    ],
    [
      "leap day",
      (p) => {
        p.protection_plans[0].policy.next_review_on = "2028-02-29";
      },
    ],
    [
      "offset timestamp",
      (p) => {
        p.created_at = "2026-10-09T03:12:45.123456-03:00";
      },
    ],
    [
      "max revision",
      (p) => {
        p.revision = Number.MAX_SAFE_INTEGER;
      },
    ],
  ])("preserves %s as manual data", (_, change) => {
    const p = mutate(change);
    expect(Model.strictParse(Model.exportPlan(p))).toEqual(p);
  });
  test("former membership/target discrepancies remain nonblocking warnings", () => {
    const plan = reports();
    plan.projects[0].member_item_ids = [];
    plan.protection_plans[0].target_ids = [];
    const codes = Model.validatePlan(plan).warnings.map((w) => w.code);
    expect(codes).toEqual(
      expect.arrayContaining(["former_exclusion", "historical_scope", "historical_target"])
    );
    expect(Model.strictParse(Model.exportPlan(plan)).restore_plans).toEqual(plan.restore_plans);
  });
});

describe("strict bounded import", () => {
  test.each([
    '{"title":"a","title":"b"}',
    '{"title":"a","ti\\u0074le":"b"}',
    '{"x":1.0}',
    '{"x":1e1}',
    '{"x":NaN}',
    '{"x":Infinity}',
    '{"x":-0}',
    '{"x":9007199254740992}',
    '{"x":01}',
    '{"x":+1}',
    '{"x":.1}',
    '{"x":true,}',
    "[1,]",
    '{"x":"\\ud800"}',
    '{"x":"\\udc00"}',
    '{"x":"unterminated}',
    '{"x":"bad\ntext"}',
    '{"x":"\\x22"}',
    "\ufeff{}",
    "{}{}",
    "",
    "null",
    "[]",
    "true",
    '{"__proto__":{"polluted":true}}',
    '{"constructor":{"prototype":{"polluted":true}}}',
  ])("rejects unsupported JSON %s", (raw) => {
    expectError(() => Model.strictParse(raw));
    expect({}.polluted).toBeUndefined();
  });
  test("rejects depth before parsing nested values", () => {
    expectError(() => Model.strictParse("[".repeat(25) + "0" + "]".repeat(25)), "depth_limit");
    expectError(() => Model.strictParse("[".repeat(24) + "0" + "]".repeat(24)), "type");
  });
  test("raw bytes cap includes whitespace and multi-byte Unicode", () => {
    const compact = Model.exportPlan(empty());
    const size = Buffer.byteLength(compact);
    expect(Model.strictParse(compact + " ".repeat(Model.LIMITS.bytes - size))).toEqual(empty());
    expectError(
      () => Model.strictParse(compact + " ".repeat(Model.LIMITS.bytes - size + 1)),
      "byte_limit"
    );
    expectError(() => Model.strictParse('"' + "📷".repeat(262144) + '"'), "byte_limit");
  });
  test("escaped Unicode and nested key pollution never affect object prototypes", () => {
    expectError(() => Model.strictParse('{"\\u005f_proto__":{}}'));
    const p = fixture();
    p.items[0].label = '\\"{\\"__proto__\\":1}\\"';
    expect(Model.strictParse(JSON.stringify(p))).toEqual(p);
  });
  test("node budget precedes schema admission", () => {
    expectError(
      () => Model.strictParse("[" + Array(100001).fill("0").join(",") + "]"),
      "node_limit"
    );
  });
  test.each([
    [
      "getter",
      () => {
        const p = fixture();
        Object.defineProperty(p, "title", {
          get() {
            throw new Error("must not run");
          },
          enumerable: true,
        });
        return p;
      },
    ],
    [
      "toJSON",
      () => {
        const p = fixture();
        p.toJSON = () => {
          throw new Error("must not run");
        };
        return p;
      },
    ],
    ["custom prototype", () => Object.assign(Object.create({ custom: true }), fixture())],
    ["undefined", () => ({ ...fixture(), title: undefined })],
    ["sparse array", () => ({ ...fixture(), drives: new Array(2) })],
    [
      "extra array field",
      () => {
        const p = fixture();
        p.drives.foo = "x";
        return p;
      },
    ],
    [
      "symbol",
      () => {
        const p = fixture();
        p[Symbol("x")] = 1;
        return p;
      },
    ],
    [
      "cycle",
      () => {
        const p = fixture();
        p.drives.push(p);
        return p;
      },
    ],
    [
      "alias object",
      () => {
        const p = fixture();
        p.drives.push(p.drives[0]);
        return p;
      },
    ],
    [
      "hidden key",
      () => {
        const p = fixture();
        Object.defineProperty(p, "hidden", { value: 1 });
        return p;
      },
    ],
  ])("rejects non-JSON runtime input %s", (_, make) =>
    expectError(() => Model.validatePlan(make()), "json_type")
  );
  test("preflight bounds oversized runtime objects before serialising", () => {
    const p = fixture();
    p.title = "x".repeat(Model.LIMITS.bytes);
    const stringify = jest.spyOn(JSON, "stringify");
    expectError(() => Model.exportPlan(p), "byte_limit");
    expect(stringify).not.toHaveBeenCalled();
    stringify.mockRestore();
  });
});

describe("immutable edits and retained history", () => {
  test("atomic batch resolves new references and advances once", () => {
    const before = empty();
    const next = run(before, {
      type: "batch",
      edits: [
        {
          type: "addRecord",
          collection: "drives",
          record: { id: id("drive", 1), label: "Laptop" },
        },
        {
          type: "addRecord",
          collection: "projects",
          record: { id: id("project", 1), label: "Photos", member_item_ids: [] },
        },
        {
          type: "addItemToProject",
          project_id: id("project", 1),
          item: {
            id: id("item", 1),
            label: "Recent",
            kind: "folder",
            location: { drive_id: id("drive", 1) },
          },
        },
      ],
    });
    expect(next.revision).toBe(2);
    expect(next.created_at).toBe(before.created_at);
    expect(next.projects[0].member_item_ids).toEqual([id("item", 1)]);
    expect(before.items).toHaveLength(0);
    expect(Object.isFrozen(next.projects[0].member_item_ids)).toBe(true);
  });
  test("failed batch leaves all previous state unchanged", () => {
    const p = empty();
    const original = Model.exportPlan(p);
    expectError(() =>
      run(p, {
        type: "batch",
        edits: [
          { type: "setTitle", title: "New name" },
          {
            type: "addRecord",
            collection: "items",
            record: { id: id("item", 1), label: "Bad", kind: "whole_drive" },
          },
        ],
      })
    );
    expect(Model.exportPlan(p)).toBe(original);
  });
  test("stale and repeated actions cannot append accidental duplicate reports", () => {
    const p = reports();
    const exercise = p.restore_plans[0];
    const action = {
      type: "appendReport",
      expected_revision: p.revision,
      now: NOW,
      restore_plan_id: exercise.id,
      check_id: exercise.checks[2].id,
      report: { id: id("report", 9), result: "reports_fail" },
    };
    const next = Model.reduce(p, action);
    expectError(() => Model.reduce(next, action), "stale_revision");
    expectError(
      () => Model.reduce(next, { ...action, expected_revision: next.revision }),
      "duplicate_id"
    );
    expect(next.restore_plans[0].checks[2].user_reports).toHaveLength(2);
  });
  test("same-time contradictory reports stay distinct and ordered", () => {
    const p = reports();
    const exercise = p.restore_plans[0];
    const first = exercise.checks[2].user_reports[0];
    const next = run(p, {
      type: "appendReport",
      now: first.recorded_at,
      restore_plan_id: exercise.id,
      check_id: exercise.checks[2].id,
      report: {
        id: id("report", 12),
        result: "reports_fail",
        notes: "Different result on the same sample",
      },
    });
    expect(next.restore_plans[0].checks[2].user_reports.map((r) => r.result)).toEqual([
      "reports_pass",
      "reports_fail",
    ]);
    expect(Model.derive(next).coverage).toBe("unknown");
    expect(Model.derive(next).counts.reports).toBe(3);
  });
  test("append records explicit scope then freezes definitions", () => {
    const p = fixture();
    const exercise = p.restore_plans[0];
    exercise.exercise_scope_note = "Three images; exact versions unknown.";
    const next = run(p, {
      type: "appendReport",
      restore_plan_id: exercise.id,
      check_id: exercise.checks[0].id,
      report: { id: id("report", 1), result: "inconclusive" },
    });
    expect(next.restore_plans[0].lifecycle).toBe("user_recorded_results");
    expect(next.restore_plans[0].checks[0].user_reports[0].recorded_at).toBe(NOW);
    expect(p.restore_plans[0].checks[0]).not.toHaveProperty("user_reports");
  });
  test.each([
    [
      "target",
      (r) => {
        r.target_id = id("target", 999);
      },
    ],
    [
      "items",
      (r) => {
        r.item_ids = [];
      },
    ],
    [
      "scope",
      (r) => {
        r.intended_scope = "whole_planned_scope";
      },
    ],
    [
      "scope description",
      (r) => {
        r.exercise_scope_note = "Something else";
      },
    ],
    [
      "snapshot",
      (r) => {
        r.snapshot_reference_text = "New snapshot";
      },
    ],
    [
      "destination",
      (r) => {
        delete r.destination;
      },
    ],
    [
      "check label",
      (r) => {
        r.checks[0].label = "Changed";
      },
    ],
    [
      "check kind",
      (r) => {
        r.checks[0].kind = "other";
      },
    ],
    [
      "check removed",
      (r) => {
        r.checks.shift();
      },
    ],
    [
      "check archived",
      (r) => {
        r.checks[0].archived = true;
      },
    ],
    [
      "reported result",
      (r) => {
        r.checks[2].user_reports[0].result = "reports_fail";
      },
    ],
    [
      "report removed",
      (r) => {
        r.checks[2].user_reports = [];
      },
    ],
  ])("cannot rebind frozen %s", (_, change) => {
    const p = reports();
    const record = copy(p.restore_plans[0]);
    change(record);
    expectError(() => run(p, { type: "replaceRecord", collection: "restore_plans", record }));
  });
  test("reported exercise can be labelled, annotated and archived", () => {
    const p = reports();
    const old = copy(p.restore_plans[0]);
    const next = run(p, {
      type: "replaceRecord",
      collection: "restore_plans",
      record: { ...old, label: "Keep this history", notes: "Recorded elsewhere", archived: true },
    });
    expect(next.restore_plans[0].checks).toEqual(old.checks);
    expect(next.restore_plans[0].archived).toBe(true);
    expectError(
      () => run(next, { type: "deleteRecord", collection: "restore_plans", id: old.id }),
      "append_only"
    );
  });
  test("generic add/replace cannot manufacture or remove report history", () => {
    const p = reports();
    const record = copy(p.restore_plans[0]);
    record.id = id("restore", 7);
    expectError(
      () => run(p, { type: "addRecord", collection: "restore_plans", record }),
      "append_only"
    );
    const draft = fixture();
    record.id = draft.restore_plans[0].id;
    expectError(
      () => run(draft, { type: "replaceRecord", collection: "restore_plans", record }),
      "append_only"
    );
  });
  test("same-batch report creation freezes subsequent edits and deletion", () => {
    const p = fixture();
    const r = p.restore_plans[0];
    const first = {
      type: "appendReport",
      restore_plan_id: r.id,
      check_id: r.checks[0].id,
      report: { id: id("report", 30), result: "reports_pass" },
    };
    expectError(
      () =>
        run(p, {
          type: "batch",
          edits: [first, { type: "deleteRecord", collection: "restore_plans", id: r.id }],
        }),
      "append_only"
    );
    expectError(
      () =>
        run(p, {
          type: "batch",
          edits: [
            first,
            { type: "replaceRecord", collection: "restore_plans", record: { ...r, label: "New" } },
          ],
        }),
      "append_only"
    );
  });
  test("referenced deletion never cascades; archival retains scope", () => {
    const p = fixture();
    const drive = p.drives[0];
    expectError(
      () => run(p, { type: "deleteRecord", collection: "drives", id: drive.id }),
      "reference"
    );
    const next = run(p, {
      type: "archiveRecord",
      collection: "drives",
      id: drive.id,
      archived: true,
    });
    expect(next.items).toEqual(p.items);
    expect(next.protection_plans).toEqual(p.protection_plans);
    const project = p.projects[0];
    const archived = run(p, {
      type: "archiveRecord",
      collection: "items",
      id: p.items[0].id,
      archived: true,
    });
    expect(archived.projects[0].member_item_ids).toEqual(project.member_item_ids);
  });
  test("explicitly resolved unreported deletions are atomic", () => {
    const p = fixture();
    const restore = p.restore_plans[0];
    const next = run(p, {
      type: "batch",
      edits: [
        { type: "deleteRecord", collection: "restore_plans", id: restore.id },
        { type: "deleteRecord", collection: "protection_plans", id: p.protection_plans[0].id },
      ],
    });
    expect(next.protection_plans).toEqual([]);
    expect(next.restore_plans).toEqual([]);
    expect(next.revision).toBe(p.revision + 1);
  });
  test("project and target changes retain historical checklist and discrepancy", () => {
    const p = reports();
    const next = run(p, {
      type: "batch",
      edits: [
        {
          type: "replaceRecord",
          collection: "projects",
          record: { ...p.projects[0], member_item_ids: [] },
        },
        {
          type: "replaceRecord",
          collection: "protection_plans",
          record: { ...p.protection_plans[0], target_ids: [] },
        },
      ],
    });
    expect(next.restore_plans).toEqual(p.restore_plans);
    expect(Model.derive(next).warnings.map((w) => w.code)).toEqual(
      expect.arrayContaining(["historical_scope", "historical_target"])
    );
  });
  test("no-op is stable and revision overflow fails without losing data", () => {
    const p = empty();
    expect(run(p, { type: "setTitle", title: p.title })).toBe(p);
    const max = { ...p, revision: Number.MAX_SAFE_INTEGER };
    expect(run(max, { type: "setTitle", title: max.title })).toBe(max);
    expectError(() => run(max, { type: "setTitle", title: "New" }), "revision_limit");
    expect(max.title).toBe(p.title);
  });
  test.each([
    { type: "futureAction" },
    { type: "batch", edits: [] },
    { type: "batch", edits: Array(101).fill({ type: "setTitle", title: "A" }) },
    { type: "batch", edits: [{ type: "batch", edits: [] }] },
    { type: "setTitle", title: "A", unexpected: true },
    { type: "addRecord", collection: "unknown", record: {} },
    { type: "addRecord", collection: "restore_plans", record: { checks: [null] } },
    {
      type: "replaceRecord",
      collection: "drives",
      record: { id: id("drive", 55), label: "Missing" },
    },
    { type: "archiveRecord", collection: "drives", id: id("drive", 55), archived: true },
    { type: "setTitle", title: "A", now: "2026-99-99T00:00:00Z" },
  ])("malformed actions fail atomically: %j", (action) => {
    const p = empty();
    expectError(() => run(p, action));
    expect(p.revision).toBe(1);
  });
});

describe("staged atomic workspace replacement", () => {
  test("preview is private-data-aware and replacement preserves imported revision/history", () => {
    const p = empty();
    const incoming = reports();
    const token = Model.stageImport(JSON.stringify(incoming), p);
    expect(token.preview.counts.reports).toBe(2);
    expect(token.preview.privacy).toMatch(/private/);
    expect(Object.isFrozen(token.document.restore_plans[0].checks)).toBe(true);
    expectError(() => Model.replaceImport(p, token, { confirm: false }), "confirmation");
    const next = Model.replaceImport(p, token, { confirm: true });
    expect(next).toEqual(incoming);
    expectError(() => Model.replaceImport(p, token, { confirm: true }), "import_token");
  });
  test("failed import keeps existing workspace", () => {
    const p = reports();
    const before = Model.exportPlan(p);
    expectError(() => Model.stageImport('{"oops":1}', p));
    expect(Model.exportPlan(p)).toBe(before);
  });
  test("cancel and forged token cannot replace workspace", () => {
    const p = empty();
    const token = Model.stageImport(JSON.stringify(fixture()), p);
    Model.cancelImport(token);
    expectError(() => Model.replaceImport(p, token, { confirm: true }), "import_token");
    expectError(
      () => Model.replaceImport(p, { document: fixture() }, { confirm: true }),
      "import_token"
    );
  });
  test("stale preview detects revision, identity and content changes", () => {
    const p = empty();
    const token = Model.stageImport(JSON.stringify(fixture()), p);
    const changed = run(p, { type: "setTitle", title: "New" });
    expectError(() => Model.replaceImport(changed, token, { confirm: true }), "stale_revision");
    expectError(
      () =>
        Model.replaceImport({ ...p, title: "Same revision, altered content" }, token, {
          confirm: true,
        }),
      "stale_revision"
    );
    expectError(
      () => Model.replaceImport({ ...p, document_id: id("plan", 2) }, token, { confirm: true }),
      "stale_revision"
    );
  });
  test("separate previews never merge two documents", () => {
    const p = empty();
    const first = Model.stageImport(JSON.stringify(fixture()), p);
    const second = Model.stageImport(JSON.stringify(reports()), p);
    const next = Model.replaceImport(p, first, { confirm: true });
    expectError(() => Model.replaceImport(next, second, { confirm: true }), "stale_revision");
  });
});

describe("independent browser module boundary", () => {
  test("loads with no app, filesystem, provider, network or storage primitives", () => {
    const source = fs.readFileSync(path.resolve(__dirname, "../manual-planning-model.js"), "utf8");
    const forbidden = jest.fn(() => {
      throw new Error("Unexpected external operation");
    });
    const sandbox = {
      fetch: forbidden,
      XMLHttpRequest: forbidden,
      localStorage: { getItem: forbidden, setItem: forbidden },
      document: undefined,
      require: forbidden,
    };
    vm.runInNewContext(source, sandbox);
    const browser = sandbox.ManualPlanningModel;
    const p = browser.strictParse(JSON.stringify(fixture()));
    expect(browser.exportPlan(p)).toBe(Model.exportPlan(fixture()));
    sandbox.plan = p;
    sandbox.actionJson = JSON.stringify({
      type: "setTitle",
      title: "Real plan",
      expected_revision: p.revision,
      now: NOW,
    });
    const changed = vm.runInNewContext(
      "ManualPlanningModel.reduce(plan, JSON.parse(actionJson))",
      sandbox
    );
    browser.derive(changed);
    const token = browser.stageImport(browser.exportPlan(p), changed);
    browser.replaceImport(changed, token, { confirm: true });
    expect(forbidden).not.toHaveBeenCalled();
  });
  test("random ID helper returns record keys without device identity", () => {
    const value = Model.newId("drive");
    expect(value).toMatch(/^drive_[0-9a-f-]{36}$/);
    expect(Model.newId("drive")).not.toBe(value);
    expectError(() => Model.newId("invalid prefix"), "id");
  });
});

describe("adversarial representation regressions", () => {
  test.each([
    "toString",
    "__proto__",
    "constructor",
    "hasOwnProperty",
    "valueOf",
    [],
    {},
    true,
    7,
    null,
  ])("rejects inherited or non-text action type %j with a controlled error", (type) =>
    expectError(() => run(empty(), { type }), "command")
  );
  test.each(["\u0085", "\u2028", "\u2029", "\u0080", "\u009f"])(
    "single-line fields reject control/line separator U+%s",
    (control) => {
      for (const field of ["title", "path_text"]) {
        const p = fixture();
        if (field === "title") p.title = `a${control}b`;
        else p.items[0].location.path_text = `a${control}b`;
        expectError(() => Model.strictParse(JSON.stringify(p)), "control_character");
      }
    }
  );
  test.each(["\u0080", "\u0085", "\u009f"])("notes reject C1 control %s", (control) => {
    const p = fixture();
    p.items[0].notes = `a${control}b`;
    expectError(() => Model.validatePlan(p), "control_character");
  });
  test("multiline notes retain ordinary whitespace and paragraph separators", () => {
    const p = fixture();
    p.items[0].notes = "First\tline\r\nSecond\u2028third\u2029fourth";
    expect(Model.strictParse(Model.exportPlan(p))).toEqual(p);
  });
  test.each([undefined, null, true, ["drive"], { prefix: "drive" }])(
    "ID helper requires a string prefix: %j",
    (prefix) => {
      expectError(() => Model.newId(prefix), "id");
    }
  );
  test("no-op edit cannot bypass timestamp type validation", () => {
    const p = empty();
    expectError(() => run(p, { type: "setTitle", title: p.title, now: [NOW] }), "timestamp");
  });
});

describe("semantic equality and collection limits", () => {
  test("object key order does not rewrite report history or generate no-op revisions", () => {
    const p = Model.strictParse(Model.exportPlan(reports()));
    const reorder = (value) =>
      Array.isArray(value)
        ? value.map(reorder)
        : value && typeof value === "object"
        ? Object.fromEntries(
            Object.entries(value)
              .reverse()
              .map(([k, v]) => [k, reorder(v)])
          )
        : value;
    const reordered = reorder(p.restore_plans[0]);
    expect(run(p, { type: "replaceRecord", collection: "restore_plans", record: reordered })).toBe(
      p
    );
    const next = run(p, {
      type: "replaceRecord",
      collection: "restore_plans",
      record: { ...reordered, label: "Renamed" },
    });
    expect(next.restore_plans[0].checks).toEqual(p.restore_plans[0].checks);
  });
  test.each([
    ["drives", 100, { label: "Drive" }],
    ["items", 2000, { label: "Scope", kind: "folder" }],
    ["projects", 200, { label: "Project", member_item_ids: [] }],
    ["backup_targets", 100, { label: "Target", kind: "unspecified" }],
    [
      "protection_plans",
      500,
      {
        label: "Protection",
        project_id: id("project", 1),
        target_ids: [],
        excluded_item_ids: [],
        policy: {},
      },
    ],
    [
      "restore_plans",
      500,
      {
        label: "Checklist",
        protection_plan_id: id("protect", 1),
        intended_scope: "undecided",
        item_ids: [],
        lifecycle: "draft",
        checks: [],
      },
    ],
  ])("enforces exact %s collection bound", (collection, limit, fields) => {
    const p = copy(empty());
    p.projects = [{ id: id("project", 1), label: "Project", member_item_ids: [] }];
    p.protection_plans = [
      {
        id: id("protect", 1),
        label: "Plan",
        project_id: id("project", 1),
        target_ids: [],
        excluded_item_ids: [],
        policy: {},
      },
    ];
    if (collection === "projects") p.protection_plans = [];
    const prefix = {
      drives: "drive",
      items: "item",
      projects: "project",
      backup_targets: "target",
      protection_plans: "protect",
      restore_plans: "restore",
    }[collection];
    p[collection] = Array.from({ length: limit }, (_, i) => ({
      id: id(prefix, i + 1),
      ...copy(fields),
    }));
    expect(() => Model.validatePlan(p)).not.toThrow();
    p[collection].push({ id: id(prefix, limit + 1), ...copy(fields) });
    expectError(() => Model.validatePlan(p), "array_limit");
  });
  test("fiftieth report is retained and fifty-first fails atomically", () => {
    const p = reports();
    const check = p.restore_plans[0].checks[2];
    check.user_reports = Array.from({ length: 49 }, (_, i) => ({
      id: id("report", i + 100),
      result: "inconclusive",
      recorded_at: NOW,
    }));
    p.restore_plans[0].reported_context.first_report_id = check.user_reports[0].id;
    p.restore_plans[0].reported_context.captured_at = NOW;
    const action = {
      type: "appendReport",
      restore_plan_id: p.restore_plans[0].id,
      check_id: check.id,
      report: { id: id("report", 999), result: "reports_pass" },
    };
    const next = run(p, action);
    expect(next.restore_plans[0].checks[2].user_reports).toHaveLength(50);
    expectError(
      () => run(next, { ...action, report: { ...action.report, id: id("report", 1000) } }),
      "array_limit"
    );
    expect(next.restore_plans[0].checks[2].user_reports).toHaveLength(50);
  });
});

describe("immutable report-time context", () => {
  test("first report captures labels, destinations and user-described versions", () => {
    const p = fixture();
    const exercise = p.restore_plans[0];
    exercise.exercise_scope_note = "Three images; versions unknown.";
    p.items[0].described_version = "Final export";
    const next = run(p, {
      type: "appendReport",
      restore_plan_id: exercise.id,
      check_id: exercise.checks[2].id,
      report: { id: id("report", 81), result: "reports_pass" },
    });
    const context = next.restore_plans[0].reported_context;
    expect(context.captured_at).toBe(NOW);
    expect(context.first_report_id).toBe(id("report", 81));
    expect(context.items[0]).toMatchObject({
      label: "Recent photos",
      described_version: "Final export",
      location: { drive_label: "Laptop" },
    });
    expect(context.target).toMatchObject({
      label: "Local photo backup",
      storage_drive_label: "Backup drive",
    });
    expect(context.destination).toMatchObject({
      drive_label: "Laptop",
      path_text: exercise.destination.path_text,
    });
    expect(context.protection_plan.project_label).toBe(p.projects[0].label);
    expect(Object.isFrozen(context.items[0].location)).toBe(true);
  });
  test("current location/provider/version corrections preserve historical meaning", () => {
    const p = reports();
    const context = copy(p.restore_plans[0].reported_context);
    const next = run(p, {
      type: "batch",
      edits: [
        {
          type: "replaceRecord",
          collection: "items",
          record: {
            ...p.items[0],
            label: "Corrected name",
            kind: "file",
            described_version: "New final",
            location: { drive_id: p.drives[1].id, path_text: "Other/image.jpg" },
          },
        },
        {
          type: "replaceRecord",
          collection: "backup_targets",
          record: {
            ...p.backup_targets[0],
            label: "New target name",
            kind: "object_storage",
            storage_drive_id: p.drives[1].id,
            provider_name: "Other provider",
            account_nickname: "Work",
          },
        },
        {
          type: "replaceRecord",
          collection: "drives",
          record: { ...p.drives[0], label: "Different current name" },
        },
        {
          type: "replaceRecord",
          collection: "projects",
          record: { ...p.projects[0], label: "Renamed project" },
        },
      ],
    });
    expect(next.restore_plans[0].reported_context).toEqual(context);
    expect(next.items[0].label).toBe("Corrected name");
    expect(Model.derive(next).warnings.map((w) => w.code)).toContain("historical_context_drift");
    expect(Model.strictParse(Model.exportPlan(next))).toEqual(next);
  });
  test("later reports retain first context even after current records change", () => {
    const p = reports();
    const context = copy(p.restore_plans[0].reported_context);
    const changed = run(p, {
      type: "replaceRecord",
      collection: "items",
      record: { ...p.items[0], label: "Changed" },
    });
    const r = changed.restore_plans[0];
    const next = run(changed, {
      type: "appendReport",
      restore_plan_id: r.id,
      check_id: r.checks[2].id,
      report: { id: id("report", 82), result: "reports_fail" },
    });
    expect(next.restore_plans[0].reported_context).toEqual(context);
    expect(next.restore_plans[0].checks[2].user_reports).toHaveLength(2);
  });
  test("same-batch corrections after first report do not rewrite captured context", () => {
    const p = fixture();
    const r = p.restore_plans[0];
    r.exercise_scope_note = "Exact user-described sample";
    const next = run(p, {
      type: "batch",
      edits: [
        {
          type: "appendReport",
          restore_plan_id: r.id,
          check_id: r.checks[0].id,
          report: { id: id("report", 83), result: "inconclusive" },
        },
        {
          type: "replaceRecord",
          collection: "items",
          record: { ...p.items[0], label: "New current label" },
        },
      ],
    });
    expect(next.restore_plans[0].reported_context.items[0].label).toBe(p.items[0].label);
    expect(Model.derive(next).warnings.map((w) => w.code)).toContain("historical_context_drift");
  });
  test.each([
    [
      "missing snapshot",
      (r) => {
        delete r.reported_context;
      },
    ],
    [
      "wrong target",
      (r) => {
        r.reported_context.target.id = id("target", 555);
      },
    ],
    [
      "wrong item",
      (r) => {
        r.reported_context.items[0].id = id("item", 555);
      },
    ],
    [
      "wrong plan",
      (r) => {
        r.reported_context.protection_plan.id = id("protect", 555);
      },
    ],
    [
      "missing historical project",
      (r) => {
        r.reported_context.protection_plan.project_id = id("project", 555);
      },
    ],
    [
      "missing first report",
      (r) => {
        r.reported_context.first_report_id = id("report", 555);
      },
    ],
    [
      "wrong first time",
      (r) => {
        r.reported_context.captured_at = NOW;
      },
    ],
    [
      "missing paired drive label",
      (r) => {
        delete r.reported_context.target.storage_drive_label;
      },
    ],
    [
      "wrong destination",
      (r) => {
        r.reported_context.destination.path_text = "Other destination";
      },
    ],
    [
      "missing destination",
      (r) => {
        delete r.reported_context.destination;
      },
    ],
    [
      "historical whole-drive path",
      (r) => {
        r.reported_context.items[0].kind = "whole_drive";
      },
    ],
    [
      "unsupported authority",
      (r) => {
        r.reported_context.verified = true;
      },
    ],
  ])("rejects imported history context %s", (_, change) => {
    const p = reports();
    change(p.restore_plans[0]);
    expectError(() => Model.strictParse(JSON.stringify(p)));
  });
  test("drafts cannot pre-author a snapshot", () => {
    const p = fixture();
    p.restore_plans[0].reported_context = reports().restore_plans[0].reported_context;
    expectError(() => Model.validatePlan(p), "reported_context");
  });
  test("record replacement cannot rewrite captured names", () => {
    const p = reports();
    const record = copy(p.restore_plans[0]);
    record.reported_context.items[0].label = "Rewrite history";
    expectError(
      () => run(p, { type: "replaceRecord", collection: "restore_plans", record }),
      "frozen_exercise"
    );
  });
  test("historical-only drive and project references remain retained", () => {
    const p = reports();
    const next = run(p, {
      type: "replaceRecord",
      collection: "backup_targets",
      record: { id: p.backup_targets[0].id, label: "Changed", kind: "other" },
    });
    expectError(
      () => run(next, { type: "deleteRecord", collection: "drives", id: p.drives[2].id }),
      "reference"
    );
    const newProject = { id: id("project", 80), label: "New grouping", member_item_ids: [] };
    const changed = run(p, {
      type: "batch",
      edits: [
        { type: "addRecord", collection: "projects", record: newProject },
        {
          type: "replaceRecord",
          collection: "protection_plans",
          record: { ...p.protection_plans[0], project_id: newProject.id },
        },
      ],
    });
    expectError(
      () => run(changed, { type: "deleteRecord", collection: "projects", id: p.projects[0].id }),
      "reference"
    );
  });
  test.each([" ", "\t\n", "\u00a0", "\u2003"])(
    "all required human text rejects whitespace %j",
    (text) => {
      for (const field of ["title", "label", "exercise_scope_note"]) {
        const p = reports();
        if (field === "title") p.title = text;
        else if (field === "label") p.drives[0].label = text;
        else p.restore_plans[0].exercise_scope_note = text;
        expectError(() => Model.validatePlan(p));
      }
    }
  );
});

test("snapshot expansion fails closed at the document cap without truncation", () => {
  const p = fixture();
  p.items = Array.from({ length: 1500 }, (_, i) => ({
    id: id("item", i + 1),
    label: "x".repeat(240),
    kind: "folder",
  }));
  p.projects[0].member_item_ids = p.items.map((item) => item.id);
  p.protection_plans[0].excluded_item_ids = [];
  const exercise = p.restore_plans[0];
  exercise.item_ids = p.items.map((item) => item.id);
  exercise.exercise_scope_note = "All named scopes; descendants and exact versions unknown.";
  const before = Model.exportPlan(p);
  expect(Buffer.byteLength(before)).toBeLessThan(Model.LIMITS.bytes);
  expectError(
    () =>
      run(p, {
        type: "appendReport",
        restore_plan_id: exercise.id,
        check_id: exercise.checks[0].id,
        report: { id: id("report", 500), result: "inconclusive" },
      }),
    "byte_limit"
  );
  expect(Model.exportPlan(p)).toBe(before);
  expect(exercise).not.toHaveProperty("reported_context");
});
