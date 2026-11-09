---
name: electronic-circuits
description: Create, modify, or review editable electronic schematics, netlists, and bills of materials using KiCad or SKiDL; invoke for circuit work that may or may not need a PCB.
---

Use only the tools the task requires. A circuit-only request does not imply a PCB,
mechanical enclosure, autorouting, rendering, or a fixed component catalog.

1. Inspect supplied native sources and interface requirements: supply rails,
   ground, signal levels, loading, connector pinout and applicable tolerances.
   Preserve the source files; create a separate revision unless overwrite was
   requested. Choose components and values for this task.
2. Use `scripts/run-kicad.sh` for KiCad CLI and
   `scripts/run-kicad.sh python script.py` for Debian-compatible pcbnew. SKiDL
   is in `scripts/run-python.sh`; select SKiDL's `KICAD9` explicitly. A netlist
   alone is not an editable schematic. For programmable KiCad9 schematic
   structure, inspect `tests/test_kicad/schematic.py` as an optional example.
3. Save native `.kicad_sch` and `.kicad_pro`, with embedded official symbols and
   portable footprint references. Document component sources and pin mapping.
4. Run real ERC with all severities and failure on violations:
   `scripts/run-kicad.sh sch erc --severity-all --exit-code-violations circuit.kicad_sch`.
   Investigate each result. Do not silently exclude findings to produce a pass.
5. Export a netlist and independently compare expected pin-to-net connections;
   a zero ERC count cannot detect every circuit logic error. Export a BOM and a
   PDF/SVG preview if useful. Simulate the circuit when the decision requires it;
   follow `skills/circuit-simulation/SKILL.md` then.
6. Report checks executed, values/tolerances assumed, findings, and paths to
   editable sources and derived outputs. Preserve previous native revisions in
   version control when another task will depend on them.

Read `docs/eda.md` for runtime separation and checked command examples. The
newer official IPC client uses `scripts/run-kicad-ipc.sh` and requires a live
KiCad GUI editor with IPC enabled; its core live read transactions have now been tested against KiCad 9.0.2
using `tests/test_kicad/ipc_acceptance.py`. API 10-only client methods remain
outside that validation. Never assume IPC and SWIG APIs are interchangeable.
