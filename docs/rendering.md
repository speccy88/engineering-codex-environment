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

## Animation acceptance and limits

Scripted animation, image-sequence rendering and H.264 MP4 export are now
acceptance tested in addition to stills:

```sh
scripts/run-blender.sh tests/test_blender/animation_acceptance.py
tests/test_blender/check_video.sh artifacts/animation
```

The small fixture rotates an asymmetric assembly by 110 degrees and separates
an upper piece by 5 mm. Blender CPU Cycles renders eight 128×128 PNGs at 8 fps,
with every pose inside the fixed camera frame. Tests verify distinct evaluated
transforms, nonblank frames, a changed silhouette and image differences, then
reopen `artifacts/animation/animation.blend` and verify its editable keyframes.
FFmpeg encodes the sequence to `animation.mp4`; ffprobe confirms H.264, eight
frames, 128×128 dimensions, 8 fps and 1.0-second duration. First/last decoded
video frames are checked for nonblank content and visible change. Detailed
evidence is in `render-result.json`, `ffprobe.json` and `video-result.json` in
the same directory.

This demonstrates scripted visualization animation, not assembly-joint
solving, physics, long-form encoding, audio mixing or GPU rendering. CPU Cycles
uses denoising disabled because this Debian build lacks OpenImageDenoise.
No second Python `bpy` wheel is needed or installed. Future animations may use
other dimensions/frame counts, but should validate their own complete output.
