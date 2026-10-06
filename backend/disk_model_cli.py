"""Read-only Disk Model CLI: JSON on stdout, optional progress on stderr."""
from __future__ import annotations

import argparse
import json
import signal
import sys

from backend.disk_model import ScanLimits, export_json, query_entries, scan_storage, validate_inventory

MAX_IMPORT_BYTES = 32 * 1024 * 1024


def load_export(path: str) -> dict:
    # Exports may contain private paths; this tool never uploads their contents.
    with open(path, "rb") as handle:
        payload = handle.read(MAX_IMPORT_BYTES + 1)
    if len(payload) > MAX_IMPORT_BYTES:
        raise ValueError("Inventory import exceeds 32 MiB")
    value = json.loads(payload)
    validate_inventory(value)
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="Observe explicitly selected folders without writing to them")
    scan.add_argument("roots", nargs="+")
    scan.add_argument("--hash-files", action="store_true", help="Opt into bounded local full-file content reads")
    scan.add_argument("--max-entries", type=int, default=20000)
    scan.add_argument("--max-depth", type=int, default=32)
    scan.add_argument("--max-directory-entries", type=int, default=5000)
    scan.add_argument("--max-seconds", type=float, default=30.0)
    scan.add_argument("--max-hash-file-bytes", type=int, default=16 * 1024 * 1024)
    scan.add_argument("--max-hash-total-bytes", type=int, default=64 * 1024 * 1024)
    scan.add_argument("--max-hash-files", type=int, default=1000)
    scan.add_argument("--exclude-name", action="append", default=[])
    scan.add_argument("--previous", help="Export used only for metadata deltas, never hash trust")
    scan.add_argument("--progress", action="store_true")
    query = sub.add_parser("query", help="Filter a saved JSON inventory without scanning")
    query.add_argument("inventory")
    query.add_argument("--root-id")
    query.add_argument("--kind")
    query.add_argument("--status")
    query.add_argument("--path-contains", default="")
    query.add_argument("--min-bytes", type=int, default=0)
    query.add_argument("--offset", type=int, default=0)
    query.add_argument("--limit", type=int, default=100)
    sub.add_parser("fixture", help="Emit synthetic viewer data without reading any disk tree")
    args = parser.parse_args(argv)
    cancelled = False

    def stop(_signal, _frame):
        nonlocal cancelled
        cancelled = True

    previous_handler = signal.getsignal(signal.SIGINT)
    try:
        if args.command == "fixture":
            from backend.disk_model_fixture import synthetic_model
            result = synthetic_model()
        elif args.command == "query":
            result = query_entries(load_export(args.inventory), root_id=args.root_id, kind=args.kind,
                                   status=args.status, path_contains=args.path_contains, min_bytes=args.min_bytes,
                                   offset=args.offset, limit=args.limit)
        else:
            signal.signal(signal.SIGINT, stop)
            limits = ScanLimits(max_entries=args.max_entries, max_depth=args.max_depth,
                                max_directory_entries=args.max_directory_entries, max_seconds=args.max_seconds,
                                hash_files=args.hash_files, max_hash_file_bytes=args.max_hash_file_bytes,
                                max_hash_total_bytes=args.max_hash_total_bytes, max_hash_files=args.max_hash_files,
                                exclude_names=tuple(args.exclude_name))
            result = scan_storage(args.roots, limits=limits,
                                  previous=load_export(args.previous) if args.previous else None,
                                  cancel=lambda: cancelled,
                                  progress=(lambda p: print(json.dumps(p), file=sys.stderr)) if args.progress else None)
        print(export_json(result), end="")
        return 2 if args.command == "scan" and result["scan"]["status"] != "complete" else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Disk Model input error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        signal.signal(signal.SIGINT, previous_handler)


if __name__ == "__main__":
    raise SystemExit(main())
