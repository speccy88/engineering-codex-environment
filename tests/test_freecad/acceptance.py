"""Real modeling, persistence, mutation, drawing, and assembly acceptance.

Run with scripts/run-freecad.sh --gui tests/test_freecad/acceptance.py.
Outputs are disposable examples, never a project's source of truth.
"""

import json
import math
import os
import subprocess
from pathlib import Path

import FreeCAD as App
import Mesh
import Part
import Sketcher
import TechDraw  # noqa: F401 - registers native TechDraw object types.
import TechDrawGui
from PySide2 import QtCore

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get("WB_ARTIFACTS", str(ROOT / "artifacts"))) / "freecad"
OUT.mkdir(parents=True, exist_ok=True)


def rectangle(sketch, width, height):
    """Fully constrained rectangle; Width and Depth are editable dimensions."""
    points = [(0, 0), (width, 0), (width, height), (0, height)]
    for index in range(4):
        a, b = points[index], points[(index + 1) % 4]
        sketch.addGeometry(
            Part.LineSegment(App.Vector(*a, 0), App.Vector(*b, 0)), False
        )
    for index in range(4):
        sketch.addConstraint(
            Sketcher.Constraint("Coincident", index, 2, (index + 1) % 4, 1)
        )
        sketch.addConstraint(
            Sketcher.Constraint("Horizontal" if index % 2 == 0 else "Vertical", index)
        )
    sketch.addConstraint(Sketcher.Constraint("Coincident", 0, 1, -1, 1))
    first = sketch.addConstraint(Sketcher.Constraint("Distance", 0, width))
    second = sketch.addConstraint(Sketcher.Constraint("Distance", 1, height))
    sketch.renameConstraint(first, "Width")
    sketch.renameConstraint(second, "Depth")
    assert sketch.FullyConstrained


def solid_check(shape, expected_volume=None):
    assert not shape.isNull() and shape.isValid() and len(shape.Solids) == 1
    assert shape.Volume > 1
    if expected_volume is not None:
        assert abs(shape.Volume - expected_volume) < 1e-5, (
            shape.Volume,
            expected_volume,
        )


def export_body(body, prefix):
    Part.export([body], str(OUT / f"{prefix}.step"))
    Mesh.export([body], str(OUT / f"{prefix}.stl"))
    imported = Part.Shape()
    imported.read(str(OUT / f"{prefix}.step"))
    solid_check(imported, body.Shape.Volume)
    mesh = Mesh.Mesh(str(OUT / f"{prefix}.stl"))
    assert mesh.CountFacets > 20 and mesh.isSolid()


def settle():
    # TechDraw's projection worker and Qt scene need their event loop.
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(1500, loop.quit)
    loop.exec_()


doc = App.newDocument("ParametricBracket")
print("STAGE: create model", flush=True)
body = doc.addObject("PartDesign::Body", "Bracket")
base = doc.addObject("Sketcher::SketchObject", "BaseSketch")
body.addObject(base)
rectangle(base, 60, 40)
pad = body.newObject("PartDesign::Pad", "BasePad")
pad.Profile, pad.Length = base, 3
base.Visibility = False
doc.recompute()
solid_check(pad.Shape, 60 * 40 * 3)

flange = body.newObject("Sketcher::SketchObject", "FlangeSketch")
flange.Placement = App.Placement(
    App.Vector(0, 3, 0), App.Rotation(App.Vector(1, 0, 0), 90)
)
rectangle(flange, 60, 25)
flange.setExpression("Constraints.Width", "BaseSketch.Constraints.Width")
upright = body.newObject("PartDesign::Pad", "FlangePad")
upright.Profile, upright.Length = flange, 3
doc.recompute()
flange.Visibility = pad.Visibility = False

holes = body.newObject("Sketcher::SketchObject", "MountingHoles")
holes.Placement.Base.z = 3
for index, x in enumerate([10, 50]):
    holes.addGeometry(Part.Circle(App.Vector(x, 15, 0), App.Vector(0, 0, 1), 3), False)
    holes.addConstraint(Sketcher.Constraint("Radius", index, 3))
    cx = holes.addConstraint(Sketcher.Constraint("DistanceX", index, 3, x))
    holes.addConstraint(Sketcher.Constraint("DistanceY", index, 3, 15))
    if index == 1:
        holes.renameConstraint(cx, "RightHoleX")
        holes.setExpression(
            "Constraints.RightHoleX", "BaseSketch.Constraints.Width - 10 mm"
        )
assert holes.FullyConstrained
pocket = body.newObject("PartDesign::Pocket", "ThroughHoles")
pocket.Profile, pocket.Length = holes, 3
doc.recompute()
holes.Visibility = upright.Visibility = False
expected = 60 * 40 * 3 + 60 * 3 * (25 - 3) - 2 * math.pi * 3**2 * 3
solid_check(body.Shape, expected)
doc.recompute()
doc.saveAs(str(OUT / "bracket.FCStd"))
print("STAGE: saved original", flush=True)
export_body(body, "bracket")
original_volume = body.Shape.Volume
App.closeDocument(doc.Name)

