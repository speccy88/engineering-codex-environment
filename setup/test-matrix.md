# Engineering acceptance and limitations

## Fritzing addition, 2026-11-10

`bash setup/verify.sh --fritzing` passed its native runtime probe, all **43 regression tests**, and actual end-to-end Fritzing acceptance. `python3 setup/check_repository.py` and `git diff --check` also passed. The independent [verified example](../examples/fritzing/verified/verification.json) records actual rendered pixels, 4 native PCB trace objects, 6 drill positions, a 60.96 × 30.48 mm contour and 3 native IPC nets matching the circuit intent. All three native PNG views were visually inspected. The installer was executed and its idempotent rerun tested; batch native execution blocks Internet sockets with seccomp.

This covers declarative through-hole/single-layer generation, conventional/custom symbols, layout/clearance checks and native SVG/PNG/Gerber/Excellon/BOM/IPC export. Tests also exercise DIP8/header branching, malformed inputs, edited archives, obstructed routes and network-denial enforcement. The generator's geometric checks are not native Fritzing DRC or electrical ERC. Dense/multilayer routing, automatic use of arbitrary stock parts in the generator, and environment publication/fresh-task restoration remain outside this validation. Existing FZZ files may use the native exporter independently. Native pick-and-place is deliberately excluded because this version misclassifies some custom through-hole parts.

The older combined CAD/scientific results below are retained historical evidence, not a rerun of every unrelated toolchain in this change.

Current-instance validation on 2026-11-09. `acceptance-results.json` records the final full run's exact commands, working directory, timestamps, exit codes and log paths. Generated logs and outputs are in the downloadable evidence bundle and ignored `artifacts/` tree. This is not a fresh-task restoration or publication claim.

## Passing functional operations

