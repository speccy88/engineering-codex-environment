# Toolchain and runtime architecture

This workbench uses native Linux tools on Debian 13 amd64. Docker is not needed
for the tested workflows. The baseline is in
[`setup/environment-report.md`](../setup/environment-report.md); publication,
installation and refresh behavior are described in
[`cloud-environment.md`](cloud-environment.md). Versions and download hashes are
recorded in the setup locks/metadata; individual acceptance results record the
versions they actually executed.

## Choose a runtime

Run commands from the checkout. Each tool is usable independently.

| Runtime | Entry point | Tested tools and compatibility |
| --- | --- | --- |
| Engineering Python 3.12 | `scripts/run-python.sh script.py` | `.venvs/engineering`: CadQuery 2.6.1, build123d 0.9.1, OCP 7.8.1.1.post1, Gmsh 4.15.2, meshio, trimesh, Shapely, scientific and export libraries, SKiDL |
| FreeCAD's Debian Python 3.13 | `scripts/run-freecad.sh script.py` | FreeCAD 1.0.0, native OCCT 7.8.1, Part, PartDesign, Sketcher; native save/reopen/edit/export |
| FreeCAD GUI-backed Python | `scripts/run-freecad.sh --gui script.py` | TechDraw dimensioned PDF/SVG export using temporary Xvfb, Qt xcb and software graphics |
| KiCad's Debian Python 3.13 | `scripts/run-kicad.sh python script.py` | KiCad 9.0.2 legacy `pcbnew` SWIG API, official symbols/footprints/3D models |
| Native KiCad CLI | `scripts/run-kicad.sh cli ...` | Schematic ERC, PCB DRC/parity, BOM, plots and fabrication/STEP exports |
| Optional KiCad IPC Python 3.12 | `scripts/run-kicad-ipc.sh script.py` | Separate `.venvs/kicad-ipc`, official kicad-python 0.8.0 (`kipy`) client; core live requests tested against KiCad 9.0.2 in a temporary editor; API 10-only methods untested |
| Blender's embedded Python 3.13 | `scripts/run-blender.sh script.py` | Blender 4.3.2, CPU Cycles, native scene save/reopen, PNG and STL; no separate `bpy` wheel |
| Native OpenSCAD | `openscad -o model.stl model.scad` | OpenSCAD 2021.01, CGAL solid export tested |
| Native simulation | `scripts/run-ngspice.sh -b model.cir` | ngspice 44.2, independent of Python |
| Java routing | `scripts/run-freerouting.sh -de board.dsn -do board.ses -mp 8 -mt 2` | Official Freerouting 2.1.0 on OpenJDK 21; noninteractive DSN→SES tested |
| Media tools | `ffmpeg ...`, `magick ...` | FFmpeg 7.1.5 and ImageMagick 7.1.1-43; still transformations and H.264 MP4 sequence encoding tested |

Do not combine FreeCAD, pcbnew, Blender and the geometry venv's binary libraries
in a single Python process. The wrappers select compatible interpreters and
library/profile locations. Native applications and the venvs are retained in
the published filesystem; ordinary tasks use them without reinstalling. No
persistent service, interactive desktop or exposed network port is required.
TechDraw starts a temporary private display; the optional IPC API is a
different client/server workflow and never starts automatically.

CadQuery/build123d deliberately share a tested OCP combination inside the
engineering venv. Newer attempted versions resolved incompatible OCP packages;
do not independently upgrade one without rerunning geometry acceptance. Native
FreeCAD uses a separate system OCCT runtime. Freerouting 2.5.0 required Java 25
and was rejected for this Java 21 runtime; the tested release is locked with a
SHA-256 digest. Debian Blender lacks OpenImageDenoise, so CPU rendering disables
denoising. Pure Qt offscreen was insufficient for TechDraw export; the tested
GUI-backed path uses Xvfb/xcb.

## Verification and evidence

`bash setup/verify.sh --quick` checks runtime wiring; it does not validate a new
engineering design. `bash setup/verify.sh --full` executes the optional
acceptance fixtures and records actual commands, working directories, exit
codes and logs under `artifacts/verification/`. Fixture outputs and detailed
numerical evidence are under `artifacts/`.

Executed acceptance covers parametric FreeCAD modification and export
roundtrips, dimensioned TechDraw export, independent CadQuery/build123d solids,
OpenSCAD solids, Gmsh/meshio tetrahedra, SKiDL netlists, KiCad ERC and routed-board
DRC/parity, assembled PCB STEP geometry, ngspice divider/RC calculations,
static PCB/enclosure assembly checks and nonblank Blender still rendering.
These tests exercise example designs, not every operation available in each
application.

Static native Assembly links and grounded/fixed-joint solve/reopen are tested. Revolute joints, limits and dynamics remain untested.
The installed optional PySpice package can generate netlists for the native
solver; its shared-library backend now passes the DC divider test with the
workspace-native library. Its legacy subprocess parser remains incompatible
with ngspice44's header. Live KiCad IPC reads and Blender image-sequence/H.264
export now pass acceptance; audio, GPU rendering and API 10-only IPC methods
remain outside validation. See the
focused documents for exact evidence and limitations:

- [FreeCAD and technical drawings](freecad.md)
- [Python geometry, scientific tools and simulation](python.md)
- [KiCad and Freerouting](eda.md)
- [Blender and media tools](rendering.md)

Git and GitHub CLI are already installed. The existing cloud Codex agent/CLI is
available; no second Codex installation, nested execution, API key or additional
API billing is needed for this workbench.
