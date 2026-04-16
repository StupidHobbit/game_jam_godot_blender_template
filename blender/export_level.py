"""
Blender → Godot 4 Level Export Script

ARCHITECTURE:
  Collection "Geometry"  → all static geo: floor, walls, terrain.
                           All mesh objects are exported together as <level>_geo.gltf.
  Collection "Props"     → repeating props (trees, barrels, rocks)
                           each UNIQUE MESH exported once as .gltf
                           all INSTANCES placed in .tscn via Transform3D
                           (use Alt+D in Blender to create linked duplicates!)
  Collection "Markers"   → Empty objects for spawning game entities
                           Custom Properties: type, scene

HOW TO USE:
  1. Model level geometry in "Geometry" collection
  2. Model each prop ONCE, then duplicate with Alt+D (linked duplicate)
     Place all prop instances in "Props" collection
  3. Add Empty objects in "Markers" collection with Custom Properties
  4. Run: blender --background level_01.blend --python blender/export_level.py

RESULT:
  assets/models/levels/level_01_geo.gltf        ← level geometry
  assets/models/props/<name>.gltf               ← each unique prop mesh (once)
  scenes/levels/level_01.tscn                   ← full scene with all instances
"""

import bpy
import math
import os
from collections import defaultdict
from mathutils import Matrix


_BLEND_DIR = os.path.dirname(bpy.data.filepath)
_BLEND_NAME = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
_ASSETS_DIR = os.path.join(_BLEND_DIR, "..", "assets")
_SCENES_DIR = os.path.join(_BLEND_DIR, "..", "scenes", "levels")
_TEXTURES_PATH = os.path.join(_ASSETS_DIR, "textures")

GEO_EXPORT_DIR = os.path.join(_ASSETS_DIR, "models", "levels")
PROPS_EXPORT_DIR = os.path.join(_ASSETS_DIR, "models", "props")

GEOMETRY_COLLECTION = "Geometry"
PROPS_COLLECTION = "Props"
MARKERS_COLLECTION = "Markers"

DEFAULT_SCENES: dict[str, str] = {
    "player_spawn": "",
    "enemy_spawn": "res://scenes/components/enemy_base.tscn",
    "collectible": "res://scenes/components/collectible.tscn",
    "trigger": "",
}


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

    title = "Level Export Report"
    if any(level == "ERROR" for level, _ in messages):
        title = "Level Export Failed"
    elif any(level == "WARN" for level, _ in messages):
        title = "Level Export Finished with Warnings"

    wm.popup_menu(draw, title=title, icon="INFO")


def _build_gltf_kwargs(
    filepath: str,
    export_dir: str,
    animations: bool = False,
    apply_modifiers: bool = True,
) -> dict:
    available = _available_gltf_params()
    textures_rel = os.path.relpath(_TEXTURES_PATH, export_dir)

    kwargs: dict = {
        "filepath": filepath,
        "use_selection": True,
        "export_format": "GLTF_SEPARATE",
        "export_yup": True,
        "export_apply": apply_modifiers,
        "export_materials": "EXPORT",
        "export_image_format": "AUTO",
        "export_animations": animations,
        "export_lights": False,
        "export_cameras": False,
    }

    optional: dict = {
        "export_normals": True,
        "export_tangents": True,
        "export_uvs": True,
        "export_texture_dir": textures_rel,
        "export_vertex_color": "MATERIAL",
        "export_colors": True,
        "export_skins": False,
        "export_morph": False,
    }

    if "export_vertex_color" in available:
        optional.pop("export_colors", None)
    else:
        optional.pop("export_vertex_color", None)

    for key, value in optional.items():
        if key in available:
            kwargs[key] = value

    return kwargs


def _mat4_to_godot(matrix: Matrix) -> str:
    """Convert a Blender Matrix4x4 to Godot Transform3D string (Y-up)."""
    m = matrix
    return (
        f"Transform3D("
        f"{m[0][0]:.6f}, {m[2][0]:.6f}, {-m[1][0]:.6f}, "
        f"{m[0][2]:.6f}, {m[2][2]:.6f}, {-m[1][2]:.6f}, "
        f"{-m[0][1]:.6f}, {-m[2][1]:.6f}, {m[1][1]:.6f}, "
        f"{m[0][3]:.6f}, {m[2][3]:.6f}, {-m[1][3]:.6f})"
    )


