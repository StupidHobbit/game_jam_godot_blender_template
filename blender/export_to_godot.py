"""
Blender -> Godot 4 Export Script (Blender 4.x compatible)

HOW TO RELOAD IN BLENDER SCRIPTING TAB:
  1. Click the folder icon (Open) and select this file from disk
  2. OR in the Text menu: Text -> Reload
  3. Then press Run Script (Alt+P)

CLI usage:
  blender --background file.blend --python blender/export_to_godot.py
"""

import bpy
import os


_BLEND_DIR = os.path.dirname(bpy.data.filepath)
_ASSETS_DIR = os.path.join(_BLEND_DIR, "..", "assets")
EXPORT_PATH = os.path.join(_ASSETS_DIR, "models")
TEXTURES_PATH = os.path.join(_ASSETS_DIR, "textures")


def _available_gltf_params() -> set:
    return {p.identifier for p in bpy.ops.export_scene.gltf.get_rna_type().properties}


def _report_summary(messages: list[tuple[str, str]]) -> None:
    if not messages:
        return

    for level, message in messages:
        print(f"[{level}] {message}")

    wm = bpy.context.window_manager
    if wm is None:
        return

    def draw(self, _context) -> None:
        for level, message in messages:
            icon = {
                "INFO": "INFO",
                "WARN": "ERROR",
                "ERROR": "CANCEL",
            }.get(level, "INFO")
            self.layout.label(text=message, icon=icon)

    title = "Export Report"
    if any(level == "ERROR" for level, _ in messages):
        title = "Export Failed"
    elif any(level == "WARN" for level, _ in messages):
        title = "Export Finished with Warnings"

    wm.popup_menu(draw, title=title, icon="INFO")


def _safe_export(filepath: str, output_dir: str) -> None:
    """Call gltf exporter with only params supported by the current Blender build."""
    available = _available_gltf_params()
    textures_rel = os.path.relpath(TEXTURES_PATH, output_dir)

    # Minimal required params — always present in any Blender 3/4 build
    kwargs: dict = {
        "filepath": filepath,
        "use_selection": True,
        "export_format": "GLTF_SEPARATE",
        "export_yup": True,
        "export_apply": False,
        "export_materials": "EXPORT",
        "export_image_format": "AUTO",
        "export_animations": True,
        "export_lights": False,
        "export_cameras": False,
    }

    # Optional params — added only if present in this Blender version
    optional: dict = {
        # Geometry
        "export_normals": True,
        "export_tangents": True,
        "export_uvs": True,
        "export_texture_dir": textures_rel,
        # Vertex colors (API changed in Blender 4.2)
        "export_vertex_color": "MATERIAL",
        "export_colors": True,
        # Skinning
        "export_skins": True,
        "export_def_bones": False,
        # Shape keys
        "export_morph": True,
        "export_morph_normal": True,
        # Animation
        "export_nla_strips": True,
        "export_optimize_animation_size": True,
        "export_anim_single_armature": True,
        "export_nla_strips_merged_animation_name": "merged",
    }

    # Vertex color: only one of the two params should be added
    if "export_vertex_color" in available:
        optional.pop("export_colors", None)
    else:
        optional.pop("export_vertex_color", None)

    for key, value in optional.items():
        if key in available:
            kwargs[key] = value

    bpy.ops.export_scene.gltf(**kwargs)


def prepare_mesh(obj: bpy.types.Object) -> None:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="OBJECT")
    for modifier in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        except RuntimeError:
            pass
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def export_object(obj: bpy.types.Object, output_dir: str, messages: list[tuple[str, str]]) -> None:
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{obj.name}.gltf")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    _safe_export(filepath, output_dir)
    messages.append(("INFO", f"Exported: {filepath}"))


def export_all_meshes() -> None:
    messages: list[tuple[str, str]] = []
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    if not mesh_objects:
        messages.append(("WARN", "No mesh objects found in scene."))
        _report_summary(messages)
        return
    for obj in mesh_objects:
        prepare_mesh(obj)
        category = str(obj.get("godot_category", "props"))
        export_object(obj, os.path.join(EXPORT_PATH, category), messages)
    messages.append(("INFO", f"Exported {len(mesh_objects)} mesh(es) to: {EXPORT_PATH}"))
    _report_summary(messages)


def export_selected_only() -> None:
    messages: list[tuple[str, str]] = []
    selected = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    if not selected:
        messages.append(("WARN", "No mesh objects selected."))
        _report_summary(messages)
        return
    for obj in selected:
        prepare_mesh(obj)
        category = str(obj.get("godot_category", "props"))
        export_object(obj, os.path.join(EXPORT_PATH, category), messages)
    messages.append(("INFO", f"Exported {len(selected)} selected mesh(es)."))
    _report_summary(messages)


if __name__ == "__main__":
    export_all_meshes()
