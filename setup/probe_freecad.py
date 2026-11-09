"""Native runtime wiring probe. Functional acceptance is a separate command."""

import FreeCAD
import Part
import Sketcher
import TechDraw

print(
    "FreeCAD",
    ".".join(FreeCAD.Version()[:3]),
    Part.__name__,
    Sketcher.__name__,
    TechDraw.__name__,
)
