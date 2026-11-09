---
name: rendering
description: Render or revise still previews of mechanical models and engineering assemblies using the workbench's headless Blender runtime; preserve editable sources and verify nonblank images.
---

# Engineering still rendering

Use the existing checkout. Cloud tasks are already isolated; do not create a
Git worktree unless the user asks for one. Read `AGENTS.md` and
`docs/rendering.md` in this repository before rendering.

1. Locate the native engineering source and its units. Preserve `.FCStd`,
   KiCad files and existing `.blend` files. A mesh is a visualization derivative,
   not a replacement for a parametric source. Reuse project geometry instead of
   redrawing approximate geometry when an existing model is available.
2. For a STEP source, tessellate using FreeCAD or a compatible OCP/CadQuery
   runtime. Blender does not natively import STEP. Document tessellation units
   and tolerance; check bounds after importing STL or another supported mesh.
3. Write a Blender Python script and invoke
   `scripts/run-blender.sh path/to/script.py [script arguments...]`. It runs
   Blender's Python, clears conflicting Python environment paths, and converts
   Python failures into a nonzero process exit. Do not install a separate `bpy`
   wheel or import the engineering venv into Blender.
4. Use CPU Cycles (`scene.cycles.device = "CPU"`) and disable denoising on this
   Debian build, which lacks OpenImageDenoise. Set modest samples, explicit
   resolution, lights and camera. Software graphics and background mode require
   no persistent service or network port. Respect the thread limit in the
   wrapper; increase it only after considering concurrent tasks and resources.
5. Save the editable `.blend`, render a PNG, reload the image, and check its
   dimensions, nonblank pixel variation and reasonable projected model
   occupancy. Reopen the `.blend` to verify geometry and camera survived saving.
   Inspect the image visually when possible. A nonempty file alone is not a
   successful render.
6. Put derivatives in a separate output directory. Record the input revision,
   units, render engine, settings, commands, exit status and output paths.
   Package native sources with the previews for download when requested.

The optional fixture is executable with:

```sh
scripts/run-blender.sh tests/test_blender/render_acceptance.py --output artifacts/blender
tests/test_blender/check_media.sh artifacts/blender
```

The fixture is an illustration, not an electrically or mechanically validated
design. Use FreeCAD/KiCad checks for engineering claims. FFmpeg and ImageMagick
have been tested for still transformations; the workbench's Blender acceptance
does not establish animation or video export readiness.
