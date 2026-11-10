"""Render an actual CAD STL for the README using Blender's CPU renderer.

scripts/run-blender.sh scripts/showcase-cad.py --input artifacts/freecad/bracket-wider.stl \
    --output docs/showcase/mechanical.png --scene artifacts/showcase/mechanical.blend
The mesh is imported unchanged; lighting and display material are illustrative.
"""

import argparse
import json
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


def point_at(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


def material(name, color, metal=0, roughness=.5):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = (*color, 1)
    node.inputs["Metallic"].default_value = metal
    node.inputs["Roughness"].default_value = roughness
    return mat


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scene", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.scene.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = .001
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = False
    scene.render.resolution_x, scene.render.resolution_y = 1280, 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = str(args.output.resolve())
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (.70, .78, .88, 1)
    background.inputs["Strength"].default_value = .45
    scene.view_settings.view_transform = "AgX"
    bpy.ops.wm.stl_import(filepath=str(args.input.resolve()))
    body = bpy.context.object
    body.name = "Imported parametric CAD bracket"
    body["source_stl"] = str(args.input)
    body.data.materials.append(material("Display material: blue aluminum", (.16, .33, .49), .55, .32))
    bpy.context.view_layer.update()
    corners = [body.matrix_world @ Vector(p) for p in body.bound_box]
    low = Vector(tuple(min(p[i] for p in corners) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in corners) for i in range(3)))
    target = (low + high) / 2
    dimensions = list(high-low)
    assert all(value > 0 for value in dimensions)

    bpy.ops.mesh.primitive_plane_add(size=2000, location=(target.x, target.y, low.z-.06))
    bpy.context.object.name = "Studio ground"
    bpy.context.object.data.materials.append(material("Studio gray", (.69, .74, .81), 0, .8))
    bpy.ops.object.camera_add(location=target + Vector((105, 135, 100)))
    camera = bpy.context.object
    camera.name = "CAD overview"
    camera.data.type = "ORTHO"
    point_at(camera, target)
    inverse = camera.rotation_euler.to_quaternion().inverted()
    projected = [inverse @ (p-target) for p in corners]
    width = max(p.x for p in projected)-min(p.x for p in projected)
    height = max(p.y for p in projected)-min(p.y for p in projected)
    camera.data.ortho_scale = max(width, height*1.6)*1.28
    scene.camera = camera
    bpy.context.view_layer.update()
    assert all(0 < p.x < 1 and 0 < p.y < 1 and p.z > 0 for p in
               [world_to_camera_view(scene, camera, c) for c in corners])
    for delta, power, size in [((-40, 65, 95), 180000, 80), ((80, -40, 60), 120000, 70), ((-80, -70, 40), 80000, 60)]:
        bpy.ops.object.light_add(type="AREA", location=target+Vector(delta))
        light = bpy.context.object
        light.data.energy = power
        light.data.shape = "DISK"
        light.data.size = size
        point_at(light, target)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.scene.resolve()))
    bpy.ops.render.render(write_still=True)
    print(json.dumps({"status":"passed", "blender":bpy.app.version_string,
                      "renderer":"Cycles CPU", "resolution":[1280,800],
                      "source_mesh_dimensions_mm":dimensions,
                      "mesh_geometry_modified":False,
                      "all_geometry_inside_frame":True, "output":str(args.output)}))


if __name__ == "__main__":
    main()
