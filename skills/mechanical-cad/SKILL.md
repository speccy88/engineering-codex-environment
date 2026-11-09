---
name: mechanical-cad
description: Create or modify parametric mechanical parts and static assemblies using the workbench's isolated FreeCAD, CadQuery, or build123d runtimes, preserving native sources and checking geometry and exports.
---

# Mechanical CAD workflow

Read `AGENTS.md`, `docs/freecad.md`, and `docs/python.md`. Use the existing
checkout; a cloud task is already isolated. Do not create a Git worktree unless
the user requests it. These tools are independent: choose a suitable one for
the user's input and intended future editing, without requiring other domains.

1. Establish units, reference coordinate system, dimensions, clearances,
   material/manufacturing assumptions and mating interfaces from the task and
   existing source files. Record unresolved engineering assumptions. For work
   depending on another cloud task, use committed native files and versioned
   interface specifications; uncommitted work is not shared across tasks.
2. Preserve input native files and write a new revision unless an overwrite is
   requested. Use `scripts/run-freecad.sh model.py [arguments...]` for FreeCAD's
   Debian Python. Add `--gui` before the script when the script needs GUI-backed
   functions such as TechDraw; the wrapper uses a private Xvfb display when
   needed, with software graphics. Use
   `scripts/run-python.sh model.py` for the separate OCP/CadQuery/build123d venv.
   Do not mix their OCCT/Python shared libraries or add one runtime's packages
   to another's module path.
3. For editable FreeCAD work, use sketches with explicit dimensions and useful
   constraints, named dimensions or properties, and native PartDesign features
   where appropriate. Recompute after changes. Avoid replacing parametric
   feature histories with anonymous imported solids unless the task calls for
   direct solid editing. Keep source construction scripts with generated parts.
4. Check actual shape validity, positive volume, number of solids, expected
   dimensions and tolerances. Use interference/clearance checks for assemblies.
   Run a design-relevant modification and recompute to verify the intended
   editable dimension changes the correct features. Assembly workbench
   availability does not prove a joint solver or motion simulation works.
5. Save `.FCStd`, reopen it in a fresh document and verify the critical geometry
   again. Export STEP for exact neutral geometry and STL for meshes when needed;
   reimport exports and compare dimensions/volume within a justified tolerance.
   Check STL watertightness when required. A STEP export does not replace a
   parametric `.FCStd` file for future editing.
6. Keep derived previews/exports in a separate output directory. Report units,
   tests, command exit status, tool versions, native source and derivative
   paths. Package native sources and interface specifications for download.

Optional acceptance fixtures live under `tests/test_freecad/`,
`tests/test_cadquery/`, and `tests/test_build123d/`; they demonstrate APIs rather
than prescribe a project design. See the corresponding actual result files
before claiming a capability was validated in the current environment.

Grounded/fixed-joint acceptance is available with `scripts/run-freecad.sh tests/test_freecad/joint_acceptance.py`. It explicitly disturbs a part, calls the native Assembly solver, validates residuals, saves/reopens and repeats the solve. The wrapper exposes FreeCAD's official Ext/PySide shim. Other joint types, limits and dynamics require their own checks.
