"""Independent build123d solid construction and neutral-format roundtrip."""

import json
import math
from pathlib import Path

from build123d import (
    Align,
    Box,
    BuildPart,
    Cylinder,
    Locations,
    Mode,
    export_step,
    export_stl,
    import_step,
)


def main(out=Path("artifacts/python/build123d")):
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").unlink(missing_ok=True)
    width, depth, thick, height, hole = 40.0, 25.0, 3.0, 25.0, 4.0
    with BuildPart() as bracket:
        Box(width, depth, thick, align=(Align.MIN, Align.MIN, Align.MIN))
        Box(width, thick, height, align=(Align.MIN, Align.MIN, Align.MIN))
        with Locations((10, 15, 0), (30, 15, 0)):
            Cylinder(
                hole / 2,
                thick,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )
    solid = bracket.part
    expected = (
        width * depth * thick
        + width * thick * (height - thick)
        - 2 * math.pi * (hole / 2) ** 2 * thick
    )
    assert solid.is_valid and len(solid.solids()) == 1
    assert abs(solid.volume - expected) < 1e-6
    export_step(solid, out / "bracket.step")
    export_stl(solid, out / "bracket.stl", tolerance=0.03, angular_tolerance=0.1)
    reopened = import_step(out / "bracket.step")
    assert reopened.is_valid and len(reopened.solids()) == 1
    assert abs(reopened.volume - expected) < 1e-5
    import trimesh

    mesh = trimesh.load_mesh(out / "bracket.stl")
    assert mesh.is_watertight and mesh.volume > 0
    assert abs(mesh.volume - expected) / expected < 0.01
    result = {
        "status": "passed",
        "volume_mm3": solid.volume,
        "reimport_volume_mm3": reopened.volume,
        "mesh_watertight": bool(mesh.is_watertight),
        "mesh_volume_mm3": float(mesh.volume),
        "native_parametric_source": "tests/test_build123d/acceptance.py",
        "outputs": [str(out / "bracket.step"), str(out / "bracket.stl")],
    }
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    import sys

    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts/python/build123d"))
