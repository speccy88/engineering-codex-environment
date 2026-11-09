# Optional PCB and enclosure integration

Run from the checkout:

```sh
scripts/run-kicad.sh python tests/test_kicad/board.py
scripts/run-python.sh tests/test_kicad/step_geometry.py
scripts/run-freecad.sh tests/test_freecad/assembly.py artifacts/eda/divider.step
scripts/run-blender.sh tests/test_blender/render_acceptance.py \
  --output artifacts/assembly-preview --stl artifacts/assembly/pcb-enclosure.stl --import-only
```

The actual KiCad STEP contains22 valid solids on a40x25mm board. The native FreeCAD document links it to a parametric50x35x18mm open enclosure. The test checks23 valid exported solids and zero measured interference. It uses the native Assembly object with static placements; joint solving is untested. This fixture has no mounting supports or connector openings and is not a production enclosure.

Editable sources: the schematic/PCB generators, generated native KiCad project, `tests/test_freecad/assembly.py`, generated `artifacts/assembly/pcb-enclosure.FCStd`, and `artifacts/assembly-preview/assembly.blend`. Neutral STEP/STL supplement these sources.

For real parallel tasks, commit the native board and interface: mm units, XY origin, outline,1.6mm thickness, component height/keepouts, connectors/mounts and revision. Design from that exact revision and repeat checks after integration.
