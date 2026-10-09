/* User-authored choices only. This format contains no observation or operation authority. */
((root, factory) => {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.ProjectIntentModel = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, () => {
  "use strict";
  const MAX_BYTES = 8192;
  const MAX_REQUEST_BYTES = 4096;
  const MAX_DEPTH = 8;
  const MAX_NODES = 256;
  const VERSION = "disk-administration-project-intent/v1";
  const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
  const fail = (message) => {
    throw new Error(message);
  };
  const ensure = (condition, message) => {
    if (!condition) fail(message);
  };
  function keys(value, names) {
    ensure(
      value !== null &&
        typeof value === "object" &&
        !Array.isArray(value) &&
        Object.keys(value).length === names.length &&
        names.every((name) => own(value, name)),
      "This file contains missing or unsupported project-choice fields."
    );
  }
  function text(value, max, empty = false) {
    ensure(
      typeof value === "string" &&
        (empty || value.length > 0) &&
        value.length <= max &&
        !/[\u0000-\u001f\u007f]/.test(value),
      "Project-choice text is invalid or too long."
    );
    // Text inputs and UTF-8 encoders must not silently replace malformed Unicode.
    for (const character of value) {
      const point = character.codePointAt(0);
      ensure(point < 0xd800 || point > 0xdfff, "Project-choice text contains invalid Unicode.");
    }
    return value;
  }
  function relative(value) {
    text(value, 240);
    ensure(
      !value.startsWith("/") &&
        !value.includes("\\") &&
        !value.includes(":") &&
        !value.split("/").some((part) => ["", ".", ".."].includes(part)),
      "Use relative intended paths without parent traversal, colons or backslashes."
    );
    return value;
  }
  function byteLength(value) {
    let bytes = 0;
    for (const character of value) {
      const point = character.codePointAt(0);
      ensure(point < 0xd800 || point > 0xdfff, "Project-choice text contains invalid Unicode.");
      bytes += point <= 0x7f ? 1 : point <= 0x7ff ? 2 : point <= 0xffff ? 3 : 4;
    }
    return bytes;
  }
  function sourceOf(reference) {
    return {
      kind: "packaged_synthetic_observations",
      scenario_id: reference.scenario_id,
      source_revision: reference.source_revision,
      observation_digest: reference.observation_digest,
      reference_decision_digest: reference.reference_decision_digest,
    };
  }
  function validateSource(source, reference) {
    const expected = sourceOf(reference);
    keys(source, Object.keys(expected));
    ensure(
      source.kind === "packaged_synthetic_observations" &&
        source.scenario_id === "aurora-observation" &&
        Number.isSafeInteger(source.source_revision) &&
        source.source_revision > 0 &&
        typeof source.observation_digest === "string" &&
        /^[a-f0-9]{64}$/.test(source.observation_digest) &&
        typeof source.reference_decision_digest === "string" &&
        /^[a-f0-9]{64}$/.test(source.reference_decision_digest),
      "This is not a supported synthetic Aurora source reference."
    );
    ensure(
      Object.keys(expected).every((name) => source[name] === expected[name]),
      "These choices refer to a different Aurora source. Current choices are unchanged; automatic rebinding is unavailable."
    );
  }
  function requestFor(intent, reference) {
    const members = new Map(intent.members.map((member) => [member.entry_id, member]));
    return {
      expected_source_revision: reference.source_revision,
      expected_observation_digest: reference.observation_digest,
      expected_reference_decision_digest: reference.reference_decision_digest,
      member_paths: reference.choices
        .map((choice) => members.get(choice.entry.id))
        .filter((member) => member.included)
        .map((member) => ({ entry_id: member.entry_id, project_path: member.project_path })),
      destination_root_id: intent.destination_root_id,
      destination_folder: intent.destination_folder,
    };
  }
  function validateIntent(intent, reference) {
    keys(intent, ["members", "destination_root_id", "destination_folder"]);
    ensure(
      Array.isArray(intent.members) &&
        intent.members.length === reference.choices.length &&
        intent.members.length === 8,
      "Save all eight Aurora choices exactly once."
    );
    const allowed = new Set(reference.choices.map((choice) => choice.entry.id));
    const members = new Map();
    for (const member of intent.members) {
      keys(member, ["entry_id", "included", "project_path"]);
      text(member.entry_id, 128);
      ensure(
        allowed.has(member.entry_id) &&
          !members.has(member.entry_id) &&
          typeof member.included === "boolean",
        "Project choices contain an unknown, repeated or invalid member."
      );
      text(member.project_path, 240, !member.included);
      if (member.included) relative(member.project_path);
      members.set(member.entry_id, member);
    }
    ensure(
      intent.members.some((member) => member.included),
      "Include at least one member before saving project choices."
    );
    text(intent.destination_root_id, 128);
    ensure(
      reference.roots.some((root) => root.id === intent.destination_root_id),
      "Choose a recorded Aurora root."
    );
    relative(intent.destination_folder);
    const normalised = {
      members: reference.choices.map((choice) => ({ ...members.get(choice.entry.id) })),
      destination_root_id: intent.destination_root_id,
      destination_folder: intent.destination_folder,
    };
    ensure(
      byteLength(JSON.stringify(requestFor(normalised, reference))) <= MAX_REQUEST_BYTES,
      "These choices exceed the existing 4 KiB review-request limit. Shorten the intended paths."
    );
    return normalised;
  }
  function validate(document, reference) {
    keys(document, ["schema_version", "document_kind", "source", "intent"]);
    ensure(
      document.schema_version === VERSION &&
        document.document_kind === "user_authored_project_intent",
      "Open a project-choices file. A saved review report or inventory cannot restore choices."
    );
    validateSource(document.source, reference);
    return validateIntent(document.intent, reference);
  }
  // A small strict parser keeps duplicate decoded keys and complexity visible.
  // The existing Disk Map parser uses the same null-prototype/duplicate-key pattern.
  function parseJSON(input) {
    let index = 0,
      nodes = 0;
    const whitespace = () => {
      while (/[ \t\r\n]/.test(input[index] || "x")) index++;
    };
    function string() {
      const start = index++;
      while (index < input.length) {
        if (input[index] === "\\") {
          index += 2;
          continue;
        }
        if (input[index++] === '"') return JSON.parse(input.slice(start, index));
      }
      fail("Unterminated JSON text.");
    }
    function value(depth) {
      ensure(
        ++nodes <= MAX_NODES && depth <= MAX_DEPTH,
        "This project-choices file is too complex."
      );
      whitespace();
      const character = input[index];
      if (character === '"') return string();
      if (character === "{" || character === "[") {
        const object = character === "{";
        const result = object ? Object.create(null) : [];
        const end = object ? "}" : "]";
        index++;
        whitespace();
        if (input[index] === end) {
          index++;
          return result;
        }
        while (index < input.length) {
          if (object) {
            whitespace();
            ensure(input[index] === '"', "Expected a JSON key.");
            const key = string();
            ensure(
              ++nodes <= MAX_NODES && key.length <= 64 && !own(result, key),
              "This file contains an oversized or repeated JSON key."
            );
            whitespace();
            ensure(input[index++] === ":", "Expected a JSON colon.");
            result[key] = value(depth + 1);
          } else result.push(value(depth + 1));
          whitespace();
          const separator = input[index++];
          if (separator === end) return result;
          ensure(separator === ",", "Expected a JSON separator.");
        }
        fail("Incomplete project-choices JSON.");
      }
      for (const [literal, parsed] of [
        ["true", true],
        ["false", false],
        ["null", null],
      ]) {
        if (input.startsWith(literal, index)) {
          index += literal.length;
          return parsed;
        }
      }
      const match = /-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(input.slice(index));
      ensure(match && match.index === 0, "Expected a JSON value.");
      index += match[0].length;
      ensure(
        /^-?(?:0|[1-9]\d*)$/.test(match[0]),
        "Project-choice revisions must use decimal integer notation."
      );
      const number = Number(match[0]);
      ensure(
        Number.isSafeInteger(number),
        "Only exact safe integers are supported in project choices."
      );
      return number;
    }
    const result = value(0);
    whitespace();
    ensure(index === input.length, "Unexpected text after project-choices JSON.");
    return result;
  }
  function parse(input, reference) {
    ensure(
      typeof input === "string" && input.length <= MAX_BYTES && byteLength(input) <= MAX_BYTES,
      "Project-choices files must be no larger than 8 KiB."
    );
    let document;
    try {
      document = parseJSON(input);
    } catch (error) {
      fail(`Cannot open project choices: ${error.message}`);
    }
    return validate(document, reference);
  }
  function serialise(intent, reference) {
    const document = {
      schema_version: VERSION,
      document_kind: "user_authored_project_intent",
      source: sourceOf(reference),
      intent: validateIntent(intent, reference),
    };
    const output = JSON.stringify(document, null, 2) + "\n";
    ensure(byteLength(output) <= MAX_BYTES, "Project-choices files must be no larger than 8 KiB.");
    return output;
  }
  return {
    MAX_BYTES,
    MAX_REQUEST_BYTES,
    MAX_DEPTH,
    MAX_NODES,
    VERSION,
    parse,
    serialise,
    validateIntent,
    requestFor,
    sourceOf,
    byteLength,
  };
});
