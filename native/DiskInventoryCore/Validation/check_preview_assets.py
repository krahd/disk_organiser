"""Keep the shared bundled catalogue byte-identical to seven canonical assets."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "native/DiskInventoryCore/Sources/DiskInventoryDesktop/Resources/Catalogue"
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
    examples = TARGET.parent / "Examples"
    expected = {"working.json": "owned-creative.example.json", "archive.json": "owned-archive.example.json"}
    sample_rows = []
    if examples.is_symlink():
        raise SystemExit("Example resources must not be symlinks.")
    for name, canonical in expected.items():
        original = ROOT / "prototypes/inventory_catalogue" / canonical
        destination = examples / name
        if original.is_symlink() or destination.is_symlink():
            raise SystemExit("Example paths must not be symlinks.")
        raw = original.read_bytes()
        if not 0 < len(raw) <= 1024 * 1024:
            raise SystemExit("Example snapshot exceeds its bound.")
        sample_rows.append({"file": name, "canonical": "prototypes/inventory_catalogue/" + canonical,
                            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        if sync:
            examples.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
        elif destination.read_bytes() != raw:
            raise SystemExit("Example differs from the canonical owned data.")
    manifest = (json.dumps({"examples": sample_rows}, indent=2) + "\n").encode()
    if sync:
        (examples / "manifest.json").write_bytes(manifest)
    elif (examples / "manifest.json").read_bytes() != manifest:
        raise SystemExit("Example manifest differs.")
    if {p.name for p in examples.iterdir()} != set(expected) | {"manifest.json"}:
        raise SystemExit("Unexpected example resource.")
    print("Application example parity passed: 2 fixed owned-example snapshots")

    validation = TARGET.parent / "CatalogueValidation"
    if validation.is_symlink() or (validation / "utf8-encoder.js").is_symlink():
        raise SystemExit("Validation resources must not be symlinks.")
    raw = (validation / "utf8-encoder.js").read_bytes()
    if not 0 < len(raw) <= 8192:
        raise SystemExit("Unexpected parser shim size.")
    manifest = (json.dumps({"assets": [{"file": "utf8-encoder.js", "bytes": len(raw),
                                     "sha256": hashlib.sha256(raw).hexdigest()}]}, indent=2) + "\n").encode()
    if sync:
        (validation / "manifest.json").write_bytes(manifest)
    elif (validation / "manifest.json").read_bytes() != manifest:
        raise SystemExit("Parser shim manifest differs.")
    if {p.name for p in validation.iterdir()} != {"utf8-encoder.js", "manifest.json"}:
        raise SystemExit("Unexpected parser-only validation resource.")
    print("Parser validation resources passed: one bounded UTF-8 shim outside the WebKit read root")


if __name__ == "__main__":
    main()
