# Engineering CAD & EDA Workbench

A reusable native Debian 13 workstation for independent Codex Cloud mechanical, electronic, simulation and rendering tasks. Tools are usable separately; examples and integration tests are optional. No fixed parts catalog, project architecture, persistent service, container or interactive desktop is required.

## Use an installed environment

```sh
cd /workspace/engineering-codex-environment
bash setup/verify.sh --quick
```

| Task | Entry point | Runtime |
| --- | --- | --- |
| CadQuery/build123d/OCP, scientific Python, Gmsh, SKiDL | `scripts/run-python.sh script.py` | isolated Python 3.12 |
| FreeCAD native FCStd and solids | `scripts/run-freecad.sh script.py` | system Python 3.13 |
| FreeCAD TechDraw PDF/SVG | `scripts/run-freecad.sh --gui script.py` | Python + temporary Xvfb |
| KiCad checks/exports | `scripts/run-kicad.sh cli ...` | KiCad 9 CLI |
| Programmatic PCB creation/modification | `scripts/run-kicad.sh python script.py` | system Python + legacy pcbnew |
| Official KiCad IPC client | `scripts/run-kicad-ipc.sh script.py` | separate client; needs live server |
| SPICE simulation | `scripts/run-ngspice.sh -b circuit.cir` | native ngspice |
| DSN to SES autorouting | `scripts/run-freerouting.sh -de board.dsn -do board.ses` | Freerouting + Java 21 |
| Rendering | `scripts/run-blender.sh script.py ...` | Blender embedded Python |
| CSG | `openscad -o model.stl model.scad` | native OpenSCAD |

Read [AGENTS.md](AGENTS.md), [toolchain](docs/toolchain.md), [independent workflows](docs/project-workflows.md), and focused [skills](skills/). Keep project source in its own repository. Preserve editable FCStd, KiCad, Blender and parametric generator sources alongside neutral exports.

## Verified behavior

The latest combined acceptance run executed **30 commands: 12 runtime/asset probes and 18 functional acceptance commands, all passed**. A separate scientific suite ran **6 pytest tests, all passed**. See [test matrix and limitations](setup/test-matrix.md), [baseline](setup/environment-report.md), and [exact versions](setup/versions.lock).

- FreeCAD: constrained parametric bracket, native reopen/dimension change, STEP/STL roundtrips, dimensioned TechDraw PDF/SVG.
- CadQuery/build123d/OpenSCAD: independent solid creation and validated exports. Gmsh/meshio: positive-volume tetrahedral roundtrip.
- KiCad: editable divider schematic/PCB, ERC0, real Freerouting DSN/SES import, DRC/parity/unconnected0, BOM/Gerber/drill and valid assembled STEP.
- ngspice:2.5V divider within1e-8V; RC transient matched analytic response within0.01V.
- Native grounded/fixed-joint solve: disturbance recovery and save/reopen verification. Live KiCad IPC reads actual board footprints, tracks and vias.
- Actual KiCad PCB plus FreeCAD enclosure:23 valid solids and zero measured interference, native sources and neutral exports.
- Blender: background CPU renders, native save/reopen, nonblank pixels, camera framing and mechanical imports. FFmpeg/ImageMagick still-image transforms, eight-frame Blender animation and verified H.264 MP4 export.

```sh
# Full engineering acceptance, separate from inexpensive CI:
bash setup/verify.sh --full
# Cheap repository/CI checks (no engineering apps installed):
python3 setup/check_repository.py
```

Generated files and command evidence live under ignored `artifacts/`. Optional [mechanical](examples/mechanical-part/README.md), [electronic](examples/electronic-circuit/README.md), and [PCB/enclosure](examples/pcb-and-enclosure/README.md) fixtures explain regeneration. Bundle a project with `scripts/export-project.sh PROJECT_DIRECTORY /workspace/project.zip`.

## Installation and cloud publication

The current machine's major CAD applications were preinstalled; this repository adds isolated hash-locked Python packages, a checksum-locked workspace native prefix, libraries and tested wrappers. [Cloud setup](docs/cloud-environment.md) distinguishes prerequisites, installation, restoration and publication.

`bash setup/install.sh` refreshes required local dependencies without modifying project source or lockfiles; it is **not** an instruction to reinstall on every new task. Save [cloud Install script](setup/cloud-install.sh) and [Start skill](setup/start-skill.md) in environment settings, review/save, then publish the prepared filesystem. A commit does not publish an environment. Fresh-task restoration remains unverified until publication and a subsequent task.

Known limits: standalone `freecadcmd --version` crashes in this distribution (tested Python wrapper works); API 10-only IPC methods and advanced joint types remain outside validation; Blender denoising is disabled because this build lacks OpenImageDenoise; basic Blender animation and H.264 export are now acceptance-tested. See the [matrix](setup/test-matrix.md) for optional PySpice status.
