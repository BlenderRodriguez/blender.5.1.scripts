import bmesh
import bpy


MERGE_DISTANCE = 0.00005
DEGENERATE_DISTANCE = 0.000001
MIN_ISLAND_FACE_COUNT = 64


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


def small_face_islands(bm, min_face_count):
    visited = set()
    islands_to_delete = []

    for face in bm.faces:
        if face in visited:
            continue

        stack = [face]
        island = []
        visited.add(face)

        while stack:
            current = stack.pop()
            island.append(current)

            for edge in current.edges:
                for linked_face in edge.link_faces:
                    if linked_face not in visited:
                        visited.add(linked_face)
                        stack.append(linked_face)

        if len(island) < min_face_count:
            islands_to_delete.extend(island)

    return islands_to_delete


def cleanup_object(obj):
    if obj.data.shape_keys:
        print(f"Skipped {obj.name}: mesh has shape keys.")
        return

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        delete_loose_geometry(bm)

        islands_to_delete = small_face_islands(bm, MIN_ISLAND_FACE_COUNT)
        if islands_to_delete:
            bmesh.ops.delete(bm, geom=islands_to_delete, context="FACES")

        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=MERGE_DISTANCE)
        bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=DEGENERATE_DISTANCE)
        delete_loose_geometry(bm)

        if bm.faces:
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

        bm.normal_update()
        bm.to_mesh(obj.data)
    finally:
        bm.free()

    obj.data.update()
    print(f"Scan cleanup finished for {obj.name}")


def main():
    for obj in target_mesh_objects(bpy.context):
        cleanup_object(obj)


if __name__ == "__main__":
    main()
