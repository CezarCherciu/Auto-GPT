"""Generate a simplified 3D model of Mysore Palace in Blender.

Run with Blender UI:
    blender --python blender/mysore_palace.py

Or headless to write a .blend file:
    blender --background --python blender/mysore_palace.py -- --output mysore_palace.blend

The script also runs under the `bpy` pip package (python -m) for headless builds.
"""

from __future__ import annotations

import math
import os
import sys

import bpy
from mathutils import Vector


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.meshes):
        bpy.data.meshes.remove(block)
    for block in list(bpy.data.materials):
        bpy.data.materials.remove(block)
    for block in list(bpy.data.curves):
        bpy.data.curves.remove(block)


def make_material(name: str, color, metallic: float = 0.0, roughness: float = 0.6):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metallic
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = roughness
    return mat


def assign(obj, material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(material)


# ---------- Primitives --------------------------------------------------------


def add_cube(name, location, scale, material):
    bpy.ops.mesh.primitive_cube_add(size=2, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(obj, material)
    return obj


def add_cylinder(name, location, radius, depth, material, verts=32):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, location=location, vertices=verts
    )
    obj = bpy.context.active_object
    obj.name = name
    assign(obj, material)
    return obj


def add_cone(name, location, r1, r2, depth, material, verts=32):
    bpy.ops.mesh.primitive_cone_add(
        radius1=r1, radius2=r2, depth=depth, location=location, vertices=verts
    )
    obj = bpy.context.active_object
    obj.name = name
    assign(obj, material)
    return obj


def add_sphere(name, location, scale, material, segments=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings, location=location
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(obj, material)
    return obj


def add_torus(name, location, major_r, minor_r, material):
    bpy.ops.mesh.primitive_torus_add(
        location=location, major_radius=major_r, minor_radius=minor_r,
        major_segments=48, minor_segments=12,
    )
    obj = bpy.context.active_object
    obj.name = name
    assign(obj, material)
    return obj


# ---------- Compound shapes ---------------------------------------------------


def onion_dome(name, base_center, radius, material_dome, material_spire, spire_color):
    """Build an onion dome (red/gold) sitting on a small drum, topped by a spire."""
    cx, cy, cz = base_center
    # Drum (cylindrical base)
    drum_h = radius * 0.45
    drum = add_cylinder(
        f"{name}_drum", (cx, cy, cz + drum_h / 2),
        radius=radius * 1.05, depth=drum_h,
        material=make_material("StoneCream", (0.93, 0.87, 0.72), roughness=0.7),
    )
    # Bulbous dome: scaled sphere with a pinch at the top via additional small sphere
    dome = add_sphere(
        f"{name}_dome",
        (cx, cy, cz + drum_h + radius * 0.75),
        scale=(radius, radius, radius * 1.15),
        material=material_dome,
    )
    # Neck between dome and spire
    neck = add_cylinder(
        f"{name}_neck",
        (cx, cy, cz + drum_h + radius * 1.85),
        radius=radius * 0.22, depth=radius * 0.35,
        material=material_spire,
    )
    # Small bulb
    bulb = add_sphere(
        f"{name}_bulb",
        (cx, cy, cz + drum_h + radius * 2.15),
        scale=(radius * 0.28, radius * 0.28, radius * 0.32),
        material=material_spire,
    )
    # Spire
    spire = add_cone(
        f"{name}_spire",
        (cx, cy, cz + drum_h + radius * 2.65),
        r1=radius * 0.07, r2=0.0, depth=radius * 0.9,
        material=material_spire,
    )
    # Finial ball
    finial = add_sphere(
        f"{name}_finial",
        (cx, cy, cz + drum_h + radius * 3.20),
        scale=(radius * 0.09,) * 3,
        material=spire_color,
    )
    return [drum, dome, neck, bulb, spire, finial]


def corner_tower(name, xy, footprint, height, dome_color, stone, gold):
    """A square tower with a red onion dome on top."""
    x, y = xy
    w, d = footprint
    parts = []
    # Main tower body (two tiers)
    parts.append(add_cube(
        f"{name}_body1", (x, y, height * 0.35),
        scale=(w / 2, d / 2, height * 0.35), material=stone,
    ))
    parts.append(add_cube(
        f"{name}_body2", (x, y, height * 0.80),
        scale=(w / 2 * 0.88, d / 2 * 0.88, height * 0.10), material=stone,
    ))
    # Cornice torus around the top
    parts.append(add_torus(
        f"{name}_cornice", (x, y, height * 0.92),
        major_r=min(w, d) * 0.48, minor_r=min(w, d) * 0.05,
        material=make_material("TrimRed", (0.55, 0.10, 0.10)),
    ))
    # Onion dome sits on top
    parts.extend(onion_dome(
        f"{name}_dome", (x, y, height * 0.94),
        radius=min(w, d) * 0.42,
        material_dome=dome_color,
        material_spire=stone,
        spire_color=gold,
    ))
    return parts


def arcade_section(name, x0, x1, y, z0, z1, arch_count, stone, shadow):
    """A colonnaded arcade with tall pointed arches across the facade."""
    width = x1 - x0
    bay = width / arch_count
    arch_h = (z1 - z0) * 0.78
    pier_w = bay * 0.22
    depth = 1.8

    # Solid upper band (above the arches)
    add_cube(
        f"{name}_upper", ((x0 + x1) / 2, y, z0 + arch_h + (z1 - z0 - arch_h) / 2),
        scale=(width / 2, depth / 2, (z1 - z0 - arch_h) / 2), material=stone,
    )
    # Piers and arch spandrels
    for i in range(arch_count + 1):
        x = x0 + i * bay
        add_cube(
            f"{name}_pier_{i}", (x, y, z0 + arch_h / 2),
            scale=(pier_w / 2, depth / 2, arch_h / 2), material=stone,
        )
    # Shadowed openings (dark backdrop so arches read visually)
    for i in range(arch_count):
        x = x0 + (i + 0.5) * bay
        add_cube(
            f"{name}_opening_{i}", (x, y + depth * 0.55, z0 + arch_h / 2),
            scale=((bay - pier_w) / 2, 0.2, arch_h / 2 - 0.2), material=shadow,
        )
        # Pointed arch top: use a triangular prism via scaled cube rotated 45
        bpy.ops.mesh.primitive_cube_add(
            size=2, location=(x, y, z0 + arch_h - 0.1),
        )
        top = bpy.context.active_object
        top.name = f"{name}_arch_{i}"
        top.scale = ((bay - pier_w) / 2, depth / 2, (bay - pier_w) / 2)
        top.rotation_euler = (0, math.radians(45), 0)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        assign(top, stone)


def roofline_domes(name, x0, x1, y, z_top, count, color, stone, gold):
    """A row of small red onion domes along the roof parapet."""
    for i in range(count):
        t = (i + 0.5) / count
        x = x0 + (x1 - x0) * t
        onion_dome(
            f"{name}_{i}", (x, y, z_top),
            radius=0.9, material_dome=color, material_spire=stone, spire_color=gold,
        )


def central_tower(name, xy, base_size, height, stone, gold, red):
    x, y = xy
    w, d = base_size
    # Stepped base tiers
    add_cube(f"{name}_t1", (x, y, 0.5 * height * 0.25),
             scale=(w / 2, d / 2, height * 0.25 / 2), material=stone)
    add_cube(f"{name}_t2", (x, y, height * 0.25 + height * 0.10),
             scale=(w * 0.42, d * 0.42, height * 0.10), material=stone)
    add_cube(f"{name}_t3", (x, y, height * 0.45 + height * 0.08),
             scale=(w * 0.34, d * 0.34, height * 0.08), material=stone)
    # Octagonal drum
    add_cylinder(
        f"{name}_drum", (x, y, height * 0.61),
        radius=min(w, d) * 0.30, depth=height * 0.12,
        material=stone, verts=8,
    )
    # Gold dome
    add_sphere(
        f"{name}_dome", (x, y, height * 0.75),
        scale=(min(w, d) * 0.34, min(w, d) * 0.34, min(w, d) * 0.42),
        material=gold,
    )
    # Upper drum + small dome (lantern)
    add_cylinder(
        f"{name}_lantern", (x, y, height * 0.86),
        radius=min(w, d) * 0.14, depth=height * 0.08,
        material=stone, verts=8,
    )
    add_sphere(
        f"{name}_lantern_dome", (x, y, height * 0.93),
        scale=(min(w, d) * 0.16, min(w, d) * 0.16, min(w, d) * 0.18),
        material=gold,
    )
    # Tall spire on top
    add_cone(f"{name}_spire", (x, y, height * 1.02),
             r1=min(w, d) * 0.05, r2=0, depth=height * 0.12, material=gold)
    add_sphere(f"{name}_finial", (x, y, height * 1.10),
               scale=(0.25, 0.25, 0.25), material=gold)
    # Red trim ring
    add_torus(f"{name}_ring", (x, y, height * 0.67),
              major_r=min(w, d) * 0.36, minor_r=0.18, material=red)


def side_dome_tower(name, xy, base_size, height, stone, gold, red):
    x, y = xy
    w, d = base_size
    add_cube(f"{name}_t1", (x, y, height * 0.30),
             scale=(w / 2, d / 2, height * 0.30), material=stone)
    add_cube(f"{name}_t2", (x, y, height * 0.72),
             scale=(w * 0.40, d * 0.40, height * 0.10), material=stone)
    add_cylinder(f"{name}_drum", (x, y, height * 0.86),
                 radius=min(w, d) * 0.34, depth=height * 0.06,
                 material=stone, verts=16)
    add_sphere(f"{name}_dome", (x, y, height * 0.96),
               scale=(min(w, d) * 0.38, min(w, d) * 0.38, min(w, d) * 0.45),
               material=gold)
    add_cone(f"{name}_spire", (x, y, height * 1.12),
             r1=0.12, r2=0, depth=height * 0.12, material=gold)
    add_torus(f"{name}_ring", (x, y, height * 0.89),
              major_r=min(w, d) * 0.40, minor_r=0.15, material=red)


# ---------- Scene -------------------------------------------------------------


def build_palace() -> None:
    # Materials
    stone      = make_material("StoneCream",   (0.93, 0.87, 0.72), roughness=0.7)
    stone_warm = make_material("StoneWarm",    (0.85, 0.76, 0.55), roughness=0.75)
    red_dome   = make_material("DomeRed",      (0.58, 0.10, 0.10), roughness=0.5)
    gold       = make_material("Gold",         (0.83, 0.68, 0.22), metallic=0.9, roughness=0.3)
    brown_gold = make_material("BronzeGold",   (0.55, 0.42, 0.18), metallic=0.8, roughness=0.35)
    shadow     = make_material("ArcadeShadow", (0.05, 0.04, 0.04), roughness=0.9)
    grass      = make_material("Grass",        (0.32, 0.48, 0.22), roughness=0.9)
    brick      = make_material("Brick",        (0.55, 0.28, 0.20), roughness=0.9)
    sky        = make_material("Sky",          (0.60, 0.64, 0.70), roughness=1.0)

    # Overall footprint (wide facade along +X)
    WIDTH = 80.0
    DEPTH = 18.0
    BASE_H = 10.0
    x0, x1 = -WIDTH / 2, WIDTH / 2
    y_front = -DEPTH / 2

    # Ground: plaza (brick) + flanking grass
    add_cube("PlazaBrick", (0, DEPTH, 0.05),
             scale=(8, 25, 0.05), material=brick)
    add_cube("GrassL", (-20, DEPTH, 0.03),
             scale=(15, 25, 0.03), material=grass)
    add_cube("GrassR", (20, DEPTH, 0.03),
             scale=(15, 25, 0.03), material=grass)
    add_cube("Ground", (0, DEPTH, 0.01),
             scale=(80, 60, 0.01), material=stone_warm)

    # Main rectangular facade mass (behind arcade)
    add_cube("MainBody", (0, 0, BASE_H / 2),
             scale=(WIDTH / 2, DEPTH / 2, BASE_H / 2), material=stone)

    # Upper set-back story with the red ornate band
    add_cube("UpperBand", (0, 0, BASE_H + 1.2),
             scale=(WIDTH / 2 * 0.98, DEPTH / 2 * 0.9, 1.2), material=red_dome)
    add_cube("UpperWall", (0, 0, BASE_H + 3.4),
             scale=(WIDTH / 2 * 0.9, DEPTH / 2 * 0.85, 1.1), material=stone)

    # Arcade across the front (ground floor colonnade with pointed arches)
    arcade_section(
        "Arcade",
        x0=x0 + 10, x1=x1 - 10,
        y=y_front - 0.2,
        z0=0.0, z1=BASE_H * 0.75,
        arch_count=11,
        stone=stone, shadow=shadow,
    )

    # Upper balcony trim (red band above arcade arches)
    add_cube("BalconyBand",
             (0, y_front - 0.2, BASE_H * 0.78),
             scale=((WIDTH - 20) / 2, 0.4, 0.4),
             material=red_dome)

    # Four corner towers with red onion domes
    tower_fp = (8.0, 8.0)
    corner_tower("TowerNW", (x0 + 4, -DEPTH / 2 + 2), tower_fp, 16.0, red_dome, stone, gold)
    corner_tower("TowerNE", (x1 - 4, -DEPTH / 2 + 2), tower_fp, 16.0, red_dome, stone, gold)
    corner_tower("TowerSW", (x0 + 4,  DEPTH / 2 - 2), tower_fp, 16.0, red_dome, stone, gold)
    corner_tower("TowerSE", (x1 - 4,  DEPTH / 2 - 2), tower_fp, 16.0, red_dome, stone, gold)

    # Two intermediate side towers with gold-brown domes
    side_dome_tower("SideL", (-18, 0), (8, 8), 18.0, stone, brown_gold, red_dome)
    side_dome_tower("SideR", ( 18, 0), (8, 8), 18.0, stone, brown_gold, red_dome)

    # Central tall tower with gold dome + spire
    central_tower("Central", (0, 0), (14, 14), 26.0, stone, gold, red_dome)

    # Row of small red onion domes along the front parapet
    roofline_domes("ParapetDomes",
                   x0=x0 + 14, x1=x1 - 14,
                   y=y_front + 1.0,
                   z_top=BASE_H + 2.0,
                   count=9, color=red_dome, stone=stone, gold=gold)

    # Camera — placed well back, aimed at the central tower mid-height
    cam_data = bpy.data.cameras.new("PalaceCam")
    cam = bpy.data.objects.new("PalaceCam", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = Vector((0, -110, 22))
    cam_target = bpy.data.objects.new("CamTarget", None)
    cam_target.location = (0, 0, 13)
    bpy.context.collection.objects.link(cam_target)
    track = cam.constraints.new(type="TRACK_TO")
    track.target = cam_target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    cam_data.lens = 50
    bpy.context.scene.camera = cam

    # Sun light
    light_data = bpy.data.lights.new("Sun", type="SUN")
    light_data.energy = 4.0
    light_data.color = (1.0, 0.96, 0.88)
    light = bpy.data.objects.new("Sun", light_data)
    light.location = (30, -40, 60)
    light.rotation_euler = (math.radians(50), math.radians(15), math.radians(30))
    bpy.context.collection.objects.link(light)

    # Sky / world background
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.55, 0.60, 0.68, 1.0)
        bg.inputs[1].default_value = 1.0

    # Render settings
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {
        e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
    } else "CYCLES"
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 900
    scene.render.film_transparent = False


def parse_output_path() -> str:
    default = os.path.join(os.path.dirname(__file__), "mysore_palace.blend")
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
        if "--output" in args:
            return args[args.index("--output") + 1]
    return default


def main() -> None:
    clear_scene()
    build_palace()
    out = parse_output_path()
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print(f"Saved Blender file to: {out}")


if __name__ == "__main__":
    main()
