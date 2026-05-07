"""Validate that Flask routes declared in backend/app.py exist in docs/openapi.json."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROUTE_RE = re.compile(r'@app\.route\("([^"]+)"')


def normalize_path(path: str) -> str:
    return re.sub(r"<([^>]+)>", r"{\1}", path)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    app_py = repo_root / "backend" / "app.py"
    spec_path = repo_root / "docs" / "openapi.json"

    app_routes = {normalize_path(match.group(1)) for match in ROUTE_RE.finditer(app_py.read_text(encoding="utf-8"))}
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec_routes = set(spec.get("paths", {}).keys())

    missing = sorted(app_routes - spec_routes)
    if missing:
      print("OpenAPI spec is missing routes:")
      for route in missing:
          print(f" - {route}")
      return 1

    print(f"OpenAPI validation passed for {len(app_routes)} routes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())