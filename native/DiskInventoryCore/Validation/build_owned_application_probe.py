"""Compile a separate owned-only process probe, never an application product."""
from pathlib import Path
import hashlib
import json
import platform
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
if platform.system() != "Darwin":
    raise SystemExit("The owned probe requires the reviewed Darwin lane.")
# swift build's official output path selects the matching module/object variant.
BIN = Path(subprocess.check_output(["xcrun", "swift", "build", "--package-path", str(ROOT), "--show-bin-path"], text=True).strip()).resolve()
if not BIN.is_relative_to((ROOT / ".build").resolve()):
    raise SystemExit("Unexpected package build location.")
TARGET = BIN / "owned-application-probe"
TARGET.mkdir(mode=0o700, exist_ok=False)
SOURCE = ROOT / "Validation/OwnedApplicationProbe"
objects = sorted((BIN / "DiskInventoryDesktop.build").glob("*.swift.o"))
if not objects or not (BIN / "Modules/DiskInventoryDesktop.swiftmodule").is_file():
    raise SystemExit("Build the debug desktop target first.")
sdk = subprocess.check_output(["xcrun", "--sdk", "macosx", "--show-sdk-path"], text=True).strip()
subprocess.run(["xcrun", "swiftc", "-swift-version", "6", "-parse-as-library", "-sdk", sdk,
                "-target", platform.machine() + "-apple-macosx13.0", "-I", str(BIN / "Modules"),
                str(SOURCE / "main.swift"), *map(str, objects), "-o", str(TARGET / "DiskLibraryOwnedProbe")], check=True)
shutil.copyfile(SOURCE / "catalogue.json", TARGET / "catalogue.json")
print(json.dumps({"owned_probe": "compiled separately", "source_sha256": hashlib.sha256((SOURCE / "main.swift").read_bytes()).hexdigest(),
                  "fixture_sha256": hashlib.sha256((SOURCE / "catalogue.json").read_bytes()).hexdigest(), "desktop_objects": len(objects)}))
