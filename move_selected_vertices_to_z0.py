import bpy
import bmesh


obj = bpy.context.edit_object

if obj is None or obj.type != "MESH" or bpy.context.mode != "EDIT_MESH":
    raise RuntimeError("Enter Edit Mode on a mesh object and select at least one vertex.")

bm = bmesh.from_edit_mesh(obj.data)
selected_verts = [vert for vert in bm.verts if vert.select]

if not selected_verts:
    raise RuntimeError("Select at least one vertex.")

matrix_world = obj.matrix_world
matrix_world_inv = matrix_world.inverted()

for vert in selected_verts:
    world_co = matrix_world @ vert.co
    world_co.z = 0.0
    vert.co = matrix_world_inv @ world_co

bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
bpy.context.view_layer.update()

print(f"Moved {len(selected_verts)} selected vertices of '{obj.name}' to world Z = 0")
