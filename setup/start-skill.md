# Start the engineering workbench

Each cloud task already runs in an isolated environment. Use the existing checkout at `/workspace/engineering-codex-environment`; do not create a Git worktree unless the user explicitly requests one.

Read `AGENTS.md`. Run `bash setup/verify.sh --quick` from the checkout. This checks runtime wiring, not project engineering correctness. Installed applications, `.local/sysroot`, `.local/share/freerouting` and `.venvs` must come from the published filesystem snapshot; do not redownload/reinstall for each task. No persistent service or network port is needed.

Choose only the tools needed for the task, using `scripts/run-python.sh`, `run-freecad.sh [--gui]`, `run-kicad.sh`, `run-ngspice.sh`, `run-freerouting.sh`, or `run-blender.sh`. Native FreeCAD/KiCad and Blender use separate Python runtimes. The FreeCAD GUI wrapper starts a temporary Xvfb process for TechDraw and cleans it up. The optional KiCad IPC client requires a live KiCad IPC server and is not the automated SWIG runtime.

Read the relevant focused `skills/*/SKILL.md` and tool documentation. Preserve editable native source files and versioned interfaces. Run appropriate geometry checks, ERC/DRC, numerical assertions or rendering checks for the actual task; `bash setup/verify.sh --full` exercises the optional workbench acceptance fixtures.

For Fritzing requests, read `docs/fritzing.md`. Generate editable FZZ and reusable FZPZ components from explicit circuit/pin/footprint specifications, validate the saved project, then use the native exporter for all three views and Gerber/drill. Inspect the actual renders and report routing/layout limitations. Fritzing's batch exporter does not run native DRC or ERC; retain the separate geometric/connectivity evidence.

For unrelated projects use their own repositories. Independent and parallel cloud tasks exchange committed files through branches/PRs; never assume uncommitted changes are shared. Use the environment's existing Git authentication without extracting credentials.

If dependencies or wrappers change, test the change, run `bash setup/install.sh` when needed, update locks/inventory, and review/save/republish the environment. A repository commit alone does not update an already published filesystem snapshot.

For live IPC tasks, `scripts/run-kicad-ipc.sh tests/test_kicad/ipc_acceptance.py` demonstrates a temporary local KiCad editor/server under Xvfb and cleans it up; no server is started by ordinary quick checks. Core requests are tested with KiCad 9.0.2; API 10-only methods are not covered. Native fixed-joint and animation/video acceptance are included in the full suite.