doc = App.openDocument(str(OUT / "bracket.FCStd"))
print("STAGE: reopened", flush=True)
body = doc.Bracket
solid_check(body.Shape, expected)
doc.BaseSketch.setDatum("Width", App.Units.Quantity("70 mm"))
doc.recompute()
expected = 70 * 40 * 3 + 70 * 3 * (25 - 3) - 2 * math.pi * 3**2 * 3
solid_check(body.Shape, expected)
assert abs(body.Shape.BoundBox.XLength - 70) < 1e-8
assert body.Shape.Volume > original_volume
export_body(body, "bracket-wider")
print("STAGE: mutated and exported", flush=True)

page = doc.addObject("TechDraw::DrawPage", "DimensionedDrawing")
template = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
template.Template = "/usr/share/freecad/Mod/TechDraw/Templates/A4_Landscape_TD.svg"
editable = template.EditableTexts
for key, value in {
    "FC-TITLE": "Parametric mounting bracket",
    "FC-SUBT": "70 x 40 x 25 mm; thickness 3 mm",
    "FC-SC": "1.5:1",
    "FC-DN": "WB-BRACKET-001",
    "FC-SH": "1 / 1",
}.items():
    if key in editable:
        editable[key] = value
template.EditableTexts = editable
page.Template = template
print("STAGE: template set", flush=True)
view = doc.addObject("TechDraw::DrawViewPart", "TopView")
view.Source, view.Direction = [body], App.Vector(0, 0, 1)
page.addView(view)
side = doc.addObject("TechDraw::DrawViewPart", "FrontView")
side.Source, side.Direction = [body], App.Vector(0, -1, 0)
page.addView(side)
doc.recompute()
settle()
print("STAGE: view projections", flush=True)
view.ScaleType = "Custom"
side.ScaleType = "Custom"
view.X, view.Y, view.Scale = 90, 120, 1.5
side.X, side.Y, side.Scale = 210, 120, 1.5
doc.recompute()
settle()

# Select real projected geometry by measured length instead of guessing Edge IDs.
edge_records = []
for index in range(1, 100):
    try:
        edge = view.getEdgeByIndex(index)
        if edge is None or edge.isNull():
            break
        edge_records.append((index, edge.Length))
    except (RuntimeError, ValueError, IndexError):
        break
assert edge_records, "No TechDraw projected edges"
print("TechDraw projected edges:", edge_records, flush=True)
for label, length, x, y in [
    ("OverallWidth", 70, 0, 45),
    ("ExposedBaseDepth", 37, -65, 0),
]:
    found = next(index for index, actual in edge_records if abs(actual - length) < 1e-6)
    dim = doc.addObject("TechDraw::DrawViewDimension", label)
    dim.Type = "Distance"
    dim.References2D = [(view, f"Edge{found}")]
    dim.FormatSpec = "%.1f mm"
    page.addView(dim)
    dim.X, dim.Y = x, y
    dim.ViewObject.Font = "DejaVu Sans"
    dim.ViewObject.Fontsize = 3.5
doc.recompute()
settle()
for dimension in [doc.OverallWidth, doc.ExposedBaseDepth]:
    assert "Invalid" not in dimension.State, dimension.State
TechDrawGui.exportPageAsPdf(page, str(OUT / "bracket-drawing.pdf"))
TechDrawGui.exportPageAsSvg(page, str(OUT / "bracket-drawing.svg"))
doc.saveAs(str(OUT / "bracket-wider.FCStd"))
assert (OUT / "bracket-drawing.pdf").read_bytes().startswith(b"%PDF")
svg_text = (OUT / "bracket-drawing.svg").read_text()
assert "70.0" in svg_text and "37.0" in svg_text, "Drawing lacks numeric dimensions"
pdf_text = subprocess.run(
    ["pdftotext", str(OUT / "bracket-drawing.pdf"), "-"],
    capture_output=True,
    text=True,
    check=True,
).stdout
assert "70.0 mm" in pdf_text and "37.0 mm" in pdf_text

result = {
    "status": "passed",
    "freecad_version": App.Version(),
    "python": __import__("sys").version,
    "original_volume_mm3": original_volume,
    "modified_volume_mm3": body.Shape.Volume,
    "modified_width_mm": body.Shape.BoundBox.XLength,
    "fully_constrained_sketches": [
        s.Name
        for s in [doc.BaseSketch, doc.FlangeSketch, doc.MountingHoles]
        if s.FullyConstrained
    ],
    "drawing_dimensions_mm": [70, 37],
    "pdf_dimension_text_verified": True,
    "files": [str(p.relative_to(ROOT)) for p in sorted(OUT.glob("*")) if p.is_file()],
}
(OUT / "results.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
