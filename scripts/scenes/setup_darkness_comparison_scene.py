import math

import bpy
from mathutils import Vector


PREFIX = "CodexDarkCompare"
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
        bpy.data.worlds,
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


def create_principled_material(name, base_color, roughness=0.35, metallic=0.0, emission=None, emission_strength=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (*base_color, 1.0)
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Metallic"].default_value = metallic
    if emission is not None:
        principled.inputs["Emission Color"].default_value = (*emission, 1.0)
        principled.inputs["Emission Strength"].default_value = emission_strength
    return material


def create_darkness_volume_material(name, absorption_density=2.8, scatter_density=0.02):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    absorption = nodes.new("ShaderNodeVolumeAbsorption")
    scatter = nodes.new("ShaderNodeVolumeScatter")
    add_shader = nodes.new("ShaderNodeAddShader")
    output = nodes.new("ShaderNodeOutputMaterial")

    absorption.inputs["Color"].default_value = (0.01, 0.01, 0.012, 1.0)
    absorption.inputs["Density"].default_value = absorption_density
    scatter.inputs["Color"].default_value = (0.03, 0.03, 0.04, 1.0)
    scatter.inputs["Density"].default_value = scatter_density

    absorption.location = (0, 120)
    scatter.location = (0, -20)
    add_shader.location = (200, 40)
    output.location = (420, 40)

    links.new(absorption.outputs["Volume"], add_shader.inputs[0])
    links.new(scatter.outputs["Volume"], add_shader.inputs[1])
    links.new(add_shader.outputs["Shader"], output.inputs["Volume"])
    return material


def assign_material(obj, material):
    obj.data.materials.clear()
    obj.data.materials.append(material)


def create_floor(collection):
    bpy.ops.mesh.primitive_plane_add(size=24.0, location=(0.0, 0.0, 0.0))
    obj = bpy.context.active_object
    obj.name = f"{PREFIX}_Floor"
    move_to_collection(obj, collection)
    assign_material(
        obj,
        create_principled_material(
            f"{PREFIX}_Floor_Mat",
            base_color=(0.08, 0.09, 0.1),
            roughness=0.88,
        ),
    )


def create_backdrop(collection):
    bpy.ops.mesh.primitive_plane_add(size=12.0, location=(0.0, 5.0, 4.2), rotation=(math.radians(90.0), 0.0, 0.0))
    obj = bpy.context.active_object
    obj.name = f"{PREFIX}_Backdrop"
    move_to_collection(obj, collection)
    assign_material(
        obj,
        create_principled_material(
            f"{PREFIX}_Backdrop_Mat",
            base_color=(0.14, 0.16, 0.18),
            roughness=1.0,
            emission=(0.28, 0.34, 0.42),
            emission_strength=2.8,
        ),
    )


def create_demo_sphere(collection, name, location, color):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.72, location=location)
    obj = bpy.context.active_object
    obj.name = name
    move_to_collection(obj, collection)
    assign_material(
        obj,
        create_principled_material(f"{name}_Mat", color, roughness=0.1, metallic=0.05),
    )
    return obj


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

    light = bpy.data.objects.new(f"{PREFIX}_NegativeLight", light_data)
    light.location = target + Vector((0.0, 0.0, 1.0))
    collection.objects.link(light)
    return light


def create_darkness_field(collection, center):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.42, location=center)
    field = bpy.context.active_object
    field.name = f"{PREFIX}_Field"
    move_to_collection(field, collection)
    assign_material(field, create_darkness_volume_material(f"{PREFIX}_Field_Mat"))

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.38, location=center)
    core = bpy.context.active_object
    core.name = f"{PREFIX}_Core"
    move_to_collection(core, collection)
    assign_material(
        core,
        create_principled_material(
            f"{PREFIX}_Core_Mat",
            base_color=(0.0, 0.0, 0.0),
            roughness=1.0,
        ),
    )
    return field, core


def create_text(collection, text, location, size=0.38):
    curve = bpy.data.curves.new(name=f"{PREFIX}_TextCurve", type="FONT")
    curve.body = text
    curve.size = size
    curve.align_x = "CENTER"

    obj = bpy.data.objects.new(f"{PREFIX}_{text.replace(' ', '_')}", curve)
    obj.location = location
    obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    collection.objects.link(obj)
    return obj


def create_camera(collection, target):
    camera_data = bpy.data.cameras.new(f"{PREFIX}_Camera_Data")
    camera = bpy.data.objects.new(f"{PREFIX}_Camera", camera_data)
    camera.location = (7.8, -9.0, 5.5)
    look_at(camera, target)
    camera_data.lens = 40
    collection.objects.link(camera)
    return camera


def configure_scene(scene, camera):
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 128
    scene.cycles.preview_samples = 32

    world = bpy.data.worlds.new(f"{PREFIX}_World")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.01, 0.012, 0.016, 1.0)
    background.inputs["Strength"].default_value = 0.025


def main():
    scene = bpy.context.scene
    purge_previous_setup()
    collection = ensure_collection(scene)

    create_floor(collection)
    create_backdrop(collection)

    left_center = Vector((-2.6, 0.0, 0.72))
    right_center = Vector((2.6, 0.0, 0.72))
    look_target = Vector((0.0, 0.0, 1.0))

    create_demo_sphere(collection, f"{PREFIX}_NegativeSphere", left_center, (0.94, 0.94, 0.96))
    create_demo_sphere(collection, f"{PREFIX}_VolumeSphere", right_center, (0.94, 0.94, 0.96))

    create_area_light(
        collection,
        f"{PREFIX}_KeyLight",
        location=(5.0, -4.2, 4.8),
        target=look_target,
        energy=2700.0,
        size=(3.0, 2.0),
        color=(1.0, 0.97, 0.93),
    )
    create_area_light(
        collection,
        f"{PREFIX}_FillLight",
        location=(-4.8, -1.9, 3.0),
        target=look_target,
        energy=1000.0,
        size=(3.6, 2.6),
        color=(0.88, 0.94, 1.0),
    )
    create_area_light(
        collection,
        f"{PREFIX}_RimLight",
        location=(0.0, 5.0, 5.2),
        target=look_target,
        energy=1800.0,
        size=(3.4, 2.1),
        color=(1.0, 1.0, 1.0),
    )

    negative_light = create_negative_light(collection, left_center)
    create_darkness_field(collection, right_center + Vector((0.0, 0.0, 0.72)))

    create_text(collection, "Negative Light", (-2.6, -1.85, 0.02), size=0.34)
    create_text(collection, "Volume Darkness", (2.6, -1.85, 0.02), size=0.34)

    camera = create_camera(collection, look_target)
    configure_scene(scene, camera)

    print("Created darkness comparison scene")
    print(f"- Collection: {collection.name}")
    print(f"- Negative light energy: {negative_light.data.energy}")


if __name__ == "__main__":
    main()
