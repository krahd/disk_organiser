"""Test-only differential oracle; every observed source is created here.

Never accepts an input source path. Reads only the fixed hosted-test output
folder, or --self-test compares separately created Python-owned fixtures.
No legacy application, database, operation or provider is imported.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
import tempfile

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from backend.inventory_snapshot import observe_snapshot
from backend.observation_session import select_root

CASES = ("empty", "nested", "links", "placeholder", "depth-limit", "directory-limit")
MAX_BYTES = 1024 * 1024


def make_fixture(root: Path, case: str, sentinel: Path) -> None:
    if case == "empty":
        return
    if case == "nested":
        (root / "notes.txt").write_bytes(b"abc")
        (root / "Projects").mkdir()
        (root / "Projects" / "README.md").write_bytes(b"hello")
        (root / "Projects" / "Clip.mov").write_bytes(b"1234567")
    elif case == "links":
        (root / "regular.txt").write_bytes(b"abc")
        os.link(root / "regular.txt", root / "alias")
        (root / "outside").symlink_to(sentinel, target_is_directory=True)
    elif case == "placeholder":
        (root / "report.icloud").write_bytes(b"")
        (root / "okay.txt").write_bytes(b"x")
    elif case == "depth-limit":
        current = root
        for index in range(9):
            current = current / f"d{index}"
            current.mkdir()
        (current / "leaf.txt").write_bytes(b"x")
    elif case == "directory-limit":
        for index in range(501):
            (root / f"f{index:03}").write_bytes(b"")
    else:
        raise AssertionError("Unknown fixed fixture")


def oracle(case: str) -> dict:
    # This harness owns both source and out-of-scope sentinel; nothing pre-existing
    # is scanned. /private avoids macOS's /var temporary-directory symlink only
    # by resolving the harness-created fixture at creation, never user input.
    with tempfile.TemporaryDirectory(prefix="disk-native-oracle-") as temporary:
        owned = Path(temporary).resolve(strict=True)
        root, sentinel = owned / "source", owned / "sentinel"
        root.mkdir()
        sentinel.mkdir()
        witness = sentinel / "not-observed.txt"
        witness.write_bytes(b"outside witness")
        make_fixture(root, case, sentinel)
        before = witness.read_bytes()
        selection = select_root(str(root))
        result = observe_snapshot(selection, f"Owned fixture {case}")
        assert result["state"] in ("observed", "partial"), (case, result["state"])
        assert result["snapshot"] is not None
        assert witness.read_bytes() == before
        assert all("not-observed" not in row["path"] for row in result["snapshot"]["entries"])
        assert selection.state == "spent"
        return result["snapshot"]


def normalise(snapshot: dict) -> dict:
    result = json.loads(json.dumps(snapshot))
    result["source"]["observed_at"] = "2026-10-09T00:00:00Z"
    result["source"]["scan_id"] = "scan_" + "0" * 24
    return result


def read_native(folder: Path, case: str) -> dict:
    # Test artifact only. Bound the read itself; no trust in a preceding stat.
    fd = os.open(folder / (case + ".json"), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode)
        data = bytearray()
        while len(data) <= MAX_BYTES:
            block = os.read(fd, min(65536, MAX_BYTES + 1 - len(data)))
            if not block:
                break
            data.extend(block)
        after = os.fstat(fd)
        assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                before.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size,
                                      after.st_mtime_ns, after.st_ctime_ns)
        assert len(data) <= MAX_BYTES
        def unique(pairs):
            result = {}
            for key, value in pairs:
                assert key not in result, "Duplicate fixture JSON key"
                result[key] = value
            return result
        return json.loads(data.decode("utf-8", "strict"), object_pairs_hook=unique)
    finally:
        os.close(fd)


def main() -> None:
    if sys.argv[1:] == ["--self-test"]:
        for case in CASES:
            assert normalise(oracle(case)) == normalise(oracle(case)), case
        print(f"Python oracle self-check: {len(CASES)} owned fixtures; no native execution claimed")
        return
    assert not sys.argv[1:], "No source/output path arguments are accepted"
    assert sys.platform == "darwin", "Actual native differential gate requires macOS"
    temporary = os.environ.get("RUNNER_TEMP")
    assert temporary and os.path.isabs(temporary)
    folder = Path(temporary) / "disk-inventory-goldens"
    assert os.environ.get("DISK_INVENTORY_GOLDEN_OUTPUT") == str(folder)
    for case in CASES:
        expected, observed = normalise(oracle(case)), normalise(read_native(folder, case))
        assert observed == expected, f"Native/Python v1 mismatch for {case}:\n{observed!r}\n{expected!r}"
        print(f"Native/Python owned parity: {case} ({len(observed['entries'])} entries)")
    print(f"Native/Python differential passed: {len(CASES)} fixed owned cases")


if __name__ == "__main__":
    main()
