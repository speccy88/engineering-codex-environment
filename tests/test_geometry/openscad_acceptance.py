"""Real OpenSCAD CGAL export and independent mesh volume/topology validation."""

import json
import math
import subprocess
from pathlib import Path

import trimesh


def main(out=Path("artifacts/python/openscad")):
    repo = Path(__file__).resolve().parents[2]
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").unlink(missing_ok=True)
    command = [
        str(repo / "scripts/run-openscad.sh"),
        "-o",
        str(out / "plate.stl"),
        str(repo / "tests/test_geometry/openscad.scad"),
    ]
    result = subprocess.run(
        command, check=False, text=True, capture_output=True, timeout=180
    )
    (out / "openscad.log").write_text(result.stdout + result.stderr)
    (out / "command.json").write_text(
        json.dumps({"command": command, "exit_code": result.returncode}, indent=2)
        + "\n"
    )
    assert result.returncode == 0, result.stderr
    mesh = trimesh.load_mesh(out / "plate.stl")
    expected = 40 * 25 * 3 - 2 * math.pi * 2**2 * 3
    assert mesh.is_watertight and mesh.volume > 0
    assert abs(mesh.volume - expected) / expected < 0.001
    assert len(mesh.split()) == 1
    evidence = {
        "status": "passed",
        "volume_mm3": float(mesh.volume),
        "expected_volume_mm3": expected,
        "watertight": bool(mesh.is_watertight),
        "components": 1,
        "editable_source": "tests/test_geometry/openscad.scad",
        "stl": str(out / "plate.stl"),
    }
    (out / "result.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence))


if __name__ == "__main__":
    main()
