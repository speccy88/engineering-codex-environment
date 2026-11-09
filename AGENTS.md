# Engineering workbench instructions

This repository is a reusable toolchain, not a home for unrelated engineering projects. The examples are optional acceptance fixtures, not a mandatory design workflow or parts catalog.

## Start and runtimes

- Each cloud task already has its own isolated workspace. Use the existing checkout; do not create Git worktrees unless explicitly requested.
- Run `bash setup/verify.sh --quick`. Use the installed snapshot; do not reinstall applications for each task. Run `setup/install.sh` only for repairs or dependency updates, then republish after validation.
- Use `scripts/run-python.sh script.py` for CadQuery/build123d/OCP/scientific work (Python 3.12).
- Use `scripts/run-freecad.sh [--gui] script.py` for native FreeCAD bindings (system Python 3.13). `--gui` initializes a private Xvfb display for TechDraw; no interactive desktop or network port is required.
- Use `scripts/run-kicad.sh python script.py` for the KiCad 9 legacy SWIG pcbnew API; `scripts/run-kicad.sh cli ...` for ERC/DRC and exports. Never import pcbnew from the geometry venv.
- The separate `.venvs/kicad-ipc` client is the newer official IPC API. It needs a running KiCad IPC server; it is not a headless substitute for pcbnew. See docs/eda.md.
- Use `scripts/run-blender.sh script.py ...` for Blender's embedded Python. Use `scripts/run-ngspice.sh` and `scripts/run-freerouting.sh` independently for simulation/routing.
- See `docs/toolchain.md`, per-tool docs and focused skills under `skills/`. Load only the relevant workflow.

## Engineering evidence

- Preserve editable `.FCStd`, `.kicad_sch`, `.kicad_pcb`, `.kicad_pro`, `.blend`, generator scripts, and dimension/interface specifications. STEP/STL and preview images are derived exports, not parametric source replacements.
- Validate solids, dimensions, constraints and roundtrip exports. Run real ERC and DRC after electrical changes and SES import. An autorouter result or an exported file alone proves neither electrical correctness nor manufacturability.
- Use numerical tolerances, units, simulation assertions and mesh/solid checks. Render in CPU/software mode when GPU hardware is unavailable. Inspect a rendered image as well as checking nonblank pixels.
- Capture commands, exit codes, tool versions, expected failures and unrun checks distinctly. Never mark a feature tested because its library imported.
- Do not overwrite supplied originals with derived exports unless asked. Place generated outputs in a separate directory. `scripts/export-project.sh SOURCE OUTPUT.zip` bundles sources and exports without caches; inspect the archive before sharing.
- This acceptance fixture does not establish suitability for production manufacture, safety-critical use, or arbitrary component designs; run checks appropriate to the user's actual project.

## Independent and parallel tasks

- Separate tasks do not share uncommitted files. Exchange committed native sources through project branches/PRs, plus versioned interface documents (units, origin, dimensions, connector positions, keepouts, layer stack and revisions).
- Define interfaces before parallel PCB/enclosure work. Merge and revalidate actual board/assembly revisions; a proxy solid must be identified as such.
- Keep workbench installation changes in this repository; keep project work in the user's chosen project repository. Never commit caches, installers, credentials or large temporary outputs.
