---
name: pcb-layout
description: Generate, modify, route, or review editable KiCad PCB projects, and export checked manufacturing files or assembled PCB geometry.
---

1. Inspect the native schematic, board, netlist, stackup, connector pinout,
   mounting interfaces, keepouts and fabrication constraints. Work on the
   existing board when asked to modify it. Do not infer missing mechanical
   interfaces from an image. Circuit design and enclosure work are independent.
2. Use `scripts/run-kicad.sh python layout.py` for KiCad9 pcbnew SWIG automation.
   Preserve native `.kicad_pcb`, `.kicad_sch` and `.kicad_pro`. Set footprint
   library IDs and symbol UUID paths, assign every pad net, and preserve useful
   placements/constraints. Independently compare pin connectivity to schematic.
3. For optional autorouting, export DSN from the source board using
   `pcbnew.ExportSpecctraDSN`, call
   `scripts/run-freerouting.sh -de board.dsn -do board.ses -mp 8 -mt 2`, then
   import SES into that exact board via `pcbnew.ImportSpecctraSES`. The wrapper
   uses Java21/Freerouting2.1 with GUI and analytics disabled. Inspect routing
   rather than treating a successful router exit as an engineering pass.
4. Run DRC on the final saved board:
   `scripts/run-kicad.sh pcb drc --severity-all --schematic-parity --exit-code-violations board.kicad_pcb`.
   Check violations, unconnected items and parity separately; do not silently
   exclude errors. Reopen the native board and confirm expected footprints,
   tracks/vias and outline dimensions. Use appropriate manufacturing rules.
5. Export Gerber, Excellon drills and BOM as requested. For STEP export, use the
   official 3D model library through the wrapper; independently reopen STEP with
   OCP/FreeCAD, validate geometry and bounds, and verify component bodies were
   not omitted. Neutral STEP does not replace editable KiCad sources.
6. Package native files, declared interfaces and required dependencies with
   derived manufacturing outputs and clear check reports. Avoid committing
   bulky temporary artifacts. Across cloud tasks use committed native sources
   and versioned interfaces, since uncommitted task workspaces are independent.

The optional divider acceptance in `tests/test_kicad/board.py` demonstrates DSN,
SES, ERC/DRC, pin connectivity and exports. Its component choices and dimensions
are test data, not a required architecture. Read `docs/eda.md` for runtime details.
