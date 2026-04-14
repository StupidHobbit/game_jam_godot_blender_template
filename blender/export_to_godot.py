"""
Blender → Godot 4 Export Script
Run from Blender: Scripting tab → Open → Run Script
Or via CLI: blender --background file.blend --python export_to_godot.py
"""

import bpy
import os

EXPORT_PATH = os.path.join(os.path.dirname(bpy.data.filepath), "..", "assets", "models")
EXPORT_FORMAT = "GLTF_SEPARATE"  # .gltf + .bin + textures (best for Godot)


def prepare_mesh(obj: bpy.types.Object) -> None:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="OBJECT")

    # Apply all modifiers
    for modifier in obj.modifiers:
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    # Apply scale/rotation/location
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def export_object(obj: bpy.types.Object, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{obj.name}.gltf")

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)

    bpy.ops.export_scene.gltf(
        filepath=filepath,
        use_selection=True,
        export_format=EXPORT_FORMAT,
        export_yup=True,
        export_apply=False,
        export_animations=True,
        export_nla_strips=True,
        export_def_bones=False,
        export_optimize_animation_size=True,
        export_image_format="AUTO",
        export_texture_dir="textures",
        export_materials="EXPORT",
        export_colors=True,
        export_normals=True,
        export_tangents=True,
        export_uvs=True,
        export_skins=True,
        export_morph=True,
        export_lights=False,
        export_cameras=False,
    )
    print(f"[OK] Exported: {filepath}")


def export_all_meshes() -> None:
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]

    if not mesh_objects:
        print("[WARN] No mesh objects found in scene.")
        return

    for obj in mesh_objects:
        prepare_mesh(obj)
        category = obj.get("godot_category", "props")
        output_dir = os.path.join(EXPORT_PATH, category)
        export_object(obj, output_dir)

    print(f"\n[DONE] Exported {len(mesh_objects)} mesh(es) to: {EXPORT_PATH}")


def export_selected_only() -> None:
    selected = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]

    if not selected:
        print("[WARN] No mesh objects selected.")
        return

    for obj in selected:
        prepare_mesh(obj)
        category = obj.get("godot_category", "props")
        output_dir = os.path.join(EXPORT_PATH, category)
        export_object(obj, output_dir)

    print(f"\n[DONE] Exported {len(selected)} selected mesh(es).")


if __name__ == "__main__":
    export_all_meshes()
