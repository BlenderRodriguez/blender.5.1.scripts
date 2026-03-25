bl_info = {
    "name": "Folder Script Runner",
    "author": "Zsolt Sandor + Codex",
    "version": (2, 0, 0),
    "blender": (5, 1, 0),
    "location": "View3D > Sidebar > Scripts",
    "description": "List Python scripts from a chosen folder and run them from buttons",
    "category": "System",
}

import contextlib
import os
import runpy
import sys
import traceback
from collections import OrderedDict

import bpy
from bpy.props import BoolProperty, CollectionProperty, StringProperty


IGNORED_DIRS = {"__pycache__", ".git"}
DEFAULT_SCRIPT_ICON = "FILE_SCRIPT"


def normalize_path(path):
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))


def pretty_script_label(filename):
    stem = os.path.splitext(os.path.basename(filename))[0]
    return stem.replace("_", " ").replace("-", " ")


def choose_script_icon(filename):
    lowered = filename.lower()
    if any(token in lowered for token in ("vertex", "vert", "edge", "face")):
        return "VERTEXSEL"
    if any(token in lowered for token in ("mesh", "object", "snap")):
        return "MESH_DATA"
    if any(token in lowered for token in ("node", "geometry", "geo")):
        return "NODETREE"
    if any(token in lowered for token in ("material", "shader")):
        return "MATERIAL"
    if any(token in lowered for token in ("camera", "render")):
        return "RENDER_STILL"
    if any(token in lowered for token in ("light", "studio")):
        return "LIGHT"
    return DEFAULT_SCRIPT_ICON


def get_addon_preferences(context):
    addon = context.preferences.addons.get(__name__)
    return addon.preferences if addon else None


def resolve_scripts_folder(context):
    preferences = get_addon_preferences(context)
    if preferences is None or not preferences.scripts_folder:
        return ""
    return bpy.path.abspath(preferences.scripts_folder)


def list_python_scripts(folder, include_subfolders=True):
    if not folder or not os.path.isdir(folder):
        return []

    current_file = normalize_path(__file__)
    folder = os.path.abspath(folder)
    scripts = []

    if include_subfolders:
        for root, dirs, files in os.walk(folder):
            dirs[:] = sorted(
                [
                    directory
                    for directory in dirs
                    if not directory.startswith(".") and directory not in IGNORED_DIRS
                ],
                key=str.lower,
            )
            for filename in sorted(files, key=str.lower):
                if filename.startswith(".") or not filename.endswith(".py"):
                    continue
                path = os.path.join(root, filename)
                if normalize_path(path) == current_file:
                    continue
                relative_path = os.path.relpath(path, folder)
                relative_dir = os.path.dirname(relative_path)
                scripts.append(
                    {
                        "path": path,
                        "name": filename,
                        "label": pretty_script_label(filename),
                        "relative_path": relative_path.replace(os.sep, "/"),
                        "relative_dir": "" if relative_dir == "." else relative_dir.replace(os.sep, "/"),
                        "icon": choose_script_icon(filename),
                    }
                )
    else:
        for entry in sorted(os.scandir(folder), key=lambda item: item.name.lower()):
            if not entry.is_file():
                continue
            if entry.name.startswith(".") or not entry.name.endswith(".py"):
                continue
            if normalize_path(entry.path) == current_file:
                continue
            scripts.append(
                {
                    "path": entry.path,
                    "name": entry.name,
                    "label": pretty_script_label(entry.name),
                    "relative_path": entry.name,
                    "relative_dir": "",
                    "icon": choose_script_icon(entry.name),
                }
            )

    return scripts


def find_favorite_index(preferences, script_path):
    normalized_path = normalize_path(script_path)
    for index, item in enumerate(preferences.favorite_scripts):
        if normalize_path(item.filepath) == normalized_path:
            return index
    return -1


def is_favorite(preferences, script_path):
    return find_favorite_index(preferences, script_path) != -1


def annotate_scripts(preferences, scripts):
    annotated = []
    for script in scripts:
        item = dict(script)
        item["favorite"] = is_favorite(preferences, script["path"])
        annotated.append(item)
    return annotated


def filter_scripts(scripts, search_query="", favorites_only=False):
    query = search_query.strip().lower()
    filtered = []

    for script in scripts:
        if favorites_only and not script["favorite"]:
            continue

        if query:
            haystack = f"{script['name']} {script['relative_path']}".lower()
            if query not in haystack:
                continue

        filtered.append(script)

    return filtered


