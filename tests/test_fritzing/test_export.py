"""Export failure gates and enforced offline native execution; no CAD needed."""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("fritzing_export", ROOT / "scripts/fritzing-export.py")
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.parts = self.folder / "parts"
        self.parts.mkdir()
        with sqlite3.connect(self.parts / "parts.db") as database:
            database.execute("CREATE TABLE parts (moduleID TEXT)")
            database.execute("INSERT INTO parts VALUES ('WireModuleID')")
        self.env = patch.dict(os.environ, {"FRITZING_PARTS_DIR": str(self.parts)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def bundle(self, name="part.custom.fzp", include_svg=True, module="custom", svg=b'<svg xmlns="http://www.w3.org/2000/svg"/>'):
        path = self.folder / "project.fzz"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("project.fz", '<module><instances><instance moduleIdRef="' + module + '"/></instances></module>')
            archive.writestr(name, '<module moduleId="custom"><views><schematicView><layers image="schematic/custom.svg"/></schematicView></views></module>')
            if include_svg:
                archive.writestr("svg.schematic.custom.svg", svg)
        return path

    def test_unresolved_part_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unresolved parts"):
            exporter.inspect_project(self.bundle(module="missing"))

    def test_missing_svg_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing bundled SVG"):
            exporter.inspect_project(self.bundle(include_svg=False))

    def test_nested_archive_member_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsafe FZZ"):
            exporter.inspect_project(self.bundle(name="nested/part.custom.fzp"))

    def test_non_svg_image_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not SVG"):
            exporter.inspect_project(self.bundle(svg=b"<html/>"))

    def test_bundled_part_resolves(self):
        result = exporter.inspect_project(self.bundle())
        self.assertEqual(result["bundled_module_count"], 1)

    def test_library_part_missing_from_database_resolves(self):
        core = self.parts / "obsolete"
        core.mkdir()
        (core / "old.fzp").write_text('<module moduleId="old"/>')
        project = self.folder / "old.fz"
        project.write_text('<module><instances><instance moduleIdRef="old"/></instances></module>')
        self.assertEqual(exporter.inspect_project(project)["module_count"], 1)

    def test_empty_svg_is_rejected(self):
        path = self.folder / "empty.svg"
        path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>')
        with self.assertRaisesRegex(ValueError, "Empty SVG"):
            exporter.validate_svg(path)

    def test_stale_output_is_refused_without_mutation(self):
        project = self.bundle()
        output = self.folder / "exports"
        output.mkdir()
        marker = output / "existing.txt"
        marker.write_text("keep")
        result = subprocess.run([sys.executable, str(ROOT / "scripts/fritzing-export.py"), str(project), "--output", str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("stale exports", result.stderr)
        self.assertEqual(marker.read_text(), "keep")
        self.assertEqual(list(output.iterdir()), [marker])

    def test_timeout_is_a_recorded_failure(self):
        evidence = []
        with self.assertRaisesRegex(RuntimeError, "124"):
            exporter.run_logged([sys.executable, "-c", "import time; time.sleep(30)"], self.folder, "timeout", 0.05, evidence)
        self.assertTrue(evidence[0]["timed_out"])
        self.assertEqual(evidence[0]["exit_code"], 124)

    def test_ipc_nets_use_fixed_columns_and_ignore_duplicate_other_side(self):
        path = self.folder / "project.ipc"
        path.write_text("P  VER   IPC-D-356A\n"
                        "317NET1R1D1         R1    -   1 D0900PA01X+030480Y+017780X1800Y0000R000 S0\n"
                        "017NET1R1D1         R1    -   1 D0900PA16X+030480Y+017780X1800Y0000R000 S0\n"
                        "317NET1R1D1         D1    -   0 D0900PA01X+045720Y+017780X1800Y0000R000 S0\n999\n")
        self.assertEqual(exporter.read_ipc_nets(path), {"NET1R1D1": ["D1.0", "R1.1"]})

    def test_ipc_header_only_is_rejected(self):
        path = self.folder / "empty.ipc"
        path.write_text("P  VER   IPC-D-356A\n999\n")
        with self.assertRaisesRegex(ValueError, "no electrical test records"):
            exporter.read_ipc_nets(path)

    def test_plain_fz_is_archived_without_overwriting_original(self):
        source = self.folder / "source.fz"
        source.write_text('<module><instances><instance moduleIdRef="WireModuleID"/></instances></module>')
        output = self.folder / "export"
        output.mkdir()
        staged = exporter.stage_project(source, output)
        self.assertEqual(staged.name, "source.fzz")
        with zipfile.ZipFile(staged) as archive:
            self.assertEqual(archive.read("source.fz"), source.read_bytes())
        self.assertEqual((output / "source/source.fz").read_bytes(), source.read_bytes())
        self.assertFalse((output / "source.fz").exists())


class OfflineTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux seccomp is required")
    def test_network_denied_but_unix_ipc_allowed(self):
        command = [sys.executable, str(ROOT / "scripts/fritzing-offline.py"), sys.executable, "-c", """
import socket, errno
for family in (socket.AF_INET, socket.AF_INET6):
    try:
        socket.socket(family, socket.SOCK_STREAM)
    except PermissionError as error:
        assert error.errno == errno.EPERM
    else:
        raise AssertionError('Network socket was permitted')
a, b = socket.socketpair()
a.send(b'x')
assert b.recv(1) == b'x'
a.close()
b.close()
"""]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
