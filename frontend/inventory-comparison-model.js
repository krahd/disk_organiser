/* Bounded comparisons of historical claims. No content or storage access. */
(function (root, factory) {
  "use strict";
  if (typeof module === "object" && module.exports)
    module.exports = factory(require("./inventory-snapshot-model.js"));
  else root.InventoryComparison = factory(root.InventoryCatalogue);
})(typeof globalThis !== "undefined" ? globalThis : this, function (C) {
  "use strict";
  const freeze = (value) => {
    if (value && typeof value === "object") {
      Object.values(value).forEach(freeze);
      Object.freeze(value);
    }
    return value;
  };
  const copy = (value) => JSON.parse(JSON.stringify(value));
  function compare(catalogue, leftId, rightId) {
    C.validate(catalogue);
    if (leftId === rightId) throw Error("Choose two different saved records.");
    const left = catalogue.records.find((r) => r.id === leftId),
      right = catalogue.records.find((r) => r.id === rightId);
    if (!left || !right) throw Error("Choose two records from the current catalogue.");
    const maps = [left, right].map((r) => new Map(r.snapshot.entries.map((e) => [e.path, e])));
    const uncertain = (entry, map) => {
      if (!entry) return false;
      if (!C.selectable(entry)) return true;
      let path = entry.path;
      while (path !== ".") {
        path = path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : ".";
        const parent = map.get(path);
        if (!parent || parent.kind !== "directory" || parent.status !== "observed") return true;
      }
      return false;
    };
    const paths = [...new Set([...maps[0].keys(), ...maps[1].keys()])]
      .filter((path) => path !== ".")
      .sort();
    const counts = {
      matching: 0,
      different: 0,
      left: 0,
      right: 0,
      uncertain: 0,
    };
    const rows = paths.map((path) => {
      const a = maps[0].get(path) || null,
        b = maps[1].get(path) || null,
        hasUncertainty = uncertain(a, maps[0]) || uncertain(b, maps[1]);
      const category = hasUncertainty
        ? "uncertain"
        : !a
        ? "right"
        : !b
        ? "left"
        : a.kind === b.kind && a.logical_bytes === b.logical_bytes
        ? "matching"
        : "different";
      counts[category]++;
      return { path, category, left: copy(a), right: copy(b) };
    });
    const source = (record) => ({
      id: record.id,
      label: record.label,
      source: copy(record.snapshot.source),
      gaps: copy(record.snapshot.gaps),
    });
    return freeze({ left: source(left), right: source(right), counts, rows });
  }
  return Object.freeze({ compare });
});