def sort_scripts(scripts, favorites_first=True):
    return sorted(
        scripts,
        key=lambda script: (
            0 if favorites_first and script["favorite"] else 1,
            script["relative_dir"].lower(),
            script["name"].lower(),
        ),
    )


def group_scripts_by_folder(scripts):
    groups = OrderedDict()
    for script in scripts:
        folder_label = script["relative_dir"] or "Root"
        groups.setdefault(folder_label, []).append(script)
    return groups


def tag_redraw_all_areas(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


@contextlib.contextmanager
def script_execution_environment(script_path):
    script_dir = os.path.dirname(script_path)
    previous_cwd = os.getcwd()
    path_added = False

    try:
        if script_dir and os.path.isdir(script_dir):
            os.chdir(script_dir)
            if script_dir not in sys.path:
                sys.path.insert(0, script_dir)
                path_added = True
        yield
    finally:
        os.chdir(previous_cwd)
        if path_added:
            try:
                sys.path.remove(script_dir)
            except ValueError:
                pass


class FOLDER_SCRIPT_RUNNER_FavoriteScript(bpy.types.PropertyGroup):
    filepath: StringProperty(name="File Path")


class FOLDER_SCRIPT_RUNNER_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    scripts_folder: StringProperty(
        name="Scripts Folder",
        subtype="DIR_PATH",
        description="Folder containing Blender Python scripts to list as buttons",
        default="",
    )
    include_subfolders: BoolProperty(
        name="Include Subfolders",
        description="Recursively list scripts from subfolders",
        default=True,
    )
    favorites_first: BoolProperty(
        name="Favorites First",
        description="Show favorite scripts before non-favorites",
        default=True,
    )
    favorite_scripts: CollectionProperty(type=FOLDER_SCRIPT_RUNNER_FavoriteScript)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "scripts_folder")
        row = layout.row(align=True)
        row.prop(self, "include_subfolders")
        row.prop(self, "favorites_first")


class FOLDER_SCRIPT_RUNNER_OT_refresh(bpy.types.Operator):
    bl_idname = "folder_script_runner.refresh"
    bl_label = "Refresh Scripts"
    bl_description = "Refresh the script list from the chosen folder"

    def execute(self, context):
        tag_redraw_all_areas(context)
        self.report({"INFO"}, "Script list refreshed")
        return {"FINISHED"}


class FOLDER_SCRIPT_RUNNER_OT_clear_search(bpy.types.Operator):
    bl_idname = "folder_script_runner.clear_search"
    bl_label = "Clear Search"
    bl_description = "Clear the current script search"

    def execute(self, context):
        context.window_manager.folder_script_runner_search = ""
        tag_redraw_all_areas(context)
        return {"FINISHED"}


class FOLDER_SCRIPT_RUNNER_OT_run_script(bpy.types.Operator):
    bl_idname = "folder_script_runner.run_script"
    bl_label = "Run Script"
    bl_description = "Run the selected Python script"

    filepath: StringProperty(
        name="Script File",
        subtype="FILE_PATH",
        options={"SKIP_SAVE"},
    )

    def execute(self, context):
        filepath = bpy.path.abspath(self.filepath)
        if not filepath or not os.path.isfile(filepath):
            self.report({"ERROR"}, "Script file not found")
            return {"CANCELLED"}

        if not filepath.endswith(".py"):
            self.report({"ERROR"}, "Only .py files can be run")
            return {"CANCELLED"}

        try:
            with script_execution_environment(filepath):
                runpy.run_path(filepath, run_name="__main__")
        except Exception as exc:
            traceback.print_exc()
            self.report({"ERROR"}, f"Script failed: {exc}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Ran {os.path.basename(filepath)}")
        return {"FINISHED"}


class FOLDER_SCRIPT_RUNNER_OT_toggle_favorite(bpy.types.Operator):
    bl_idname = "folder_script_runner.toggle_favorite"
    bl_label = "Toggle Favorite"
    bl_description = "Add or remove this script from favorites"

    filepath: StringProperty(
        name="Script File",
        subtype="FILE_PATH",
        options={"SKIP_SAVE"},
    )

    def execute(self, context):
        preferences = get_addon_preferences(context)
        if preferences is None:
            self.report({"ERROR"}, "Add-on preferences unavailable")
            return {"CANCELLED"}

        filepath = bpy.path.abspath(self.filepath)
        index = find_favorite_index(preferences, filepath)

        if index == -1:
            item = preferences.favorite_scripts.add()
            item.filepath = filepath
            self.report({"INFO"}, f"Added favorite: {os.path.basename(filepath)}")
        else:
            preferences.favorite_scripts.remove(index)
            self.report({"INFO"}, f"Removed favorite: {os.path.basename(filepath)}")

        tag_redraw_all_areas(context)
        return {"FINISHED"}


