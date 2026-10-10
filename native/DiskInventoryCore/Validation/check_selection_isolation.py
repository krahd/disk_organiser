"""Check the actual SwiftPM dependency graph; never present a panel or sign code."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def validate_graph(graph):
    targets = graph.get("targets")
    products = graph.get("products")
    if not isinstance(targets, list) or not isinstance(products, list):
        raise ValueError("Missing resolved package graph")
    mapped = {t["name"]: t for t in targets}
    if len(mapped) != len(targets):
        raise ValueError("Duplicate target identity")
    selection = "DiskInventorySelection"
    tests = "DiskInventorySelectionTests"
    if selection not in mapped or tests not in mapped:
        raise ValueError("Missing isolated selection target/tests")
    if mapped[selection].get("target_dependencies", []):
        raise ValueError("Selection must not depend on an observer or application")
    if mapped[tests].get("target_dependencies") != [selection]:
        raise ValueError("Selection tests must have only their isolated target")

    def closure(names):
        visited = set()
        pending = list(names)
        while pending:
            name = pending.pop()
            if name in visited:
                continue
            if name not in mapped:
                raise ValueError("Unresolved target edge")
            visited.add(name)
            edges = mapped[name].get("target_dependencies", [])
            if not isinstance(edges, list) or not all(isinstance(e, str) for e in edges):
                raise ValueError("Invalid dependency edge")
            pending.extend(edges)
        return visited

    product_names = [p.get("name") for p in products]
    if product_names != ["DiskOrganiserPreview"]:
        raise ValueError("Unexpected ordinary product or exposed selection product")
    for product in products:
        reachable = closure(product["targets"])
        if selection in reachable or tests in reachable or "DiskInventoryCore" in reachable:
            raise ValueError("Ordinary product acquired selection or observer access")
    return {"selection_module": "isolated", "ordinary_product": "unchanged", "scope": "dependency graph only"}


if __name__ == "__main__":
    graph = json.loads(subprocess.check_output([
        "xcrun", "swift", "package", "--package-path", str(ROOT), "describe", "--type", "json"
    ], text=True))
    print(json.dumps(validate_graph(graph), sort_keys=True))
