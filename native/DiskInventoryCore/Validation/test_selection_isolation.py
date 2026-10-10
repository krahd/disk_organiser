"""Pure graph-oracle tests; no Swift execution or filesystem/source access."""
import copy
import unittest
from check_selection_isolation import validate_graph


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.graph = {"products": [{"name": "DiskOrganiserPreview", "targets": ["App"]}], "targets": [
            {"name": "App", "target_dependencies": ["Desktop"]}, {"name": "Desktop"},
            {"name": "DiskInventoryCore"}, {"name": "DiskInventorySelection"},
            {"name": "DiskInventorySelectionTests", "target_dependencies": ["DiskInventorySelection"]}
        ]}

    def test_isolated_graph_is_admitted(self):
        self.assertEqual(validate_graph(self.graph)["scope"], "dependency graph only")

    def test_transitive_selection_or_observer_product_edge_refuses(self):
        for name in ["DiskInventorySelection", "DiskInventoryCore", "DiskInventorySelectionTests"]:
            value = copy.deepcopy(self.graph)
            value["targets"][1]["target_dependencies"] = [name]
            with self.assertRaises(ValueError):
                validate_graph(value)

    def test_new_product_refuses(self):
        self.graph["products"].append({"name": "Picker", "targets": ["DiskInventorySelection"]})
        with self.assertRaises(ValueError):
            validate_graph(self.graph)

    def test_selection_or_test_dependency_expansion_refuses(self):
        for index in [3, 4]:
            value = copy.deepcopy(self.graph)
            value["targets"][index]["target_dependencies"] = ["Desktop"]
            with self.assertRaises(ValueError):
                validate_graph(value)

    def test_duplicate_or_unresolved_target_refuses(self):
        value = copy.deepcopy(self.graph)
        value["targets"].append({"name": "App"})
        with self.assertRaises(ValueError):
            validate_graph(value)
        self.graph["targets"][0]["target_dependencies"] = ["missing"]
        with self.assertRaises(ValueError):
            validate_graph(self.graph)


if __name__ == "__main__":
    unittest.main()
