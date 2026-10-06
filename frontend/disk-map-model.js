/* Pure, bounded import validation. No filesystem, storage, network or action APIs. */
((root, factory) => {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.DiskMapModel = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, () => {
  "use strict";
  const MAX_BYTES = 8 * 1024 * 1024;
  const MAX_ENTRIES = 20000;
  const MAX_NODES = 350000;
  const MAX_DEPTH = 32;
  const MAX_FIELD_CHARS = 4096;
  const MAX_KEY_CHARS = 256;
  const MAX_TEXT_CHARS = 4 * 1024 * 1024;
  const MAX_REFERENCE_LINKS = 100000;
  const MAX_FREE_ITEMS = 128;
  const own = (value, key) => Object.prototype.hasOwnProperty.call(value, key);
  const object = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
  class ImportError extends Error {
    constructor(message) {
      super(message);
      this.name = "ImportError";
    }
  }
  const fail = (message) => {
    throw new ImportError(message);
  };
  const ensure = (condition, message) => {
    if (!condition) fail(message);
  };
  const supportedKeywords = new Set([
    "$schema",
    "$defs",
    "$ref",
    "title",
    "description",
    "type",
    "const",
    "enum",
    "anyOf",
    "allOf",
    "if",
    "then",
    "else",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "minLength",
    "maxLength",
    "maxItems",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "pattern",
    "format",
  ]);
  function auditSchema(schema) {
    ensure(object(schema), "The bundled model contract could not be loaded.");
    for (const key of Object.keys(schema))
      ensure(
        supportedKeywords.has(key),
        "The bundled contract uses an unsupported validation rule."
      );
    if (schema.$ref)
      ensure(
        /^#\/\$defs\/[A-Za-z_]+$/.test(schema.$ref),
        "Only bundled contract references are supported."
      );
    for (const key of ["properties", "$defs"])
      if (schema[key]) Object.values(schema[key]).forEach(auditSchema);
    for (const key of ["items", "additionalProperties", "if", "then", "else"])
      if (object(schema[key])) auditSchema(schema[key]);
    for (const key of ["anyOf", "allOf"]) if (schema[key]) schema[key].forEach(auditSchema);
  }
  function budget(value) {
    const stack = [{ value, depth: 0, key: "" }];
    let count = 0,
      textChars = 0,
      referenceLinks = 0;
    while (stack.length) {
      const item = stack.pop();
      count++;
      ensure(
        count <= MAX_NODES && item.depth <= MAX_DEPTH,
        "This export is too complex for this preview. The previous view has been kept."
      );
      const v = item.value;
      if (typeof v === "string") {
        textChars += v.length;
        ensure(
          v.length <= MAX_FIELD_CHARS && textChars <= MAX_TEXT_CHARS,
          "The export exceeds the viewer's field or total text budget."
        );
      } else if (typeof v === "bigint") {
        ensure(
          ["mtime_ns", "ctime_ns", "inode", "device"].includes(item.key),
          "A storage size or count is too large to display exactly in this viewer."
        );
      } else if (typeof v === "number") {
        ensure(Number.isFinite(v), "The export contains a non-finite number.");
        // Nanosecond timestamps and opaque inode/device identifiers can exceed
        // binary64 integer precision. They are never used as identity authority.
        if (Number.isInteger(v) && !Number.isSafeInteger(v))
          ensure(
            ["mtime_ns", "ctime_ns", "inode", "device"].includes(item.key),
            "A storage size or count is too large to display exactly in this viewer."
          );
      } else if (v !== null && typeof v === "object") {
        ensure(
          Array.isArray(v) ||
            Object.getPrototypeOf(v) === Object.prototype ||
            Object.getPrototypeOf(v) === null,
          "Only plain JSON objects can be opened."
        );
        const keys = Object.keys(v);
        if (Array.isArray(v)) {
          const largeCollections = new Set([
            "entries",
            "directories",
            "evidence",
            "relationships",
            "findings",
            "plan_alternatives",
            "errors",
            "exclusions",
            "added",
            "changed",
            "unchanged_metadata",
            "no_longer_observed",
            "unverified_absent",
          ]);
          const references = item.key.endsWith("_ids") || item.key === "depends_on";
          if (references) referenceLinks += v.length;
          ensure(
            v.length <=
              (references || largeCollections.has(item.key) ? MAX_ENTRIES : MAX_FREE_ITEMS),
            "An export collection exceeds this viewer's bounded presentation limit."
          );
          ensure(
            referenceLinks <= MAX_REFERENCE_LINKS,
            "The export exceeds the viewer's reference/search work budget."
          );
        } else
          ensure(
            keys.length <= MAX_FREE_ITEMS,
            "An evidence object has too many fields for this viewer."
          );
        for (const key of keys) {
          textChars += key.length;
          ensure(
            key.length <= MAX_KEY_CHARS && textChars <= MAX_TEXT_CHARS,
            "The export exceeds the viewer's key or total text budget."
          );
          ensure(
            !["__proto__", "prototype", "constructor"].includes(key),
            "The export contains an unsupported object key."
          );
          stack.push({ value: v[key], depth: item.depth + 1, key });
        }
      } else ensure(v === null || typeof v === "boolean", "Only JSON data can be opened.");
    }
  }
  function dateTime(value) {
    const match =
      /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.exec(
        value
      );
    if (!match || !Number.isFinite(Date.parse(value))) return false;
    const [, y, m, d, h, minute, second] = match.map(Number);
    return (
      y >= 1 &&
      m >= 1 &&
      m <= 12 &&
      d >= 1 &&
      d <= new Date(Date.UTC(y, m, 0)).getUTCDate() &&
      h < 24 &&
      minute < 60 &&
      second < 60
    );
  }
  function shape(value, rule, schema, path = "model") {
    const invalid = () => fail(`The export does not match Disk Model v1 at ${path.slice(0, 160)}.`);
    if (rule.$ref) {
      const name = rule.$ref.split("/").pop();
      ensure(own(schema.$defs, name), "A bundled contract definition is missing.");
      return shape(value, schema.$defs[name], schema, path);
    }
    if (rule.anyOf) {
      const valid = rule.anyOf.some((r) => {
        try {
          shape(value, r, schema, path);
          return true;
        } catch (error) {
          if (!(error instanceof ImportError)) throw error;
          return false;
        }
      });
      if (!valid) invalid();
    }
    if (rule.allOf) rule.allOf.forEach((r) => shape(value, r, schema, path));
    if (rule.if) {
      let matches = true;
      try {
        shape(value, rule.if, schema, path);
      } catch (error) {
        if (!(error instanceof ImportError)) throw error;
        matches = false;
      }
      shape(value, rule[matches ? "then" : "else"] || {}, schema, path);
    }
    const kinds = {
      null: value === null,
      boolean: typeof value === "boolean",
      integer: Number.isInteger(value) || typeof value === "bigint",
      number: (typeof value === "number" && Number.isFinite(value)) || typeof value === "bigint",
      string: typeof value === "string",
      array: Array.isArray(value),
      object: object(value),
    };
    if (rule.type && !(Array.isArray(rule.type) ? rule.type : [rule.type]).some((t) => kinds[t]))
      invalid();
    if (own(rule, "const") && value !== rule.const) invalid();
    if (rule.enum && !rule.enum.some((v) => v === value)) invalid();
    if (typeof value === "number" || typeof value === "bigint") {
      if (
        (typeof value === "number" && !Number.isFinite(value)) ||
        (own(rule, "minimum") && value < rule.minimum) ||
        (own(rule, "maximum") && value > rule.maximum) ||
        (own(rule, "exclusiveMinimum") && value <= rule.exclusiveMinimum)
      )
        invalid();
    }
    if (typeof value === "string") {
      const length = Array.from(value).length;
      if (
        (own(rule, "minLength") && length < rule.minLength) ||
        (own(rule, "maxLength") && length > rule.maxLength) ||
        (rule.pattern && !new RegExp(rule.pattern, "u").test(value))
      )
        invalid();
      if (rule.format) {
        ensure(rule.format === "date-time", "The bundled contract uses an unsupported format.");
        if (!dateTime(value)) invalid();
      }
    }
    if (Array.isArray(value)) {
      if (own(rule, "maxItems") && value.length > rule.maxItems) invalid();
      value.forEach((v, i) => shape(v, rule.items || {}, schema, `${path}[${i}]`));
    } else if (object(value)) {
      if (rule.required?.some((key) => !own(value, key))) invalid();
      for (const key of Object.keys(value)) {
        if (rule.properties && own(rule.properties, key))
          shape(value[key], rule.properties[key], schema, `${path}.${key}`);
        else if (rule.additionalProperties === false) invalid();
        else if (object(rule.additionalProperties))
          shape(value[key], rule.additionalProperties, schema, `${path}.${key}`);
      }
    }
  }
  function mapRecords(records, key = "id") {
    const map = new Map();
    for (const record of records) {
      ensure(!map.has(record[key]), "The export repeats a record identity.");
      map.set(record[key], record);
    }
    return map;
  }
  function refs(ids, records, message = "The export contains a missing or repeated reference.") {
    ensure(new Set(ids).size === ids.length && ids.every((id) => records.has(id)), message);
  }
  function sameCountMap(actual, expected) {
    const keys = new Set([...Object.keys(actual), ...Object.keys(expected)]);
    return [...keys].every((key) => (actual[key] || 0) === (expected[key] || 0));
  }
  function safeSum(values) {
    const sum = values.reduce((a, b) => a + b, 0);
    ensure(Number.isSafeInteger(sum), "The combined storage size is too large to display exactly.");
    return sum;
  }
  function semantics(model) {
    ensure(
      model.entries.length <= MAX_ENTRIES,
      `This viewer supports at most ${MAX_ENTRIES.toLocaleString()} entries per export.`
    );
    const roots = mapRecords(model.scan.roots),
      entries = mapRecords(model.entries),
      evidence = mapRecords(model.evidence),
      findings = mapRecords(model.findings),
      relationships = mapRecords(model.relationships),
      directories = mapRecords(model.directories, "entry_id"),
      plans = mapRecords(model.plan_alternatives);
    const addresses = new Set(),
      children = new Map();
    for (const entry of model.entries) {
      ensure(roots.has(entry.root_id), "An entry names an unknown scan root.");
      const address = JSON.stringify([entry.root_id, entry.relative_path]);
      ensure(!addresses.has(address), "The export repeats a root-relative address.");
      addresses.add(address);
      if (entry.parent_id === null)
        ensure(entry.relative_path === ".", "A root entry has an inconsistent relative address.");
      else {
        const parent = entries.get(entry.parent_id);
        ensure(
          parent && parent.kind === "directory" && parent.root_id === entry.root_id,
          "An entry has an inconsistent parent."
        );
        const prefix = parent.relative_path === "." ? "" : `${parent.relative_path}/`;
        const tail = entry.relative_path.slice(prefix.length);
        ensure(
          entry.relative_path.startsWith(prefix) && tail && tail !== "." && !tail.includes("/"),
          "An entry address does not match its parent."
        );
      }
      if (entry.kind === "file")
        ensure(entry.logical_bytes !== null, "A file observation is missing its logical size.");
      if (!children.has(entry.parent_id)) children.set(entry.parent_id, []);
      children.get(entry.parent_id).push(entry.id);
      let parent = entry,
        depth = 0;
      while (parent.parent_id !== null) {
        parent = entries.get(parent.parent_id);
        depth++;
        ensure(
          parent && depth <= 65,
          "The export contains a cyclic or excessively deep parent chain."
        );
      }
    }
    for (const item of model.evidence) refs(item.member_ids, entries);
    for (const item of [...model.findings, ...model.relationships]) {
      refs(item.member_ids, entries);
      refs(item.evidence_ids, evidence);
    }
    for (const item of model.directories) {
      ensure(
        entries.get(item.entry_id)?.kind === "directory",
        "A directory summary does not refer to a directory."
      );
      refs(item.direct_member_ids, entries);
      const members = new Set(children.get(item.entry_id) || []);
      ensure(
        item.direct_member_ids.length === members.size &&
          item.direct_member_ids.every((id) => members.has(id)),
        "A directory summary disagrees with its observed direct members."
      );
      item.role_hypotheses.forEach((role) => refs(role.evidence_ids, evidence));
    }
    for (const entry of model.entries.filter((e) => e.kind === "directory"))
      ensure(directories.has(entry.id), "A directory summary is missing.");
    const directoryFacts = new Map();
    for (const [id] of directories) {
      const entry = entries.get(id),
        gaps = new Set();
      if (entry.status !== "observed") gaps.add(`directory_${entry.status}`);
      if (model.scan.coverage.stop_reason) gaps.add("scan_interrupted");
      directoryFacts.set(id, { logical_bytes: 0, observed_files: 0, uncertain_entries: 0, gaps });
    }
    for (const exclusion of model.scan.exclusions)
      directoryFacts.get(exclusion.entry_id)?.gaps.add(exclusion.reason);
    for (const entry of model.entries) {
      const totals = directoryFacts.get(entry.parent_id);
      if (!totals) continue;
      if (entry.status !== "observed") {
        totals.uncertain_entries++;
        totals.gaps.add("descendant_not_observed");
      } else if (entry.kind === "file") {
        totals.logical_bytes = safeSum([totals.logical_bytes, entry.logical_bytes]);
        totals.observed_files++;
      }
    }
    const deepest = [...directories.keys()].sort((a, b) => {
      const depth = (id) =>
        entries.get(id).relative_path === "." ? 0 : entries.get(id).relative_path.split("/").length;
      return depth(b) - depth(a);
    });
    for (const id of deepest) {
      const totals = directoryFacts.get(id),
        parent = directoryFacts.get(entries.get(id).parent_id);
      if (!parent) continue;
      for (const key of ["logical_bytes", "observed_files", "uncertain_entries"])
        parent[key] = safeSum([parent[key], totals[key]]);
      if (totals.gaps.size) parent.gaps.add("descendant_coverage_incomplete");
    }
    for (const [id, declared] of directories) {
      const actual = directoryFacts.get(id);
      ensure(
        ["logical_bytes", "observed_files", "uncertain_entries"].every(
          (key) => declared[key] === actual[key]
        ),
        "Directory accounting contradicts its observed descendants."
      );
      ensure(
        declared.coverage.complete === (actual.gaps.size === 0) &&
          new Set(declared.coverage.reasons).size === declared.coverage.reasons.length &&
          declared.coverage.reasons.length === actual.gaps.size &&
          declared.coverage.reasons.every((reason) => actual.gaps.has(reason)),
        "Directory coverage contradicts the recorded gaps or scan interruption."
      );
    }
    const expectedScanStatus =
      model.scan.coverage.stop_reason === "cancelled"
        ? "cancelled"
        : model.scan.coverage.stop_reason ||
          model.scan.errors.length ||
          model.scan.exclusions.length ||
          model.entries.some((e) => e.status !== "observed") ||
          model.scan.roots.some((r) => r.status !== "observed")
        ? "partial"
        : "complete";
    ensure(
      model.scan.status === expectedScanStatus,
      "Scan completion contradicts its recorded gaps, roots or stop state."
    );
    for (const plan of model.plan_alternatives) {
      refs(plan.finding_ids, findings);
      refs(plan.scope_member_ids, entries);
      const scope = new Set(plan.scope_member_ids),
        alternatives = new Set();
      for (const alternative of plan.alternatives) {
        ensure(!alternatives.has(alternative.id), "A review choice is repeated.");
        alternatives.add(alternative.id);
        refs(alternative.unchanged_member_ids, scope);
        refs(alternative.uncertain_member_ids, scope);
        ensure(
          alternative.unchanged_member_ids.length === scope.size,
          "Read-only choices must retain every scoped member."
        );
        const steps = new Set();
        for (const step of alternative.steps) {
          refs(step.depends_on, steps);
          refs(step.member_ids, scope);
          refs(step.evidence_ids, evidence);
          ensure(!steps.has(step.id), "A review step is repeated.");
          steps.add(step.id);
        }
      }
    }
    for (const item of [...model.scan.errors, ...model.scan.exclusions])
      refs([item.entry_id], entries);
    for (const key of ["added", "changed", "unchanged_metadata"]) refs(model.changes[key], entries);
    for (const key of ["no_longer_observed", "unverified_absent"])
      ensure(
        new Set(model.changes[key]).size === model.changes[key].length &&
          model.changes[key].every((id) => !entries.has(id)),
        "Historical absence references conflict with current observations."
      );
    const changeMembership = new Set();
    for (const key of [
      "added",
      "changed",
      "unchanged_metadata",
      "no_longer_observed",
      "unverified_absent",
    ])
      for (const id of model.changes[key]) {
        ensure(!changeMembership.has(id), "Reported change categories overlap.");
        changeMembership.add(id);
      }
    const hashCounts = Object.create(null);
    for (const entry of model.entries.filter((e) => e.kind === "file"))
      hashCounts[entry.hash.status] = (hashCounts[entry.hash.status] || 0) + 1;
    ensure(
      sameCountMap(hashCounts, model.scan.coverage.hash_status_counts),
      "Reported per-file hash states disagree with the entries."
    );
    ensure(
      (model.scan.hash_policy === "bounded_sha256") === model.scan.limits.hash_files &&
        model.scan.coverage.hashed_files <= model.scan.coverage.hash_attempts,
      "Reported hash policy or attempt counts are inconsistent."
    );
    if (model.scan.hash_policy === "metadata_only")
      ensure(
        model.scan.coverage.hashed_files === 0 &&
          model.scan.coverage.hash_attempts === 0 &&
          model.scan.coverage.hashed_bytes === 0 &&
          !(hashCounts.verified || 0),
        "Metadata-only records cannot claim content verification."
      );
    const observed = model.entries.filter((e) => e.kind === "file" && e.status === "observed");
    const statusCounts = Object.create(null);
    for (const entry of model.entries)
      statusCounts[entry.status] = (statusCounts[entry.status] || 0) + 1;
    const a = model.aggregates,
      coverage = model.scan.coverage;
    ensure(
      a.logical_bytes_by_path === safeSum(observed.map((e) => e.logical_bytes)) &&
        a.observed_regular_files === observed.length,
      "Reported logical totals disagree with the observed entries."
    );
    ensure(
      coverage.entries_observed === model.entries.length &&
        sameCountMap(a.status_counts, statusCounts) &&
        sameCountMap(coverage.status_counts, statusCounts),
      "Reported coverage counts disagree with the entries."
    );
    ensure(
      a.partial === (model.scan.status !== "complete") &&
        coverage.complete_within_policy === (model.scan.status === "complete"),
      "Reported coverage states disagree."
    );
    const unique = new Map();
    const fingerprintKeys = [
      "device",
      "inode",
      "size",
      "mtime_ns",
      "ctime_ns",
      "mode",
      "link_count",
    ];
    for (const e of observed) {
      const key = e.object_id || e.id,
        prior = unique.get(key);
      if (prior && e.object_id !== null) {
        const sameFingerprint =
          (prior.fingerprint === null && e.fingerprint === null) ||
          (prior.fingerprint &&
            e.fingerprint &&
            fingerprintKeys.every((field) => prior.fingerprint[field] === e.fingerprint[field]));
        ensure(
          prior.logical_bytes === e.logical_bytes &&
            prior.allocated_bytes === e.allocated_bytes &&
            prior.allocation_source === e.allocation_source &&
            prior.link_count === e.link_count &&
            sameFingerprint,
          "Aliases of one reported object contain conflicting size, allocation or fingerprint observations."
        );
        if (prior.hash.status === "verified" && e.hash.status === "verified")
          ensure(
            prior.hash.value === e.hash.value,
            "Aliases of one reported object have conflicting recorded hashes."
          );
      } else unique.set(key, e);
    }
    const identityUnknown = observed.filter((e) => e.object_id === null).length;
    ensure(
      a.object_identity_unknown_paths === identityUnknown,
      "Unknown object counts disagree with the observations."
    );
    const values = [...unique.values()],
      allocated = values.filter((e) => e.allocated_bytes !== null);
    const expected = identityUnknown
      ? {
          logical_bytes_by_observed_object: null,
          known_allocated_bytes_by_observed_object: null,
          allocation_unknown_objects: null,
          distinct_observed_file_objects: null,
          hard_link_alias_paths: null,
        }
      : {
          logical_bytes_by_observed_object: safeSum(values.map((e) => e.logical_bytes)),
          known_allocated_bytes_by_observed_object: allocated.length
            ? safeSum(allocated.map((e) => e.allocated_bytes))
            : null,
          allocation_unknown_objects: values.length - allocated.length,
          distinct_observed_file_objects: values.length,
          hard_link_alias_paths: observed.length - values.length,
        };
    for (const [key, value] of Object.entries(expected))
      ensure(
        a[key] === value,
        "Reported object or allocation totals disagree with the observations."
      );
    const categoryValues = Object.values(a.by_extension_category);
    ensure(
      safeSum(categoryValues.map((x) => x.entry_count)) === observed.length &&
        safeSum(categoryValues.map((x) => x.logical_bytes)) === a.logical_bytes_by_path,
      "Reported category totals disagree with the observations."
    );
    return {
      model,
      roots,
      entries,
      evidence,
      findings,
      relationships,
      directories,
      plans,
      children,
      searchPaths: new Map(
        model.entries.map((entry) => [entry.id, entry.relative_path.toLocaleLowerCase()])
      ),
    };
  }
  function validate(model, schema) {
    auditSchema(schema);
    budget(model);
    shape(model, schema, schema);
    return semantics(model);
  }
  function utf8Bytes(text) {
    let bytes = 0;
    for (const char of text) {
      const n = char.codePointAt(0);
      bytes += n <= 0x7f ? 1 : n <= 0x7ff ? 2 : n <= 0xffff ? 3 : 4;
      if (bytes > MAX_BYTES) break;
    }
    return bytes;
  }
  function parseJSON(text) {
    let index = 0,
      values = 0;
    const numeric = /-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/y;
    const whitespace = () => {
      while (index < text.length && [" ", "\t", "\r", "\n"].includes(text[index])) index++;
    };
    function string() {
      const start = index++;
      while (index < text.length) {
        if (text[index] === "\\") {
          index += 2;
          continue;
        }
        if (text[index++] === '"') return JSON.parse(text.slice(start, index));
      }
      throw new Error("Unterminated string");
    }
    function value(depth) {
      ensure(
        ++values <= MAX_NODES && depth <= MAX_DEPTH,
        "This export is too complex for this preview."
      );
      whitespace();
      const char = text[index];
      if (char === '"') return string();
      if (char === "{") {
        index++;
        whitespace();
        const result = Object.create(null);
        if (text[index] === "}") {
          index++;
          return result;
        }
        while (true) {
          whitespace();
          if (text[index] !== '"') throw new Error("Expected key");
          const key = string();
          ensure(
            key.length <= MAX_KEY_CHARS && !own(result, key),
            "The export has an oversized or repeated JSON object key."
          );
          whitespace();
          if (text[index++] !== ":") throw new Error("Expected colon");
          result[key] = value(depth + 1);
          whitespace();
          const separator = text[index++];
          if (separator === "}") return result;
          if (separator !== ",") throw new Error("Expected comma");
        }
      }
      if (char === "[") {
        index++;
        whitespace();
        const result = [];
        if (text[index] === "]") {
          index++;
          return result;
        }
        while (true) {
          result.push(value(depth + 1));
          whitespace();
          const separator = text[index++];
          if (separator === "]") return result;
          if (separator !== ",") throw new Error("Expected comma");
        }
      }
      for (const [literal, parsed] of [
        ["true", true],
        ["false", false],
        ["null", null],
      ])
        if (text.startsWith(literal, index)) {
          index += literal.length;
          return parsed;
        }
      numeric.lastIndex = index;
      const match = numeric.exec(text);
      if (!match) throw new Error("Expected JSON value");
      index = numeric.lastIndex;
      const number = Number(match[0]);
      if (Number.isInteger(number) && !Number.isSafeInteger(number)) {
        ensure(
          /^-?\d+$/.test(match[0]),
          "Large observation integers must use the producer's decimal integer format."
        );
        return BigInt(match[0]);
      }
      return number;
    }
    const result = value(0);
    whitespace();
    if (index !== text.length) throw new Error("Trailing input");
    return result;
  }
  function parse(text, schema) {
    ensure(
      typeof text === "string" && text.length <= MAX_BYTES && utf8Bytes(text) <= MAX_BYTES,
      "This viewer can open exports up to 8 MiB. The previous view has been kept."
    );
    let model;
    try {
      model = parseJSON(text);
    } catch (error) {
      if (error instanceof ImportError) throw error;
      fail("This file is not valid JSON. The previous view has been kept.");
    }
    return validate(model, schema);
  }
  return {
    MAX_BYTES,
    MAX_ENTRIES,
    MAX_NODES,
    MAX_DEPTH,
    MAX_FIELD_CHARS,
    MAX_KEY_CHARS,
    MAX_TEXT_CHARS,
    MAX_REFERENCE_LINKS,
    MAX_FREE_ITEMS,
    ImportError,
    parse,
    validate,
    auditSchema,
  };
});
