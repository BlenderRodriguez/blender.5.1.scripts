import bpy


GROUP_NAME = "Codex Surface Subdivision"
MODIFIER_NAME = "Surface Subdivision GN"
DEMO_OBJECT_NAME = "Codex_Subdivision_Surface"


def target_mesh_objects(context):
    targets = [obj for obj in context.selected_objects if obj.type == "MESH"]
    if not targets:
        active = context.active_object
        if active and active.type == "MESH":
            targets = [active]
    return targets


def create_demo_surface():
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0.0, 0.0, 0.0))
    obj = bpy.context.active_object
    obj.name = DEMO_OBJECT_NAME
    if obj.data:
        obj.data.name = f"{DEMO_OBJECT_NAME}_Mesh"
    print(f"No mesh selected. Created demo surface: {obj.name}")
    return [obj]


def group_input_items(node_group):
    return {
        item.name: item
        for item in node_group.interface.items_tree
        if item.item_type == "SOCKET" and item.in_out == "INPUT"
    }


def ensure_node_group():
    existing = bpy.data.node_groups.get(GROUP_NAME)
    if existing and existing.bl_idname == "GeometryNodeTree":
        return existing

    node_group = bpy.data.node_groups.new(GROUP_NAME, "GeometryNodeTree")
    node_group.is_modifier = True
    node_group.use_fake_user = True

    interface = node_group.interface

    interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")

    viewport_level = interface.new_socket(
        name="Viewport Level",
        in_out="INPUT",
        socket_type="NodeSocketInt",
    )
    viewport_level.default_value = 1
    viewport_level.min_value = 0
    viewport_level.max_value = 8
    viewport_level.description = "Subdivision level used while looking through the viewport"

    render_level = interface.new_socket(
        name="Render Level",
        in_out="INPUT",
        socket_type="NodeSocketInt",
    )
    render_level.default_value = 2
    render_level.min_value = 0
    render_level.max_value = 8
    render_level.description = "Subdivision level used for final renders"

    smooth_surface = interface.new_socket(
        name="Smooth Surface",
        in_out="INPUT",
        socket_type="NodeSocketBool",
    )
    smooth_surface.default_value = True
    smooth_surface.description = "Use Subdivision Surface instead of flat Subdivide Mesh"

    interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    nodes = node_group.nodes
    links = node_group.links

    group_input = nodes.new("NodeGroupInput")
    group_input.location = (-720.0, 0.0)

    group_output = nodes.new("NodeGroupOutput")
    group_output.location = (260.0, 0.0)
    group_output.is_active_output = True

    is_viewport = nodes.new("GeometryNodeIsViewport")
    is_viewport.location = (-520.0, -220.0)

    level_switch = nodes.new("GeometryNodeSwitch")
    level_switch.name = "Viewport Render Level"
    level_switch.label = "Viewport / Render Level"
    level_switch.input_type = "INT"
    level_switch.location = (-280.0, -40.0)

    simple_subdivide = nodes.new("GeometryNodeSubdivideMesh")
    simple_subdivide.label = "Simple Subdivide"
    simple_subdivide.location = (-20.0, 140.0)

    smooth_subdivide = nodes.new("GeometryNodeSubdivisionSurface")
    smooth_subdivide.label = "Smooth Subdivide"
    smooth_subdivide.location = (-20.0, -120.0)

    surface_switch = nodes.new("GeometryNodeSwitch")
    surface_switch.name = "Surface Mode"
    surface_switch.label = "Smooth Surface"
    surface_switch.input_type = "GEOMETRY"
    surface_switch.location = (170.0, 0.0)

    links.new(group_input.outputs["Viewport Level"], level_switch.inputs["True"])
    links.new(group_input.outputs["Render Level"], level_switch.inputs["False"])
    links.new(is_viewport.outputs["Is Viewport"], level_switch.inputs["Switch"])

    links.new(group_input.outputs["Geometry"], simple_subdivide.inputs["Mesh"])
    links.new(group_input.outputs["Geometry"], smooth_subdivide.inputs["Mesh"])
    links.new(level_switch.outputs["Output"], simple_subdivide.inputs["Level"])
    links.new(level_switch.outputs["Output"], smooth_subdivide.inputs["Level"])

    links.new(group_input.outputs["Smooth Surface"], surface_switch.inputs["Switch"])
    links.new(simple_subdivide.outputs["Mesh"], surface_switch.inputs["False"])
    links.new(smooth_subdivide.outputs["Mesh"], surface_switch.inputs["True"])

    links.new(surface_switch.outputs["Output"], group_output.inputs["Geometry"])

    return node_group


def ensure_modifier(obj, node_group):
    modifier = obj.modifiers.get(MODIFIER_NAME)
    if modifier and modifier.type != "NODES":
        modifier = None

    if modifier is None:
        modifier = obj.modifiers.new(MODIFIER_NAME, "NODES")

    modifier.node_group = node_group
    modifier.show_viewport = True
    modifier.show_render = True

    inputs = group_input_items(node_group)
    default_values = {
        "Viewport Level": 1,
        "Render Level": 2,
        "Smooth Surface": True,
    }

    for name, value in default_values.items():
        identifier = inputs[name].identifier
        if identifier not in modifier.keys():
            modifier[identifier] = value

    return modifier


def main():
    targets = target_mesh_objects(bpy.context)
    if not targets:
        targets = create_demo_surface()

    node_group = ensure_node_group()

    for obj in targets:
        ensure_modifier(obj, node_group)
        print(f"Applied {MODIFIER_NAME} to {obj.name}")


if __name__ == "__main__":
    main()
