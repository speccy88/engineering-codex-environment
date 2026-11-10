"""Behavioral checks for editable Fritzing projects; no GUI or third-party Python."""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/fritzing-project.py"
DEMO = ROOT / "examples/fritzing/led-series.json"
sys.path.insert(0, str(ROOT / "scripts"))


class FritzingWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.design = json.loads(DEMO.read_text())

    def command(self, *args):
        return subprocess.run([sys.executable, str(CLI), *map(str, args)],
                              cwd=ROOT, text=True, capture_output=True, timeout=90)

    def generate(self, design=None, directory="output"):
        source = self.directory / (directory + ".json")
        source.write_text(json.dumps(self.design if design is None else design))
        destination = self.directory / directory
        return self.command("generate", source, "--output", destination), destination

    def rejected(self, design, pattern=None):
        result, destination = self.generate(design)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertFalse(list(destination.glob("*.fzz")), "Invalid design produced a project archive")
        if pattern:
            self.assertRegex(result.stdout + result.stderr, pattern)

    def valid_project(self):
        result, destination = self.generate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        archives = list(destination.glob("*.fzz"))
        self.assertEqual(len(archives), 1)
        return destination, archives[0]

    def rewrite_archive(self, archive, mutate):
        with zipfile.ZipFile(archive) as original:
            entries = {name: original.read(name) for name in original.namelist()}
        mutate(entries)
        target = self.directory / "modified.fzz"
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as output:
            for name, content in entries.items():
                output.writestr(name, content)
        return target

    def test_editable_archive_has_parts_assets_and_connected_views(self):
        destination, archive = self.valid_project()
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
            self.assertEqual(len([name for name in names if name.endswith(".fz")]), 1)
            self.assertGreaterEqual(len([name for name in names if name.endswith(".fzp")]), len(self.design["parts"]))
            self.assertGreaterEqual(len([name for name in names if name.endswith(".svg")]), 3 * len(self.design["parts"]))
            sketch = ET.fromstring(bundle.read(next(name for name in names if name.endswith(".fz"))))
        instances = sketch.findall("instances/instance")
        self.assertGreater(len(instances), len(self.design["parts"]))
        for view in ("schematicView", "pcbView"):
            self.assertTrue(sketch.findall(f".//{view}/connectors/connector/connects/connect"),
                            f"No editable connectivity in {view}")
        self.assertTrue(list((destination / "parts").glob("*.fzpz")))
        result = self.command("validate", archive)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_overlapping_component_bodies_are_rejected(self):
        first = self.design["parts"][0]
        self.design["parts"][1]["pcb"] = copy.deepcopy(first["pcb"])
        self.rejected(self.design)

    def test_component_outside_board_is_rejected(self):
        self.design["parts"][0]["pcb"]["x_mm"] = self.design["board"]["width_mm"] + 5
        self.rejected(self.design)

    def test_body_outside_board_is_rejected_even_when_pads_fit(self):
        part = self.design["parts"][0]
        part["body"]["width_mm"] = 80
        self.design["parts"] = [part]
        self.design["nets"] = [{"name": "SHORT", "pins": ["J1.1", "J1.2"]}]
        self.rejected(self.design)

    def test_duplicate_reference_is_rejected(self):
        self.design["parts"][1]["ref"] = self.design["parts"][0]["ref"]
        self.rejected(self.design)

    def test_duplicate_net_name_is_rejected(self):
        self.design["nets"][1]["name"] = self.design["nets"][0]["name"]
        self.rejected(self.design)

    def test_overlapping_holes_are_rejected_even_on_same_net(self):
        part = self.design["parts"][0]
        part["pins"][1]["x_mm"] = part["pins"][0]["x_mm"]
        part["pins"][1]["y_mm"] = part["pins"][0]["y_mm"] + .254
        self.design["parts"] = [part]
        self.design["nets"] = [{"name": "SAME_NET", "pins": ["J1.1", "J1.2"]}]
        self.rejected(self.design)

    def test_explicit_schematic_overlap_is_rejected(self):
        for part in self.design["parts"]:
            part["schematic"] = {"x_mm": 10.16, "y_mm": 10.16}
        self.rejected(self.design)

    def test_unsupported_fields_do_not_silently_disappear(self):
        self.design["board"]["layers"] = 4
        self.rejected(self.design)

    def test_explicit_unconnected_pin_is_preserved(self):
        part = copy.deepcopy(self.design["parts"][0])
        part["ref"] = "TP1"
        part["pins"] = [part["pins"][0]]
        part["pcb"] = {"x_mm": 5.08, "y_mm": 20.32}
        self.design["parts"].append(part)
        self.design["unconnected"] = ["TP1.1"]
        destination, archive = self.valid_project()
        result = self.command("validate", archive)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dip_eight_with_headers_preserves_multiterminal_nets(self):
        # Synthetic continuity fixture: each DIP pin bank shares a separate net.
        # This is not an application circuit or a suggested IC pin assignment.
        self.design["name"] = "dip-eight-connectivity"
        self.design["board"].update(width_mm=81.28, height_mm=60.96, grid_mm=.508)
        dip = {"ref": "U1", "kind": "dip", "value": "8-pin connectivity fixture",
               "body": {"width_mm": 12.7, "height_mm": 12.7},
               "pcb": {"x_mm": 30.48, "y_mm": 20.32}, "pins": []}
        for i in range(8):
            dip["pins"].append({"id": str(i + 1), "name": "P" + str(i + 1),
                                "x_mm": 2.54 if i < 4 else 10.16,
                                "y_mm": 2.54 * (i + 1) if i < 4 else 2.54 * (8 - i)})
        left = copy.deepcopy(self.design["parts"][0])
        left["pcb"] = {"x_mm": 5.08, "y_mm": 20.32}
        right = copy.deepcopy(left)
        right.update(ref="J2", pcb={"x_mm": 60.96, "y_mm": 20.32})
        self.design["parts"] = [dip, left, right]
        self.design["nets"] = [
            {"name": "LEFT", "pins": ["J1.1", "J1.2", "U1.1", "U1.2", "U1.3", "U1.4"]},
            {"name": "RIGHT", "pins": ["J2.1", "J2.2", "U1.5", "U1.6", "U1.7", "U1.8"]},
        ]
        destination, archive = self.valid_project()
        with zipfile.ZipFile(archive) as bundle:
            sketch = ET.fromstring(bundle.read("project.fz"))
        instances = sketch.findall("instances/instance")
        indices = {instance.findtext("title"): instance.get("modelIndex")
                   for instance in instances if instance.findtext("title") in ("U1", "J1", "J2")}
        for view in ("breadboardView", "schematicView", "pcbView"):
            adjacency = {}

            def link(a, b):
                adjacency.setdefault(a, set()).add(b)
                adjacency.setdefault(b, set()).add(a)

            for instance in instances:
                index = instance.get("modelIndex")
                saved_view = instance.find("views/" + view)
                if saved_view is None:
                    continue
                if instance.get("moduleIdRef") == "WireModuleID":
                    link((index, "connector0"), (index, "connector1"))
                for connector in saved_view.findall("connectors/connector"):
                    for connection in connector.findall("connects/connect"):
                        link((index, connector.get("connectorId")),
                             (connection.get("modelIndex"), connection.get("connectorId")))
            reached_groups = []
            for net in self.design["nets"]:
                terminals = []
                for name in net["pins"]:
                    ref, pin = name.split(".")
                    terminals.append((indices[ref], "connector" + str(int(pin) - 1)))
                reached, pending = set(), [terminals[0]]
                while pending:
                    item = pending.pop()
                    if item not in reached:
                        reached.add(item)
                        pending.extend(adjacency.get(item, ()))
                self.assertTrue(set(terminals) <= reached, f"{view}: disconnected {net['name']}")
                reached_groups.append(reached)
            self.assertFalse(reached_groups[0] & reached_groups[1], f"{view}: separate nets shorted")
        with zipfile.ZipFile(destination / "parts" / "U1.fzpz") as bundle:
            definition = next(name for name in bundle.namelist() if name.endswith(".fzp"))
            self.assertEqual(len(ET.fromstring(bundle.read(definition)).findall("connectors/connector")), 8)

    def test_pin_assigned_to_two_nets_is_rejected(self):
        self.design["nets"][1]["pins"].append(self.design["nets"][0]["pins"][0])
        self.rejected(self.design)

    def test_unassigned_pin_is_rejected(self):
        self.design["nets"][0]["pins"].pop()
        self.rejected(self.design)

    def test_unknown_pin_is_rejected(self):
        self.design["nets"][0]["pins"][0] = "DOES_NOT_EXIST.999"
        self.rejected(self.design)

    def test_nonfinite_geometry_is_rejected(self):
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value):
                design = copy.deepcopy(self.design)
                design["board"]["width_mm"] = value
                self.rejected(design)

    def test_nonpositive_manufacturing_rules_are_rejected(self):
        for field in ("grid_mm", "trace_width_mm"):
            with self.subTest(field=field):
                design = copy.deepcopy(self.design)
                design["board"][field] = 0
                self.rejected(design)

    def test_unsupported_schema_is_rejected(self):
        self.design["schema_version"] = 100
        self.rejected(self.design)

    def test_boolean_schema_version_is_rejected(self):
        self.design["schema_version"] = True
        self.rejected(self.design)

    def test_reference_cannot_escape_output_directory(self):
        self.design["parts"][0]["ref"] = "../../escaped"
        self.rejected(self.design)
        self.assertFalse((self.directory / "escaped.fzp").exists())

    def test_saved_project_missing_custom_svg_is_rejected(self):
        _, archive = self.valid_project()

        def remove_svg(entries):
            name = next(name for name in entries if name.endswith(".svg"))
            del entries[name]
            manifest = json.loads(entries["engineering-manifest.json"])
            del manifest["members_sha256"][name]
            entries["engineering-manifest.json"] = json.dumps(manifest).encode()

        modified = self.rewrite_archive(archive, remove_svg)
        result = self.command("validate", modified)
        self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_saved_project_changed_connectivity_is_rejected(self):
        _, archive = self.valid_project()

        def disconnect(entries):
            name = next(name for name in entries if name.endswith(".fz"))
            sketch = ET.fromstring(entries[name])
            connections = sketch.find(".//pcbView/connectors/connector/connects")
            self.assertIsNotNone(connections)
            connections.clear()
            entries[name] = ET.tostring(sketch)
            # A regenerated digest is insufficient: validate actual connectivity.
            manifest = json.loads(entries["engineering-manifest.json"])
            manifest["members_sha256"][name] = hashlib.sha256(entries[name]).hexdigest()
            entries["engineering-manifest.json"] = json.dumps(manifest).encode()

        modified = self.rewrite_archive(archive, disconnect)
        result = self.command("validate", modified)
        self.assertNotEqual(result.returncode, 0, result.stdout)


