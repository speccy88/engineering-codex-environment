#!/usr/bin/env python3
"""Check the actual assembled PCB STEP with independent OCCT Python bindings.

Run with scripts/run-python.sh (engineering venv), separately from pcbnew.
"""

import argparse
import json
from pathlib import Path

from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer

ROOT = Path(__file__).resolve().parents[2]


def check(output):
    reader = STEPControl_Reader()
    assert reader.ReadFile(str(output / "divider.step")) == IFSelect_RetDone
    assert reader.TransferRoots() > 0
    shape = reader.OneShape()
    assert not shape.IsNull() and BRepCheck_Analyzer(shape).IsValid()
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    count = 0
    while explorer.More():
        assert BRepCheck_Analyzer(explorer.Current()).IsValid()
        count += 1
        explorer.Next()
    # More than a board slab: this fixture must include physical component bodies.
    assert count >= 4, count
    bbox = Bnd_Box()
    BRepBndLib.Add_s(shape, bbox)
    bounds = bbox.Get()
    extents = [bounds[i + 3] - bounds[i] for i in range(3)]
    assert abs(extents[0] - 40) < 0.01 and abs(extents[1] - 25) < 0.01, extents
    assert extents[2] > 5, "Missing assembled pin-header geometry"
    result = {
        "status": "passed",
        "valid_solids": count,
        "bounds_mm": bounds,
        "extents_mm": extents,
    }
    (output / "pcb-step-result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output", nargs="?", type=Path, default=ROOT / "artifacts" / "eda"
    )
    print(json.dumps(check(parser.parse_args().output), indent=2))
