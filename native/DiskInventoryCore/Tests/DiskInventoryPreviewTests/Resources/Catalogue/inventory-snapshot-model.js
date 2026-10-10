/* Historical display claims only. No filesystem, network, storage or provider access. */
(function (root, factory) {
  "use strict";
  if (typeof module === "object" && module.exports)
    module.exports = factory(require("./manual-planning-model.js"));
  else root.InventoryCatalogue = factory(root.ManualPlanningModel);
})(typeof globalThis !== "undefined" ? globalThis : this, function (M) {
  "use strict";
  const VERSION = "disk-organiser/inventory-snapshot/v1";
  const CATALOGUE = "disk-organiser/inventory-catalogue/v1";
  const LIMITS = Object.freeze({
    bytes: 4 * 1024 * 1024,
    snapshotBytes: 1024 * 1024,
    sources: 32,
    entries: 10000,
    sourceEntries: 2000,
  });
  const fail = (message) => {
    throw new Error(message);
  };
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const freeze = (o) => {
    if (o && typeof o === "object") {
      Object.values(o).forEach(freeze);
      Object.freeze(o);
    }
    return o;
  };
  const clone = (o) => JSON.parse(JSON.stringify(o));
  function fields(o, keys) {
    if (
      !o ||
      typeof o !== "object" ||
      Array.isArray(o) ||
      Object.keys(o).length !== keys.length ||
      keys.some((k) => !own(o, k))
    )
      fail("Missing or unsupported snapshot field.");
  }
  function text(v, max = 240) {
    if (
      typeof v !== "string" ||
      !v.trim() ||
      Array.from(v).length > max ||
      /[\x00-\x1f\x7f-\x9f\u2028\u2029]/.test(v)
    )
      fail("Use bounded text without control characters.");
    for (let i = 0; i < v.length; i++) {
      const c = v.charCodeAt(i);
      if (c >= 0xd800 && c <= 0xdbff) {
        const n = v.charCodeAt(++i);
        if (!(n >= 0xdc00 && n <= 0xdfff)) fail("Invalid Unicode text.");
      } else if (c >= 0xdc00 && c <= 0xdfff) fail("Invalid Unicode text.");
    }
  }
  function decimal(v) {
    if (typeof v !== "string" || !/^(0|[1-9][0-9]{0,29})$/.test(v))
      fail("Byte and count values must be bounded decimal strings.");
  }
  function path(v) {
    text(v, 1024);
    if (
      v !== "." &&
      (v.startsWith("/") ||
        v.includes("\\") ||
        v.split("/").some((p) => !p || p === "." || p === ".."))
    )
      fail("Snapshot paths must be unambiguous relative text.");
  }
  function stamp(v) {
    text(v, 40);
    const m =
      /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?(Z|([+-])(\d{2}):(\d{2}))$/.exec(
        v
      );
    if (!m) fail("Use a valid observation date with timezone.");
    const y = +m[1],
      mo = +m[2],
      d = +m[3],
      days = [
        31,
        y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0) ? 29 : 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
      ];
    if (
      y < 1 ||
      mo < 1 ||
      mo > 12 ||
      d < 1 ||
      d > days[mo - 1] ||
      +m[4] > 23 ||
      +m[5] > 59 ||
      +m[6] > 59 ||
      (m[7] !== "Z" && (+m[9] > 23 || +m[10] > 59))
    )
      fail("Invalid observation date.");
    return m;
  }
  function formatObservationDate(value) {
    let parts;
    try {
      parts = stamp(value);
    } catch {
      return "Date unavailable";
    }
    // Display the recorded wall time, never the browser's timezone. The full
    // original stamp stays in source details and exported history.
    const months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
      ],
      offset = parts[7],
      zone =
        offset === "-00:00"
          ? "UTC (local offset unknown)"
          : offset === "Z" || offset === "+00:00"
          ? "UTC"
          : `UTC${offset}`;
    return `${Number(
      parts[3]
    )} ${months[Number(parts[2]) - 1]} ${parts[1]}, ${parts[4]}:${parts[5]} ${zone}`;
  }
  function budget(value, max) {
    let size = 0;
    const add = (n) => {
      size += n;
      if (size > max) fail("Artifact exceeds its byte budget; the current catalogue is unchanged.");
    };
    const walk = (v) => {
      if (typeof v === "string") add(new TextEncoder().encode(JSON.stringify(v)).length);
      else if (v === null) add(4);
      else if (Array.isArray(v)) {
        add(2 + Math.max(0, v.length - 1));
        v.forEach(walk);
      } else if (v && typeof v === "object") {
        const keys = Object.keys(v);
        add(2 + Math.max(0, keys.length - 1));
        keys.forEach((k) => {
          walk(k);
          add(1);
          walk(v[k]);
        });
      } else fail("Unsupported JSON value.");
    };
    walk(value);
    return size;
  }
  // The format deliberately has no JSON numeric or Boolean fields. Decimal size
  // strings survive large filesystem values without rounding in JavaScript.
  function parseJson(input) {
    if (
      typeof input !== "string" ||
      input.length > LIMITS.bytes ||
      new TextEncoder().encode(input).length > LIMITS.bytes
    )
      fail("File exceeds the 4 MiB import limit.");
    let i = 0,
      nodes = 0;
    const ws = () => {
      while (/[\x20\t\r\n]/.test(input[i] || "x")) i++;
    };
    function str() {
      const start = i++;
      while (i < input.length) {
        if (input[i] === "\\") {
          i += 2;
          continue;
        }
        if (input[i++] === '"') {
          let s;
          try {
            s = JSON.parse(input.slice(start, i));
          } catch (_) {
            fail("Malformed JSON string.");
          }
          return s;
        }
      }
      fail("Unterminated JSON string.");
    }
    function value(depth) {
      if (++nodes > 150000 || depth > 12) fail("JSON structure exceeds its bounded format.");
      ws();
      const ch = input[i];
      if (ch === '"') return str();
      if (input.slice(i, i + 4) === "null") {
        i += 4;
        return null;
      }
      if (ch !== "{" && ch !== "[") fail("Expected snapshot text, object, list or null.");
      const object = ch === "{",
        out = object ? Object.create(null) : [],
        end = object ? "}" : "]";
      i++;
      ws();
      if (input[i] === end) {
        i++;
        return out;
      }
      while (i < input.length) {
        if (object) {
          if (input[i] !== '"') fail("Expected a JSON key.");
          const key = str();
          if (own(out, key)) fail("Duplicate JSON key.");
          ws();
          if (input[i++] !== ":") fail("Expected a JSON colon.");
          out[key] = value(depth + 1);
        } else out.push(value(depth + 1));
        ws();
        if (input[i] === end) {
          i++;
          return out;
        }
        if (input[i++] !== ",") fail("Expected a JSON separator.");
        ws();
      }
      fail("Unterminated JSON structure.");
    }
    const out = value(0);
    ws();
    if (i !== input.length) fail("Unexpected text after JSON.");
    return out;
  }
  function validateSnapshot(s) {
    fields(s, ["schema_version", "source", "entries", "gaps"]);
    if (s.schema_version !== VERSION) fail("Unsupported inventory snapshot version.");
    fields(s.source, ["label", "observed_at", "scan_id", "coverage"]);
    text(s.source.label);
    stamp(s.source.observed_at);
    if (typeof s.source.scan_id !== "string" || !/^scan_[a-f0-9]{24}$/.test(s.source.scan_id))
      fail("Invalid source reference.");
    if (!["complete", "partial"].includes(s.source.coverage))
      fail("Only historical complete or partial observations can be displayed.");
    if (!Array.isArray(s.entries) || !s.entries.length || s.entries.length > LIMITS.sourceEntries)
      fail("Snapshot must contain 1–2,000 entry records.");
    const paths = new Map();
    s.entries.forEach((e) => {
      fields(e, ["path", "kind", "status", "logical_bytes"]);
      path(e.path);
      if (paths.has(e.path)) fail("Repeated source-relative path.");
      paths.set(e.path, e);
      if (
        !["file", "directory", "symlink", "special", "unknown"].includes(e.kind) ||
        !["observed", "stale", "disappeared", "unreadable", "unsupported", "excluded"].includes(
          e.status
        )
      )
        fail("Unsupported entry kind or status.");
      if (e.kind === "file") decimal(e.logical_bytes);
      else if (e.logical_bytes !== null) fail("Only file records may state logical bytes.");
      if (s.source.coverage === "complete" && e.status !== "observed")
        fail("Complete coverage conflicts with entry gaps.");
    });
    if (paths.get(".")?.kind !== "directory" || paths.get(".")?.status !== "observed")
      fail("Snapshot needs its observed selected-folder record.");
    s.entries.forEach((e) => {
      if (e.path === ".") return;
      const parent = e.path.includes("/") ? e.path.slice(0, e.path.lastIndexOf("/")) : ".";
      if (paths.get(parent)?.kind !== "directory")
        fail("Entry parent is missing or is not a directory.");
    });
    fields(s.gaps, ["exclusions", "error_count", "stop_reason"]);
    decimal(s.gaps.error_count);
    if (
      BigInt(s.gaps.error_count) > 2000n ||
      !Array.isArray(s.gaps.exclusions) ||
      s.gaps.exclusions.length > 32
    )
      fail("Gap summary exceeds bounds.");
    const reasons = new Set();
    s.gaps.exclusions.forEach((g) => {
      fields(g, ["reason", "count"]);
      text(g.reason, 120);
      decimal(g.count);
      if (reasons.has(g.reason) || BigInt(g.count) < 1n || BigInt(g.count) > 10000n)
        fail("Invalid exclusion summary.");
      reasons.add(g.reason);
    });
    if (s.gaps.stop_reason !== null) text(s.gaps.stop_reason, 120);
    if (
      s.source.coverage === "complete" &&
      (s.gaps.exclusions.length || s.gaps.error_count !== "0" || s.gaps.stop_reason !== null)
    )
      fail("Complete coverage conflicts with declared gaps.");
    budget(s, LIMITS.snapshotBytes);
    return s;
  }
  function validate(c) {
    fields(c, ["schema_version", "records"]);
    if (c.schema_version !== CATALOGUE) fail("Unsupported catalogue version.");
    if (!Array.isArray(c.records) || c.records.length > LIMITS.sources)
      fail("Catalogue supports up to 32 separately labelled snapshot records.");
    const ids = new Set();
    let entries = 0;
    c.records.forEach((r) => {
      fields(r, ["id", "label", "snapshot"]);
      if (
        typeof r.id !== "string" ||
        !/^source_[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(r.id) ||
        ids.has(r.id)
      )
        fail("Invalid or repeated catalogue record ID.");
      ids.add(r.id);
      text(r.label);
      validateSnapshot(r.snapshot);
      entries += r.snapshot.entries.length;
    });
    if (entries > LIMITS.entries) fail("Catalogue exceeds 10,000 total entry records.");
    budget(c, LIMITS.bytes);
    return c;
  }
  const empty = () => freeze({ schema_version: CATALOGUE, records: [] });
  function parse(input) {
    const v = parseJson(input);
    if (v?.schema_version === VERSION) validateSnapshot(v);
    else validate(v);
    return freeze(clone(v));
  }
  function add(c, snapshot, label, id = M.newId("source")) {
    validate(c);
    validateSnapshot(snapshot);
    const next = { schema_version: CATALOGUE, records: [...c.records, { id, label, snapshot }] };
    validate(next);
    return freeze(clone(next));
  }
  function rename(c, id, label) {
    validate(c);
    if (!c.records.some((r) => r.id === id)) fail("Catalogue record no longer exists.");
    const next = {
      schema_version: CATALOGUE,
      records: c.records.map((r) => (r.id === id ? { ...r, label } : r)),
    };
    validate(next);
    return freeze(clone(next));
  }
  function exportCatalogue(c) {
    validate(c);
    return JSON.stringify(c);
  }
  function summary(snapshot) {
    validateSnapshot(snapshot);
    const groups = new Map();
    let bytes = 0n,
      files = 0,
      uncertain = 0;
    snapshot.entries
      .filter((e) => e.path !== ".")
      .forEach((e) => {
        const key = e.path.includes("/")
          ? e.path.split("/")[0]
          : e.kind === "directory"
          ? e.path
          : "";
        if (!groups.has(key))
          groups.set(key, { path: key, entries: 0, files: 0, bytes: 0n, uncertain: 0 });
        const g = groups.get(key);
        g.entries++;
        if (e.status === "observed" && e.kind === "file") {
          g.bytes += BigInt(e.logical_bytes);
          bytes += BigInt(e.logical_bytes);
          g.files++;
          files++;
        }
        if (e.status !== "observed") {
          g.uncertain++;
          uncertain++;
        }
      });
    return {
      bytes,
      files,
      uncertain,
      groups: [...groups.values()].sort((a, b) => a.path.localeCompare(b.path)),
    };
  }
  const selectable = (e) =>
    e.path !== "." && e.status === "observed" && ["file", "directory"].includes(e.kind);
  function buildPlan(c, selections, title, now) {
    validate(c);
    text(title);
    if (!Array.isArray(selections) || !selections.length || selections.length > 2000)
      fail("Choose 1–2,000 files or folders for the project.");
    const chosen = new Map(),
      rows = [];
    selections.forEach((s) => {
      fields(s, ["source_id", "path"]);
      const record = c.records.find((r) => r.id === s.source_id),
        entry = record?.snapshot.entries.find((e) => e.path === s.path);
      if (!entry || !selectable(entry))
        fail("Only listed observed files or folders can be selected for a manual plan.");
      const prior = chosen.get(record.id) || [];
      if (
        prior.some((p) => p === s.path || p.startsWith(s.path + "/") || s.path.startsWith(p + "/"))
      )
        fail("Choose either a folder or its contained entries, not both.");
      prior.push(s.path);
      chosen.set(record.id, prior);
      rows.push({ record, entry });
    });
    const plan = clone(M.createEmptyPlan({ title, document_id: M.newId("plan"), now })),
      drives = new Map();
    rows.forEach(({ record, entry }) => {
      const source = record.snapshot.source;
      if (!drives.has(record.id)) {
        const id = M.newId("drive");
        drives.set(record.id, id);
        plan.drives.push({
          id,
          label: record.label,
          kind: "unspecified",
          notes: `User-labelled catalogue record. Physical identity and current presence unknown. Historical folder label: ${source.label}. Observation claimed: ${source.observed_at}. Reference: ${source.scan_id}. Imported claims are unauthenticated.`,
        });
      }
      plan.items.push({
        id: M.newId("item"),
        label: Array.from(entry.path.split("/").pop()).slice(0, 240).join(""),
        kind: entry.kind === "directory" ? "folder" : "file",
        location: { drive_id: drives.get(record.id), path_text: entry.path },
        notes: `Imported historical snapshot claim, not a live check. Original folder label: ${source.label}. Observed at (claimed): ${source.observed_at}. Source reference: ${source.scan_id}. Original relative path: ${entry.path}. Scope coverage: ${source.coverage}. Relative to that selected folder, not the drive root. Selection is manual intent; versions, dependencies, capacity and protection remain unknown.`,
      });
    });
    const projectId = M.newId("project");
    plan.projects.push({
      id: projectId,
      label: title,
      member_item_ids: plan.items.map((i) => i.id),
      notes:
        "Membership selected by the user from unauthenticated historical snapshot claims. No file operation has been performed.",
    });
    plan.protection_plans.push({
      id: M.newId("protection"),
      label: `${Array.from(title).slice(0, 220).join("")} protection`,
      project_id: projectId,
      target_ids: [],
      excluded_item_ids: [],
      policy: {},
    });
    M.validatePlan(plan);
    return freeze(plan);
  }
  return Object.freeze({
    VERSION,
    CATALOGUE,
    LIMITS,
    empty,
    parse,
    add,
    rename,
    validate,
    validateSnapshot,
    exportCatalogue,
    summary,
    selectable,
    buildPlan,
    formatObservationDate,
  });
});
