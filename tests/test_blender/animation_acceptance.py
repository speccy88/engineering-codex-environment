"""Render an editable eight-frame Blender animation for workbench acceptance.

This is a tiny engineering visualization fixture, not a mechanical motion or
joint-solver simulation. Execute through scripts/run-blender.sh.
"""

import argparse
import json
import math
import runpy
import statistics
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/animation")
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    out = Path(args.output).resolve()
    frames = out / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    # Remove only this acceptance fixture's prior frame files. The encoder must
    # not accidentally consume extra frames retained from an older run.
    for old_frame in frames.glob("frame_*.png"):
        old_frame.unlink()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    helpers = runpy.run_path(str(Path(__file__).with_name("render_acceptance.py")))
    material, box, point_at = (helpers[key] for key in ("material", "box", "point_at"))

    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.001
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.seed = 42
    scene.cycles.use_animated_seed = False
    scene.cycles.use_denoising = False
    scene.render.resolution_x = scene.render.resolution_y = 128
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True
    scene.render.fps = 8
    scene.frame_start, scene.frame_end = 1, 8
    scene.render.filepath = str(frames / "frame_")
    scene.world.color = (0.25, 0.25, 0.25)

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
    pivot = bpy.context.object
    pivot.name = "Animated assembly pivot"
    blue = material("Anodized base", (0.06, 0.25, 0.5), metallic=0.4)
    orange = material("Moving copper fixture", (0.8, 0.25, 0.03), metallic=0.5)
    base = box("Asymmetric base", (0, 0, 1.5), (40, 12, 3), blue, 0.6)
    post = box("Offset upright", (15, 0, 9), (5, 12, 15), orange, 0.5)
    cap = box("Exploded upper piece", (12, 0, 18), (12, 16, 2), blue, 0.4)
    for obj in (base, post, cap):
        obj.parent = pivot
    pivot.rotation_euler.z = 0
    pivot.keyframe_insert(data_path="rotation_euler", frame=1)
    pivot.rotation_euler.z = math.radians(110)
    pivot.keyframe_insert(data_path="rotation_euler", frame=8)
    cap.location.z = 18
    cap.keyframe_insert(data_path="location", frame=1)
    cap.location.z = 23
    cap.keyframe_insert(data_path="location", frame=8)

    bpy.ops.object.camera_add(location=(85, -110, 90))
    camera = bpy.context.object
    camera.name = "Fixed animation camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 65
    point_at(camera, (0, 0, 9))
    scene.camera = camera
    for location, energy, size in [
        ((20, -35, 90), 120000, 65),
        ((-60, 0, 45), 65000, 50),
    ]:
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.data.energy, light.data.size = energy, size
        point_at(light, (0, 0, 5))

    poses = []
    for frame in range(1, 9):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for obj in (base, post, cap):
            for corner in obj.bound_box:
                point = world_to_camera_view(
                    scene, camera, obj.matrix_world @ Vector(corner)
                )
                assert 0 < point.x < 1 and 0 < point.y < 1 and point.z > 0
        poses.append(
            {
                "frame": frame,
                "rotation_z_radians": pivot.rotation_euler.z,
                "cap_height_mm": cap.location.z,
            }
        )
    assert poses[-1]["rotation_z_radians"] - poses[0]["rotation_z_radians"] > 1.0
    assert poses[-1]["cap_height_mm"] - poses[0]["cap_height_mm"] > 4.9
    scene.frame_set(1)
    native = out / "animation.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(native))
    bpy.ops.render.render(animation=True)

    images = []
    frame_checks = []
    for frame in range(1, 9):
        path = frames / f"frame_{frame:04d}.png"
        image = bpy.data.images.load(str(path), check_existing=False)
        assert tuple(image.size) == (128, 128)
        pixels = list(image.pixels)
        mask = [value > 0.5 for value in pixels[3::4]]
        occupancy = sum(mask) / len(mask)
        foreground = [
            pixels[i] for i in range(0, len(pixels), 4) if pixels[i + 3] > 0.5
        ]
        variation = statistics.pstdev(foreground)
        assert 0.03 < occupancy < 0.8, occupancy
        assert variation > 0.03, variation
        images.append((pixels, mask))
        frame_checks.append(
            {
                "frame": frame,
                "geometry_fraction": occupancy,
                "foreground_stddev": variation,
            }
        )
    silhouette_change = sum(a != b for a, b in zip(images[0][1], images[-1][1])) / (
        128 * 128
    )
    image_difference = statistics.fmean(
        abs(a - b) for a, b in zip(images[0][0], images[-1][0])
    )
    assert silhouette_change > 0.02, silhouette_change
    assert image_difference > 0.01, image_difference
    bpy.ops.wm.open_mainfile(filepath=str(native))
    restored_pivot = bpy.data.objects["Animated assembly pivot"]
    restored_cap = bpy.data.objects["Exploded upper piece"]
    assert restored_pivot.animation_data.action is not None
    assert restored_cap.animation_data.action is not None
    assert bpy.context.scene.frame_end == 8 and bpy.context.scene.render.fps == 8
    bpy.context.scene.frame_set(8)
    assert restored_pivot.rotation_euler.z > 1 and restored_cap.location.z > 22.9
    result = {
        "status": "passed",
        "blender": bpy.app.version_string,
        "python": sys.version,
        "engine": "CYCLES",
        "device": "CPU",
        "samples": 12,
        "denoising": False,
        "resolution": [128, 128],
        "frame_count": 8,
        "fps": 8,
        "poses": poses,
        "frames": frame_checks,
        "first_last_silhouette_change": silhouette_change,
        "first_last_mean_absolute_pixel_difference": image_difference,
        "native_reopen_with_keyframes": True,
        "outputs": [str(native), str(frames)],
        "scope": "Scripted visualization animation; not an assembly-joint or physics simulation.",
    }
    (out / "render-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
