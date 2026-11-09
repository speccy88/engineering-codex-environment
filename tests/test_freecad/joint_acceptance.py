"""Native FreeCAD grounded/fixed joint solve, perturbation and persistence test.

Run: scripts/run-freecad.sh tests/test_freecad/joint_acceptance.py
The two valid solids meet at a face; they do not overlap.
"""

import importlib
import json
import os
from pathlib import Path

import FreeCAD as App
import Part

# The wrapper exposes FreeCAD's official Ext/PySide compatibility package.
importlib.import_module("AssemblyApp")
JointObject = importlib.import_module("JointObject")

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get("WB_ARTIFACTS", str(ROOT / "artifacts"))) / "joints"
OUT.mkdir(parents=True, exist_ok=True)
doc = App.newDocument("FixedJointAcceptance")
assembly = doc.addObject("Assembly::AssemblyObject", "Assembly")
assembly.Type = "Assembly"
joints = assembly.newObject("Assembly::JointGroup", "Joints")
base = assembly.newObject("Part::Box", "GroundedBase")
base.Length, base.Width, base.Height = 20, 20, 4
base.Placement = App.Placement(App.Vector(10, 20, 30), App.Rotation(15, 25, 35))
block = assembly.newObject("Part::Box", "MountedBlock")
block.Length, block.Width, block.Height = 8, 8, 4
block.Placement = App.Placement(App.Vector(50, -20, 60), App.Rotation(70, 50, 10))
doc.recompute()

ground = joints.newObject("App::FeaturePython", "GroundedJoint")
JointObject.GroundedJoint(ground, base)
fixed = joints.newObject("App::FeaturePython", "FixedJoint")
JointObject.Joint(fixed, 0)
fixed.Offset1 = App.Placement(App.Vector(6, 6, 4), App.Rotation())
fixed.Proxy.setJointConnectors(
    fixed,
    [
        [assembly, [base.Name + ".", base.Name + "."]],
        [assembly, [block.Name + ".", block.Name + "."]],
    ],
)
doc.recompute()
grounded_placement = App.Placement(base.Placement)
offset = App.Placement(App.Vector(6, 6, 4), App.Rotation())
target = grounded_placement * offset
assert fixed.JointType == "Fixed"
assert assembly.isPartGrounded(base)


def disturb_and_solve(assembly, base, block, target):
    """Exercise the solver independently of the joint creator's presolve."""
    block.Placement = App.Placement(App.Vector(-35, 41, 75), App.Rotation(70, -35, 10))
    before = App.Placement(block.Placement)
    assert not before.isSame(target, 1e-6)
    code = assembly.solve()
    assembly.Document.recompute()
    assert code == 0, f"Native Assembly solver failed: {code}"
    assert block.Placement.isSame(target, 1e-6), (block.Placement, target)
    assert base.Placement.isSame(grounded_placement, 1e-6)
    assert base.Shape.isValid() and block.Shape.isValid()
    assert len(base.Shape.Solids) == len(block.Shape.Solids) == 1
    assert abs(base.Shape.Volume - 1600) < 1e-7
    assert abs(block.Shape.Volume - 256) < 1e-7
    assert base.Shape.common(block.Shape).Volume < 1e-6
    assert base.Shape.distToShape(block.Shape)[0] < 1e-6
    return {
        "native_solve_return_code": code,
        "position_before_mm": list(before.Base),
        "position_after_mm": list(block.Placement.Base),
        "target_position_mm": list(target.Base),
        "translation_error_mm": (block.Placement.Base - target.Base).Length,
        "rotation_error_rad": (
            block.Placement.Rotation * target.Rotation.inverted()
        ).Angle,
        "intersection_volume_mm3": base.Shape.common(block.Shape).Volume,
        "surface_separation_mm": base.Shape.distToShape(block.Shape)[0],
    }


initial = disturb_and_solve(assembly, base, block, target)
native = OUT / "grounded-fixed-assembly.FCStd"
doc.saveAs(str(native))
Part.export([base, block], str(OUT / "grounded-fixed-assembly.step"))
name = doc.Name
App.closeDocument(name)
doc = App.openDocument(str(native))
assert doc.FixedJoint.JointType == "Fixed"
assert doc.GroundedJoint.ObjectToGround == doc.GroundedBase
assert doc.FixedJoint.Proxy is not None
reopened = disturb_and_solve(doc.Assembly, doc.GroundedBase, doc.MountedBlock, target)
doc.save()
imported = Part.Shape()
imported.read(str(OUT / "grounded-fixed-assembly.step"))
assert imported.isValid() and len(imported.Solids) == 2
assert abs(imported.Volume - 1856) < 1e-6
result = {
    "status": "passed",
    "command": "scripts/run-freecad.sh tests/test_freecad/joint_acceptance.py",
    "freecad_version": App.Version(),
    "joint_type": "Fixed",
    "grounded_body": "GroundedBase",
    "initial_solve": initial,
    "reopened_solve": reopened,
    "native_proxy_preserved": True,
    "step_solid_count": len(imported.Solids),
    "limitations": "One grounded body plus one fixed joint; revolute joints, motion limits, redundant constraints and multibody dynamics not exercised",
    "files": [
        str(native.relative_to(ROOT)),
        str((OUT / "grounded-fixed-assembly.step").relative_to(ROOT)),
    ],
}
(OUT / "results.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