class FOLDER_SCRIPT_RUNNER_PT_panel(bpy.types.Panel):
    bl_label = "Folder Script Runner"
    bl_idname = "FOLDER_SCRIPT_RUNNER_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Scripts"

    def draw(self, context):
        layout = self.layout
        preferences = get_addon_preferences(context)

        if preferences is None:
            layout.label(text="Add-on preferences unavailable", icon="ERROR")
            return

        layout.prop(preferences, "scripts_folder", text="Folder", icon="FILE_FOLDER")

        options_row = layout.row(align=True)
        options_row.prop(preferences, "include_subfolders", text="Subfolders", toggle=True)
        options_row.prop(
            context.window_manager,
            "folder_script_runner_favorites_only",
            text="Favorites",
            toggle=True,
        )
        options_row.operator("folder_script_runner.refresh", text="Refresh", icon="FILE_REFRESH")

        search_row = layout.row(align=True)
        search_row.prop(
            context.window_manager,
            "folder_script_runner_search",
            text="",
            icon="VIEWZOOM",
        )
        search_row.operator("folder_script_runner.clear_search", text="", icon="PANEL_CLOSE")

        folder = resolve_scripts_folder(context)
        if not folder:
            layout.label(text="Choose a folder to list scripts.", icon="INFO")
            return

        if not os.path.isdir(folder):
            layout.label(text="Folder does not exist.", icon="ERROR")
            return

        scripts = list_python_scripts(folder, include_subfolders=preferences.include_subfolders)
        scripts = annotate_scripts(preferences, scripts)
        scripts = filter_scripts(
            scripts,
            search_query=context.window_manager.folder_script_runner_search,
            favorites_only=context.window_manager.folder_script_runner_favorites_only,
        )
        scripts = sort_scripts(scripts, favorites_first=preferences.favorites_first)
        groups = group_scripts_by_folder(scripts)

        favorite_count = sum(1 for script in scripts if script["favorite"])
        layout.label(
            text=f"{len(scripts)} script(s), {favorite_count} favorite(s)",
            icon="FILE_SCRIPT",
        )

        if not scripts:
            layout.label(text="No matching Python scripts found.", icon="INFO")
            return

        for folder_label, folder_scripts in groups.items():
            box = layout.box()
            box.label(text=folder_label, icon="FILE_FOLDER")

            column = box.column(align=True)
            for script in folder_scripts:
                row = column.row(align=True)
                favorite_icon = "CHECKBOX_HLT" if script["favorite"] else "CHECKBOX_DEHLT"
                favorite_button = row.operator(
                    "folder_script_runner.toggle_favorite",
                    text="",
                    icon=favorite_icon,
                )
                favorite_button.filepath = script["path"]

                run_button = row.operator(
                    "folder_script_runner.run_script",
                    text=script["label"],
                    icon=script["icon"],
                )
                run_button.filepath = script["path"]

                if script["relative_path"] != script["name"]:
                    path_row = column.row()
                    path_row.enabled = False
                    path_row.label(text=script["relative_path"])


classes = (
    FOLDER_SCRIPT_RUNNER_FavoriteScript,
    FOLDER_SCRIPT_RUNNER_Preferences,
    FOLDER_SCRIPT_RUNNER_OT_refresh,
    FOLDER_SCRIPT_RUNNER_OT_clear_search,
    FOLDER_SCRIPT_RUNNER_OT_run_script,
    FOLDER_SCRIPT_RUNNER_OT_toggle_favorite,
    FOLDER_SCRIPT_RUNNER_PT_panel,
)


def register():
    bpy.types.WindowManager.folder_script_runner_search = StringProperty(
        name="Search",
        description="Filter scripts by name or subfolder path",
        default="",
    )
    bpy.types.WindowManager.folder_script_runner_favorites_only = BoolProperty(
        name="Favorites Only",
        description="Show only favorite scripts",
        default=False,
    )

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.WindowManager.folder_script_runner_favorites_only
    del bpy.types.WindowManager.folder_script_runner_search


if __name__ == "__main__":
    register()
