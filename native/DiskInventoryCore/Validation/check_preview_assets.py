"""Keep the test-only bundled catalogue byte-identical to seven canonical assets."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "native/DiskInventoryCore/Tests/DiskInventoryPreviewTests/Resources/Catalogue"
NAMES = (
    "inventory-catalogue.html", "inventory-catalogue.js", "inventory-catalogue.css",
    "inventory-snapshot-model.js", "inventory-comparison-model.js",
    "manual-planning-model.js", "manual-workspace.css",
)


def main():
    if sys.argv[1:] not in ([], ["--sync"]):
        raise SystemExit("Only --sync (explicit source copy) or no arguments (check) is supported.")
    sync = sys.argv[1:] == ["--sync"]
    rows = []
    for name in NAMES:
        source = ROOT / "frontend" / name
        destination = TARGET / name
        if source.is_symlink() or destination.is_symlink() or TARGET.is_symlink():
            raise SystemExit("A bundled asset path must not be a symlink.")
        raw = source.read_bytes()
        if not 0 < len(raw) <= 256 * 1024:
            raise SystemExit("Unexpected asset size.")
        rows.append({"file": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        if sync:
            TARGET.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
        elif destination.read_bytes() != raw:
            raise SystemExit(f"Bundled asset differs from canonical frontend: {name}")
    manifest = (json.dumps({"assets": rows}, indent=2) + "\n").encode()
    if sync:
        (TARGET / "manifest.json").write_bytes(manifest)
    elif (TARGET / "manifest.json").read_bytes() != manifest:
        raise SystemExit("Bundled asset manifest differs.")
    if {p.name for p in TARGET.iterdir()} != set(NAMES) | {"manifest.json"}:
        raise SystemExit("Unexpected file in WebKit's narrow read root.")
    print(f"Owned WebKit asset parity passed: {len(rows)} exact canonical assets")


if __name__ == "__main__":
    main()
