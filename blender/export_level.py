"""
Blender → Godot 4 Level Export Script

ARCHITECTURE:
  Collection "Geometry"  → all static geo: floor, walls, terrain AND grass.
                           Objects WITHOUT Geometry Nodes modifier:
                             → exported as level_01_geo.gltf (export_apply=True)
                           Objects WITH a Geometry Nodes modifier (grass scatter):
                             → instances collected via depsgraph.object_instances
                             → each UNIQUE MESH exported once as a .gltf
                             → MultiMeshInstance3D written directly into .tscn
                               (mesh stored once, transforms as array — no duplication)
  Collection "Props"     → repeating props (trees, barrels, rocks)
                           each UNIQUE MESH exported once as .gltf
                           all INSTANCES placed in .tscn via Transform3D
                           (use Alt+D in Blender to create linked duplicates!)
  Collection "Markers"   → Empty objects for spawning game entities
                           Custom Properties: type, scene

HOW TO USE:
  1. Model unique geometry in "Geometry" collection
  2. Add grass: create a plane (grass_surface), add Geometry Nodes modifier,
     scatter grass_blade instances. Place grass_surface in "Geometry" collection.
     The script detects it automatically by the presence of a NODES modifier.
  3. Model each prop ONCE, then duplicate with Alt+D (linked duplicate)
     Place all prop instances in "Props" collection
  4. Add Empty objects in "Markers" collection with Custom Properties
  5. Run: blender --background level_01.blend --python blender/export_level.py

RESULT:
  assets/models/levels/level_01_geo.gltf         ← regular geometry
  assets/models/levels/grass/<mesh>.gltf         ← each unique grass mesh (once)
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
GRASS_EXPORT_DIR = os.path.join(_ASSETS_DIR, "models", "levels", "grass")
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


def _has_geometry_nodes(obj: bpy.types.Object) -> bool:
    """Return True if the object has at least one Geometry Nodes modifier."""
    return any(mod.type == "NODES" for mod in obj.modifiers)


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
) -> None:
    """Select only `obj` and export it as glTF."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(**_build_gltf_kwargs(filepath, export_dir))


# ---------------------------------------------------------------------------
# Grass: collect instances via depsgraph, export each unique mesh once
# ---------------------------------------------------------------------------

class GrassMeshData:
    """Holds export path and list of world-space transforms for one grass mesh."""
    def __init__(self, res_path: str):
        self.res_path = res_path          # res://assets/models/levels/grass/<name>.gltf
        self.transforms: list[str] = []  # Godot Transform3D strings


def collect_grass_instances(
    gn_objs: list[bpy.types.Object],
) -> dict[str, GrassMeshData]:
    """
    Iterate depsgraph.object_instances to find all instances spawned by the
    Geometry Nodes modifiers on `gn_objs`.

    Returns dict: mesh_data_name → GrassMeshData
      - each unique mesh is exported once
      - all instance transforms are collected per mesh
    """
    os.makedirs(GRASS_EXPORT_DIR, exist_ok=True)

    # Set of parent object names we care about
    gn_obj_names = {obj.name for obj in gn_objs}

    depsgraph = bpy.context.evaluated_depsgraph_get()

    # mesh_data_name → GrassMeshData
    grass_data: dict[str, GrassMeshData] = {}
    # mesh_data_name → source object (for export)
    mesh_source: dict[str, bpy.types.Object] = {}

    for inst in depsgraph.object_instances:
        # We only want instances whose parent is one of our GN scatter objects
        if not inst.is_instance:
            continue
        parent = inst.parent
        if parent is None or parent.original.name not in gn_obj_names:
            continue
        inst_obj = inst.object
        if inst_obj.type != "MESH" or inst_obj.data is None:
            continue

        mesh_name = inst_obj.data.name
        safe_name = mesh_name.replace(".", "_").replace(" ", "_")

        if mesh_name not in grass_data:
            res_path = f"res://assets/models/levels/grass/{safe_name}.gltf"
            grass_data[mesh_name] = GrassMeshData(res_path)
            mesh_source[mesh_name] = inst_obj.original  # original (non-evaluated)

        # inst.matrix_world is the world transform of this instance
        grass_data[mesh_name].transforms.append(_mat4_to_godot(inst.matrix_world))

    # Export each unique mesh once
    for mesh_name, data in grass_data.items():
        safe_name = mesh_name.replace(".", "_").replace(" ", "_")
        filepath = os.path.join(GRASS_EXPORT_DIR, f"{safe_name}.gltf")
        src_obj = mesh_source[mesh_name]
        _export_single_mesh_object(src_obj, filepath, GRASS_EXPORT_DIR)
        print(
            f"[OK] Grass mesh '{mesh_name}': {len(data.transforms)} instance(s) → {filepath}"
        )

    return grass_data


# ---------------------------------------------------------------------------
# Geometry export
# ---------------------------------------------------------------------------

