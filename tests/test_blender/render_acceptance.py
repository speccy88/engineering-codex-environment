"""A still-render acceptance test, executed by scripts/run-blender.sh.

Creates an editable PCB/enclosure illustration, optionally importing another
tool's STL. This is an illustration, not electrical/mechanical validation.
"""

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


def material(name, color, metallic=0.0, roughness=0.4):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1.0)
    result.use_nodes = True
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return result


def box(name, center, dimensions, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    result = bpy.context.object
    result.name = name
    result.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = result.modifiers.new("Edge radii", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        result.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    result.data.materials.append(mat)
    return result


def point_at(obj, target):
    obj.rotation_euler = (
        (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/blender")
    parser.add_argument("--stl", type=Path)
    parser.add_argument(
        "--import-only",
        action="store_true",
        help="Render only the supplied STL; omit the illustrative fixture",
    )
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.001  # geometry coordinates in millimetres
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 48
    # Debian's Blender build does not include OpenImageDenoise. CPU path tracing
    # is supported; select it directly rather than relying on GPU denoisers.
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 640
    scene.render.resolution_y = 480
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True
    scene.render.filepath = str(out / "assembly-preview.png")
    scene.world.color = (0.25, 0.25, 0.25)

    case = material("Enclosure anodized aluminum", (0.11, 0.18, 0.24), metallic=0.65)
    pcb = material("PCB soldermask", (0.015, 0.25, 0.08))
    copper = material("Copper pads", (0.7, 0.4, 0.06), metallic=0.8)
    component = material("Component body", (0.08, 0.08, 0.09))
    # Separate editable pieces keep the example simple and reveal the interior.
    box("Enclosure base 64x44x3 mm", (0, 0, 1.5), (64, 44, 3), case, 1.0)
    box("Rear wall", (0, 21, 9), (64, 2, 15), case, 0.5)
    box("Left wall", (-31, 0, 9), (2, 40, 15), case, 0.5)
    box("Right wall", (31, 0, 9), (2, 40, 15), case, 0.5)
    box("PCB illustration 50x30x1.6 mm", (0, 0, 8), (50, 30, 1.6), pcb, 0.3)
    for x in (-20, 20):
        for y in (-10, 10):
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=24, radius=1.8, depth=3.7, location=(x, y, 5.35)
            )
            bpy.context.object.name = "Mounting standoff"
            bpy.context.object.data.materials.append(copper)
    for x in (-10, 10):
        box("Resistor illustration", (x, 0, 10), (7, 3, 2.4), component, 0.4)
        for pad_x in (x - 4.5, x + 4.5):
            box("Pad illustration", (pad_x, 0, 8.85), (2, 3.3, 0.15), copper)

    imported = None
    imported_dimensions = None
    fixture_meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    assert not args.import_only or args.stl, "--import-only requires --stl"
    if args.stl:
        assert args.stl.is_file(), args.stl
        bpy.ops.wm.stl_import(filepath=str(args.stl.resolve()))
        imported = bpy.context.object
        imported.name = "Imported native-CAD STL preview"
        imported.data.materials.append(case)
        imported.location = (0, 45, 0)
        bpy.context.view_layer.update()
        imported_dimensions = list(imported.dimensions)
        assert all(math.isfinite(value) and value > 0 for value in imported_dimensions)
        assert len(imported.data.polygons) > 0
        if args.import_only:
            for obj in fixture_meshes:
                bpy.data.objects.remove(obj, do_unlink=True)
            imported.location = (0, 0, 0)

    bpy.context.view_layer.update()
    corners = [
        obj.matrix_world @ Vector(corner)
        for obj in scene.objects
        if obj.type == "MESH"
        for corner in obj.bound_box
    ]
    minimum = Vector(tuple(min(p[i] for p in corners) for i in range(3)))
    maximum = Vector(tuple(max(p[i] for p in corners) for i in range(3)))
    target = (minimum + maximum) / 2
    bpy.ops.object.camera_add(location=target + Vector((100, -125, 110)))
    camera = bpy.context.object
    camera.name = "Engineering overview camera"
    camera.data.type = "ORTHO"
    point_at(camera, target)
    inverse_rotation = camera.rotation_euler.to_quaternion().inverted()
    projected = [inverse_rotation @ (p - target) for p in corners]
    width = max(p.x for p in projected) - min(p.x for p in projected)
    height = max(p.y for p in projected) - min(p.y for p in projected)
    aspect = scene.render.resolution_x / scene.render.resolution_y
    camera.data.ortho_scale = max(width, height * aspect) * 1.2
    scene.camera = camera
    bpy.context.view_layer.update()
    framing = [world_to_camera_view(scene, camera, p) for p in corners]
    assert all(0 < p.x < 1 and 0 < p.y < 1 and p.z > 0 for p in framing), (
        "Geometry outside render frame"
    )
    for loc, power, size in [((20, -35, 90), 120000, 65), ((-60, 0, 45), 65000, 50)]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.data.energy = power
        light.data.shape = "DISK"
        light.data.size = size
        point_at(light, (0, 0, 0))

    minimum_meshes = 1 if args.import_only else 10
    assert len([o for o in scene.objects if o.type == "MESH"]) >= minimum_meshes
    blend = out / "assembly.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.render.render(write_still=True)
    png = out / "assembly-preview.png"
    image = bpy.data.images.load(str(png), check_existing=False)
    assert tuple(image.size) == (640, 480), tuple(image.size)
    pixels = list(image.pixels)
    alpha = pixels[3::4]
    occupancy = sum(a > 0.5 for a in alpha) / len(alpha)
    foreground = [pixels[i] for i in range(0, len(pixels), 4) if pixels[i + 3] > 0.5]
    variation = statistics.pstdev(foreground)
    assert 0.06 < occupancy < 0.85, (
        f"Unexpected projected geometry occupancy: {occupancy}"
    )
    assert variation > 0.04, f"Blank/flat foreground: {variation}"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    # Reopen native scene to check its geometry and camera survived serialization.
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    assert bpy.context.scene.camera is not None
    assert sum(o.type == "MESH" for o in bpy.context.scene.objects) >= minimum_meshes
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        obj.select_set(obj.type == "MESH")
    stl = out / "assembly-preview.stl"
    bpy.ops.wm.stl_export(filepath=str(stl), export_selected_objects=True)
    assert stl.stat().st_size > 1000
    result = {
        "status": "passed",
        "blender": bpy.app.version_string,
        "python": sys.version,
        "engine": "CYCLES",
        "device": "CPU",
        "samples": 48,
        "denoising": False,
        "resolution": [640, 480],
        "foreground_fraction": occupancy,
        "foreground_red_stddev": variation,
        "native_reopen": True,
        "imported_stl": str(args.stl) if args.stl else None,
        "imported_dimensions_mm": imported_dimensions,
        "all_geometry_inside_frame": True,
        "illustrative_fixture_included": not args.import_only,
        "outputs": [str(blend), str(png), str(stl)],
        "scope": "Rendering illustration only; engineering validation belongs to CAD/EDA tests.",
    }
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
