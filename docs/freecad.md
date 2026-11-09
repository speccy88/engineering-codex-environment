# FreeCAD native runtime

FreeCAD 1.0.0 is supplied by Debian 13 packages (package version
`1.0.0+dfsg-8+deb13u3`) with OCCT 7.8.1, Python 3.13.5, Qt 5.15 and
PySide2 5.15.16. The engineering Python virtual environment is separate.
Do not install pip packages over the distribution's FreeCAD bindings or
load the CadQuery OCP libraries into this process.

## Entry points

From the repository root:

```bash
# Geometry, sketches, native documents, STEP/STL and static assemblies:
scripts/run-freecad.sh your_model.py [arguments...]

# TechDraw vector export and other operations needing FreeCAD GUI services:
scripts/run-freecad.sh --gui your_drawing.py [arguments...]
```

The wrapper uses `/usr/bin/python3`, explicit native module search paths,
repository-local writable XDG directories and software graphics. It clears
inherited `PYTHONHOME` and `PYTHONPATH` contamination. Its `--gui` mode starts
a private Xvfb display when `DISPLAY` is absent, initializes Qt and FreeCAD's
GUI, hides the window and terminates Xvfb when Python exits. No desktop,
network port or persistent service is required. The locally extracted,
verified Debian Xvfb package is provided by `setup/install.sh`.

The Python script may import `FreeCAD`, `Part`, `Sketcher`, `Mesh`, `Import`,
`TechDraw` and `AssemblyApp`. Import `FreeCAD` before `AssemblyApp`; loading
the assembly extension before the application is initialized can crash the
native process. For `--gui`, the wrapper already creates the QApplication.

`freecadcmd --help` succeeds, but this distribution's `freecadcmd --version`
raises SIGSEGV inside `Py_EncodeLocale` and returns exit code 1 through its
crash handler. It is therefore not the supported scripting entry point here.
The native `/usr/bin/python3` wrapper is the tested alternative, and Python
exceptions propagate as a failing process exit code.
Plain `QT_QPA_PLATFORM=offscreen` supports
core modeling but does not supply the OpenGL context required by the full GUI.
`FreeCADGui.setupWithoutGUI()` can compute TechDraw projections but did not
produce PDF output. The tested solution is Xvfb with `QT_QPA_PLATFORM=xcb`.

## Verified operations

```bash
scripts/run-freecad.sh --gui tests/test_freecad/acceptance.py

# Generate EDA acceptance first; this uses the actual populated PCB STEP:
scripts/run-freecad.sh tests/test_freecad/assembly.py artifacts/eda/divider.step
```

The first script creates three fully constrained sketches and a PartDesign
body with base pad, flange pad and two through-hole pockets. It saves
`bracket.FCStd`, exports STEP/STL, closes and reopens the native file, changes
the named `BaseSketch.Constraints.Width` dimension from 60 to 70 mm, recomputes
dependent features, and saves `bracket-wider.FCStd`. It checks solid validity,
analytic volume, final width, a STEP geometry round trip and closed STL meshes.

Its TechDraw page retains real projected geometry and linked measured
dimensions: 70 mm overall width and 37 mm exposed base depth (40 mm total
depth minus the 3 mm flange). It exports `bracket-drawing.pdf` and
`bracket-drawing.svg` and saves the drawing in the wider native document.
Use a standard installed text font such as DejaVu Sans for dimensions; the
distribution's osifont PDF output exhibited damaged glyphs. The supplied
FreeCAD template emits harmless PDF path warnings in Poppler but the exported
page was rasterized and visually inspected. No drawing is accepted on file
existence alone.

The assembly script reads the real KiCad-exported PCB STEP (22 valid solids,
40 x 25 x 11.54 mm populated extent), creates a 50 x 35 x 18 mm parametric
enclosure using additive/subtractive PartDesign primitives, and places them
in a native `Assembly::AssemblyObject` with component links. It checks all
source solids, the enclosure volume, zero PCB/enclosure intersection, STEP
round-trip solid count (23), and the reopened native assembly.

Assembly workbench loading and linked static placement are tested. Native
grounded/fixed joint solving is additionally covered by:

```bash
scripts/run-freecad.sh tests/test_freecad/joint_acceptance.py
```

This core-only test uses FreeCAD's distribution-shipped `JointObject` API and
the official `/usr/share/freecad/Ext` PySide compatibility package. It creates
two valid nonintersecting blocks with touching mounting faces, grounds the
base, and joins the mounted block using a fixed joint with an explicit local
connector offset. It deliberately moves and rotates the mounted block away
from the constraint, calls the real native `Assembly.solve()` method, verifies
its successful return code and full restored placement, then saves and reopens
`artifacts/joints/grounded-fixed-assembly.FCStd` and repeats the disturbance
and solve. Both stages check the grounded placement, solid volumes, zero
intersection and zero mounting-surface separation. STEP reimport checks two
valid solids with matching total volume; results are in
`artifacts/joints/results.json`.

This verifies one grounded body and one fixed joint, including persisted
Python joint proxies. Revolute joints, motion limits, redundant constraints
and multibody dynamics remain untested. The example PCB enclosure is a
clearance fixture; it has no mounting supports, lid, or connector openings and
is not a manufacture-ready product design.

## Output paths

- `artifacts/freecad/`: native bracket files, STEP/STL, dimensioned PDF/SVG,
  `results.json`, and acceptance log.
- `artifacts/assembly/`: native PCB/enclosure assembly, compound STEP/STL,
  separate enclosure STEP/STL, and `results.json`.

Generated files remain outside Git by default. Preserve the `.FCStd` document
alongside neutral exports when continuing a design. For a real project,
record interface dimensions, units, origins and coordinate transforms in its
versioned specification; commit native sources in that project's repository.

Re-running the examples overwrites only their own disposable artifact paths;
FreeCAD may retain `.FCBak` recovery copies in those directories.
