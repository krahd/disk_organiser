"use strict";
// Test-only fixed native artifacts. No browser, source inventory or application.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const C = require("../../../frontend/inventory-snapshot-model.js");
const cases = ["empty", "nested", "links", "placeholder", "depth-limit", "directory-limit"];
const folder =
  process.env.RUNNER_TEMP && path.join(process.env.RUNNER_TEMP, "disk-inventory-goldens");
assert(folder && path.isAbsolute(folder));
assert.equal(process.env.DISK_INVENTORY_GOLDEN_OUTPUT, folder);
assert.equal(process.argv.length, 2, "No source/output path arguments");
let catalogue = C.empty();
for (const name of cases) {
  const filename = path.join(folder, `${name}.json`);
  const fd = fs.openSync(filename, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
  let bytes;
  try {
    const before = fs.fstatSync(fd, { bigint: true });
    assert(before.isFile());
    const buffer = Buffer.alloc(C.LIMITS.snapshotBytes + 1);
    let used = 0;
    while (used < buffer.length) {
      const read = fs.readSync(fd, buffer, used, buffer.length - used, null);
      if (!read) break;
      used += read;
    }
    const after = fs.fstatSync(fd, { bigint: true });
    for (const key of ["dev", "ino", "size", "mtimeNs", "ctimeNs"])
      assert.equal(before[key], after[key]);
    assert(used <= C.LIMITS.snapshotBytes);
    bytes = buffer.subarray(0, used);
  } finally {
    fs.closeSync(fd);
  }
  const input = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  const snapshot = C.parse(input);
  assert.equal(snapshot.source.label, `Owned fixture ${name}`);
  assert.equal(snapshot.schema_version, C.VERSION);
  assert.equal(Object.hasOwn(snapshot.source, "trusted"), false);
  assert.equal(Object.hasOwn(snapshot.source, "physical_volume_identity"), false);
  assert(Object.isFrozen(snapshot));
  catalogue = C.add(catalogue, snapshot, `Native owned ${name}`);
  // Generated output must remain ordinary untrusted v1 input, including exactly
  // the same rejection rules after malicious modification of that artifact.
  const hostile = JSON.parse(input);
  hostile.source.trusted = "true";
  assert.throws(() => C.parse(JSON.stringify(hostile)));
  const duplicate = input.replace(
    '"schema_version":',
    '"schema_version":"duplicate","schema_version":'
  );
  assert.notEqual(duplicate, input);
  assert.throws(() => C.parse(duplicate));
  const escapedDuplicate = input.replace(
    '"schema_version":',
    '"schema_\\u0076ersion":"duplicate","schema_version":'
  );
  assert.throws(() => C.parse(escapedDuplicate));
  console.log(`Unchanged JS parser accepts native ${name}; authority/duplicate injection rejects`);
}
assert.deepEqual(C.parse(C.exportCatalogue(catalogue)), catalogue);
assert.equal(catalogue.records.length, cases.length);
console.log(`Native parser/catalogue roundtrip passed: ${cases.length} snapshots`);
