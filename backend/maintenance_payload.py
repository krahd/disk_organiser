"""Resource bounds for an already-open maintenance JSON payload.

Importing this module does not load the app or open files. These are new
product limits, not a schema or a filesystem/path safety boundary.
"""

import json


MAX_BYTES = 64 * 1024
MAX_DEPTH = 32
MAX_NODES = 4096


def _check_depth(text):
    """Bound container nesting before the recursive JSON decoder runs."""
    depth = 0
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise ValueError("Maintenance JSON exceeds nesting limit")
        elif char in "]}":
            depth -= 1
            if depth < 0:
                raise ValueError("Invalid maintenance JSON container")
    # The standard decoder remains responsible for syntax validation.


def _check_nodes(value):
    """Count the retained root, containers, scalar values and object keys.

    Iterators keep traversal state proportional to depth, not payload width.
    Duplicate object keys retain the standard decoder's last-value semantics.
    """
    count = 0
    pending = [iter((value,))]
    while pending:
        try:
            node = next(pending[-1])
        except StopIteration:
            pending.pop()
            continue
        count += 1
        if isinstance(node, dict):
            count += len(node)  # Each retained object key is one string node.
            pending.append(iter(node.values()))
        elif isinstance(node, list):
            pending.append(iter(node))
        if count > MAX_NODES:
            raise ValueError("Maintenance JSON exceeds node limit")


def read_maintenance_payload(stream):
    """Read once from a binary stream and return an unchanged JSON value.

    Read at most MAX_BYTES + 1 bytes; reject overflow before UTF-8 decoding.
    The caller owns opening and closing the stream. This helper never writes,
    repairs, truncates or retries it, and gives no guarantee about open/read
    blocking or the provenance of its contents.
    """
    raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Maintenance JSON exceeds byte limit")
    text = raw.decode("utf-8")
    _check_depth(text)
    value = json.loads(text)
    _check_nodes(value)
    return value
