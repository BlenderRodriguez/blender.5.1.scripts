import bpy
from mathutils import Matrix


def lowest_world_z(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        if not mesh.vertices:
            return None

        matrix_world = evaluated.matrix_world
        return min((matrix_world @ vertex.co).z for vertex in mesh.vertices)
    finally:
        evaluated.to_mesh_clear()


def move_bottom_to_zero(obj, depsgraph):
    min_z = lowest_world_z(obj, depsgraph)
    if min_z is None:
        return None

    delta_z = -min_z
    if abs(delta_z) < 1e-9:
        return 0.0

    obj.matrix_world = Matrix.Translation((0.0, 0.0, delta_z)) @ obj.matrix_world
    return delta_z


def main():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    targets = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]

    if not targets:
        active = bpy.context.active_object
        if active and active.type == "MESH":
            targets = [active]

    if not targets:
        raise RuntimeError("Select at least one mesh object, or make a mesh object active.")

    for obj in targets:
        delta_z = move_bottom_to_zero(obj, depsgraph)
        if delta_z is None:
            print(f"Skipped {obj.name}: mesh has no vertices.")
        else:
            print(f"{obj.name}: moved {delta_z:.6f} on world Z.")

    bpy.context.view_layer.update()


if __name__ == "__main__":
    main()
