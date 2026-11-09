"""Create, export and reimport a parametric CadQuery bracket independently."""

import json
import math
from pathlib import Path

import cadquery as cq


def main(out=Path("artifacts/python/cadquery")):
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").unlink(missing_ok=True)
    width, depth, thick, height, hole = 40.0, 25.0, 3.0, 25.0, 4.0
    base = cq.Workplane("XY").box(width, depth, thick, centered=(False, False, False))
    upright = cq.Workplane("XY").box(
        width, thick, height, centered=(False, False, False)
    )
    bracket = base.union(upright)
    for x in (10.0, 30.0):
        drill = cq.Workplane("XY").center(x, 15).circle(hole / 2).extrude(thick)
        bracket = bracket.cut(drill)
    solid = bracket.val()
    expected = (
        width * depth * thick
        + width * thick * (height - thick)
        - 2 * math.pi * (hole / 2) ** 2 * thick
    )
    assert solid.isValid() and len(solid.Solids()) == 1
    assert abs(solid.Volume() - expected) < 1e-6
    cq.exporters.export(bracket, str(out / "bracket.step"))
    cq.exporters.export(
        bracket, str(out / "bracket.stl"), tolerance=0.03, angularTolerance=0.1
    )
    reopened = cq.importers.importStep(str(out / "bracket.step")).val()
    assert reopened.isValid() and len(reopened.Solids()) == 1
    assert abs(reopened.Volume() - expected) < 1e-5
    import trimesh

    mesh = trimesh.load_mesh(out / "bracket.stl")
    assert mesh.is_watertight and mesh.volume > 0
    assert abs(mesh.volume - expected) / expected < 0.01
    result = {
        "status": "passed",
        "volume_mm3": solid.Volume(),
        "reimport_volume_mm3": reopened.Volume(),
        "mesh_watertight": bool(mesh.is_watertight),
        "mesh_volume_mm3": float(mesh.volume),
        "native_parametric_source": "tests/test_cadquery/acceptance.py",
        "outputs": [str(out / "bracket.step"), str(out / "bracket.stl")],
    }
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    import sys

    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts/python/cadquery"))
