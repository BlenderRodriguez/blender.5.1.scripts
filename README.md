# Blender 5.1 Scripts

This repo contains a Blender add-on for running Python scripts from a folder, plus a small set of utility scripts.

## Contents

- `folder_script_runner_addon.py`
  Installable Blender add-on. It lets you choose a scripts folder in the Blender UI and run scripts from buttons.
- `scripts/snap_mesh_bottom_to_z0.py`
  Moves the selected mesh object(s) so the lowest visible vertex sits at world `Z = 0`.
- `scripts/move_selected_vertices_to_z0.py`
  Moves selected vertices in Edit Mode to world `Z = 0`.
- `scripts/unpack_resources_next_to_blend.py`
  Unpacks packed resources next to the current saved `.blend` file.
- `scripts/cleanup/mesh_cleanup_gentle.py`
  Safe, light cleanup for selected mesh objects.
- `scripts/cleanup/mesh_cleanup_aggressive.py`
  Stronger cleanup for messier geometry.
- `scripts/cleanup/mesh_cleanup_cad_import.py`
  Cleanup focused on CAD and import meshes.
- `scripts/cleanup/mesh_cleanup_scan.py`
  Cleanup focused on scan and photogrammetry meshes.
- `scripts/geometry_nodes/setup_surface_subdivision_viewport_render.py`
  Creates a geometry-nodes subdivision setup with separate viewport and render levels.

## Add-on Features

- Choose the scripts folder from the Blender UI
- List scripts from the selected folder
- Optional subfolder scanning
- Search filter
- Favorites
- Per-script icons based on filename

## Install The Add-on

1. Open Blender.
2. Go to `Edit > Preferences > Add-ons`.
3. Click `Install from Disk`.
4. Choose `folder_script_runner_addon.py`.
5. Enable the add-on.

## Use The Add-on

1. Open the `View3D` sidebar.
2. Go to the `Scripts` tab.
3. Set the folder path to this repo's `scripts` folder.

Example folder:

```text
/Users/sandorzsolt/Documents/GitHub/blender.5.1/blender.5.1.scripts/scripts
```

4. Use the generated buttons to run scripts.
5. Use `Subfolders`, `Favorites`, and the search box to organize the list.

## Notes

- Scripts are run inside Blender's Python environment.
- The add-on leaves itself out of the runnable script list.
- The utility scripts can also be opened manually in Blender's Text Editor and run there.
