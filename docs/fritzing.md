# Fritzing generation, routing and exports

This workflow uses the actual Fritzing application for rendering and manufacturing
exports. A separate Python generator creates editable projects, custom parts,
placements and traces from a declarative circuit description. It requires no
interactive desktop, cloud API, GPU or persistent service.

## Install and verify

```sh
# Once when preparing or repairing the environment snapshot:
bash setup/install-fritzing.sh
scripts/run-fritzing.sh --version

# Independent Fritzing acceptance; leaves other engineering runtimes alone:
python3 tests/test_fritzing/acceptance.py
python3 -m unittest discover -s tests/test_fritzing -p 'test_*.py' -v
```

The installer pins Debian-compatible upstream Fritzing and its parts library in
`setup/fritzing-native.json`. Packages are hash-checked and extracted into the
workspace's `.local/sysroot`; the system package database is unchanged. Repeated
tasks use the retained installation. The launcher supplies isolated writable
settings and Qt's offscreen backend. Linux seccomp blocks Internet socket creation
for the application and its children; a missing filter is a hard failure. The base
image supplies `libseccomp.so.2` and system Python's PySide2 QtSvg bindings. Missing
libraries or assets are errors.

`setup/install.sh` includes this installer. Commit/push updates the repository,
but does not publish the prepared cloud filesystem. Refresh the environment's
checkout, run installation and acceptance, then save/publish the environment
snapshot. Validate restoration in a subsequent task before claiming it works.

The native acceptance fixture reads Fritzing's IPC-D-356A netlist to compare every
pin assignment, measures the exported board contour, checks the drill-hole
positions against the requested millimetre dimensions, and checks nonblank pixels
in all three views. The stock board's outline stroke is compensated so requested
dimensions describe the Gerber contour centreline.

## Generate a project

```sh
python3 scripts/fritzing-project.py generate examples/fritzing/led-series.json \
  --output artifacts/my-fritzing-project
python3 scripts/fritzing-project.py validate artifacts/my-fritzing-project/project.fzz
python3 scripts/fritzing-export.py artifacts/my-fritzing-project/project.fzz \
  --output artifacts/my-fritzing-exports --png
```

Use a new output directory for each revision. Preserve the circuit JSON, editable
`.fz` and self-contained `.fzz`, custom `.fzpz` parts with `.fzp`/SVG sources, BOM,
layout/check reports, native exports and command logs. Bundle the project and
exports together with `scripts/export-project.sh`. An SVG or PNG alone is not an
editable circuit.

The formal [JSON Schema](../examples/fritzing/design.schema.json) and
[example](../examples/fritzing/led-series.json) specify the accepted inputs.
Coordinates use millimetres, with PCB positions measured from the board's upper
left and pin coordinates measured from the footprint's upper left. `body` is the
complete footprint bounding box, including pads. The circuit describes:

- Board width/height, copper trace width, clearance, edge clearance and route grid
  in millimetres.
- Components with stable references, values, explicit connector IDs, physical
  pad coordinates and body dimensions. Positions can be specified or generated.
- Named nets with exact `reference.connector` assignments and explicitly unused
  pins. Do not guess the package pin order from the schematic symbol.

The generator supports resistor, capacitor, LED, header, DIP and generic component
representations. Generic symbols and footprints permit custom pin maps, but the
physical dimensions still require verification against the actual part datasheet.
These generated component drawings are editable assets, not a complete replacement
for the stock parts library's illustrations.

## Parts library and reusable components

```sh
python3 scripts/fritzing-parts.py search resistor --limit 5
python3 scripts/fritzing-parts.py search '555'
python3 scripts/fritzing-parts.py inspect EXACT_MODULE_ID
```

Inspection returns exact connector IDs, SVG references, layer IDs and internal
bus connections. `--parts-dir` or `FRITZING_PARTS_DIR` can select another library.
Search/inspect does not automatically convert stock parts into the generator's
physical model. Use verified pin and footprint dimensions when describing a new
generated part. Existing projects using stock components can go directly to the
native exporter.

Every generated part includes a breadboard representation, schematic symbol and
PCB footprint in one reusable FZPZ archive. Import it with Fritzing's normal part
import operation. The FZZ also embeds its custom assets so another user can open
the project without manually installing each part first.

## Layout and routing checks

The generator places parts deterministically, checks their bounding boxes, routes
orthogonal schematic connections around obstacles, and creates actual PCB trace
objects with connector references. PCB routing is a bounded single-layer grid
search. It checks the supported model's copper spacing, board edge clearance and
net connectivity. Failed placement or incomplete routing must fail the command;
do not relax a rule just to obtain a successful file.

Use these controls to improve a difficult layout: change component placement,
increase board area, choose realistic pad sizes/trace widths, or use a finer route
grid. A dense board can require a different placement or the existing KiCad and
Freerouting workflow. Automatic multilayer routing, vias, copper pours, impedance
control and a full electrical rules checker are outside this generator's scope.

Native Fritzing batch rendering/exporting is not native DRC. The installed binary
does not expose its interactive autorouter/DRC as a supported command-line API.
The Python router and checks are separate and identified as such in the evidence.
Do not report “Fritzing DRC passed”, “ERC passed”, or “ready for fabrication” based
on these checks alone. Verify circuit behavior, ratings, package pinout and actual
fabricator rules for each design.

## Native rendering and manufacturing files

```sh
# Existing or generated projects:
python3 scripts/fritzing-export.py source.fzz --output artifacts/render --format svg --png
python3 scripts/fritzing-export.py source.fzz --output artifacts/manufacturing --format gerber
```

The wrapper stages a copy in a fresh private job directory, executes Fritzing's
`--svg`, `--gerber`, or `--all` directory services, and records commands, timeouts and
outcomes. SVG mode produces breadboard, schematic and PCB views; PNGs are derived
from these native SVGs using the system QtSvg renderer. Manufacturing output comes from
Fritzing's Gerber/Excellon exporter, not a separate handwritten export engine.
`--format all` additionally retains the native BOM and IPC-D-356A netlist. Native
pick-and-place output is excluded because this application version can misclassify
custom through-hole parts as surface-mount.

Open the actual rendered images before delivery. Review component and label
spacing, wire junctions/crossings, board fit and trace visibility. Successful file
creation proves neither visual quality nor electrical correctness. For an
arbitrary uploaded FZZ, rendering success also does not establish connectivity or
design-rule compliance.

## License and upstream sources

Fritzing's application code uses GPL-3.0-or-later, and its parts artwork has
separate Creative Commons licensing. Keep the package copyright/license files
under `.local/sysroot/usr/share/doc/fritzing*`; consult these files for the exact
terms of the installed versions. Package versions, source links, provenance and
checksums are retained in the installation manifest. The installer does not
remove notices or relicense upstream code/artwork.

- Application: <https://github.com/fritzing/fritzing-app>
- Parts: <https://github.com/fritzing/fritzing-parts>
- Batch services: `src/fapplication.cpp` in the matching application source.
- Native archive/import implementation: `src/mainwindow/mainwindow.cpp`.

No prebuilt executable or complete upstream parts library is vendored in this
Git repository; the pinned packages are installed into the retained environment.
The verified native renders retain Fritzing's attribution. Generated
projects should carry any attribution required by the specific parts/artwork
they reuse.
