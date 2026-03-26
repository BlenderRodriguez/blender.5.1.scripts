import math

import bpy
from mathutils import Vector


PREFIX = "CodexNegLight"
COLLECTION_NAME = f"{PREFIX}_Demo"


def purge_previous_setup():
    for obj in list(bpy.data.objects):
        if obj.name.startswith(PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)

    for collection in list(bpy.data.collections):
        if collection.name.startswith(PREFIX):
            bpy.data.collections.remove(collection)

    for datablocks in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.curves,
    ):
        for datablock in list(datablocks):
            if datablock.name.startswith(PREFIX) and datablock.users == 0:
                datablocks.remove(datablock)


def ensure_collection(scene):
    collection = bpy.data.collections.new(COLLECTION_NAME)
    scene.collection.children.link(collection)
    return collection


def move_to_collection(obj, collection):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def look_at(obj, target):
    direction = target - obj.location
    rotation = direction.to_track_quat("-Z", "Y")
    obj.rotation_euler = rotation.to_euler()


def create_principled_material(name, base_color, roughness=0.4, metallic=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (*base_color, 1.0)
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Metallic"].default_value = metallic
    return material


def assign_material(obj, material):
    obj.data.materials.clear()
    obj.data.materials.append(material)


def create_floor(collection):
    bpy.ops.mesh.primitive_plane_add(size=18.0, location=(0.0, 0.0, 0.0))
    obj = bpy.context.active_object
    obj.name = f"{PREFIX}_Floor"
    move_to_collection(obj, collection)
    assign_material(
        obj,
        create_principled_material(
            f"{PREFIX}_Floor_Mat",
            base_color=(0.13, 0.135, 0.15),
            roughness=0.85,
        ),
    )
    return obj


def create_sphere(collection, name, location, color):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.72, location=location)
    obj = bpy.context.active_object
    obj.name = name
    move_to_collection(obj, collection)
    assign_material(
        obj,
        create_principled_material(f"{name}_Mat", base_color=color, roughness=0.12),
    )
    return obj


def create_camera(collection, target):
    camera_data = bpy.data.cameras.new(f"{PREFIX}_Camera_Data")
    camera = bpy.data.objects.new(f"{PREFIX}_Camera", camera_data)
    camera.location = (7.0, -8.0, 4.9)
    look_at(camera, target)
    camera_data.lens = 42
    collection.objects.link(camera)
    return camera


def create_area_light(collection, name, location, target, energy, size, color):
    light_data = bpy.data.lights.new(name=f"{name}_Data", type="AREA")
    light_data.energy = energy
    light_data.color = color
    light_data.shape = "RECTANGLE"
    light_data.size = size[0]
    light_data.size_y = size[1]

    light = bpy.data.objects.new(name, light_data)
    light.location = location
    look_at(light, target)
    collection.objects.link(light)
    return light


def create_negative_light(collection, target):
    light_data = bpy.data.lights.new(name=f"{PREFIX}_NegativeLight_Data", type="POINT")
    light_data.energy = -900.0
    light_data.shadow_soft_size = 1.2
    light_data.color = (1.0, 1.0, 1.0)

    light = bpy.data.objects.new(f"{PREFIX}_NegativeLight", light_data)
    light.location = target + Vector((0.0, 0.0, 1.0))
    collection.objects.link(light)
    return light


def create_ring_marker(collection, location):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=1.15,
        minor_radius=0.035,
        location=location,
        rotation=(math.radians(90.0), 0.0, 0.0),
    )
    obj = bpy.context.active_object
    obj.name = f"{PREFIX}_Marker"
    move_to_collection(obj, collection)
    assign_material(
        obj,
        create_principled_material(
            f"{PREFIX}_Marker_Mat",
            base_color=(0.02, 0.02, 0.025),
            roughness=0.9,
            metallic=0.0,
        ),
    )
    return obj


def create_text(collection, text, location, rotation=(math.radians(90.0), 0.0, 0.0), size=0.42):
    curve = bpy.data.curves.new(name=f"{PREFIX}_TextCurve", type="FONT")
    curve.body = text
    curve.size = size
    curve.align_x = "CENTER"

    text_obj = bpy.data.objects.new(f"{PREFIX}_Label", curve)
    text_obj.location = location
    text_obj.rotation_euler = rotation
    collection.objects.link(text_obj)
    return text_obj


def configure_scene(scene, camera):
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 128
    scene.cycles.preview_samples = 32

    world = scene.world
    if world is None:
        world = bpy.data.worlds.new(f"{PREFIX}_World")
        scene.world = world

    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.015, 0.018, 0.024, 1.0)
    background.inputs["Strength"].default_value = 0.04


def main():
    scene = bpy.context.scene
    purge_previous_setup()
    collection = ensure_collection(scene)

    create_floor(collection)
    left_target = Vector((-1.4, 0.0, 0.72))
    right_target = Vector((1.7, 0.0, 0.72))

    create_sphere(collection, f"{PREFIX}_LitSphere", left_target, (0.92, 0.92, 0.95))
    create_sphere(collection, f"{PREFIX}_DarkenedSphere", right_target, (0.92, 0.92, 0.95))

    create_area_light(
        collection,
        f"{PREFIX}_KeyLight",
        location=(4.8, -4.0, 4.7),
        target=Vector((0.0, 0.0, 0.8)),
        energy=2600.0,
        size=(3.0, 2.0),
        color=(1.0, 0.97, 0.93),
    )
    create_area_light(
        collection,
        f"{PREFIX}_FillLight",
        location=(-4.4, -1.6, 2.5),
        target=Vector((0.0, 0.0, 0.8)),
        energy=900.0,
        size=(3.4, 2.4),
        color=(0.9, 0.95, 1.0),
    )
    create_area_light(
        collection,
        f"{PREFIX}_RimLight",
        location=(0.0, 4.6, 5.2),
        target=Vector((0.0, 0.0, 0.8)),
        energy=1700.0,
        size=(3.0, 2.0),
        color=(1.0, 1.0, 1.0),
    )

    negative_light = create_negative_light(collection, right_target)
    create_ring_marker(collection, negative_light.location)
    create_text(collection, "Negative Light", (1.7, -1.6, 0.02), size=0.34)

    camera = create_camera(collection, Vector((0.2, 0.0, 0.9)))
    configure_scene(scene, camera)

    print("Created negative light demo scene")
    print(f"- Collection: {collection.name}")
    print(f"- Negative light energy: {negative_light.data.energy}")


if __name__ == "__main__":
    main()
