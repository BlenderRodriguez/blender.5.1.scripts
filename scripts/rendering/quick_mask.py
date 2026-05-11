import bpy

# ============================================================
# CONFIG
# ============================================================

MASK_MATERIAL_NAME = "MASK_White_Emission"
BASE_MATERIAL_NAME = "MASK_Black_NoEmission"

MASK_COLOR = (1, 1, 1, 1)
MASK_EMISSION_STRENGTH = 3.0

BASE_COLOR = (0, 0, 0, 1)

# How to identify the base/background objects
BASE_NAME_KEYWORDS = [
    "base",
    "plane",
    "ground",
    "floor",
    "background",
    "bg",
]

# Optional: objects inside this collection will be treated as base/background.
# Set to None to ignore.
BASE_COLLECTION_NAME = None
# Example:
# BASE_COLLECTION_NAME = "Mask_Background"

# Optional: use a custom object property.
# Example: select object -> Object Properties -> Custom Properties:
# mask_role = base
USE_CUSTOM_PROPERTY = True
CUSTOM_PROPERTY_NAME = "mask_role"
CUSTOM_PROPERTY_BASE_VALUE = "base"

# Include meshes hidden in viewport/render?
INCLUDE_HIDDEN_OBJECTS = False

# Use emission for mask objects?
# True = bright white unlit mask
# False = plain white material
USE_EMISSION_FOR_MASK = True

# Render settings
SET_RENDER_SETTINGS = True


# ============================================================
# MATERIAL HELPERS
# ============================================================

def get_or_create_emission_material(name, color, strength):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)

    node_tree = ensure_material_node_tree(mat)
    nodes = node_tree.nodes
    nodes.clear()

    emission = nodes.new(type="ShaderNodeEmission")
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = strength

    output = nodes.new(type="ShaderNodeOutputMaterial")
    node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])

    return mat


def get_or_create_principled_material(name, base_color, emission_strength=0.0):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)

    node_tree = ensure_material_node_tree(mat)
    nodes = node_tree.nodes
    nodes.clear()

    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Roughness"].default_value = 1.0

    # Blender 4.x
    if "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Strength"].default_value = emission_strength

    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (0, 0, 0, 1)

    # Blender 3.x compatibility
    if "Emission" in bsdf.inputs:
        bsdf.inputs["Emission"].default_value = (0, 0, 0, 1)

    output = nodes.new(type="ShaderNodeOutputMaterial")
    node_tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    return mat


def ensure_material_node_tree(mat):
    if mat.node_tree is None and hasattr(mat, "use_nodes"):
        mat.use_nodes = True

    if mat.node_tree is None:
        raise RuntimeError(f"Material {mat.name} has no node tree.")

    return mat.node_tree


def assign_single_material(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


# ============================================================
# OBJECT CLASSIFICATION
# ============================================================

def object_is_in_collection(obj, collection_name):
    if not collection_name:
        return False

    for collection in obj.users_collection:
        if collection.name == collection_name:
            return True

    return False


def is_base_object(obj):
    name = obj.name.lower()

    # Method 1: custom property
    if USE_CUSTOM_PROPERTY:
        value = obj.get(CUSTOM_PROPERTY_NAME)
        if isinstance(value, str) and value.lower() == CUSTOM_PROPERTY_BASE_VALUE.lower():
            return True

    # Method 2: collection
    if object_is_in_collection(obj, BASE_COLLECTION_NAME):
        return True

    # Method 3: name keywords
    for keyword in BASE_NAME_KEYWORDS:
        if keyword.lower() in name:
            return True

    return False


def should_process_object(obj):
    if obj.type != "MESH":
        return False

    if INCLUDE_HIDDEN_OBJECTS:
        return True

    if obj.hide_get():
        return False

    if obj.hide_render:
        return False

    return True


# ============================================================
# MAIN
# ============================================================

def create_mask_material():
    if USE_EMISSION_FOR_MASK:
        return get_or_create_emission_material(
            MASK_MATERIAL_NAME,
            MASK_COLOR,
            MASK_EMISSION_STRENGTH,
        )

    return get_or_create_principled_material(
        MASK_MATERIAL_NAME,
        MASK_COLOR,
        emission_strength=0.0,
    )


def configure_render_settings(scene):
    scene.render.engine = "CYCLES"

    if scene.world:
        scene.world.color = (0, 0, 0)

    scene.render.film_transparent = False

    # Keep the mask output close to raw black and white values.
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1


def apply_quick_mask(context):
    mask_mat = create_mask_material()
    base_mat = get_or_create_principled_material(
        BASE_MATERIAL_NAME,
        BASE_COLOR,
        emission_strength=0.0,
    )

    mask_count = 0
    base_count = 0
    skipped_count = 0

    for obj in context.scene.objects:
        if not should_process_object(obj):
            skipped_count += 1
            continue

        if is_base_object(obj):
            assign_single_material(obj, base_mat)
            base_count += 1
        else:
            assign_single_material(obj, mask_mat)
            mask_count += 1

    if SET_RENDER_SETTINGS:
        configure_render_settings(context.scene)

    return mask_count, base_count, skipped_count


def main():
    mask_count, base_count, skipped_count = apply_quick_mask(bpy.context)

    print("Mask material assignment complete.")
    print(f"Mask objects: {mask_count}")
    print(f"Base/background objects: {base_count}")
    print(f"Skipped objects: {skipped_count}")


if __name__ == "__main__":
    main()
