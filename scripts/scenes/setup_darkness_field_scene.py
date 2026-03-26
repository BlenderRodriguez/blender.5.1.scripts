import math

import bpy
from mathutils import Vector


PREFIX = "CodexDarkness"
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


def create_principled_material(name, base_color, roughness=0.5, metallic=0.0, emission=None, emission_strength=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (*base_color, 1.0)
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Metallic"].default_value = metallic
    if emission is not None:
        principled.inputs["Emission Color"].default_value = (*emission, 1.0)
        principled.inputs["Emission Strength"].default_value = emission_strength
    return material


def create_emission_material(name, color, strength):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    emission = nodes.new("ShaderNodeEmission")
    output = nodes.new("ShaderNodeOutputMaterial")
    emission.inputs["Color"].default_value = (*color, 1.0)
    emission.inputs["Strength"].default_value = strength
    emission.location = (0, 0)
    output.location = (220, 0)
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def create_darkness_volume_material(name, absorption_density=2.5, scatter_density=0.03):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    absorption = nodes.new("ShaderNodeVolumeAbsorption")
    scatter = nodes.new("ShaderNodeVolumeScatter")
    add_shader = nodes.new("ShaderNodeAddShader")
    output = nodes.new("ShaderNodeOutputMaterial")

    absorption.inputs["Color"].default_value = (0.015, 0.015, 0.02, 1.0)
    absorption.inputs["Density"].default_value = absorption_density
    scatter.inputs["Color"].default_value = (0.04, 0.04, 0.05, 1.0)
    scatter.inputs["Density"].default_value = scatter_density

    absorption.location = (0, 120)
    scatter.location = (0, -40)
    add_shader.location = (220, 40)
    output.location = (460, 40)

    links.new(absorption.outputs["Volume"], add_shader.inputs[0])
    links.new(scatter.outputs["Volume"], add_shader.inputs[1])
    links.new(add_shader.outputs["Shader"], output.inputs["Volume"])
    return material


def assign_material(obj, material):
    obj.data.materials.clear()
    obj.data.materials.append(material)


def create_floor(collection):
    bpy.ops.mesh.primitive_plane_add(size=18.0, location=(0.0, 0.0, 0.0))
    obj = bpy.context.active_object
    obj.name = f"{PREFIX}_Floor"
    move_to_collection(obj, collection)
    material = create_principled_material(
        f"{PREFIX}_Floor_Mat",
        base_color=(0.08, 0.085, 0.1),
        roughness=0.82,
    )
    assign_material(obj, material)
    return obj


def create_backdrop(collection):
    bpy.ops.mesh.primitive_plane_add(size=10.0, location=(0.0, 4.4, 3.6), rotation=(math.radians(90.0), 0.0, 0.0))
    obj = bpy.context.active_object
    obj.name = f"{PREFIX}_Backdrop"
    move_to_collection(obj, collection)
    material = create_emission_material(
        f"{PREFIX}_Backdrop_Mat",
        color=(0.75, 0.9, 1.0),
        strength=4.0,
    )
    assign_material(obj, material)
    return obj


def create_demo_objects(collection):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.62, location=(-1.9, -0.8, 0.62))
    left_sphere = bpy.context.active_object
    left_sphere.name = f"{PREFIX}_Sphere_Left"
    move_to_collection(left_sphere, collection)
    assign_material(
        left_sphere,
        create_principled_material(
            f"{PREFIX}_Sphere_Left_Mat",
            base_color=(0.92, 0.92, 0.96),
            roughness=0.08,
            metallic=0.1,
        ),
    )

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.62, location=(1.9, -0.2, 0.62))
    right_sphere = bpy.context.active_object
    right_sphere.name = f"{PREFIX}_Sphere_Right"
    move_to_collection(right_sphere, collection)
    assign_material(
        right_sphere,
        create_principled_material(
            f"{PREFIX}_Sphere_Right_Mat",
            base_color=(0.08, 0.1, 0.14),
            roughness=0.14,
            metallic=0.0,
            emission=(0.08, 0.75, 1.0),
            emission_strength=8.0,
        ),
    )


def create_darkness_field(collection):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.45, location=(0.0, 0.0, 1.45))
    field = bpy.context.active_object
    field.name = f"{PREFIX}_Field"
    move_to_collection(field, collection)
    assign_material(field, create_darkness_volume_material(f"{PREFIX}_Field_Mat"))

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.42, location=(0.0, 0.0, 1.45))
    core = bpy.context.active_object
    core.name = f"{PREFIX}_Core"
    move_to_collection(core, collection)
    assign_material(
        core,
        create_principled_material(
            f"{PREFIX}_Core_Mat",
            base_color=(0.0, 0.0, 0.0),
            roughness=1.0,
            metallic=0.0,
        ),
    )

    return field, core


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


def create_camera(collection, target):
    camera_data = bpy.data.cameras.new(f"{PREFIX}_Camera_Data")
    camera = bpy.data.objects.new(f"{PREFIX}_Camera", camera_data)
    camera.location = (6.6, -7.0, 4.8)
    look_at(camera, target)
    camera_data.lens = 44
    collection.objects.link(camera)
    return camera


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
    background.inputs["Color"].default_value = (0.007, 0.008, 0.012, 1.0)
    background.inputs["Strength"].default_value = 0.02


def main():
    scene = bpy.context.scene
    purge_previous_setup()
    collection = ensure_collection(scene)

    create_floor(collection)
    create_backdrop(collection)
    create_demo_objects(collection)
    field, _core = create_darkness_field(collection)

    target = Vector((0.0, 0.0, 1.45))
    create_area_light(
        collection,
        f"{PREFIX}_KeyLight",
        location=(4.5, -3.6, 4.8),
        target=target,
        energy=2600.0,
        size=(3.0, 2.0),
        color=(1.0, 0.96, 0.92),
    )
    create_area_light(
        collection,
        f"{PREFIX}_FillLight",
        location=(-4.0, -2.4, 2.8),
        target=target,
        energy=950.0,
        size=(3.6, 2.6),
        color=(0.86, 0.92, 1.0),
    )
    create_area_light(
        collection,
        f"{PREFIX}_RimLight",
        location=(0.0, 3.6, 4.8),
        target=target,
        energy=1800.0,
        size=(3.2, 2.0),
        color=(1.0, 1.0, 1.0),
    )

    camera = create_camera(collection, target)
    configure_scene(scene, camera)

    print("Created darkness field demo scene:")
    print(f"- Collection: {collection.name}")
    print(f"- Field object: {field.name}")
    print(f"- Camera: {camera.name}")


if __name__ == "__main__":
    main()
