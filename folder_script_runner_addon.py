bl_info = {
    "name": "Folder Script Runner",
    "author": "Zsolt Sandor + Codex",
    "version": (1, 0, 0),
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

import bpy
from bpy.props import StringProperty


def get_addon_preferences(context):
    addon = context.preferences.addons.get(__name__)
    return addon.preferences if addon else None


def resolve_scripts_folder(context):
    preferences = get_addon_preferences(context)
    if preferences is None or not preferences.scripts_folder:
        return ""
    return bpy.path.abspath(preferences.scripts_folder)


def list_python_scripts(folder):
    if not folder or not os.path.isdir(folder):
        return []

    current_filename = os.path.basename(__file__)
    scripts = []
    for entry in os.scandir(folder):
        if not entry.is_file():
            continue
        if entry.name.startswith(".") or not entry.name.endswith(".py"):
            continue
        if entry.name == current_filename:
            continue
        scripts.append(entry.path)

    return sorted(scripts, key=lambda path: os.path.basename(path).lower())


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


class FOLDER_SCRIPT_RUNNER_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    scripts_folder: StringProperty(
        name="Scripts Folder",
        subtype="DIR_PATH",
        description="Folder containing Blender Python scripts to list as buttons",
        default="",
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "scripts_folder")


class FOLDER_SCRIPT_RUNNER_OT_refresh(bpy.types.Operator):
    bl_idname = "folder_script_runner.refresh"
    bl_label = "Refresh Scripts"
    bl_description = "Refresh the script list from the chosen folder"

    def execute(self, context):
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        self.report({"INFO"}, "Script list refreshed")
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

        layout.prop(preferences, "scripts_folder", text="Folder")

        row = layout.row(align=True)
        row.operator("folder_script_runner.refresh", text="Refresh", icon="FILE_REFRESH")

        folder = resolve_scripts_folder(context)
        if not folder:
            layout.label(text="Choose a folder to list scripts.", icon="INFO")
            return

        if not os.path.isdir(folder):
            layout.label(text="Folder does not exist.", icon="ERROR")
            return

        scripts = list_python_scripts(folder)
        layout.label(text=f"{len(scripts)} script(s) found", icon="FILE_SCRIPT")

        if not scripts:
            layout.label(text="No Python scripts in this folder.", icon="INFO")
            return

        column = layout.column(align=True)
        for script_path in scripts:
            label = os.path.splitext(os.path.basename(script_path))[0].replace("_", " ")
            operator = column.operator(
                "folder_script_runner.run_script",
                text=label,
                icon="PLAY",
            )
            operator.filepath = script_path


classes = (
    FOLDER_SCRIPT_RUNNER_Preferences,
    FOLDER_SCRIPT_RUNNER_OT_refresh,
    FOLDER_SCRIPT_RUNNER_OT_run_script,
    FOLDER_SCRIPT_RUNNER_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
