"""
Blender → Godot 4 Level Export Script

ARCHITECTURE:
  Collection "Geometry"  → all static geo: floor, walls, terrain AND grass.
                           Objects WITHOUT Geometry Nodes modifier:
                             → exported as level_01_geo.gltf (export_apply=True)
                           Objects WITH a Geometry Nodes modifier (grass scatter):
                             → exported as level_01_grass.gltf
                               (export_apply=False + export_gpu_instances=True)
                               Godot imports as MultiMeshInstance3D (1 draw call,
                               mesh stored once via EXT_mesh_gpu_instancing)
                           Detection is automatic — no separate collection needed.
                           IMPORTANT: do NOT add "Realize Instances" node in the
                           Geometry Nodes graph, or instances will be baked into
                           unique geometry and the file will bloat.
  Collection "Props"     → repeating props (trees, barrels, rocks)
                           each UNIQUE MESH exported once as .gltf
                           all INSTANCES placed in .tscn via Transform3D
                           (use Alt+D in Blender to create linked duplicates!)
  Collection "Markers"   → Empty objects for spawning game entities
                           Custom Properties: type, scene

HOW TO USE:
  1. Model unique geometry in "Geometry" collection
  2. Add grass: create a plane (grass_surface), add Geometry Nodes modifier,
     scatter grass_blade instances — NO Realize Instances node!
     Place grass_surface in "Geometry" collection alongside other geo.
  3. Model each prop ONCE, then duplicate with Alt+D (linked duplicate)
     Place all prop instances in "Props" collection
  4. Add Empty objects in "Markers" collection with Custom Properties
  5. Run: blender --background level_01.blend --python blender/export_level.py

RESULT:
  assets/models/levels/level_01_geo.gltf    ← regular geometry
  assets/models/levels/level_01_grass.gltf  ← grass (EXT_mesh_gpu_instancing)
  assets/models/props/<name>.gltf           ← each unique prop mesh (once)
  scenes/levels/level_01.tscn              ← full scene with all instances
"""

import bpy
import os
from collections import defaultdict


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


def _build_gltf_kwargs(
    filepath: str,
    export_dir: str,
    animations: bool = False,
    apply_modifiers: bool = True,
    gpu_instances: bool = False,
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

    # EXT_mesh_gpu_instancing — supported in Blender 4.x
    # Keeps Geometry Nodes instances compact (mesh stored once, transforms as array)
    if gpu_instances and "export_gpu_instances" in available:
        kwargs["export_gpu_instances"] = True

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


def _has_geometry_nodes(obj: bpy.types.Object) -> bool:
    """Return True if the object has at least one Geometry Nodes modifier."""
    return any(mod.type == "NODES" for mod in obj.modifiers)


def export_geometry() -> tuple[str, str]:
    """
    Export the 'Geometry' collection as up to two .gltf files:
      - level_01_geo.gltf   — regular meshes (export_apply=True)
      - level_01_grass.gltf — meshes with Geometry Nodes modifier
                              (export_apply=False + export_gpu_instances=True)
                              so EXT_mesh_gpu_instancing is preserved and Godot
                              imports them as MultiMeshInstance3D (1 draw call).

    Returns (geo_res, grass_res) — res:// paths, empty string if nothing exported.
    """
    os.makedirs(GEO_EXPORT_DIR, exist_ok=True)

    col = bpy.data.collections.get(GEOMETRY_COLLECTION)
    if not col:
        print(f"[WARN] Collection '{GEOMETRY_COLLECTION}' not found.")
        return "", ""

    regular_objs: list[bpy.types.Object] = []
    gn_objs: list[bpy.types.Object] = []

    for obj in col.all_objects:
        if obj.type != "MESH":
            continue
        if _has_geometry_nodes(obj):
            gn_objs.append(obj)
        else:
            regular_objs.append(obj)

    geo_res = ""
    grass_res = ""

    # --- Regular geometry ---
    if regular_objs:
        filepath = os.path.join(GEO_EXPORT_DIR, f"{_BLEND_NAME}_geo.gltf")
        bpy.ops.object.select_all(action="DESELECT")
        for obj in regular_objs:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(**_build_gltf_kwargs(filepath, GEO_EXPORT_DIR))
        geo_res = f"res://assets/models/levels/{_BLEND_NAME}_geo.gltf"
        print(f"[OK] Geometry ({len(regular_objs)} object(s)): {filepath}")
    else:
        print(f"[INFO] No regular mesh objects in '{GEOMETRY_COLLECTION}'.")

    # --- Geometry Nodes objects (grass, foliage, etc.) ---
    if gn_objs:
        filepath = os.path.join(GEO_EXPORT_DIR, f"{_BLEND_NAME}_grass.gltf")
        bpy.ops.object.select_all(action="DESELECT")
        for obj in gn_objs:
            obj.select_set(True)

        available = _available_gltf_params()
        if "export_gpu_instances" not in available:
            print(
                "[WARN] export_gpu_instances not available in this Blender version. "
                "Grass will be exported with apply_modifiers=True (instances baked). "
                "Upgrade to Blender 4.x for proper EXT_mesh_gpu_instancing support."
            )
            bpy.ops.export_scene.gltf(
                **_build_gltf_kwargs(filepath, GEO_EXPORT_DIR, apply_modifiers=True)
            )
        else:
            bpy.ops.export_scene.gltf(
                **_build_gltf_kwargs(
                    filepath,
                    GEO_EXPORT_DIR,
                    apply_modifiers=False,
                    gpu_instances=True,
                )
            )

        grass_res = f"res://assets/models/levels/{_BLEND_NAME}_grass.gltf"
        print(f"[OK] Grass/GN ({len(gn_objs)} object(s)): {filepath}")
    else:
        print(f"[INFO] No Geometry Nodes objects in '{GEOMETRY_COLLECTION}'.")

    return geo_res, grass_res


def export_props() -> dict[str, str]:
    """
    Export each unique prop mesh once.
    Returns dict: mesh_data_name → res:// path
    Uses linked duplicates (Alt+D) — same mesh.data = same file.
    """
    os.makedirs(PROPS_EXPORT_DIR, exist_ok=True)

    col = bpy.data.collections.get(PROPS_COLLECTION)
    if not col:
        print(f"[WARN] Collection '{PROPS_COLLECTION}' not found — no props exported.")
        return {}

    # Group objects by their mesh data (linked duplicates share the same mesh)
    mesh_groups: dict[str, list[bpy.types.Object]] = defaultdict(list)
    for obj in col.all_objects:
        if obj.type == "MESH" and obj.data:
            mesh_groups[obj.data.name].append(obj)

    mesh_to_res: dict[str, str] = {}

    for mesh_name, instances in mesh_groups.items():
        # Export only the first instance as the source mesh
        source = instances[0]
        safe_name = mesh_name.replace(".", "_").replace(" ", "_")
        filepath = os.path.join(PROPS_EXPORT_DIR, f"{safe_name}.gltf")

        bpy.ops.object.select_all(action="DESELECT")
        source.select_set(True)
        bpy.context.view_layer.objects.active = source

        bpy.ops.export_scene.gltf(**_build_gltf_kwargs(filepath, PROPS_EXPORT_DIR))
        res_path = f"res://assets/models/props/{safe_name}.gltf"
        mesh_to_res[mesh_name] = res_path
        print(f"[OK] Prop '{mesh_name}' ({len(instances)} instance(s)): {filepath}")

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
            "transform": _mat4_to_godot(obj),
        })
    return instances


