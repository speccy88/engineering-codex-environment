# Independent engineering tasks

The workbench supplies tools, not a mandatory design process, circuit catalog
or project architecture. Start only the runtimes a task needs. Examples and
acceptance fixtures demonstrate capabilities; unrelated projects belong in
their own repositories with their own requirements and native source files.

From an existing checkout, read `AGENTS.md` and run
`bash setup/verify.sh --quick`. Published environments retain applications,
venvs and local native packages. Do not reinstall the full toolchain or create
a Git worktree for each task: cloud tasks already have isolated workspaces.
Create a worktree only when explicitly requested. Choose the relevant focused
skill under `skills/` and use its wrapper/runtime.

| Task | Typical independent entry point | Relevant validation |
| --- | --- | --- |
| Create/review a circuit without a PCB | KiCad schematic CLI, SKiDL or ngspice | Schematic ERC/connectivity, numerical simulation assertions as appropriate |
| Make a board from an existing schematic | KiCad pcbnew and CLI | Pin/net parity, board outline/placement, DRC/unconnected checks; optionally DSN→Freerouting→SES→DRC |
| Modify an existing PCB | Load native `.kicad_pcb` and matching project/schematic | Preserve rules and native sources; rerun affected DRC/parity and regenerate exports |
| Create a part, bracket or enclosure | FreeCAD, CadQuery, build123d or OpenSCAD | Dimensions, shape validity, tolerances, editable-source reopen and export roundtrip |
| Enclose an existing PCB | Read verified PCB STEP plus a versioned interface specification | Units/origin, connector access, mounting constraints, clearance and interference |
| Make technical drawings | FreeCAD/TechDraw with `run-freecad.sh --gui` | Dimension references/values, page visibility, export inspection and native reopen |
| Render an existing assembly | Convert CAD geometry to mesh, use Blender wrapper | Bounds/units, camera framing, nonblank image and editable `.blend` reopening |
| Run a supplied SPICE netlist | `run-ngspice.sh -b circuit.cir` | Solver completion, numerical tolerances, time/frequency coverage and units |
| Repair/review existing files | Open native files with the relevant tool | Reproduce the issue, retain originals, apply scoped edits and rerun meaningful checks |

No simulation is required merely to render a supplied assembly, and no PCB is
required merely to design a circuit. Select checks that can catch failures in
the actual task. A passing workbench fixture does not establish correctness of
a new design. Distinguish a checked result, a merely generated artifact and an
untested feature in the delivery notes.

## Continuing previous work and parallel tasks

Independent Codex Cloud tasks do not share uncommitted filesystem changes or
live processes. Dependencies between tasks must use committed native sources,
branches/PRs, or deliberately exported files available to the next task.

1. Commit a versioned requirements/interface document before splitting work.
   Identify units, axes/origin, board outline, maximum component envelopes,
   mounting-hole centers/diameters, connector keepouts, clearance/tolerance
   assumptions, file names and source revision as relevant.
2. Give each task an explicit owned component and its input commit. Circuit,
   board, enclosure and visualization work can proceed separately when their
   interfaces are defined. Use branches and pull requests to review their
   native sources, scripts and validation evidence.
3. Avoid editing the same native document concurrently. Binary CAD files are
   often unsuitable for line-based merging; choose an owner, exchange linked
   subcomponents, or regenerate from reviewed parametric source. Resolve
   interface changes explicitly instead of silently moving another component.
4. At integration, record each input commit, verify units/origins, reopen the
   native assembly and run actual connectivity/clearance/geometry checks.
   Regenerate derived previews/exports from those inputs. Do not treat a
   rendered image as evidence of electrical or mechanical validity.
5. Commit approved native project sources to the project repository and provide
   a download bundle containing sources, required local assets, neutral exports
   and concise validation results. Avoid committing package caches, temporary
   installers or the workbench's runtime directories.

The workbench repository itself holds environment configuration, tests,
examples and instructions. Its dependency or wrapper changes require the
review/install/test/republish process in
[cloud-environment.md](cloud-environment.md). Committing project files does not
automatically update the published environment snapshot.

Focused references: [toolchain](toolchain.md), [formats](file-formats.md),
[FreeCAD](freecad.md), [EDA](eda.md), [Python/simulation](python.md),
[rendering](rendering.md).
