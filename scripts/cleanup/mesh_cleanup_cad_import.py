import math

import bmesh
import bpy


MERGE_DISTANCE = 0.0001
DEGENERATE_DISTANCE = 0.00001
JOIN_FACE_ANGLE = math.radians(20.0)
JOIN_SHAPE_ANGLE = math.radians(20.0)
LIMITED_DISSOLVE_ANGLE = math.radians(1.0)


def target_mesh_objects(context):
    targets = [obj for obj in context.selected_objects if obj.type == "MESH"]
    if not targets:
        active = context.active_object
        if active and active.type == "MESH":
            targets = [active]
    if not targets:
        raise RuntimeError("Select at least one mesh object, or make a mesh object active.")
    return targets


def delete_loose_geometry(bm):
    loose_edges = [edge for edge in bm.edges if not edge.link_faces]
    if loose_edges:
        bmesh.ops.delete(bm, geom=loose_edges, context="EDGES")

    loose_verts = [vert for vert in bm.verts if not vert.link_edges]
    if loose_verts:
        bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")


def cleanup_object(obj):
    if obj.data.shape_keys:
        print(f"Skipped {obj.name}: mesh has shape keys.")
        return

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=MERGE_DISTANCE)
        bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=DEGENERATE_DISTANCE)
        delete_loose_geometry(bm)

        if bm.faces:
            bmesh.ops.join_triangles(
                bm,
                faces=list(bm.faces),
                angle_face_threshold=JOIN_FACE_ANGLE,
                angle_shape_threshold=JOIN_SHAPE_ANGLE,
                compare_materials=True,
                compare_sharp=True,
                compare_seam=True,
                compare_uvs=True,
            )

        if bm.edges:
            bmesh.ops.dissolve_limit(
                bm,
                angle_limit=LIMITED_DISSOLVE_ANGLE,
                use_dissolve_boundaries=False,
                verts=list(bm.verts),
                edges=list(bm.edges),
            )

        if bm.faces:
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

        bm.normal_update()
        bm.to_mesh(obj.data)
    finally:
        bm.free()

    obj.data.update()
    print(f"CAD/import cleanup finished for {obj.name}")


def main():
    for obj in target_mesh_objects(bpy.context):
        cleanup_object(obj)


if __name__ == "__main__":
    main()
