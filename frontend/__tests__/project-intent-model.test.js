const fs = require("fs");
const path = require("path");
const fixture = require("./project-observation-fixture.json");
const modulePath = path.join(__dirname, "../project-intent-model.js");
const model = require(modulePath);
const copy = (value) => JSON.parse(JSON.stringify(value));
function choices() {
  const selected = new Map(
    fixture.decision.member_paths.map((member) => [member.entry_id, member.project_path])
  );
  return {
    members: fixture.choices.map((choice) => ({
      entry_id: choice.entry.id,
      included: selected.has(choice.entry.id),
      project_path: selected.get(choice.entry.id) || choice.default_project_path,
    })),
    destination_root_id: fixture.decision.destination_root_id,
    destination_folder: "Saved Aurora",
  };
}
function document() {
  return JSON.parse(model.serialise(choices(), fixture));
}

test("project choices have an independent resumable intent contract", () => {
  expect(fs.existsSync(modulePath)).toBe(true);
  const model = require(modulePath);
  const selected = new Map(
    fixture.decision.member_paths.map((member) => [member.entry_id, member.project_path])
  );
  const intent = {
    members: fixture.choices.map((choice) => ({
      entry_id: choice.entry.id,
      included: selected.has(choice.entry.id),
      project_path: selected.get(choice.entry.id) || choice.default_project_path,
    })),
    destination_root_id: fixture.decision.destination_root_id,
    destination_folder: "Saved Aurora",
  };
  const text = model.serialise(intent, fixture);
  expect(model.parse(text, fixture)).toEqual(intent);
  expect(JSON.parse(text).document_kind).toBe("user_authored_project_intent");
  expect(text).not.toContain("acknowledged");
  expect(text).not.toContain("fingerprint");
});

test("unchecked edits survive and selected members project in reference order", () => {
  const intent = choices();
  intent.members[3].project_path = "../unfinished: <b>é😀</b>";
  intent.members[4].project_path = "";
  intent.members.reverse();
  const reopened = model.parse(model.serialise(intent, fixture), fixture);
  expect(reopened.members.map((member) => member.entry_id)).toEqual(
    fixture.choices.map((choice) => choice.entry.id)
  );
  expect(reopened.members[3].project_path).toBe("../unfinished: <b>é😀</b>");
  expect(reopened.members[4].project_path).toBe("");
  expect(model.requestFor(reopened, fixture).member_paths).toEqual(fixture.decision.member_paths);
});

test.each([
  [
    "extra root",
    (value) => {
      value.evidence = {};
    },
  ],
  [
    "wrong version",
    (value) => {
      value.schema_version = "other/v1";
    },
  ],
  [
    "display report",
    (value) => {
      value.document_kind = "synthetic_display_report";
    },
  ],
  [
    "source extra evidence",
    (value) => {
      value.source.hash = "trusted";
    },
  ],
  [
    "source real flag",
    (value) => {
      value.source.kind = "real";
    },
  ],
  [
    "scenario",
    (value) => {
      value.source.scenario_id = "another";
    },
  ],
  [
    "zero revision",
    (value) => {
      value.source.source_revision = 0;
    },
  ],
  [
    "string revision",
    (value) => {
      value.source.source_revision = "1";
    },
  ],
  [
    "null revision",
    (value) => {
      value.source.source_revision = null;
    },
  ],
  [
    "fraction revision",
    (value) => {
      value.source.source_revision = 1.5;
    },
  ],
  [
    "digest type",
    (value) => {
      value.source.observation_digest = 1;
    },
  ],
  [
    "digest uppercase",
    (value) => {
      value.source.observation_digest = "A".repeat(64);
    },
  ],
  [
    "digest short",
    (value) => {
      value.source.observation_digest = "a";
    },
  ],
  [
    "missing source",
    (value) => {
      delete value.source;
    },
  ],
  [
    "approval",
    (value) => {
      value.intent.acknowledged = true;
    },
  ],
  [
    "wrong members type",
    (value) => {
      value.intent.members = {};
    },
  ],
  [
    "missing member",
    (value) => {
      value.intent.members.pop();
    },
  ],
  [
    "duplicate member",
    (value) => {
      value.intent.members[1] = value.intent.members[0];
    },
  ],
  [
    "unknown member",
    (value) => {
      value.intent.members[0].entry_id = "new-path";
    },
  ],
  [
    "member extra field",
    (value) => {
      value.intent.members[0].version = "verified";
    },
  ],
  [
    "string inclusion",
    (value) => {
      value.intent.members[0].included = "true";
    },
  ],
  [
    "empty selection",
    (value) => {
      value.intent.members.forEach((member) => {
        member.included = false;
      });
    },
  ],
  [
    "unknown root",
    (value) => {
      value.intent.destination_root_id = "/some/path";
    },
  ],
  [
    "non-text folder",
    (value) => {
      value.intent.destination_folder = [];
    },
  ],
  [
    "overlong folder",
    (value) => {
      value.intent.destination_folder = "a".repeat(241);
    },
  ],
  [
    "overlong unchecked path",
    (value) => {
      value.intent.members[3].project_path = "a".repeat(241);
    },
  ],
  [
    "unchecked newline",
    (value) => {
      value.intent.members[3].project_path = "unfinished\npath";
    },
  ],
  [
    "unchecked DEL",
    (value) => {
      value.intent.members[3].project_path = "unfinished\x7fpath";
    },
  ],
  [
    "unchecked surrogate",
    (value) => {
      value.intent.members[3].project_path = "\ud800";
    },
  ],
])("rejects %s without changing input", (_name, mutate) => {
  const value = document();
  mutate(value);
  const snapshot = JSON.stringify(value);
  expect(() => model.parse(snapshot, fixture)).toThrow();
  expect(JSON.stringify(value)).toBe(snapshot);
});

