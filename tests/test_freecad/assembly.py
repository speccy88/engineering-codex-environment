"""Assemble a real KiCad STEP PCB with a parametric enclosure in native FreeCAD.

scripts/run-freecad.sh tests/test_freecad/assembly.py artifacts/eda/divider.step
"""

import importlib
import json
import os
import sys
from pathlib import Path

import FreeCAD as App
import Mesh
import Part

importlib.import_module("AssemblyApp")  # Must follow FreeCAD initialization.

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get("WB_ARTIFACTS", str(ROOT / "artifacts"))) / "assembly"
OUT.mkdir(parents=True, exist_ok=True)
pcb_path = Path(sys.argv[1]).resolve()
assert pcb_path.is_file(), "Supply the actual KiCad-exported populated PCB STEP"
shape = Part.Shape()
shape.read(str(pcb_path))
assert shape.isValid() and len(shape.Solids) >= 3
assert all(s.isValid() and s.Volume > 0 for s in shape.Solids)
bounds = shape.BoundBox
assert abs(bounds.XLength - 40) < 0.01 and abs(bounds.YLength - 25) < 0.01

doc = App.newDocument("PCBEnclosure")
assembly = doc.addObject("Assembly::AssemblyObject", "Assembly")
assembly.newObject("Assembly::JointGroup", "Joints")
shell = doc.addObject("PartDesign::Body", "Enclosure")
outer = shell.newObject("PartDesign::AdditiveBox", "Outer")
outer.Length, outer.Width, outer.Height = 50, 35, 18
inner = shell.newObject("PartDesign::SubtractiveBox", "Cavity")
inner.Length, inner.Width, inner.Height = 46, 31, 18
inner.Placement.Base = App.Vector(2, 2, 2)
doc.recompute()
board = doc.addObject("PartDesign::Feature", "PopulatedPCB")
board.Label = "Real KiCad resistor divider, exported STEP"
board.Shape = shape
board.Placement.Base = App.Vector(5 - bounds.XMin, 5 - bounds.YMin, 3.5 - bounds.ZMin)
board.addProperty("App::PropertyString", "SourceInterface")
board.SourceInterface = (
    str(pcb_path.relative_to(ROOT)) if pcb_path.is_relative_to(ROOT) else pcb_path.name
)
for source in [shell, board]:
    link = assembly.newObject("App::Link", source.Name + "Instance")
    link.setLink(source)
doc.recompute()
assert shell.Shape.isValid() and len(shell.Shape.Solids) == 1
assert abs(shell.Shape.Volume - (50 * 35 * 18 - 46 * 31 * 16)) < 1e-6
intersection = shell.Shape.common(board.Shape).Volume
assert intersection < 1e-6, f"Interference: {intersection} mm^3"
assert board.Shape.BoundBox.ZMax < 18
doc.saveAs(str(OUT / "pcb-enclosure.FCStd"))
Part.export([shell, board], str(OUT / "pcb-enclosure.step"))
Mesh.export([shell, board], str(OUT / "pcb-enclosure.stl"))
# Preserve individual editable/native input files alongside compound neutral exports.
Part.export([shell], str(OUT / "enclosure.step"))
Mesh.export([shell], str(OUT / "enclosure.stl"))
roundtrip = Part.Shape()
roundtrip.read(str(OUT / "pcb-enclosure.step"))
assert roundtrip.isValid() and len(roundtrip.Solids) == len(shape.Solids) + 1
name = doc.Name
App.closeDocument(name)
doc = App.openDocument(str(OUT / "pcb-enclosure.FCStd"))
assert doc.Assembly.TypeId == "Assembly::AssemblyObject"
assert len(doc.PopulatedPCB.Shape.Solids) == len(shape.Solids)
result = {
    "status": "passed",
    "source_pcb": str(pcb_path),
    "source_pcb_solid_count": len(shape.Solids),
    "source_pcb_bounds_mm": [bounds.XLength, bounds.YLength, bounds.ZLength],
    "enclosure_outer_mm": [50, 35, 18],
    "assembly_solid_count": len(roundtrip.Solids),
    "interference_volume_mm3": intersection,
    "assembly_type": "Native Assembly::AssemblyObject with two linked static components",
    "limitations": "Static placement; assembly joint solver not exercised; enclosure has no connector openings or mounting supports",
    "files": [str(p.relative_to(ROOT)) for p in sorted(OUT.iterdir()) if p.is_file()],
}
(OUT / "results.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
