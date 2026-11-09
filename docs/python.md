# Engineering Python and simulation runtimes

Use `scripts/run-python.sh your_script.py` for the CPython 3.12 engineering environment. It sets writable cache/data/config directories, Matplotlib's configuration directory, and the installed KiCad 9 symbol-library path. It does not import FreeCAD, pcbnew, or Blender. Run their dedicated wrappers instead: those APIs depend on the distribution's Python 3.13 and native packages.

## Reproducible dependencies

`setup/requirements.in` describes requested engineering packages; `setup/requirements.lock` pins the entire resolved dependency graph with SHA-256 hashes. Installation uses the existing `uv` binary, verified TLS, and a writable cache:

```sh
UV_CACHE_DIR=/workspace/.cache/uv UV_SYSTEM_CERTS=true uv venv --python python3 .venvs/engineering
UV_CACHE_DIR=/workspace/.cache/uv UV_SYSTEM_CERTS=true uv pip sync \
  --python .venvs/engineering/bin/python --require-hashes setup/requirements.lock
```

The `python3` command must resolve to the cloud agent's CPython 3.12, not `/usr/bin/python3` (Debian's 3.13). The published filesystem retains this virtual environment and installed applications. Ordinary tasks use wrappers; they do not reinstall packages. Changing a lock or interpreter requires a controlled reinstall, acceptance rerun, and environment republish.

CadQuery **2.6.1**, build123d **0.9.1**, and cadquery-ocp **7.8.1.1.post1** are deliberately compatible. Latest CadQuery 2.8.0 plus build123d 0.12.0 resolved to overlapping `cadquery-ocp`/`cadquery-ocp-novtk` distributions and failed a real CadQuery import (`IVtkOCC_Shape`). The selected versions passed solid construction and export/reimport; no distribution source was patched. OCP is the Python binding to its packaged OCCT 7.8 implementation; FreeCAD uses its separately installed system OCCT runtime.

Installed package versions are in `setup/requirements.lock`, with the selected tested package inventory recorded in `artifacts/python/geometry/result.json`. The inventory includes NumPy, SciPy, SymPy, pandas, Pint, Shapely, Matplotlib, pytest, Ruff, Gmsh, trimesh, meshio, PyMuPDF, svgwrite, ezdxf, SKiDL, and optional PySpice.

## Independent runnable workflows

```sh
scripts/run-python.sh tests/test_cadquery/acceptance.py
scripts/run-python.sh tests/test_build123d/acceptance.py
scripts/run-python.sh tests/test_geometry/acceptance.py
scripts/run-python.sh tests/test_geometry/openscad_acceptance.py
scripts/run-python.sh tests/test_geometry/skidl_acceptance.py
scripts/run-python.sh tests/test_ngspice/acceptance.py
scripts/run-python.sh -m pytest -q tests/test_cadquery tests/test_build123d tests/test_geometry tests/test_ngspice
```

These are optional examples and acceptance checks, not a required project architecture. CadQuery and build123d scripts are native editable parametric source; their STEP/STL outputs supplement the source. Each creates its model independently, checks a valid single solid and analytical volume, writes STEP/STL, reimports STEP, and verifies watertight STL topology and volume. OpenSCAD uses the independent editable `tests/test_geometry/openscad.scad` source and validates its CGAL-generated STL similarly.

Gmsh creates a tetrahedral unit cube. The mesh test checks positive tetrahedral volumes, summed volume, and meshio VTU connectivity roundtrip. It also exercises unit conversion, Shapely topology, SciPy linear solving, SymPy, and DXF/PDF/SVG exports. Gmsh boundary entity sets are not included in VTU: the volume mesh preserves coordinates and tetrahedral connectivity.

SKiDL 3.0 defaults to a KiCad 10 backend. For the installed KiCad 9 libraries explicitly call `set_default_tool(KICAD9)` before creating stock parts. `skidl_acceptance.py` generates the 5 V divider netlist with stock Device resistors, a connector, assigned footprints, and actual SKiDL ERC. KiCad schematic ERC and PCB DRC remain separate checks in the EDA workflow. SKiDL may warn about absent global tables for other KiCad versions; those optional backends are not configured. The test checks ERC and netlist generation error counts rather than assuming a written netlist is valid.

## Simulation

`scripts/run-ngspice.sh` runs either an installed native ngspice or the user-owned `.local/sysroot/usr/bin/ngspice`, with its library and SPICE data paths. No Python package is required for this wrapper:

```sh
scripts/run-ngspice.sh -b path/to/circuit.cir
```

The native ngspice 44.2 acceptance executes two actual circuit simulations. The resistor divider returns **2.5 V** within **1e-8 V**. The RC transient is checked against the analytic exponential, monotonicity, and time coverage; the initial run produced 573 rows and maximum error **1.34e-5 V**, below **0.01 V**. Native `.cir` sources, solver output, CSVs, plots, commands and numerical evidence are in `artifacts/ngspice/`.

Optional PySpice **1.5** has a **tested shared-library backend** using the isolated Debian `libngspice0` **44.2+ds-1** package. Select the library explicitly before creating a simulator:

```python
from pathlib import Path
from PySpice.Spice.NgSpice.Shared import NgSpiceShared
NgSpiceShared.LIBRARY_PATH = str(Path(".local/sysroot/usr/lib/x86_64-linux-gnu/libngspice.so").resolve())
simulator = circuit.simulator(simulator="ngspice-shared")
analysis = simulator.operating_point()
```

The real shared-backend divider returned **2.5 V** within **1e-8 V**. PySpice emits `Unsupported Ngspice version 44` because its advertised version list predates this solver; the explicit operating-point test passes. The basic shared solver runs without a system `spinit`; optional XSPICE/OSDI code models are unvalidated. Its subprocess backend remains blocked by the legacy parser rejecting ngspice 44.2's `Note` header. PySpice netlist generation followed by the native ngspice wrapper is also tested. Rerun `scripts/run-python.sh tests/test_ngspice/probe_pyspice.py`; per-backend results are in `artifacts/ngspice/pyspice-status.json`. Package provenance and authenticated hashes are in `setup/pyspice-native.json`. No package source is patched.

## KiCad IPC separation

The official `kicad-python` **0.8.0** client (`import kipy`) lives in `.venvs/kicad-ipc`, pinned with hashes in `setup/kicad-ipc.lock`. Run it with `scripts/run-kicad-ipc.sh your_client.py`. Its import is tested. A live IPC operation requires a running IPC-enabled KiCad GUI and is not claimed as tested. It is independent of the distribution's legacy `pcbnew` SWIG API and does not replace that API's headless capabilities.

## Resource and evidence policy

Model and mesh acceptance uses two Gmsh threads and modest sample sizes. Simulations and file conversion require no persistent service, network port, cloud API, or extra Codex invocation. Generated files remain under ignored `artifacts/`; commit native project sources and specifications to the relevant project repository when coordinating separate cloud tasks.

The general Python wrapper now selects the native shared library through `LD_LIBRARY_PATH`. `setup/configure_native.py` creates a user-owned ngspice init file with relocated code-model paths and two threads; the hash-verified vendor init file remains unchanged. `tests/test_ngspice/shared_acceptance.py` verifies the default PySpice shared backend without modifying its class configuration. Advanced XSPICE/OSDI circuit behavior remains untested.
