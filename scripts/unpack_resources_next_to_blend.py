import os
import re
from pathlib import Path

import bpy


def sanitize_name(name):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return cleaned or "resource"


def has_packed_data(data_block):
    packed_file = getattr(data_block, "packed_file", None)
    packed_files = getattr(data_block, "packed_files", None)
    return packed_file is not None or bool(packed_files)


def guess_filename(filepath, fallback_name):
    basename = os.path.basename(bpy.path.abspath(filepath)) if filepath else ""
    if basename:
        return basename
    return sanitize_name(fallback_name)


def unique_target_path(base_folder, subfolder, filename, used_paths):
    folder = base_folder / subfolder
    folder.mkdir(parents=True, exist_ok=True)

    stem = Path(filename).stem or "resource"
    suffix = Path(filename).suffix
    candidate = folder / filename
    index = 1

    while str(candidate).lower() in used_paths:
        candidate = folder / f"{stem}_{index}{suffix}"
        index += 1

    used_paths.add(str(candidate).lower())
    return candidate


def show_message(title, message, icon="INFO"):
    def draw(self, _context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def assign_target_paths(base_folder):
    used_paths = set()
    packed_items = []

    resource_groups = (
        ("images", bpy.data.images),
        ("movieclips", bpy.data.movieclips),
        ("sounds", bpy.data.sounds),
        ("fonts", bpy.data.fonts),
    )

    for subfolder, collection in resource_groups:
        for data_block in collection:
            if not has_packed_data(data_block):
                continue

            filename = guess_filename(getattr(data_block, "filepath", ""), data_block.name)
            target_path = unique_target_path(base_folder, subfolder, filename, used_paths)
            data_block.filepath = bpy.path.relpath(str(target_path))
            packed_items.append(
                {
                    "subfolder": subfolder,
                    "name": data_block.name,
                    "path": str(target_path),
                    "data_block": data_block,
                }
            )

    return packed_items


def unpack_direct_items(packed_items):
    unpacked = []
    deferred = []

    for item in packed_items:
        data_block = item["data_block"]
        unpack_method = getattr(data_block, "unpack", None)
        if unpack_method is None:
            deferred.append(item)
            continue

        unpack_method(method="WRITE_LOCAL")
        unpacked.append(item)

    return unpacked, deferred


def main():
    blend_path = bpy.data.filepath
    if not blend_path:
        bpy.ops.wm.save_as_mainfile("INVOKE_DEFAULT")
        message = "Save the .blend first, then run this script again to unpack resources next to it."
        print(message)
        show_message("Save Blend First", message, icon="INFO")
        return

    blend_file = Path(bpy.path.abspath(blend_path))
    blend_dir = blend_file.parent
    resource_folder = blend_dir / f"{blend_file.stem}_resources"
    resource_folder.mkdir(parents=True, exist_ok=True)

    packed_items = assign_target_paths(resource_folder)
    if not packed_items:
        print("No packed resources found. Nothing to unpack.")
        return

    unpacked_items, deferred_items = unpack_direct_items(packed_items)

    if deferred_items:
        bpy.ops.file.unpack_all(method="WRITE_LOCAL")
        unpacked_items.extend(deferred_items)

    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile()

    print(f"Unpacked {len(unpacked_items)} resource(s) into: {resource_folder}")
    for item in unpacked_items:
        print(f"[{item['subfolder']}] {item['name']} -> {item['path']}")


if __name__ == "__main__":
    main()
