# EDA runtimes and independent tools

KiCad9.0.2, official symbol and footprint packages9.0.2, official 3D package9.0.2
and legacy pcbnew SWIG bindings use Debian Python3.13.5. They are deliberately
separate from the Python3.12 geometry/scientific environment. Use:

```sh
scripts/run-kicad.sh --version
scripts/run-kicad.sh python my_board_script.py
scripts/run-kicad.sh sch erc --severity-all --exit-code-violations project.kicad_sch
scripts/run-kicad.sh pcb drc --severity-all --schematic-parity --exit-code-violations project.kicad_pcb
```

The wrapper clears external Python paths for SWIG, supplies writable XDG profile
locations, copies official library tables if absent and discovers the unpacked
3D model library under `.local/sysroot/usr/share/kicad/3dmodels`. It never edits
system configuration. KiCad library variables remain overridable by the caller.
Use system Python for pcbnew; importing its binary module in the geometry venv
is unsupported. Board automation can load/save footprints, placements, tracks,
vias, layers and native boards. `pcbnew.ExportSpecctraDSN` and
`pcbnew.ImportSpecctraSES` bridge to the independent autorouter.

The separate `.venvs/kicad-ipc` environment contains official kicad-python0.8.0
(import name `kipy`); `scripts/run-kicad-ipc.sh` selects it. IPC is the newer
client/server API, not a replacement Python import for pcbnew. A live IPC session
requires an open KiCad GUI editor with IPC enabled. The client import is tested;
a live GUI IPC transaction has not been validated. Normal headless board tests
use the tested SWIG runtime. No editor/server starts automatically.

SKiDL is available in `scripts/run-python.sh`; select `KICAD9` explicitly with
SKiDL3 because its default library target is KiCad10. SKiDL netlist generation
alone does not produce a validated schematic/board. Use KiCad ERC/DRC and inspect
connectivity before labeling output valid.

## Freerouting

The official release JAR2.1.0 runs on installed OpenJDK21.0.13. Its TLS-downloaded
artifact SHA256 is
`2c07d58f75dac03782664081e7a58b41c25400d871a9fcf166a2ea6fe60d5def`.
The2.5.0 JAR was evaluated and rejected because it requires Java25(class69),
while this runtime supports Java21(class65). The incompatible artifact was
removed; no verification bypass or alternate unofficial binary was used.

```sh
scripts/run-freerouting.sh -de board.dsn -do board.ses -mp 8 -mt 2
```

The wrapper disables GUI and anonymous analytics and caps heap at2GiB. SES
must be imported into the exact source board, followed by real DRC. Preserve
native `.kicad_sch`, `.kicad_pcb` and `.kicad_pro`; Gerber/Excellon, DSN, SES and
STEP are derived formats.

## Verified acceptance

`tests/test_kicad/schematic.py` creates the optional divider and executes ERC
with all severities, exports a real BOM/XML netlist/SVG, and checks every pin's
net assignment. `tests/test_kicad/board.py` loads official footprints, assigns
matching UUID paths/library IDs, crosschecks board pin nets against schematic,
exports DSN, routes and imports SES, then executes DRC including schematic
parity before fabrication and STEP exports. No DRC findings are excluded.

`tests/test_kicad/step_geometry.py` independently reads assembled STEP through
OCP/OCCT, checks every solid is valid and verifies board XY plus component
height. This detects successful exports that silently omitted component models.

Current execution: ERC0, DRC0, unconnected0, schematic parity0; actual routing
contains copper tracks and a through via. Reopened native board has3 footprints.
STEP has22 valid solids and40×25×11.54mm assembled extents. Evidence and files:
`artifacts/eda/{schematic,pcb,pcb-step}-result.json`, `pcb-commands.json`,
`divider.kicad_sch`, `divider.kicad_pcb`, `divider.kicad_pro`, `divider.dsn`,
`divider.ses`, `gerbers/`, `bom.csv`, `divider.step` and SVG preview folders.

These checks validate this fixture's circuit/board connectivity, manufacturing
rules and geometry. They do not establish safety, electrical loading, thermal,
EMC or fabrication constraints for arbitrary user designs; choose engineering
checks appropriate to each independent task.
