# Rendering runtime

`scripts/run-blender.sh script.py [arguments...]` runs `/usr/bin/blender` in
background mode with its own Python (Blender 4.3.2, Python 3.13.5 on this image).
It removes `PYTHONHOME` and `PYTHONPATH`; do not inject the general engineering
venv into Blender. It sets software OpenGL and uses two threads by default;
`ENGINEERING_THREADS` overrides the thread limit. A Python exception gives a
nonzero process exit status through `--python-exit-code 1`.

CPU Cycles rendering works without a desktop, display server, GPU or network
port. This Debian Blender build lacks OpenImageDenoise; select
`scene.cycles.use_denoising = False`. The acceptance test actually renders with
48 samples, reloads the PNG, checks transparent-background projected geometry
occupancy and foreground variation, then reopens the saved `.blend` scene to
verify editable geometry and camera data survived serialization.

Run from the repository:

```sh
scripts/run-blender.sh tests/test_blender/render_acceptance.py --output artifacts/blender
tests/test_blender/check_media.sh artifacts/blender
# Import a CAD-generated tessellation for visualization:
scripts/run-blender.sh tests/test_blender/render_acceptance.py \
  --output artifacts/blender-cad --stl artifacts/freecad/bracket.stl --import-only
```

The fixture uses millimetres (`scene.unit_settings.scale_length = 0.001`). Its
PCB, component and enclosure shapes are illustrative; they are not an
electrically checked board or a mechanically validated assembly. Use the
FreeCAD and KiCad acceptance evidence for engineering checks. Import the actual
project geometry when producing a project preview. STEP is not a native
Blender import format: use FreeCAD/OCP/CadQuery to tessellate into STL, or use a
supported mesh format. Preserve native `.FCStd`/KiCad sources alongside meshes.
The `--import-only` option omits the illustrative enclosure/PCB and renders only
the supplied mesh, with bounds checked and a camera fitted to include all
geometry. Without it, an imported mesh appears alongside the fixture.

Outputs are `assembly.blend` (native editable illustration),
`assembly-preview.png`, `assembly-preview.stl`, and `result.json` under the
selected output directory. `check_media.sh` exercises ImageMagick and FFmpeg
with real still-image transformations, validates the resulting dimensions,
and writes `media-result.json`. The native Blender scene reopens on desktop
Blender. Geometry alone is not a substitute for parametric CAD sources.

Blender supports scripted frame ranges, camera keyframes, exploded views, and
image sequences. For later animation tasks, set scene frame ranges and render
frames, then encode with the installed FFmpeg. This workbench acceptance
renders still images; video encoding and animations have not been acceptance
tested. No second Python `bpy` wheel is needed or installed.
