"""Pure descriptions for a future owned-folder probe. No I/O or access authority.

Reconstructed checkpoint, not a byte recovery of the lost host implementation.
Parsing these claims never proves a signature, filesystem identity or OS grant.
"""
from dataclasses import dataclass
import json
import re
import stat


class Refusal(ValueError):
    pass


FIXTURE_BYTES = 4096
INVENTORY_BYTES = 8 * 1024 * 1024
MAX_ENTRIES = 20000
MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_LINKS = 40
MAX_STEPS = 4096
MAX_TOTAL_STEPS = 200000
SELECTED = b"0123456789abcdef0123456789abcdef"
SIBLING = b"fedcba9876543210fedcba9876543210"
BUNDLE_PREFIX = "org.diskorganiser.owned-selection-probe."
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def utf8(value):
    require(type(value) is str, "text required")
    try:
        return value.encode("utf-8", "strict")
    except UnicodeError as error:
        raise Refusal("invalid Unicode") from error


def keys(value, expected):
    require(type(value) is dict and set(value) == set(expected), "unexpected fields")


def integer(value, upper):
    require(type(value) is int and 0 <= value <= upper, "integer range")
    return value


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, "duplicate JSON key")
        value[key] = item
    return value


def decode_claim(data, maximum):
    require(type(data) is bytes and 0 < len(data) <= maximum, "JSON byte budget")
    # Bound parser nesting without treating brackets inside JSON strings as structure.
    depth, quoted, escaped = 0, False, False
    for byte in data:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            require(depth <= 16, "JSON nesting budget")
        elif byte in (93, 125):
            depth -= 1
            require(depth >= 0, "invalid JSON nesting")
    def invalid_constant(value):
        raise Refusal("non-finite JSON number")
    def invalid_float(value):
        raise Refusal("non-integer JSON number")
    try:
        return json.loads(data.decode("utf-8", "strict"), object_pairs_hook=_pairs,
                          parse_constant=invalid_constant, parse_float=invalid_float)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise Refusal("invalid bounded JSON claim") from error


def _path(value, absolute=False, root=False):
    raw = utf8(value)
    require(0 < len(raw) <= 1024 and "\\" not in value and
            all(ord(c) >= 32 and ord(c) != 127 for c in value), "unsafe path")
    if root and value == ".":
        return value
    require(value.startswith("/") == absolute, "path form")
    parts = value[1:].split("/") if absolute else value.split("/")
    require(all(p not in ("", ".", "..") for p in parts), "non-exact path")
    return value


@dataclass(frozen=True)
class ObjectClaim:
    device: int
    inode: int
    mode: int
    uid: int
    gid: int
    size: int


@dataclass(frozen=True)
class FixtureClaim:
    run_id: str
    case_id: str
    bundle_identifier: str
    paths: tuple[tuple[str, str], ...]
    objects: tuple[tuple[str, ObjectClaim], ...]


def parse_fixture_claim(data):
    """Validate claimed synthetic coordinates; do not open or trust them."""
    value = decode_claim(data, FIXTURE_BYTES)
    keys(value, {"schemaVersion", "runID", "caseID", "bundleIdentifier", "fixtureParent",
                 "selectedPath", "selectedFile", "siblingFile", "absentPath", "objects",
                 "selectedBytesHex", "siblingBytesHex"})
    require(type(value["schemaVersion"]) is int and value["schemaVersion"] == 1, "schema")
    for key in ("runID", "caseID"):
        require(type(value[key]) is str and UUID.fullmatch(value[key]) is not None, "canonical UUID")
    require(value["bundleIdentifier"] == BUNDLE_PREFIX + value["caseID"], "case-bound bundle")
    parent = _path(value["fixtureParent"], absolute=True)
    expected = {"fixtureParent": parent, "selectedPath": parent + "/selected",
                "selectedFile": parent + "/selected/probe.bin",
                "siblingFile": parent + "/outside/sentinel.bin",
                "absentPath": parent + "/selected/must-remain-absent.bin"}
    for key, path in expected.items():
        _path(path, absolute=True)
        require(value[key] == path, "fixed fixture coordinate")
    require(value["selectedBytesHex"] == SELECTED.hex() and
            value["siblingBytesHex"] == SIBLING.hex(), "fixed nonempty controls")
    keys(value["objects"], {"parent", "selected", "selectedFile", "siblingFile"})
    objects = []
    for key, item in sorted(value["objects"].items()):
        keys(item, {"device", "inode", "mode", "uid", "gid", "size"})
        for field in ("device", "size"):
            integer(item[field], 2**63 - 1)
        integer(item["inode"], 2**64 - 1)
        for field in ("mode", "uid", "gid"):
            integer(item[field], 2**32 - 1)
        directory = key in ("parent", "selected")
        require(item["mode"] == (stat.S_IFDIR | 0o700 if directory else stat.S_IFREG | 0o600),
                "fixed owned fixture mode")
        if not directory:
            require(item["size"] == 32, "fixed content length")
        objects.append((key, ObjectClaim(**item)))
    require(len({(o.device, o.inode) for _, o in objects}) == 4, "distinct object claims")
    require(len({(o.device, o.uid, o.gid) for _, o in objects}) == 1, "same owned filesystem claims")
    return FixtureClaim(value["runID"], value["caseID"], value["bundleIdentifier"],
                        tuple(sorted(expected.items())), tuple(objects))


