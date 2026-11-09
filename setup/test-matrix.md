# Engineering acceptance and limitations

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
| Installed/imported; live operation untested | Official kicad-python0.8.0 IPC API | Requires a live IPC-enabled KiCad GUI/server; automated headless path uses tested KiCad 9 SWIG/CLI instead. |
| Untested | Assembly joint solving/motion | Native static Assembly object and actual geometry checks passed; no joint solver acceptance. Example enclosure has no connector openings/mounting supports. |
| Unavailable feature in build; supported mode tested | Blender OpenImageDenoise | Debian build lacks denoiser. CPU Cycles48samples works with denoising disabled. |
| Installed, untested behavior | Animation/video and advanced engineering workflows | Blender/FFmpeg are available; this acceptance covers still rendering/image transforms, not MP4 animation or arbitrary user designs. |
| External configuration pending | GitHub REST/PR operations | Fresh api.github.com CONNECT returned403; domain addition saved in configuration draft. Git push works independently. |
| Not executed | Publication/fresh-task restoration | Must review/save/publish through environment settings, then validate in a new task. Current-instance tests do not establish restoration. |

The baseline, exact inventory, Python hash locks and native download digests live in setup/. No test was replaced with file-existence-only validation, and engineering source was not patched to conceal an incompatibility.