def _mat4_to_godot_obj(obj: bpy.types.Object) -> str:
    return _mat4_to_godot(obj.matrix_world)


def _export_single_mesh_object(
    obj: bpy.types.Object,
    filepath: str,
    export_dir: str,
    apply_modifiers: bool = True,
) -> None:
    """Select only `obj` and export it as glTF."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        **_build_gltf_kwargs(filepath, export_dir, apply_modifiers=apply_modifiers)
    )


# ---------------------------------------------------------------------------
# Geometry export
# ---------------------------------------------------------------------------

def export_geometry(messages: list[tuple[str, str]]) -> str:
    """Export all mesh objects from the 'Geometry' collection into one glTF."""
    os.makedirs(GEO_EXPORT_DIR, exist_ok=True)

    col = bpy.data.collections.get(GEOMETRY_COLLECTION)
    if not col:
        messages.append(("WARN", f"Collection '{GEOMETRY_COLLECTION}' not found."))
        return ""

    geometry_objects = [obj for obj in col.all_objects if obj.type == "MESH"]
    if not geometry_objects:
        messages.append(("INFO", f"No mesh objects in '{GEOMETRY_COLLECTION}'."))
        return ""

    filepath = os.path.join(GEO_EXPORT_DIR, f"{_BLEND_NAME}_geo.gltf")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in geometry_objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(**_build_gltf_kwargs(filepath, GEO_EXPORT_DIR))

    geo_res = f"res://assets/models/levels/{_BLEND_NAME}_geo.gltf"
    messages.append(("INFO", f"Geometry ({len(geometry_objects)} object(s)): {filepath}"))
    return geo_res


# ---------------------------------------------------------------------------
# Props
# ---------------------------------------------------------------------------

def export_props(messages: list[tuple[str, str]]) -> dict[str, str]:
    """
    Export each unique prop mesh once.
    Returns dict: mesh_data_name → res:// path
    Uses linked duplicates (Alt+D) — same mesh.data = same file.
    """
    os.makedirs(PROPS_EXPORT_DIR, exist_ok=True)

    col = bpy.data.collections.get(PROPS_COLLECTION)
    if not col:
        messages.append(("WARN", f"Collection '{PROPS_COLLECTION}' not found — no props exported."))
        return {}

    # Group objects by their mesh data (linked duplicates share the same mesh)
    mesh_groups: dict[str, list[bpy.types.Object]] = defaultdict(list)
    for obj in col.all_objects:
        if obj.type == "MESH" and obj.data:
            mesh_groups[obj.data.name].append(obj)

    mesh_to_res: dict[str, str] = {}

    for mesh_name, instances in mesh_groups.items():
        source = instances[0]
        safe_name = mesh_name.replace(".", "_").replace(" ", "_")
        filepath = os.path.join(PROPS_EXPORT_DIR, f"{safe_name}.gltf")

        original_matrix = source.matrix_world.copy()
        source.matrix_world = Matrix.Identity(4)
        try:
            _export_single_mesh_object(
                source,
                filepath,
                PROPS_EXPORT_DIR,
                apply_modifiers=False,
            )
        finally:
            source.matrix_world = original_matrix
        res_path = f"res://assets/models/props/{safe_name}.gltf"
        mesh_to_res[mesh_name] = res_path
        messages.append(("INFO", f"Prop '{mesh_name}' ({len(instances)} instance(s)): {filepath}"))

    return mesh_to_res


def collect_prop_instances(mesh_to_res: dict[str, str]) -> list[dict]:
    """Collect all prop instance transforms grouped by mesh."""
    col = bpy.data.collections.get(PROPS_COLLECTION)
    if not col:
        return []

    instances = []
    for obj in col.all_objects:
        if obj.type != "MESH" or not obj.data:
            continue
        res_path = mesh_to_res.get(obj.data.name)
        if not res_path:
            continue
        instances.append({
            "name": obj.name,
            "mesh": obj.data.name,
            "scene": res_path,
            "transform": _mat4_to_godot_obj(obj),
        })
    return instances


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

def collect_markers(messages: list[tuple[str, str]]) -> list[dict]:
    markers = []
    col = bpy.data.collections.get(MARKERS_COLLECTION)
    if not col:
        messages.append(("WARN", f"Collection '{MARKERS_COLLECTION}' not found."))
        return markers

    for obj in col.all_objects:
        if obj.type not in ("EMPTY", "MESH"):
            continue
        marker_type = str(obj.get("type", ""))
        if not marker_type:
            continue
        scene_path = str(obj.get("scene", DEFAULT_SCENES.get(marker_type, "")))
        markers.append({
            "name": obj.name,
            "type": marker_type,
            "scene": scene_path,
            "transform": _mat4_to_godot_obj(obj),
        })

    messages.append(("INFO", f"Markers: {len(markers)}"))
    return markers


# ---------------------------------------------------------------------------
# .tscn generation
# ---------------------------------------------------------------------------

def generate_tscn(
    geo_res: str,
    prop_instances: list[dict],
    markers: list[dict],
    messages: list[tuple[str, str]],
) -> None:
    os.makedirs(_SCENES_DIR, exist_ok=True)

    # Collect unique PackedScene resources (geo + props + markers)
    unique_scenes: list[str] = []
    if geo_res:
        unique_scenes.append(geo_res)
    for item in prop_instances + markers:
        path = item.get("scene", "")
        if path and path not in unique_scenes:
            unique_scenes.append(path)

    res_id_map = {path: f"{i + 1}_res" for i, path in enumerate(unique_scenes)}
    load_steps = len(unique_scenes) + 1

    lines: list[str] = [f"[gd_scene load_steps={load_steps} format=3]", ""]

    # PackedScene ext_resources (geo, props, markers)
    for path, res_id in res_id_map.items():
        lines.append(f'[ext_resource type="PackedScene" path="{path}" id="{res_id}"]')

    lines += ["", '[node name="Level" type="Node3D"]', ""]

    # Geometry
    if geo_res:
        lines.append(
            f'[node name="Geometry" parent="." instance=ExtResource("{res_id_map[geo_res]}")]'
        )
        lines.append("")

    # Player spawn
    player_spawn = next((m for m in markers if m["type"] == "player_spawn"), None)
    if player_spawn:
        lines.append('[node name="PlayerSpawn" type="Marker3D" parent="."]')
        lines.append(f'transform = {player_spawn["transform"]}')
        lines.append("")

    # Prop instances
    name_counts: dict[str, int] = defaultdict(int)
    for inst in prop_instances:
        safe_mesh = inst["mesh"].replace(".", "_").replace(" ", "_")
        name_counts[safe_mesh] += 1
        node_name = f"{safe_mesh}_{name_counts[safe_mesh]:03d}"
        res_id = res_id_map.get(inst["scene"], "")
        if not res_id:
            continue
        lines.append(
            f'[node name="{node_name}" parent="." instance=ExtResource("{res_id}")]'
        )
        lines.append(f'transform = {inst["transform"]}')
        lines.append("")

    # Entity markers
    for marker in markers:
        if marker["type"] == "player_spawn" or not marker["scene"]:
            continue
        res_id = res_id_map.get(marker["scene"], "")
        if not res_id:
            continue
        safe_name = marker["name"].replace(".", "_").replace(" ", "_")
        lines.append(
            f'[node name="{safe_name}" parent="." instance=ExtResource("{res_id}")]'
        )
        lines.append(f'transform = {marker["transform"]}')
        lines.append("")

    tscn_path = os.path.join(_SCENES_DIR, f"{_BLEND_NAME}.tscn")
    with open(tscn_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    messages.append(("INFO", f"Scene: {tscn_path}"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    messages: list[tuple[str, str]] = []
    if not bpy.data.filepath:
        messages.append(("ERROR", "Save the .blend file before running this script."))
        _report_summary(messages)
        return

    messages.append(("INFO", f"Exporting level: {_BLEND_NAME}"))
    geo_res = export_geometry(messages)
    mesh_to_res = export_props(messages)
    prop_instances = collect_prop_instances(mesh_to_res)
    markers = collect_markers(messages)
    generate_tscn(geo_res, prop_instances, markers, messages)

    total_props = len(prop_instances)
    unique_meshes = len(mesh_to_res)
    messages.append(
        (
            "INFO",
            f"Done: props {total_props} instance(s) from {unique_meshes} mesh(es).",
        )
    )
    _report_summary(messages)


# Run regardless of execution context:
# - blender --background file.blend --python export_level.py  (__name__ == "__main__")
# - Blender Scripting tab → Run Script                        (__name__ != "__main__")
main()