def collect_markers() -> list[dict]:
    markers = []
    col = bpy.data.collections.get(MARKERS_COLLECTION)
    if not col:
        print(f"[WARN] Collection '{MARKERS_COLLECTION}' not found.")
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
            "transform": _mat4_to_godot(obj),
        })

    print(f"[OK] Markers: {len(markers)}")
    return markers


def _mat4_to_godot(obj: bpy.types.Object) -> str:
    """Convert Blender world matrix to Godot Transform3D (Y-up)."""
    m = obj.matrix_world
    return (
        f"Transform3D("
        f"{m[0][0]:.6f}, {m[2][0]:.6f}, {-m[1][0]:.6f}, "
        f"{m[0][2]:.6f}, {m[2][2]:.6f}, {-m[1][2]:.6f}, "
        f"{-m[0][1]:.6f}, {-m[2][1]:.6f}, {m[1][1]:.6f}, "
        f"{m[0][3]:.6f}, {m[2][3]:.6f}, {-m[1][3]:.6f})"
    )


def generate_tscn(
    geo_res: str,
    grass_res: str,
    prop_instances: list[dict],
    markers: list[dict],
) -> None:
    os.makedirs(_SCENES_DIR, exist_ok=True)

    # Collect unique PackedScene resources
    unique_scenes: list[str] = []
    if geo_res:
        unique_scenes.append(geo_res)
    if grass_res:
        unique_scenes.append(grass_res)
    for item in prop_instances + markers:
        path = item.get("scene", "")
        if path and path not in unique_scenes:
            unique_scenes.append(path)

    res_id_map = {path: f"{i + 1}_res" for i, path in enumerate(unique_scenes)}
    load_steps = len(unique_scenes) + 1  # +1 for the root node

    lines: list[str] = [f"[gd_scene load_steps={load_steps} format=3]", ""]

    for path, res_id in res_id_map.items():
        lines.append(f'[ext_resource type="PackedScene" path="{path}" id="{res_id}"]')

    lines += ["", '[node name="Level" type="Node3D"]', ""]

    if geo_res:
        lines.append(f'[node name="Geometry" parent="." instance=ExtResource("{res_id_map[geo_res]}")]')
        lines.append("")

    if grass_res:
        lines.append(f'[node name="Grass" parent="." instance=ExtResource("{res_id_map[grass_res]}")]')
        lines.append("")

    # Player spawn marker (special — just a Marker3D, no instancing)
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
        lines.append(f'[node name="{node_name}" parent="." instance=ExtResource("{res_id}")]')
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
        lines.append(f'[node name="{safe_name}" parent="." instance=ExtResource("{res_id}")]')
        lines.append(f'transform = {marker["transform"]}')
        lines.append("")

    tscn_path = os.path.join(_SCENES_DIR, f"{_BLEND_NAME}.tscn")
    with open(tscn_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[OK] Scene: {tscn_path}")


def main() -> None:
    if not bpy.data.filepath:
        print("[ERROR] Save the .blend file before running this script.")
        return

    print(f"\n=== Exporting level: {_BLEND_NAME} ===\n")
    geo_res, grass_res = export_geometry()
    mesh_to_res = export_props()
    prop_instances = collect_prop_instances(mesh_to_res)
    markers = collect_markers()
    generate_tscn(geo_res, grass_res, prop_instances, markers)

    total_props = len(prop_instances)
    unique_meshes = len(mesh_to_res)
    print(f"\n[DONE] {total_props} prop instance(s) from {unique_meshes} unique mesh(es).")


if __name__ == "__main__":
    main()
