/* Independent manual planning metadata. No filesystem, provider or app operations. */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.ManualPlanningModel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const SCHEMA = {
    $schema: "https://json-schema.org/draft/2020-12/schema",
    $id: "urn:disk-organiser:manual-storage-plan:v1",
    title: "Disk Organiser manual storage plan v1",
    description:
      "User-authored planning metadata. Imported claims are untrusted. No observation, authenticated version, backup verification, execution or recovery authority is represented.",
    type: "object",
    additionalProperties: false,
    properties: {
      schema_version: {
        const: "disk-organiser/manual-storage-plan/v1",
      },
      document_id: {
        $ref: "#/$defs/id",
      },
      title: {
        type: "string",
        minLength: 1,
        maxLength: 240,
        pattern: "\\S",
      },
      revision: {
        type: "integer",
        minimum: 1,
        maximum: 9007199254740991,
      },
      created_at: {
        $ref: "#/$defs/timestamp",
      },
      updated_at: {
        $ref: "#/$defs/timestamp",
      },
      drives: {
        type: "array",
        items: {
          $ref: "#/$defs/drive",
        },
        maxItems: 100,
      },
      items: {
        type: "array",
        items: {
          $ref: "#/$defs/item",
        },
        maxItems: 2000,
      },
      projects: {
        type: "array",
        items: {
          $ref: "#/$defs/project",
        },
        maxItems: 200,
      },
      backup_targets: {
        type: "array",
        items: {
          $ref: "#/$defs/target",
        },
        maxItems: 100,
      },
      protection_plans: {
        type: "array",
        items: {
          $ref: "#/$defs/protectionPlan",
        },
        maxItems: 500,
      },
      restore_plans: {
        type: "array",
        items: {
          $ref: "#/$defs/restorePlan",
        },
        maxItems: 500,
      },
    },
    required: [
      "schema_version",
      "document_id",
      "title",
      "revision",
      "created_at",
      "updated_at",
      "drives",
      "items",
      "projects",
      "backup_targets",
      "protection_plans",
      "restore_plans",
    ],
    $defs: {
      id: {
        type: "string",
        pattern:
          "^[a-z][a-z0-9]{0,11}_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        maxLength: 49,
        description:
          "An application record key, never evidence of a physical drive, file or account identity.",
      },
      timestamp: {
        type: "string",
        format: "date-time",
        pattern:
          "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\\.[0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})$",
        maxLength: 40,
      },
      date: {
        type: "string",
        format: "date",
        pattern: "^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
        maxLength: 10,
      },
      location: {
        type: "object",
        additionalProperties: false,
        properties: {
          drive_id: {
            $ref: "#/$defs/id",
          },
          path_text: {
            type: "string",
            minLength: 1,
            maxLength: 2048,
            pattern: "\\S",
          },
        },
        required: ["drive_id"],
      },
      availabilityReport: {
        type: "object",
        additionalProperties: false,
        properties: {
          status: {
            type: "string",
            enum: ["available", "unavailable", "unsure"],
          },
          recorded_at: {
            $ref: "#/$defs/timestamp",
          },
          note: {
            type: "string",
            minLength: 1,
            maxLength: 1000,
            pattern: "\\S",
          },
        },
        required: ["status", "recorded_at"],
      },
      drive: {
        type: "object",
        additionalProperties: false,
        properties: {
          id: {
            $ref: "#/$defs/id",
          },
          label: {
            type: "string",
            minLength: 1,
            maxLength: 240,
            pattern: "\\S",
          },
          kind: {
            type: "string",
            enum: [
              "internal_drive",
              "external_drive",
              "network_storage",
              "cloud_location",
              "other",
              "unspecified",
            ],
          },
          purposes: {
            type: "array",
            items: {
              type: "string",
              enum: ["working", "archive", "backup", "other"],
            },
            maxItems: 4,
            uniqueItems: true,
          },
          availability_report: {
            $ref: "#/$defs/availabilityReport",
          },
          notes: {
            type: "string",
            minLength: 1,
            maxLength: 2000,
            pattern: "\\S",
          },
          archived: {
            type: "boolean",
          },
        },
        required: ["id", "label"],
      },
      item: {
        type: "object",
        additionalProperties: false,
        properties: {
          id: {
            $ref: "#/$defs/id",
          },
          label: {
            type: "string",
            minLength: 1,
            maxLength: 240,
            pattern: "\\S",
          },
          kind: {
            type: "string",
            enum: ["file", "folder", "whole_drive", "unspecified"],
          },
          location: {
            $ref: "#/$defs/location",
          },
          described_version: {
            type: "string",
            minLength: 1,
            maxLength: 240,
            pattern: "\\S",
          },
          notes: {
            type: "string",
            minLength: 1,
            maxLength: 2000,
            pattern: "\\S",
          },
          archived: {
            type: "boolean",
          },
        },
        required: ["id", "label", "kind"],
      },
      project: {
        type: "object",
        additionalProperties: false,
        properties: {
          id: {
            $ref: "#/$defs/id",
          },
          label: {
            type: "string",
            minLength: 1,
            maxLength: 240,
            pattern: "\\S",
          },
          member_item_ids: {
            type: "array",
            items: {
              $ref: "#/$defs/id",
            },
            maxItems: 2000,
            uniqueItems: true,
          },
          intended_home: {
            $ref: "#/$defs/location",
          },
          notes: {
            type: "string",
            minLength: 1,
            maxLength: 2000,
            pattern: "\\S",
          },
          archived: {
            type: "boolean",
          },
        },
        required: ["id", "label", "member_item_ids"],
      },
      target: {
        type: "object",
        additionalProperties: false,
        properties: {
          id: {
            $ref: "#/$defs/id",
          },
          label: {
            type: "string",
            minLength: 1,
            maxLength: 240,
            pattern: "\\S",
          },
          kind: {
            type: "string",
            enum: [
              "local_storage",
              "network_storage",
              "object_storage",
              "managed_backup",
              "sync_service",
              "other",
              "unspecified",
            ],
          },
          storage_drive_id: {
            $ref: "#/$defs/id",
          },
          provider_name: {
            type: "string",
            minLength: 1,
            maxLength: 120,
            pattern: "\\S",
          },
          account_nickname: {
            type: "string",
            minLength: 1,
            maxLength: 120,
            pattern: "\\S",
          },
          region_note: {
            type: "string",
            minLength: 1,
            maxLength: 240,
            pattern: "\\S",
          },
          independence_note: {
            type: "string",
            minLength: 1,
            maxLength: 1000,
            pattern: "\\S",
          },
          notes: {
            type: "string",
            minLength: 1,
            maxLength: 2000,
            pattern: "\\S",
          },
          archived: {
            type: "boolean",
          },
        },
        required: ["id", "label", "kind"],
      },
      policy: {
        type: "object",
        additionalProperties: false,
        properties: {
          desired_independent_copies: {
            type: "integer",
            minimum: 1,
            maximum: 10,
          },
          desired_frequency: {
            type: "string",
            enum: [
              "daily",
              "weekly",
              "monthly",
              "after_changes",
              "before_drive_retirement",
              "custom",
            ],
          },
          frequency_note: {
            type: "string",
            minLength: 1,
            maxLength: 240,
            pattern: "\\S",
          },
          desired_retention: {
            type: "string",
            minLength: 1,
            maxLength: 500,
            pattern: "\\S",
          },
          max_acceptable_backup_age_days: {
            type: "integer",
            minimum: 1,
            maximum: 3650,
          },
          desired_restore_checks: {
            type: "array",
            items: {
              type: "string",
              enum: [
                "file_readability",
                "byte_comparison",
                "metadata",
                "application_opening",
                "other",
              ],
            },
            maxItems: 5,
            uniqueItems: true,
          },
          restore_check_note: {
            type: "string",
            minLength: 1,
            maxLength: 500,
            pattern: "\\S",
          },
          next_review_on: {
            $ref: "#/$defs/date",
          },
        },
        required: [],
      },
      protectionPlan: {
        type: "object",
        additionalProperties: false,
        properties: {
          id: {
            $ref: "#/$defs/id",
          },
          label: {
            type: "string",
            minLength: 1,
            maxLength: 240,
            pattern: "\\S",
          },
          project_id: {
            $ref: "#/$defs/id",
          },
          target_ids: {
            type: "array",
            items: {
              $ref: "#/$defs/id",
            },
            maxItems: 100,
            uniqueItems: true,
          },
          excluded_item_ids: {
            type: "array",
            items: {
              $ref: "#/$defs/id",
            },
            maxItems: 2000,
            uniqueItems: true,
          },
          policy: {
            $ref: "#/$defs/policy",
          },
          notes: {
            type: "string",
            minLength: 1,
            maxLength: 2000,
            pattern: "\\S",
          },
          archived: {
            type: "boolean",
          },
        },
        required: ["id", "label", "project_id", "target_ids", "excluded_item_ids", "policy"],
      },
      check: {
        type: "object",
        additionalProperties: false,
        properties: {
          id: {
            $ref: "#/$defs/id",
          },
          label: {
            type: "string",
            minLength: 1,
            maxLength: 500,
            pattern: "\\S",
          },
          kind: {
            type: "string",
            enum: [
              "locate_snapshot",
              "confirm_scope",
              "confirm_destination",
              "confirm_capacity",
              "confirm_access",
              "file_readability",
              "byte_comparison",
              "metadata",
              "application_opening",
              "other",
            ],
          },
          user_reports: {
            type: "array",
            items: {
              type: "object",
              additionalProperties: false,
              properties: {
                id: {
                  $ref: "#/$defs/id",
                },
                result: {
                  type: "string",
                  enum: ["reports_pass", "reports_fail", "inconclusive", "not_applicable"],
                },
                recorded_at: {
                  $ref: "#/$defs/timestamp",
                },
                performed_at: {
                  $ref: "#/$defs/timestamp",
                },
                notes: {
                  type: "string",
                  minLength: 1,
                  maxLength: 2000,
                  pattern: "\\S",
                },
              },
              required: ["id", "result", "recorded_at"],
            },
            maxItems: 50,
          },
          archived: {
            type: "boolean",
          },
        },
        required: ["id", "label", "kind"],
      },
      restorePlan: {
        type: "object",
        additionalProperties: false,
        properties: {
          id: {
            $ref: "#/$defs/id",
          },
          label: {
            type: "string",
            minLength: 1,
            maxLength: 240,
            pattern: "\\S",
          },
          protection_plan_id: {
            $ref: "#/$defs/id",
          },
          target_id: {
            $ref: "#/$defs/id",
          },
          intended_scope: {
            type: "string",
            enum: ["sample", "whole_planned_scope", "undecided"],
          },
          item_ids: {
            type: "array",
            items: {
              $ref: "#/$defs/id",
            },
            maxItems: 2000,
            uniqueItems: true,
          },
          exercise_scope_note: {
            type: "string",
            minLength: 1,
            maxLength: 1000,
            pattern: "\\S",
          },
          snapshot_reference_text: {
            type: "string",
            minLength: 1,
            maxLength: 500,
            pattern: "\\S",
          },
          destination: {
            $ref: "#/$defs/location",
          },
          capacity_note: {
            type: "string",
            minLength: 1,
            maxLength: 1000,
            pattern: "\\S",
          },
          access_note: {
            type: "string",
            minLength: 1,
            maxLength: 1000,
            pattern: "\\S",
          },
          lifecycle: {
            type: "string",
            enum: ["draft", "prepared", "user_recorded_results"],
          },
          checks: {
            type: "array",
            items: {
              $ref: "#/$defs/check",
            },
            maxItems: 100,
          },
          notes: {
            type: "string",
            minLength: 1,
            maxLength: 2000,
            pattern: "\\S",
          },
          archived: {
            type: "boolean",
          },
          reported_context: {
            $ref: "#/$defs/reportedContext",
          },
        },
        required: [
          "id",
          "label",
          "protection_plan_id",
          "intended_scope",
          "item_ids",
          "lifecycle",
          "checks",
        ],
      },
      snapshotLocation: {
        type: "object",
        additionalProperties: false,
        properties: {
          drive_id: {
            $ref: "#/$defs/id",
          },
          path_text: {
            type: "string",
            minLength: 1,
            maxLength: 2048,
            pattern: "\\S",
          },
          drive_label: {
            type: "string",
            minLength: 1,
            maxLength: 240,
            pattern: "\\S",
          },
        },
        required: ["drive_id", "drive_label"],
      },
      snapshotItem: {
        type: "object",
        additionalProperties: false,
        properties: {
          id: {
            $ref: "#/$defs/id",
          },
          label: {
            type: "string",
            minLength: 1,
            maxLength: 240,
            pattern: "\\S",
          },
          kind: {
            type: "string",
            enum: ["file", "folder", "whole_drive", "unspecified"],
          },
          location: {
            $ref: "#/$defs/snapshotLocation",
          },
          described_version: {
            type: "string",
            minLength: 1,
            maxLength: 240,
            pattern: "\\S",
          },
        },
        required: ["id", "label", "kind"],
      },
      snapshotTarget: {
        type: "object",
        additionalProperties: false,
        properties: {
          id: {
            $ref: "#/$defs/id",
          },
          label: {
            type: "string",
            minLength: 1,
            maxLength: 240,
            pattern: "\\S",
          },
          kind: {
            type: "string",
            enum: [
              "local_storage",
              "network_storage",
              "object_storage",
              "managed_backup",
              "sync_service",
              "other",
              "unspecified",
            ],
          },
          storage_drive_id: {
            $ref: "#/$defs/id",
          },
          provider_name: {
            type: "string",
            minLength: 1,
            maxLength: 120,
            pattern: "\\S",
          },
          account_nickname: {
            type: "string",
            minLength: 1,
            maxLength: 120,
            pattern: "\\S",
          },
          region_note: {
            type: "string",
            minLength: 1,
            maxLength: 240,
            pattern: "\\S",
          },
          independence_note: {
            type: "string",
            minLength: 1,
            maxLength: 1000,
            pattern: "\\S",
          },
          storage_drive_label: {
            type: "string",
            minLength: 1,
            maxLength: 240,
            pattern: "\\S",
          },
        },
        required: ["id", "label", "kind"],
      },
      reportedContext: {
        type: "object",
        additionalProperties: false,
        properties: {
          captured_at: {
            $ref: "#/$defs/timestamp",
          },
          first_report_id: {
            $ref: "#/$defs/id",
          },
          protection_plan: {
            type: "object",
            additionalProperties: false,
            properties: {
              id: {
                $ref: "#/$defs/id",
              },
              label: {
                type: "string",
                minLength: 1,
                maxLength: 240,
                pattern: "\\S",
              },
              project_id: {
                $ref: "#/$defs/id",
              },
              project_label: {
                type: "string",
                minLength: 1,
                maxLength: 240,
                pattern: "\\S",
              },
            },
            required: ["id", "label", "project_id", "project_label"],
          },
          target: {
            $ref: "#/$defs/snapshotTarget",
          },
          items: {
            type: "array",
            items: {
              $ref: "#/$defs/snapshotItem",
            },
            maxItems: 2000,
          },
          destination: {
            $ref: "#/$defs/snapshotLocation",
          },
        },
        required: ["captured_at", "first_report_id", "protection_plan", "target", "items"],
      },
    },
  };
  const LIMITS = Object.freeze({ bytes: 1048576, depth: 24, nodes: 100000 });
  const COLLECTIONS = Object.freeze([
    "drives",
    "items",
    "projects",
    "backup_targets",
    "protection_plans",
    "restore_plans",
  ]);
  const own = (value, key) => Object.prototype.hasOwnProperty.call(value, key);
  class PlanError extends Error {
    constructor(code, path, message) {
      super(`${path}: ${message}`);
      this.name = "PlanError";
      this.code = code;
      this.path = path;
    }
  }
  function fail(code, path, message) {
    throw new PlanError(code, path, message);
  }
  function freeze(value) {
    if (value && typeof value === "object") {
      Object.values(value).forEach(freeze);
      Object.freeze(value);
    }
    return value;
  }
  // Reject unpaired UTF-16 surrogates instead of lossy replacement during export.
  function utf8Length(text, path = "$", limit = LIMITS.bytes) {
    let bytes = 0;
    for (let i = 0; i < text.length; i += 1) {
      const n = text.charCodeAt(i);
      if (n >= 0xd800 && n <= 0xdbff) {
        const next = text.charCodeAt(++i);
        if (!(next >= 0xdc00 && next <= 0xdfff))
          fail("unicode", path, "Unpaired Unicode surrogate.");
        bytes += 4;
      } else if (n >= 0xdc00 && n <= 0xdfff) fail("unicode", path, "Unpaired Unicode surrogate.");
      else bytes += n < 0x80 ? 1 : n < 0x800 ? 2 : 3;
      if (bytes > limit) fail("byte_limit", path, "Planning document exceeds 1 MiB of UTF-8 JSON.");
    }
    return bytes;
  }
  function stringBytes(text, path) {
    let extra = 2;
    for (let i = 0; i < text.length; i += 1) {
      const n = text.charCodeAt(i);
      if (n === 34 || n === 92 || [8, 9, 10, 12, 13].includes(n)) extra += 1;
      else if (n < 32) extra += 5;
    }
    return utf8Length(text, path) + extra;
  }
  // Bounded canonical-byte accounting happens before JSON.stringify or cloning.
  function inspectJson(value) {
    const seen = new Set();
    let nodes = 0;
    let bytes = 0;
    function add(amount, path) {
      bytes += amount;
      if (bytes > LIMITS.bytes)
        fail("byte_limit", path, "Planning document exceeds 1 MiB of UTF-8 JSON.");
    }
    function visit(item, depth, path) {
      nodes += 1;
      if (nodes > LIMITS.nodes)
        fail("node_limit", path, "Planning document exceeds 100,000 JSON nodes and keys.");
      if (typeof item === "string") {
        add(stringBytes(item, path), path);
        return;
      }
      if (typeof item === "number") {
        if (!Number.isSafeInteger(item) || Object.is(item, -0))
          fail("integer", path, "Only safe integer values without negative zero are supported.");
        add(String(item).length, path);
        return;
      }
      if (typeof item === "boolean" || item === null) {
        add(String(item).length, path);
        return;
      }
      if (!item || typeof item !== "object")
        fail("json_type", path, "Only plain JSON data is supported.");
      if (depth >= LIMITS.depth)
        fail("depth_limit", path, "Planning document exceeds 24 nested containers.");
      if (seen.has(item))
        fail(
          "json_type",
          path,
          "Circular or shared object references are unsupported; use JSON data."
        );
      seen.add(item);
      const array = Array.isArray(item);
      const proto = Object.getPrototypeOf(item);
      if (
        (!array && proto !== Object.prototype && proto !== null) ||
        (array && proto !== Array.prototype)
      )
        fail("json_type", path, "Only plain JSON objects and arrays are supported.");
      const keys = Reflect.ownKeys(item);
      if (keys.length > LIMITS.nodes - nodes + (array ? 1 : 0))
        fail("node_limit", path, "Planning document exceeds 100,000 JSON nodes and keys.");
      if (keys.some((key) => typeof key !== "string"))
        fail("json_type", path, "Symbol keys are unsupported.");
      if (
        array &&
        (keys.length !== item.length + 1 ||
          keys.some((key, i) => key !== (i < item.length ? String(i) : "length")))
      )
        fail("json_type", path, "Sparse arrays and array properties are unsupported.");
      add(2 + Math.max(0, keys.length - (array ? 1 : 0) - 1), path);
      for (const key of keys) {
        if (array && key === "length") continue;
        const descriptor = Object.getOwnPropertyDescriptor(item, key);
        if (!descriptor.enumerable || !own(descriptor, "value"))
          fail("json_type", path, "Accessors and hidden properties are unsupported.");
        if (!array) {
          nodes += 1;
          add(stringBytes(key, path) + 1, path);
        }
        visit(
          descriptor.value,
          depth + 1,
          array ? `${path}[${key}]` : `${path}.${key.slice(0, 80)}`
        );
      }
    }
    visit(value, 0, "$");
    return bytes;
  }
  function parseJson(source) {
    if (typeof source !== "string") fail("json_type", "$", "Choose a UTF-8 JSON text artifact.");
    // UTF-16 length is a cheap conservative precheck before scanning UTF-8 bytes.
    if (source.length > LIMITS.bytes)
      fail("byte_limit", "$", "Planning document exceeds 1 MiB of UTF-8 JSON.");
    utf8Length(source);
    let at = 0;
    let nodes = 0;
    const invalid = (message) => fail("json_syntax", `$[character ${at}]`, message);
    const space = () => {
      while (/[\x20\t\n\r]/.test(source[at] || "!")) at += 1;
    };
    function count() {
      nodes += 1;
      if (nodes > LIMITS.nodes)
        fail("node_limit", "$", "Planning document exceeds 100,000 JSON nodes and keys.");
    }
    function string() {
      const start = at++;
      while (at < source.length) {
        const c = source[at++];
        if (c === '"') {
          let result;
          try {
            result = JSON.parse(source.slice(start, at));
          } catch (_) {
            invalid("Invalid JSON string.");
          }
          utf8Length(result);
          return result;
        }
        if (c === "\\") at += 1;
      }
      invalid("Unterminated JSON string.");
    }
    function value(depth) {
      space();
      count();
      const c = source[at];
      if (c === '"') return string();
      if (c === "{" || c === "[") {
        if (depth >= LIMITS.depth)
          fail("depth_limit", "$", "Planning document exceeds 24 nested containers.");
        at += 1;
        space();
        const object = c === "{";
        const result = object ? Object.create(null) : [];
        const end = object ? "}" : "]";
        if (source[at] === end) {
          at += 1;
          return result;
        }
        while (at < source.length) {
          if (object) {
            if (source[at] !== '"') invalid("Expected an object key.");
            count();
            const key = string();
            space();
            if (own(result, key)) fail("duplicate_key", "$", "Duplicate JSON object key.");
            if (source[at++] !== ":") invalid("Expected a colon after an object key.");
            result[key] = value(depth + 1);
          } else result.push(value(depth + 1));
          space();
          if (source[at] === end) {
            at += 1;
            return result;
          }
          if (source[at++] !== ",") invalid("Expected a comma or closing container.");
          space();
        }
        invalid("Unterminated JSON container.");
      }
      for (const [word, result] of [
        ["true", true],
        ["false", false],
        ["null", null],
      ]) {
        if (source.startsWith(word, at)) {
          at += word.length;
          return result;
        }
      }
      const start = at;
      while (at < source.length && /[0-9eE.+-]/.test(source[at])) at += 1;
      const token = source.slice(start, at);
      if (!/^-?(0|[1-9][0-9]*)$/.test(token))
        invalid("Only integer JSON number tokens are supported; decimals and exponents are not.");
      const result = Number(token);
      if (!Number.isSafeInteger(result) || Object.is(result, -0))
        fail("integer", "$", "Integer is out of range or uses unsupported negative zero.");
      return result;
    }
    const result = value(0);
    space();
    if (at !== source.length) invalid("Unexpected content after JSON value.");
    return result;
  }
  function validDate(value) {
    if (typeof value !== "string") return false;
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    if (!match) return false;
    const [, ys, ms, ds] = match;
    const y = Number(ys),
      m = Number(ms),
      d = Number(ds);
    const leap = y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0);
    const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    return y >= 1 && m >= 1 && m <= 12 && d >= 1 && d <= days[m - 1];
  }
  function validTimestamp(value) {
    if (typeof value !== "string") return false;
    const m =
      /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?(Z|([+-])(\d{2}):(\d{2}))$/.exec(
        value
      );
    return (
      !!m &&
      validDate(m[1]) &&
      Number(m[2]) < 24 &&
      Number(m[3]) < 60 &&
      Number(m[4]) < 60 &&
      (m[5] === "Z" || (Number(m[7]) < 24 && Number(m[8]) < 60))
    );
  }
  function structure(value, definition, path = "$", key = "") {
    const rule = definition.$ref ? SCHEMA.$defs[definition.$ref.split("/").pop()] : definition;
    if (own(rule, "const") && value !== rule.const)
      fail(
        "schema_version",
        path,
        "Unsupported schema version; this workspace supports manual-storage-plan/v1 only."
      );
    if (rule.enum && !rule.enum.includes(value)) fail("enum", path, "Unsupported choice.");
    if (rule.type === "object") {
      if (!value || typeof value !== "object" || Array.isArray(value))
        fail("type", path, "Expected an object.");
      for (const required of rule.required || [])
        if (!own(value, required))
          fail("required", `${path}.${required}`, "Required field is missing.");
      for (const field of Object.keys(value)) {
        if (!own(rule.properties, field))
          fail("unknown_field", path, `Unsupported field: ${field.slice(0, 80)}.`);
        structure(value[field], rule.properties[field], `${path}.${field}`, field);
      }
    } else if (rule.type === "array") {
      if (!Array.isArray(value)) fail("type", path, "Expected a list.");
      if (value.length > rule.maxItems)
        fail("array_limit", path, `List exceeds ${rule.maxItems} entries.`);
      if (rule.uniqueItems && new Set(value).size !== value.length)
        fail("duplicate_reference", path, "Repeated choices are unsupported.");
      value.forEach((item, index) => structure(item, rule.items, `${path}[${index}]`, key));
    } else if (rule.type === "string") {
      if (typeof value !== "string") fail("type", path, "Expected text.");
      const length = Array.from(value).length;
      if ((rule.minLength && length < rule.minLength) || length > rule.maxLength)
        fail(
          "text_limit",
          path,
          `Text must contain ${rule.minLength || 0}–${rule.maxLength} Unicode characters.`
        );
      if (rule.pattern && !new RegExp(rule.pattern).test(value))
        fail("text_format", path, "Text does not match the required format.");
      const multiline = key.endsWith("note") || key === "notes";
      if (
        (multiline
          ? /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]/
          : /[\x00-\x1f\x7f-\x9f\u2028\u2029]/
        ).test(value)
      )
        fail("control_character", path, "Unsupported control character.");
      if (rule.format === "date" && !validDate(value))
        fail("date", path, "Use a valid calendar date, YYYY-MM-DD (year 0001–9999).");
      if (rule.format === "date-time" && !validTimestamp(value))
        fail(
          "timestamp",
          path,
          "Use a valid timestamp with timezone; leap seconds are unsupported."
        );
    } else if (rule.type === "integer") {
      if (
        !Number.isSafeInteger(value) ||
        typeof value !== "number" ||
        value < rule.minimum ||
        value > rule.maximum
      )
        fail("integer", path, `Use an integer from ${rule.minimum} to ${rule.maximum}.`);
    } else if (rule.type === "boolean" && typeof value !== "boolean")
      fail("type", path, "Expected true or false.");
  }
  function reportCount(exercise) {
    return exercise.checks.reduce((sum, check) => sum + (check.user_reports || []).length, 0);
  }
  function captureContext(plan, exercise, firstReport) {
    function find(collection, id) {
      const found = plan[collection].find((record) => record.id === id);
      if (!found)
        fail(
          "reference",
          "$.restore_plans.reported_context",
          `Cannot snapshot unresolved ${collection} reference.`
        );
      return found;
    }
    function describe(record) {
      return Object.fromEntries(
        Object.entries(record).filter(([key]) => key !== "notes" && key !== "archived")
      );
    }
    const protection = find("protection_plans", exercise.protection_plan_id);
    const project = find("projects", protection.project_id);
    const target = clone(describe(find("backup_targets", exercise.target_id)));
    if (target.storage_drive_id)
      target.storage_drive_label = find("drives", target.storage_drive_id).label;
    const items = exercise.item_ids.map((id) => {
      const item = clone(describe(find("items", id)));
      if (item.location) item.location.drive_label = find("drives", item.location.drive_id).label;
      return item;
    });
    const context = {
      captured_at: firstReport.recorded_at,
      first_report_id: firstReport.id,
      protection_plan: {
        id: protection.id,
        label: protection.label,
        project_id: project.id,
        project_label: project.label,
      },
      target,
      items,
    };
    if (exercise.destination)
      context.destination = {
        ...exercise.destination,
        drive_label: find("drives", exercise.destination.drive_id).label,
      };
    return context;
  }
  function semantic(plan) {
    const warnings = [];
    const warn = (code, path, message) => warnings.push({ code, path, message });
    const ids = new Set([plan.document_id]);
    const maps = Object.create(null);
    function unique(record, path) {
      if (ids.has(record.id))
        fail("duplicate_id", `${path}.id`, "Application record IDs must be globally unique.");
      ids.add(record.id);
    }
    for (const collection of COLLECTIONS) {
      maps[collection] = new Map();
      plan[collection].forEach((record, index) => {
        unique(record, `$.${collection}[${index}]`);
        maps[collection].set(record.id, record);
      });
    }
    function reference(collection, id, path) {
      if (!maps[collection].has(id))
        fail("reference", path, `Reference must resolve to a retained ${collection} record.`);
      return maps[collection].get(id);
    }
    function location(value, path) {
      if (value) reference("drives", value.drive_id, `${path}.drive_id`);
    }
    warn(
      "coverage_unknown",
      "$",
      "Manual planning information only. Current backup coverage is unknown."
    );
    warn(
      "identity_unknown",
      "$",
      "Named records do not establish physical identity, independent copies, available capacity or authenticated versions."
    );
    const labels = new Map();
    plan.drives.forEach((drive, i) => {
      const path = `$.drives[${i}]`;
      if (drive.availability_report)
        warn(
          "availability_self_report",
          path,
          `Availability is a dated self-report (${drive.availability_report.recorded_at}), not a current check.`
        );
      if (labels.has(drive.label))
        warn(
          "same_label",
          path,
          "Another drive record has the same label; this does not establish physical sameness."
        );
      labels.set(drive.label, true);
    });
    const pathLabels = new Set();
    plan.items.forEach((item, i) => {
      const path = `$.items[${i}]`;
      location(item.location, `${path}.location`);
      if (item.kind === "whole_drive" && (!item.location || own(item.location, "path_text")))
        fail(
          "whole_drive",
          `${path}.location`,
          "Whole-drive scope requires a named drive and no path text."
        );
      if (!item.location) warn("location_missing", path, "Location has not been recorded.");
      else if (!item.location.path_text && item.kind !== "whole_drive")
        warn("path_missing", path, "Path not recorded; the drive root has not been selected.");
      if (item.kind === "folder" || item.kind === "whole_drive")
        warn(
          "descendants_unknown",
          path,
          "Descendant membership and byte counts are unknown; listed scopes may overlap."
        );
      if (item.location && item.location.path_text) {
        const address = JSON.stringify([item.location.drive_id, item.location.path_text]);
        if (pathLabels.has(address))
          warn(
            "same_path_text",
            path,
            "Another item has the same recorded path text; this does not establish identical content."
          );
        pathLabels.add(address);
      }
    });
    plan.projects.forEach((project, i) => {
      location(project.intended_home, `$.projects[${i}].intended_home`);
      project.member_item_ids.forEach((id, j) =>
        reference("items", id, `$.projects[${i}].member_item_ids[${j}]`)
      );
    });
    plan.backup_targets.forEach((target, i) => {
      if (target.storage_drive_id)
        reference("drives", target.storage_drive_id, `$.backup_targets[${i}].storage_drive_id`);
      if (target.kind === "sync_service")
        warn(
          "sync_intent",
          `$.backup_targets[${i}]`,
          "A sync-service entry does not establish versioned backup or retention."
        );
    });
    plan.protection_plans.forEach((protection, i) => {
      const path = `$.protection_plans[${i}]`;
      const project = reference("projects", protection.project_id, `${path}.project_id`);
      const members = new Set(project.member_item_ids);
      protection.target_ids.forEach((id, j) =>
        reference("backup_targets", id, `${path}.target_ids[${j}]`)
      );
      protection.excluded_item_ids.forEach((id, j) => {
        reference("items", id, `${path}.excluded_item_ids[${j}]`);
        if (!members.has(id))
          warn(
            "former_exclusion",
            path,
            "An exclusion refers to a former project member and remains retained."
          );
      });
      if (!protection.target_ids.length)
        warn("target_missing", path, "No intended backup target has been chosen.");
      if (!Object.keys(protection.policy).length)
        warn("policy_missing", path, "Desired protection policy has not been recorded.");
    });
    plan.restore_plans.forEach((exercise, i) => {
      const path = `$.restore_plans[${i}]`;
      const protection = reference(
        "protection_plans",
        exercise.protection_plan_id,
        `${path}.protection_plan_id`
      );
      const project = maps.projects.get(protection.project_id);
      const scope = new Set(project.member_item_ids);
      protection.excluded_item_ids.forEach((id) => scope.delete(id));
      if (exercise.target_id) {
        reference("backup_targets", exercise.target_id, `${path}.target_id`);
        if (!protection.target_ids.includes(exercise.target_id))
          warn(
            "historical_target",
            path,
            "Checklist target differs from the current plan; earlier reports remain bound to their recorded selection."
          );
      }
      exercise.item_ids.forEach((id, j) => {
        reference("items", id, `${path}.item_ids[${j}]`);
        if (!scope.has(id))
          warn(
            "historical_scope",
            path,
            "Checklist selection differs from current intended scope; earlier reports remain retained."
          );
      });
      location(exercise.destination, `${path}.destination`);
      exercise.checks.forEach((check, j) => {
        unique(check, `${path}.checks[${j}]`);
        (check.user_reports || []).forEach((report, k) =>
          unique(report, `${path}.checks[${j}].user_reports[${k}]`)
        );
      });
      const reports = reportCount(exercise);
      if (
        (reports || exercise.lifecycle === "prepared") &&
        (!exercise.target_id ||
          !exercise.item_ids.length ||
          exercise.intended_scope === "undecided" ||
          !exercise.exercise_scope_note)
      )
        fail(
          "exercise_scope",
          path,
          "Prepared or reported checklists require target, selection, decided scope and a sample/scope description."
        );
      if (!!reports !== (exercise.lifecycle === "user_recorded_results"))
        fail(
          "report_lifecycle",
          path,
          "Reported-results lifecycle must have reports, and reports require that lifecycle."
        );
      if (!!reports !== own(exercise, "reported_context"))
        fail(
          "reported_context",
          `${path}.reported_context`,
          "Reported results require their immutable historical context; drafts must omit it."
        );
      if (reports) {
        const context = exercise.reported_context;
        const first = exercise.checks
          .flatMap((check) => check.user_reports || [])
          .find((report) => report.id === context.first_report_id);
        if (!first || first.recorded_at !== context.captured_at)
          fail(
            "reported_context",
            `${path}.reported_context`,
            "Historical context must name its first report and recording time in this exercise."
          );
        if (
          context.protection_plan.id !== exercise.protection_plan_id ||
          context.target.id !== exercise.target_id ||
          !equal(
            context.items.map((item) => item.id),
            exercise.item_ids
          )
        )
          fail(
            "reported_context",
            `${path}.reported_context`,
            "Historical context must match this exercise's recorded plan, target and ordered item selection."
          );
        const historicalDestination =
          context.destination &&
          Object.fromEntries(
            Object.entries(context.destination).filter(([key]) => key !== "drive_label")
          );
        if (!equal(historicalDestination, exercise.destination))
          fail(
            "reported_context",
            `${path}.reported_context.destination`,
            "Historical destination must match this exercise's frozen destination."
          );
        location(context.destination, `${path}.reported_context.destination`);
        reference(
          "projects",
          context.protection_plan.project_id,
          `${path}.reported_context.protection_plan.project_id`
        );
        if (own(context.target, "storage_drive_id") !== own(context.target, "storage_drive_label"))
          fail(
            "reported_context",
            `${path}.reported_context.target`,
            "Historical drive ID and label must be recorded together."
          );
        if (context.target.storage_drive_id)
          reference(
            "drives",
            context.target.storage_drive_id,
            `${path}.reported_context.target.storage_drive_id`
          );
        context.items.forEach((item, j) => {
          location(item.location, `${path}.reported_context.items[${j}].location`);
          if (item.kind === "whole_drive" && (!item.location || own(item.location, "path_text")))
            fail(
              "whole_drive",
              `${path}.reported_context.items[${j}]`,
              "Historical whole-drive scope requires a drive and no path text."
            );
        });
        if (!equal(context, captureContext(plan, exercise, first)))
          warn(
            "historical_context_drift",
            path,
            "Current names, locations, versions or target descriptions differ from this checklist's frozen report-time context. Earlier reports retain the historical descriptions."
          );
      }
      if (reports)
        warn(
          "self_report",
          path,
          "Results and their frozen report-time descriptions are user statements, not verified recovery. Imported history is untrusted."
        );
    });
    return warnings;
  }
  function validatePlan(plan) {
    inspectJson(plan);
    structure(plan, SCHEMA);
    return freeze({ warnings: semantic(plan) });
  }
  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }
  function equal(a, b) {
    if (a === b) return true;
    if (!a || !b || typeof a !== "object" || typeof b !== "object") return false;
    if (Array.isArray(a) !== Array.isArray(b)) return false;
    const keys = Object.keys(a);
    return (
      keys.length === Object.keys(b).length &&
      keys.every((key) => own(b, key) && equal(a[key], b[key]))
    );
  }
  function strictParse(text) {
    const plan = parseJson(text);
    validatePlan(plan);
    return freeze(clone(plan));
  }
  function exportPlan(plan) {
    validatePlan(plan);
    return JSON.stringify(plan);
  }
  function createEmptyPlan({ title, document_id, now }) {
    const plan = {
      schema_version: SCHEMA.properties.schema_version.const,
      document_id,
      title,
      revision: 1,
      created_at: now,
      updated_at: now,
    };
    COLLECTIONS.forEach((collection) => {
      plan[collection] = [];
    });
    validatePlan(plan);
    return freeze(plan);
  }
  function newId(prefix) {
    if (typeof prefix !== "string" || !/^[a-z][a-z0-9]{0,11}$/.test(prefix))
      fail("id", "$", "Use a lowercase application ID prefix of 1–12 characters.");
    const crypto = typeof globalThis !== "undefined" && globalThis.crypto;
    if (!crypto || typeof crypto.getRandomValues !== "function")
      fail("randomness_unavailable", "$", "Secure random IDs are unavailable in this browser.");
    let uuid;
    if (typeof crypto.randomUUID === "function") uuid = crypto.randomUUID();
    else {
      const bytes = crypto.getRandomValues(new Uint8Array(16));
      bytes[6] = (bytes[6] & 15) | 64;
      bytes[8] = (bytes[8] & 63) | 128;
      const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
      uuid = `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(
        16,
        20
      )}-${hex.slice(20)}`;
    }
    return `${prefix}_${uuid}`;
  }
  function commandFields(command, names, path) {
    for (const key of Object.keys(command))
      if (!["type", ...names].includes(key))
        fail("command", path, `Unsupported action field: ${key}.`);
    for (const key of names)
      if (!own(command, key))
        fail("command", `${path}.${key}`, "Required action field is missing.");
  }
  function reduce(plan, action) {
    validatePlan(plan);
    inspectJson(action);
    if (!action || typeof action !== "object" || Array.isArray(action))
      fail("command", "$action", "Expected an edit action.");
    if (action.expected_revision !== plan.revision)
      fail(
        "stale_revision",
        "$action.expected_revision",
        "The workspace changed; review the edit again."
      );
    if (!validTimestamp(action.now))
      fail(
        "timestamp",
        "$action.now",
        "An application-recorded timezone-bearing timestamp is required."
      );
    const candidate = clone(plan);
    const command = clone(action);
    delete command.expected_revision;
    delete command.now;
    const history = new Map(plan.restore_plans.filter((r) => reportCount(r)).map((r) => [r.id, r]));
    function find(collection, id) {
      const record = candidate[collection].find((entry) => entry.id === id);
      if (!record)
        fail("record_missing", `$action.${collection}`, "The selected record no longer exists.");
      return record;
    }
    function edit(input, path) {
      if (!input || typeof input !== "object" || Array.isArray(input))
        fail("command", path, "Expected an edit action.");
      const type = input.type;
      if (typeof type !== "string") fail("command", path, "Action type must be text.");
      if (type === "setTitle") {
        commandFields(input, ["title"], path);
        candidate.title = input.title;
        return;
      }
      if (type === "addItemToProject") {
        commandFields(input, ["project_id", "item"], path);
        const project = find("projects", input.project_id);
        structure(input.item, SCHEMA.properties.items.items, `${path}.item`);
        candidate.items.push(clone(input.item));
        project.member_item_ids.push(input.item.id);
        return;
      }
      if (type === "appendReport") {
        commandFields(input, ["restore_plan_id", "check_id", "report"], path);
        const exercise = find("restore_plans", input.restore_plan_id);
        const check = exercise.checks.find((entry) => entry.id === input.check_id);
        if (!check) fail("record_missing", `${path}.check_id`, "Checklist check no longer exists.");
        if (!input.report || typeof input.report !== "object" || Array.isArray(input.report))
          fail("command", `${path}.report`, "Expected a report.");
        if (own(input.report, "recorded_at"))
          fail(
            "command",
            `${path}.report.recorded_at`,
            "Report recording time is supplied by the action context."
          );
        const report = { ...input.report, recorded_at: action.now };
        if (!reportCount(exercise))
          exercise.reported_context = captureContext(candidate, exercise, report);
        check.user_reports = [...(check.user_reports || []), report];
        exercise.lifecycle = "user_recorded_results";
        return;
      }
      const actionFields = {
        addRecord: ["collection", "record"],
        replaceRecord: ["collection", "record"],
        archiveRecord: ["collection", "id", "archived"],
        deleteRecord: ["collection", "id"],
      };
      const fields = own(actionFields, type) ? actionFields[type] : null;
      if (!fields) fail("command", path, "Unsupported edit action.");
      commandFields(input, fields, path);
      if (!COLLECTIONS.includes(input.collection))
        fail("command", `${path}.collection`, "Unsupported record collection.");
      if (type === "addRecord" || type === "replaceRecord") {
        if (!input.record || typeof input.record !== "object" || Array.isArray(input.record))
          fail("command", `${path}.record`, "Expected a record.");
        structure(input.record, SCHEMA.properties[input.collection].items, `${path}.record`);
        if (input.collection === "restore_plans") {
          const old = candidate.restore_plans.find((r) => r.id === input.record.id);
          const oldReports = old ? old.checks.flatMap((c) => c.user_reports || []) : [];
          const incomingReports = Array.isArray(input.record.checks)
            ? input.record.checks.flatMap((c) => c.user_reports || [])
            : [];
          if (!equal(oldReports, incomingReports))
            fail(
              "append_only",
              path,
              "Record results through appendReport; existing report history cannot be replaced."
            );
          if (old && reportCount(old)) {
            const permitted = new Set(["label", "notes", "archived"]);
            const snapshot = (r) =>
              Object.fromEntries(Object.entries(r).filter(([key]) => !permitted.has(key)));
            if (!equal(snapshot(old), snapshot(input.record)))
              fail(
                "frozen_exercise",
                path,
                "Reported exercise scope and check definitions are frozen. Create a new checklist for changes."
              );
          }
        }
        if (type === "addRecord") candidate[input.collection].push(clone(input.record));
        else {
          const old = find(input.collection, input.record.id);
          candidate[input.collection][candidate[input.collection].indexOf(old)] = clone(
            input.record
          );
        }
      } else {
        const record = find(input.collection, input.id);
        if (type === "archiveRecord") record.archived = input.archived;
        else {
          if (input.collection === "restore_plans" && reportCount(record))
            fail(
              "append_only",
              path,
              "Reported checklists must be retained; archive instead of deleting history."
            );
          candidate[input.collection] = candidate[input.collection].filter(
            (r) => r.id !== input.id
          );
        }
      }
    }
    if (command.type === "batch") {
      commandFields(command, ["edits"], "$action");
      if (!Array.isArray(command.edits) || !command.edits.length || command.edits.length > 100)
        fail("command", "$action.edits", "Use 1–100 edits per atomic batch.");
      command.edits.forEach((entry, i) => edit(entry, `$action.edits[${i}]`));
    } else edit(command, "$action");
    // Final enforcement also protects a report created earlier in the same batch.
    for (const [id, old] of history) {
      const current = candidate.restore_plans.find((r) => r.id === id);
      if (!current) fail("append_only", "$action", "Report history must be retained.");
      for (const check of old.checks) {
        const next = current.checks.find((c) => c.id === check.id);
        if (
          !next ||
          !equal(
            (next.user_reports || []).slice(0, (check.user_reports || []).length),
            check.user_reports || []
          )
        )
          fail(
            "append_only",
            "$action",
            "Earlier reports must remain unchanged and in insertion order."
          );
      }
    }
    if (equal(candidate, plan)) return plan;
    if (plan.revision === Number.MAX_SAFE_INTEGER)
      fail(
        "revision_limit",
        "$.revision",
        "Revision limit reached; export this plan before creating a new document."
      );
    candidate.revision += 1;
    candidate.updated_at = action.now;
    validatePlan(candidate);
    return freeze(candidate);
  }
  const stagedImports = new WeakMap();
  function derive(plan) {
    const validation = validatePlan(plan);
    const counts = Object.fromEntries(COLLECTIONS.map((name) => [name, plan[name].length]));
    counts.reports = plan.restore_plans.reduce((sum, exercise) => sum + reportCount(exercise), 0);
    const projects = plan.projects.map((project) => {
      const summary = {
        id: project.id,
        label: project.label,
        member_item_ids: [...project.member_item_ids],
      };
      if (project.intended_home) summary.intended_home = clone(project.intended_home);
      summary.protection_plans = plan.protection_plans
        .filter((p) => p.project_id === project.id)
        .map((p) => {
          const excluded = new Set(p.excluded_item_ids);
          return {
            id: p.id,
            target_ids: [...p.target_ids],
            effective_item_ids: project.member_item_ids.filter((id) => !excluded.has(id)),
            excluded_item_ids: [...p.excluded_item_ids],
            coverage: "unknown",
          };
        });
      return summary;
    });
    return freeze({ coverage: "unknown", warnings: validation.warnings, counts, projects });
  }
  function stageImport(text, currentPlan) {
    const before = exportPlan(currentPlan);
    const document = strictParse(text);
    const summary = derive(document);
    const token = freeze({
      document,
      preview: {
        title: document.title,
        revision: document.revision,
        counts: summary.counts,
        warnings: summary.warnings,
        privacy:
          "This plaintext artifact may contain private labels, paths, account nicknames, notes and self-reports. Imported claims are untrusted. Replacing the workspace replaces its current history; save the current plan first if needed.",
      },
    });
    stagedImports.set(token, before);
    return token;
  }
  function replaceImport(currentPlan, token, options) {
    if (!options || options.confirm !== true)
      fail("confirmation", "$import", "Confirm replacement after reviewing the import preview.");
    if (!token || !stagedImports.has(token))
      fail("import_token", "$import", "Import preview is missing, cancelled or already used.");
    if (stagedImports.get(token) !== exportPlan(currentPlan))
      fail(
        "stale_revision",
        "$import",
        "Workspace changed after preview; review this import again."
      );
    stagedImports.delete(token);
    return token.document;
  }
  function cancelImport(token) {
    stagedImports.delete(token);
  }
  freeze(SCHEMA);
  return Object.freeze({
    PlanError,
    LIMITS,
    COLLECTIONS,
    schema: SCHEMA,
    createEmptyPlan,
    newId,
    validatePlan,
    strictParse,
    exportPlan,
    reduce,
    derive,
    stageImport,
    replaceImport,
    cancelImport,
  });
});
