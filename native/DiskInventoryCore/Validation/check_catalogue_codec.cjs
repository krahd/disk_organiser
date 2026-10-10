/* Compare the parser-only UTF-8 shim and isolated codec with canonical Node admission. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../../..");
const assets = path.join(root, "native/DiskInventoryCore/Sources/DiskInventoryDesktop/Resources");
const model = require(path.join(root, "frontend/inventory-snapshot-model.js"));
const corpus = JSON.parse(fs.readFileSync(path.join(root,
  "native/DiskInventoryCore/Tests/DiskInventoryPreviewTests/Resources/LibraryValidation/corpus.json"), "utf8"));
const context = vm.createContext({});
for (const name of ["CatalogueValidation/utf8-encoder.js", "Catalogue/manual-planning-model.js", "Catalogue/inventory-snapshot-model.js"])
  vm.runInContext(fs.readFileSync(path.join(assets, name), "utf8"), context);
const encode = vm.runInContext("(s) => Array.from(new TextEncoder().encode(s))", context);
const canonical = (input) => {
  const value = model.parse(input);
  if (value.schema_version !== model.CATALOGUE) throw Error("not a catalogue");
  return model.exportCatalogue(value);
};
const isolated = vm.runInContext(`(text) => {
  const value = InventoryCatalogue.parse(text);
  if (value.schema_version !== InventoryCatalogue.CATALOGUE) throw Error("not a catalogue");
  return InventoryCatalogue.exportCatalogue(value);
}`, context);
let samples = ["", "ascii", "\u0000\u007f\u0080\u07ff\u0800\uffff", "😀𐀀\ud800x\udfff", "\ud800\ud800\udc00", "e\u0301é"];
let seed = 0x13456789;
for (let n = 0; n < 4096; n++) {
  let s = "";
  for (let j = 0; j < 32; j++) { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; s += String.fromCharCode(seed & 0xffff); }
  samples.push(s);
}
for (const input of samples) assert.deepEqual(Array.from(encode(input)), Array.from(new TextEncoder().encode(input)));
assert.throws(() => encode("x".repeat(4 * 1024 * 1024 + 1)));
for (const row of corpus) {
  let result = null;
  try { result = canonical(row.input); } catch (_) {}
  assert.equal(result, row.canonical, row.name + " canonical expectation");
  if (result === null) assert.throws(() => isolated(row.input), row.name);
  else assert.equal(isolated(row.input), result, row.name);
}
assert.equal(vm.runInContext("typeof process + ':' + typeof require + ':' + typeof fetch + ':' + typeof document", context), "undefined:undefined:undefined:undefined");
console.log(`Catalogue codec source parity passed: ${corpus.length} admission cases and ${samples.length} UTF-8 samples`);