class RoutingGeometryTests(unittest.TestCase):
    """Independent physical failures and graph continuity, including T branches."""

    def setUp(self):
        from fritzing_workflow.routing import route_view, validate_geometry
        self.route = route_view
        self.validate = validate_geometry
        self.pins = {
            "J1.1": {"x": 2.0, "y": 5.0, "radius": 0.5, "net": "A"},
            "J2.1": {"x": 18.0, "y": 5.0, "radius": 0.5, "net": "A"},
            "J3.1": {"x": 10.0, "y": 2.0, "radius": 0.5, "net": "B"},
            "J4.1": {"x": 10.0, "y": 8.0, "radius": 0.5, "net": "B"},
        }
        self.rules = {"width": 20, "height": 10, "clearance": 0.2,
                      "trace_width": 0.25, "edge_clearance": 0.5}

    def test_crossing_different_nets_is_rejected(self):
        traces = [{"net": "A", "a": [2, 5], "b": [18, 5]},
                  {"net": "B", "a": [10, 2], "b": [10, 8]}]
        errors = self.validate(self.pins, traces, **self.rules)
        self.assertTrue(any("segments" in error and "clearance" in error for error in errors), errors)

    def test_trace_through_wrong_pad_is_rejected(self):
        self.pins["J3.1"]["y"] = 5
        errors = self.validate(self.pins, [{"net": "A", "a": [2, 5], "b": [18, 5]}], **self.rules)
        self.assertTrue(any("pad J3.1" in error and "clearance" in error for error in errors), errors)

    def test_pad_to_pad_clearance_is_enforced(self):
        self.pins["J3.1"]["x"] = 2.5
        self.pins["J3.1"]["y"] = 5
        errors = self.validate(self.pins, [], **self.rules)
        self.assertTrue(any("pads" in error and "clearance" in error for error in errors), errors)

    def test_copper_width_is_included_at_board_edge(self):
        pins = {"P1": {"x": 2, "y": 0.6, "radius": 0.01, "net": "A"},
                "P2": {"x": 18, "y": 0.6, "radius": 0.01, "net": "A"}}
        errors = self.validate(pins, [{"net": "A", "a": [2, .6], "b": [18, .6]}], **self.rules)
        self.assertTrue(any("segment" in error and "edge" in error for error in errors), errors)

    def test_multiterminal_net_routes_around_keepout(self):
        pins = {name: dict(pin, net="A") for name, pin in self.pins.items()}
        obstacle = [[8, 4, 12, 6]]
        result = self.route(pins, [{"name": "A", "pins": list(pins)}], grid=.5,
                            obstacles=obstacle, **self.rules)
        self.assertTrue(result["segments"])
        self.assertEqual(self.validate(pins, result["segments"], obstacles=obstacle, **self.rules), [])
        # Removing every segment at one terminal must be detected as an open net.
        traces = [segment for segment in result["segments"]
                  if [2, 5] not in (segment["a"], segment["b"])]
        errors = self.validate(pins, traces, obstacles=obstacle, **self.rules)
        self.assertTrue(any("unrouted" in error for error in errors), errors)

    def test_unroutable_keepout_barrier_fails(self):
        pins = {name: pin for name, pin in self.pins.items() if pin["net"] == "A"}
        with self.assertRaisesRegex(ValueError, "cannot be routed"):
            self.route(pins, [{"name": "A", "pins": list(pins)}], grid=.5,
                       obstacles=[[9, 0, 11, 10]], **self.rules)

    def test_grid_that_cannot_represent_pad_pitch_is_rejected(self):
        pins = {name: pin for name, pin in self.pins.items() if pin["net"] == "A"}
        pins["J1.1"]["x"] = 2.54
        with self.assertRaisesRegex(ValueError, "not on"):
            self.route(pins, [{"name": "A", "pins": list(pins)}], grid=.5, **self.rules)

    def test_long_schematic_label_cannot_extend_outside_layout_box(self):
        from fritzing_workflow.project import normalize, schematic
        design = json.loads(DEMO.read_text())
        design["parts"][1]["value"] = "W" * 40
        try:
            part = normalize(design)["parts"][1]
            svg, width, _height, _pins = schematic(part)
        except ValueError:
            # Rejecting text that cannot fit is preferable to a clipped drawing.
            return
        root = ET.fromstring(svg)
        label = next(node for node in root.iter() if node.tag.endswith("text") and node.text == "W" * 40)
        # DejaVu Sans W is approximately 0.989 em; 0.9 is a conservative lower
        # bound that catches gross clipping without a platform font dependency.
        label_width_lower_bound = len(label.text) * float(label.get("font-size")) * .9
        self.assertGreaterEqual(width, label_width_lower_bound,
                                "Accepted label is wider than its placement/SVG bounds")

    def test_long_generic_pin_labels_do_not_overlap_across_columns(self):
        from fritzing_workflow.project import schematic
        part = {"ref": "U1", "kind": "generic", "value": "8-pin interface",
                "pins": [{"name": "W" * 16} for _ in range(8)]}
        try:
            svg, _width, _height, _pins = schematic(part)
        except ValueError:
            return
        labels = [node for node in ET.fromstring(svg).iter()
                  if node.tag.endswith("text") and node.text == "W" * 16]
        for left in labels:
            if left.get("text-anchor") != "start":
                continue
            for right in labels:
                if right.get("text-anchor") != "end" or right.get("y") != left.get("y"):
                    continue
                left_end = float(left.get("x")) + 16 * float(left.get("font-size")) * .9
                right_start = float(right.get("x")) - 16 * float(right.get("font-size")) * .9
                self.assertLessEqual(left_end, right_start, "Opposite pin labels overlap inside symbol")


if __name__ == "__main__":
    unittest.main()