def export_geometry() -> tuple[str, dict[str, GrassMeshData]]:
    """
    Export the 'Geometry' collection.

    Regular meshes → level_01_geo.gltf (export_apply=True).
    Meshes with Geometry Nodes modifier → instances collected via depsgraph,
    each unique mesh exported once, transforms stored for MultiMeshInstance3D.

    Returns (geo_res, grass_data):
      geo_res    — res:// path to geo gltf, or ""
      grass_data — dict mesh_name → GrassMeshData (may be empty)
    """
    os.makedirs(GEO_EXPORT_DIR, exist_ok=True)

    col = bpy.data.collections.get(GEOMETRY_COLLECTION)
    if not col:
        print(f"[WARN] Collection '{GEOMETRY_COLLECTION}' not found.")
        return "", {}

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

    # --- Geometry Nodes grass ---
    grass_data: dict[str, GrassMeshData] = {}
    if gn_objs:
        grass_data = collect_grass_instances(gn_objs)
        if not grass_data:
            print("[WARN] GN objects found but no instances collected from depsgraph.")
    else:
        print(f"[INFO] No Geometry Nodes objects in '{GEOMETRY_COLLECTION}'.")

    return geo_res, grass_data


# ---------------------------------------------------------------------------
# Props
# ---------------------------------------------------------------------------

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
            "transform": _mat4_to_godot_obj(obj),
        })
    return instances


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

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
            "transform": _mat4_to_godot_obj(obj),
        })

    print(f"[OK] Markers: {len(markers)}")
    return markers


# ---------------------------------------------------------------------------
# .tscn generation
# ---------------------------------------------------------------------------

def generate_tscn(
    geo_res: str,
    grass_data: dict[str, GrassMeshData],
    prop_instances: list[dict],
    markers: list[dict],
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

    # Grass meshes are Mesh resources, not PackedScenes — handled separately
    # res_path → internal resource id (for ext_resource)
    grass_mesh_res_ids: dict[str, str] = {}
    for i, (mesh_name, gd) in enumerate(grass_data.items()):
        grass_mesh_res_ids[gd.res_path] = f"grass_{i + 1}_mesh"

    res_id_map = {path: f"{i + 1}_res" for i, path in enumerate(unique_scenes)}
    load_steps = len(unique_scenes) + len(grass_mesh_res_ids) + 1

    lines: list[str] = [f"[gd_scene load_steps={load_steps} format=3]", ""]

    # PackedScene ext_resources (geo, props, markers)
    for path, res_id in res_id_map.items():
        lines.append(f'[ext_resource type="PackedScene" path="{path}" id="{res_id}"]')

    # Mesh ext_resources for grass
    for res_path, res_id in grass_mesh_res_ids.items():
        lines.append(f'[ext_resource type="Mesh" path="{res_path}" id="{res_id}"]')

    lines += ["", '[node name="Level" type="Node3D"]', ""]

    # Geometry
    if geo_res:
        lines.append(
            f'[node name="Geometry" parent="." instance=ExtResource("{res_id_map[geo_res]}")]'
        )
        lines.append("")

    # Grass — one MultiMeshInstance3D per unique mesh
    for mesh_name, gd in grass_data.items():
        safe_name = mesh_name.replace(".", "_").replace(" ", "_")
        mesh_res_id = grass_mesh_res_ids[gd.res_path]
        instance_count = len(gd.transforms)

        # Build the transform array for MultiMesh
        # Godot PackedFloat32Array for MultiMesh uses 12 floats per instance
        # (Transform3D = basis 3×3 + origin 3 = 12 floats, row-major)
        # We write it as a sub-resource inline.
        sub_res_id = f"{safe_name}_mm"

        lines.append(f'[sub_resource type="MultiMesh" id="{sub_res_id}"]')
        lines.append(f'transform_format = 1')  # TRANSFORM_3D
        lines.append(f'instance_count = {instance_count}')
        lines.append(f'mesh = ExtResource("{mesh_res_id}")')

        # Build packed float array: 12 floats per instance (Transform3D row-major)
        floats: list[str] = []
        for tf_str in gd.transforms:
            # tf_str is "Transform3D(a,b,c, d,e,f, g,h,i, tx,ty,tz)"
            inner = tf_str[len("Transform3D("):-1]
            floats.extend(v.strip() for v in inner.split(","))

        lines.append(f'instance_transforms = PackedFloat32Array({", ".join(floats)})')
        lines.append("")

        lines.append(f'[node name="Grass_{safe_name}" type="MultiMeshInstance3D" parent="."]')
        lines.append(f'multimesh = SubResource("{sub_res_id}")')
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

    total_grass = sum(len(gd.transforms) for gd in grass_data.values())
    print(f"[OK] Scene: {tscn_path}  (grass instances: {total_grass})")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if not bpy.data.filepath:
        print("[ERROR] Save the .blend file before running this script.")
        return

    print(f"\n=== Exporting level: {_BLEND_NAME} ===\n")
    geo_res, grass_data = export_geometry()
    mesh_to_res = export_props()
    prop_instances = collect_prop_instances(mesh_to_res)
    markers = collect_markers()
    generate_tscn(geo_res, grass_data, prop_instances, markers)

    total_props = len(prop_instances)
    unique_meshes = len(mesh_to_res)
    total_grass = sum(len(gd.transforms) for gd in grass_data.values())
    print(
        f"\n[DONE] props: {total_props} instance(s) from {unique_meshes} mesh(es), "
        f"grass: {total_grass} instance(s) from {len(grass_data)} mesh(es)."
    )


if __name__ == "__main__":
    main()