| Capability | Actual check | Evidence under artifacts/ |
| --- | --- | --- |
| FreeCAD Part/PartDesign/Sketcher | Three fully constrained sketches, pads/pocket, valid bracket, native save/reopen, width60→70mm, recompute | freecad/results.json; bracket.FCStd; bracket-wider.FCStd |
| FreeCAD STEP/STL | Solid validity and volume after STEP roundtrip; watertight meshes | freecad/*.step, *.stl |
| TechDraw | Native view/dimension objects; actual PDF/SVG, extracted70.0mm/37.0mm labels and visually reviewed raster | freecad/bracket-drawing.pdf, .svg, -preview.png |
| CadQuery 2.6.1 | Independent bracket, analytical volume5564.601776mm³, valid STEP roundtrip, watertight STL | python/cadquery/result.json |
| build123d 0.9.1 | Independent model with same analytic checks and neutral exports | python/build123d/result.json |
| OpenSCAD | Actual CGAL CSG export, single watertight STL and analytic-volume tolerance | python/openscad/result.json |
| Gmsh/meshio |403 tetrahedra, all positive volumes, summed unit-cube volume1.0, VTU connectivity roundtrip | python/geometry/result.json |
| Scientific/export libraries | Unit conversion, topology, linear solve, symbolic checks, actual DXF/SVG/PDF readback | python/geometry/result.json |
| SKiDL | Stock-library divider netlist, SKiDL ERC0 errors/0 warnings; netlist0 errors,6 visible optional-table/tag warnings | python/skidl/result.json |
| KiCad schematic | Editable native schematic, actual ERC all severities0, XML pin-connectivity assertions, BOM+SVG | eda/schematic-result.json; erc.json |
| KiCad PCB + Freerouting | Footprints/net parity, DSN export, Java headless routing, actual SES import, tracks+via | eda/pcb-result.json; divider.dsn; divider.ses |
| KiCad final DRC | All severities and schematic parity,0 violations and0 unconnected items | eda/drc.json |
| Manufacturing/assembled STEP | Gerbers+Excellon, BOM,22 independently valid STEP solids and40×25×11.54mm assembly bounds | eda/gerbers/; bom.csv; pcb-step-result.json |
| ngspice native | Divider2.5V within1e-8V; RC573rows, max error about1.34e-5V below0.01V, CSV+graphs | ngspice/results.json; divider.csv; rc.csv; *.png |
| PySpice shared API | Actual default shared-backend DC solution2.5V, plus independent netlist-builder/native-solver check | ngspice/pyspice-shared-result.json; pyspice-status.json |
| Native FreeCAD assembly | Actual KiCad PCB22solids + enclosure; native Assembly object with static links;23valid solids, zero interference | assembly/results.json; pcb-enclosure.FCStd/.step/.stl |
| Blender background | CPU Cycles, native .blend save/reopen, imported CAD geometry, nonblank pixels and all mesh corners in camera frame | blender-cad/result.json; assembly-preview/result.json |
| FFmpeg/ImageMagick | Actual image transforms to320×240, dimensions checked | blender-cad/media-result.json |
| FreeCAD fixed-joint solver | Explicitly disturb translation/rotation; native solve returns 0, residual about 7.1e-15 mm and 0 rad; save/reopen/repeat, valid STEP | joints/results.json |
| Live KiCad IPC | Temporary Xvfb/editor, version/ping/open board, 3 footprints at expected locations, 12 tracks and 1 via; source unchanged, processes cleaned | ipc/latest-result.json |
| Blender animation + MP4 | Editable keyframes, 8 distinct/nonblank PNGs, CPU render; H.264, 128×128, 8 fps, 1 s; decoded-frame motion | animation/render-result.json; animation/video-result.json |
| Repository integrity | AST parsing, shell syntax/executable bits, JSON/skill frontmatter, locked download hashes | setup/check_repository.py |
| Python regression suite |6 pytest tests passed;15 upstream deprecation warnings retained | python/pytest.log |

## Failures, alternatives and untested features

| Status | Capability | Technical cause / supported alternative |
| --- | --- | --- |
| Known executable failure; working alternative tested | `freecadcmd --version` | Distribution interpreter startup crashes in Py_EncodeLocale. Use isolated native-Python wrapper; standalone --help returned0. |
| Failed initial mode; working alternative tested | Pure Qt offscreen TechDraw | No OpenGL context/modal warning prevented full GUI export. Private Xvfb+xcb produces verified dimensioned PDF/SVG. |
| Initial dependency conflict repaired | Latest CadQuery/build123d mix | Overlapping OCP vtk/novtk distributions broke IVtk import. Compatible versions pinned with hashes and real model tests. |
| Initial runtime mismatch repaired | Freerouting 2.5 | Requires Java25. Official2.1.0 is pinned and tested on Java21. |
| Optional backend failure | PySpice 1.5 subprocess API | Legacy output parser rejects ngspice 44 Note header. Shared API and native executable both pass. PySpice still warns version44 is unrecognized; advanced code-model simulations are untested. |
| Untested API subset | Official kicad-python 0.8.0 IPC API | Core requests pass against KiCad 9.0.2; client declares API 10.0.6, and API 10-only methods are outside validation. |
| Untested joint subset | Advanced Assembly behavior | Grounded/fixed joint solving and reopen pass; revolute joints, limits, redundant constraints and dynamics remain untested. Example enclosure has no connector openings/mounting supports. |
| Unavailable feature in build; supported mode tested | Blender OpenImageDenoise | Debian build lacks denoiser. CPU Cycles48samples works with denoising disabled. |
| Untested advanced behavior | Audio, GPU and long-form rendering | Basic eight-frame Blender animation/image sequence/H.264 export passes; audio, physics, GPU and arbitrary user designs require their own checks. |
| External configuration pending | GitHub REST/PR operations | Fresh api.github.com CONNECT returned403; domain addition saved in configuration draft. Git push works independently. |
| Not executed | Publication/fresh-task restoration | Must review/save/publish through environment settings, then validate in a new task. Current-instance tests do not establish restoration. |

The baseline, exact inventory, Python hash locks and native download digests live in setup/. No test was replaced with file-existence-only validation, and engineering source was not patched to conceal an incompatibility.