@dataclass(frozen=True)
class InventoryClaim:
    """Immutable description; neither an observed listing nor a trusted seal."""
    descendants: tuple[str, ...]
    resolved_links: tuple[tuple[str, str], ...]
    total_claimed_bytes: int


def _resolve_link(path, rows, remaining):
    resolved = path.split("/")[:-1]
    require(len(resolved) <= 128 and len("/".join(resolved).encode()) <= 1024,
            "initial resolution budget")
    pending = rows[path]["target"].split("/")
    seen = set()
    expansions = 1
    for unused in range(MAX_STEPS):
        remaining[0] -= 1
        require(remaining[0] >= 0, "aggregate resolution budget")
        require(len(pending) <= 1024 and len("/".join(pending).encode()) <= 16384,
                "pending resolution budget")
        state = (tuple(resolved), tuple(pending))
        require(state not in seen, "link cycle")
        seen.add(state)
        if not pending:
            return "/".join(resolved) or "."
        current = "/".join(resolved) or "."
        require(rows[current]["kind"] == "directory", "non-directory intermediate")
        part = pending.pop(0)
        if part in ("", "."):
            continue
        if part == "..":
            require(bool(resolved), "link escapes root")
            resolved.pop()
            continue
        candidate = "/".join(resolved + [part])
        require(candidate in rows, "missing link target")
        row = rows[candidate]
        if row["kind"] == "symlink":
            expansions += 1
            require(expansions <= MAX_LINKS, "link expansion budget")
            pending = row["target"].split("/") + pending
        else:
            resolved.append(part)
            require(len(resolved) <= 128 and len(candidate.encode()) <= 1024,
                    "resolved path budget")
    raise Refusal("resolution step budget")


def validate_inventory_claim(entries):
    """Pure complete-inventory validation; links resolve only against these rows."""
    require(type(entries) is list and 1 <= len(entries) <= MAX_ENTRIES, "entry budget")
    rows, total = {}, 0
    kinds = {"directory": stat.S_IFDIR, "file": stat.S_IFREG, "symlink": stat.S_IFLNK}
    for item in entries:
        require(type(item) is dict and type(item.get("kind")) is str and
                item["kind"] in kinds, "inventory kind")
        kind = item["kind"]
        keys(item, {"path", "kind", "mode", "uid", "gid"} |
             ({"size", "sha256"} if kind == "file" else {"target"} if kind == "symlink" else set()))
        path = _path(item["path"], root=True)
        require(path not in rows, "duplicate inventory path")
        for field in ("mode", "uid", "gid"):
            integer(item[field], 2**32 - 1)
        require(stat.S_IFMT(item["mode"]) == kinds[kind], "kind/mode mismatch")
        if kind == "file":
            integer(item["size"], MAX_FILE_BYTES)
            require(type(item["sha256"]) is str and SHA256.fullmatch(item["sha256"]) is not None,
                    "digest form")
            total += item["size"]
            require(total <= MAX_TOTAL_BYTES, "total byte budget")
        if kind == "symlink":
            target = item["target"]
            require(0 < len(utf8(target)) <= 1024 and not target.startswith("/") and
                    "\\" not in target and all(ord(c) >= 32 and ord(c) != 127 for c in target),
                    "relative link target required")
        rows[path] = item
    require("." in rows and rows["."]["kind"] == "directory", "one directory root required")
    for path in rows:
        if path != ".":
            parent = path.rpartition("/")[0] or "."
            require(parent in rows and rows[parent]["kind"] == "directory", "real parent required")
    remaining = [MAX_TOTAL_STEPS]
    targets = tuple((path, _resolve_link(path, rows, remaining)) for path in sorted(rows)
                    if rows[path]["kind"] == "symlink")
    return InventoryClaim(tuple(sorted(set(rows) - {"."})), targets, total)


def parse_inventory_claim(data):
    value = decode_claim(data, INVENTORY_BYTES)
    keys(value, {"schemaVersion", "entries"})
    require(type(value["schemaVersion"]) is int and value["schemaVersion"] == 1, "schema")
    return validate_inventory_claim(value["entries"])


if __name__ == "__main__":
    raise SystemExit(2)  # No operational path, fixture, signing or launch CLI.
