"""Exercise actual Fritzing loading, three-view rendering and fabrication export."""

import datetime
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "artifacts/fritzing-acceptance" / stamp
    out.mkdir(parents=True)
    commands = []

    def run(name, args):
        command = [str(arg) for arg in args]
        log = out / (name + ".log")
        with log.open("w") as stream:
            process = subprocess.run(command, cwd=ROOT, stdout=stream,
                                     stderr=subprocess.STDOUT, timeout=300)
        commands.append({"name": name, "command": command,
                         "exit_code": process.returncode, "log": str(log)})
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if process.returncode:
            raise AssertionError(f"{name} failed: {log.read_text()}")
        return log.read_text()

    source = ROOT / "examples/fritzing/led-series.json"
    project = out / "project"
    exports = out / "exports"
    result = {"status": "failed", "native_drc": "not_run", "commands": commands}
    try:
        run("generate", [sys.executable, ROOT / "scripts/fritzing-project.py", "generate", source, "--output", project])
        archive = project / "project.fzz"
        run("validate", [sys.executable, ROOT / "scripts/fritzing-project.py", "validate", archive])
        with zipfile.ZipFile(archive) as bundle:
            sketch = ET.fromstring(bundle.read("project.fz"))
        pcb_wires = [node for node in sketch.findall("instances/instance")
                     if node.get("moduleIdRef") == "WireModuleID"
                     and node.find("views/pcbView/geometry") is not None
                     and int(node.find("views/pcbView/geometry").get("wireFlags", "0")) & 4]
        assert pcb_wires, "Generated PCB has no native copper trace objects"
        run("native-export", [sys.executable, ROOT / "scripts/fritzing-export.py", archive, "--output", exports, "--png"])
        evidence = json.loads((exports / "export-report.json").read_text())
        assert evidence["status"] == "passed", evidence
        assert evidence["project"]["bundled_module_count"] >= 3
        magick = shutil.which("magick")
        assert magick, "ImageMagick required for pixel checks"
        pixel_checks = {}
        for view in ("breadboard", "schematic", "pcb"):
            png = exports / f"project_{view}.png"
            measurement = run("pixels-" + view, [magick, "identify", "-format", "%w %h %[fx:standard_deviation]", png])
            width, height, deviation = map(float, measurement.split())
            assert width >= 30 and height >= 30 and deviation > .01, (view, measurement)
            pixel_checks[view] = {"width": width, "height": height, "standard_deviation": deviation}
        copper = (exports / "project_copperBottom.gbl").read_text()
        assert re.search(r"D0?1\*", copper), "Copper export has no drawing operations"
        drill = (exports / "project_drill.txt").read_text()
        holes = re.findall(r"^X[-+\d.]+Y[-+\d.]+", drill, flags=re.M)
        expected_holes = sum(len(part["pins"]) for part in json.loads(source.read_text())["parts"])
        assert len(holes) == expected_holes, (len(holes), expected_holes, drill)
        contour = (exports / "project_contour.gm1").read_text()
        assert len(re.findall(r"D0?1\*", contour)) >= 4, "Board contour missing"
        # Measure native fabrication coordinates, independently of generator reports.
        assert "%FSLAX23Y23*%" in contour and "%MOIN*%" in contour
        outline = [(int(x) * .0254, int(y) * .0254)
                   for x, y in re.findall(r"X(-?\d+)Y(-?\d+)D0?[12]\*", contour)]
        xmin, xmax = min(p[0] for p in outline), max(p[0] for p in outline)
        ymin, ymax = min(p[1] for p in outline), max(p[1] for p in outline)
        design = json.loads(source.read_text())
        assert abs(xmax - xmin - design["board"]["width_mm"]) < .03
        assert abs(ymax - ymin - design["board"]["height_mm"]) < .03
        assert "INCH" in drill
        actual_pads = [(int(x) * .00254 - xmin, ymax - int(y) * .00254)
                       for x, y in re.findall(r"^X(-?\d+)Y(-?\d+)$", drill, flags=re.M)]
        expected_pads = [(part["pcb"]["x_mm"] + pin["x_mm"], part["pcb"]["y_mm"] + pin["y_mm"])
                         for part in design["parts"] for pin in part["pins"]]
        for expected in expected_pads:
            assert min(math.dist(expected, actual) for actual in actual_pads) < .03, (expected, actual_pads)
        ipc = (exports / "project.ipc").read_text()
        parts = {part["ref"]: part for part in design["parts"]}
        native_nets = {}
        for net, ref, connector in re.findall(r"^317(\S+)\s+(\S+)\s*-\s*(\d+)\s+D", ipc, flags=re.M):
            pin = parts[ref]["pins"][int(connector)]["id"]
            native_nets.setdefault(net, set()).add(ref + "." + pin)
        assert {frozenset(pins) for pins in native_nets.values()} == {
            frozenset(net["pins"]) for net in design["nets"]}, native_nets
        result.update(status="passed", native_version=evidence["version"],
                      trace_objects=len(pcb_wires), drilled_holes=len(holes),
                      contour_width_mm=xmax-xmin, contour_height_mm=ymax-ymin,
                      native_hole_positions_match=True,
                      native_ipc_nets_match=True, native_ipc_net_count=len(native_nets),
                      pixel_checks=pixel_checks, project=str(archive), exports=str(exports))
    except (AssertionError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        result["error"] = str(error)
        raise
    finally:
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        (out.parent / "latest.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"status": result["status"], "evidence": str(out)}, indent=2))


if __name__ == "__main__":
    main()