test.each(["source_revision", "observation_digest", "reference_decision_digest"])(
  "rejects stale %s without rebinding",
  (key) => {
    const value = document();
    value.source[key] = key === "source_revision" ? 2 : "0".repeat(64);
    expect(() => model.parse(JSON.stringify(value), fixture)).toThrow(/different Aurora source/);
  }
);

test.each([
  "",
  "/absolute",
  "a\\b",
  "a:b",
  "a//b",
  ".",
  "..",
  "a/../b",
  "a/./b",
  "a/",
  "\u0000",
  "line\npath",
  "\udc00",
])("rejects invalid selected path %j", (path) => {
  const value = choices();
  value.members[0].project_path = path;
  expect(() => model.serialise(value, fixture)).toThrow();
});

test("valid spelling is never trimmed, case-folded or Unicode-normalised", () => {
  const value = choices();
  value.members[0].project_path = " É/e\u0301/😀 <name> ";
  const reopened = model.parse(model.serialise(value, fixture), fixture);
  expect(reopened.members[0].project_path).toBe(value.members[0].project_path);
});

test("240 UTF-16 code units match existing text controls", () => {
  const value = choices();
  value.members[0].project_path = "😀".repeat(120);
  expect(model.parse(model.serialise(value, fixture), fixture).members[0].project_path).toBe(
    value.members[0].project_path
  );
  value.members[0].project_path += "a";
  expect(() => model.serialise(value, fixture)).toThrow(/too long/);
});

test.each([
  '{"source":1,"\\u0073ource":2}',
  '{"source":{"kind":1,"kind":2}}',
  '{"__proto__":{"polluted":true}}',
  '{"constructor":{"prototype":{"polluted":true}}}',
  "[1,]",
  '{"x":1,}',
  '{"x":01}',
  '{"x":NaN}',
  '{"x":Infinity}',
  '{"x":1e309}',
  '{"x":9007199254740993}',
  "{} trailing",
  "{",
  "null",
  "[]",
  '"text"',
  "\ufeff{}",
])("rejects unsupported JSON %s", (input) => {
  expect(() => model.parse(input, fixture)).toThrow();
  expect({}.polluted).toBeUndefined();
});

test("bounded parser rejects duplicate decoded keys before last-value collapse", () => {
  const value = model.serialise(choices(), fixture);
  const repeated = value.replace(
    '"document_kind":',
    '"schema_version":"injected", "document_kind":'
  );
  expect(() => model.parse(repeated, fixture)).toThrow(/repeated JSON key/);
});

test.each([
  "1.0000000000000001",
  "0.99999999999999999",
  "1.0",
  "1e0",
  "1e-400",
  "9007199254740993",
])("rejects noncanonical or inexact raw revision %s", (token) => {
  const input = model
    .serialise(choices(), fixture)
    .replace('"source_revision": 1', `"source_revision": ${token}`);
  expect(() => model.parse(input, fixture)).toThrow();
});

test("8 KiB boundary measures actual UTF-8 bytes", () => {
  const value = model.serialise(choices(), fixture);
  const exact = value + " ".repeat(model.MAX_BYTES - model.byteLength(value));
  expect(model.parse(exact, fixture)).toEqual(choices());
  expect(() => model.parse(exact + " ", fixture)).toThrow(/8 KiB/);
  expect(() => model.parse("é".repeat(4097), fixture)).toThrow(/8 KiB/);
});

test("depth and node budgets are enforced while parsing", () => {
  expect(() => model.parse("[".repeat(9) + "0" + "]".repeat(9), fixture)).toThrow(/too complex/);
  expect(() => model.parse("[" + Array(256).fill("0").join(",") + "]", fixture)).toThrow(
    /too complex/
  );
  expect(() => model.parse("[" + Array(255).fill("0").join(",") + "]", fixture)).toThrow(
    /unsupported project-choice fields/
  );
});

test("projected existing request uses exact byte ceiling, not file size", () => {
  const value = choices();
  value.members.forEach((member) => {
    member.included = true;
    member.project_path = "é".repeat(180);
  });
  const size = model.byteLength(JSON.stringify(model.requestFor(value, fixture)));
  expect(size).toBeLessThan(4096);
  let needed = 4096 - size;
  for (const member of value.members) {
    const extra = Math.min(240 - member.project_path.length, needed);
    member.project_path += "a".repeat(extra);
    needed -= extra;
  }
  expect(needed).toBe(0);
  expect(model.byteLength(JSON.stringify(model.requestFor(value, fixture)))).toBe(4096);
  expect(() => model.serialise(value, fixture)).not.toThrow();
  value.destination_folder += "a";
  expect(() => model.serialise(value, fixture)).toThrow(/4 KiB/);
});

test("serialisation does not mutate caller data or export unrelated state", () => {
  const value = choices(),
    before = copy(value),
    original = copy(fixture);
  const reference = { ...fixture, token: "TOKEN_SENTINEL", arbitrary: "PRIVATE_SENTINEL" };
  const json = model.serialise(value, reference);
  expect(value).toEqual(before);
  expect(fixture).toEqual(original);
  expect(json).not.toMatch(
    /TOKEN_SENTINEL|PRIVATE_SENTINEL|acknowledged|fingerprint|executable|backup|restore/
  );
});
