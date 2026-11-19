"""READ-ONLY audit: Blueprints whose component tree has the old blueprint_add_component multi-root shape.

Run inside the open editor (works on today's DLL; it only reads):
    $env:FOA_AREAS='QA'; python Tools/Unreal/ue_remote.py Tools/QA/audit_scs_roots.py [AUDIT_ROOT=/Game/FoA] [AUDIT_OFFSET=0] [AUDIT_LIMIT=200]

Before Hayba restart 11, blueprint_add_component added every component as an SCS ROOT node: the first one became the
actor's RootComponent and the rest hung off nothing. UI's BP_ItemInspect broke this way: the mesh was the root, so its
"relative" location acted as a world transform and the item rendered at the world origin.

Flags per Blueprint:
  multi_root     more than one scene component with no parent (only one can be the RootComponent; the others are
                 not attached to anything);
  visual_root    the root is a primitive (mesh, sprite, ...) the Blueprint itself added, not a SceneComponent pivot;
  offset_root    that root carries a non-zero relative location/rotation, the BP_ItemInspect symptom (on a root it is
                 the actor's world placement, not an offset).
Writes Saved/Audit/scs_roots_<stamp>.json and prints one line per flagged Blueprint plus the full component tree.
Nothing is saved, compiled, modified or spawned, and the source stays inside the python_run policy.
"""
import json
import os
import time

import unreal

ROOT = os.environ.get("AUDIT_ROOT", "/Game/FoA")
OFFSET = int(os.environ.get("AUDIT_OFFSET", "0"))
LIMIT = int(os.environ.get("AUDIT_LIMIT", "200"))

SDS = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
LIB = unreal.SubobjectDataBlueprintFunctionLibrary
registry = unreal.AssetRegistryHelpers.get_asset_registry()
flt = unreal.ARFilter(package_paths=[ROOT], class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "Blueprint")],
                      recursive_paths=True, recursive_classes=True)
assets = sorted(registry.get_assets(flt), key=lambda a: str(a.package_name))
batch = assets[OFFSET:OFFSET + LIMIT]


def vec_nonzero(v):
    return v is not None and (abs(v.x) > 0.01 or abs(v.y) > 0.01 or abs(v.z) > 0.01)


def rot_nonzero(r):
    return r is not None and (abs(r.pitch) > 0.01 or abs(r.yaw) > 0.01 or abs(r.roll) > 0.01)


def component_tree(bp):
    """[{name, class, parent, scene, root, inherited, default_scene_root, rel_loc, rel_rot}] for every component."""
    out = []
    for h in SDS.k2_gather_subobject_data_for_blueprint(bp):
        d = LIB.get_data(h)
        if not LIB.is_component(d):
            continue  # the actor itself
        obj = LIB.get_object_for_blueprint(d, bp)
        ph = LIB.get_parent_handle(d)
        parent = ""
        if LIB.is_handle_valid(ph):
            pd = LIB.get_data(ph)
            parent = "" if LIB.is_actor(pd) else str(LIB.get_variable_name(pd))
        scene = bool(LIB.is_scene_component(d))
        rel_loc = obj.get_editor_property("relative_location") if (scene and obj is not None) else None
        rel_rot = obj.get_editor_property("relative_rotation") if (scene and obj is not None) else None
        out.append({
            "name": str(LIB.get_variable_name(d)),
            "class": obj.get_class().get_name() if obj is not None else "",
            "parent": parent,
            "scene": scene,
            "root": bool(LIB.is_root_component(d)),
            "inherited": bool(LIB.is_inherited_component(d)) or bool(LIB.is_native_component(d)),
            "default_scene_root": bool(LIB.is_default_scene_root(d)),
            "primitive": obj is not None and isinstance(obj, unreal.PrimitiveComponent),
            "rel_loc": [round(rel_loc.x, 2), round(rel_loc.y, 2), round(rel_loc.z, 2)] if rel_loc is not None else None,
            "rel_rot": [round(rel_rot.pitch, 2), round(rel_rot.yaw, 2), round(rel_rot.roll, 2)] if rel_rot is not None else None,
            "_loc": rel_loc, "_rot": rel_rot,
        })
    return out


report = {"root": ROOT, "total_blueprints": len(assets), "offset": OFFSET, "checked": 0, "flagged": [], "skipped": []}
for a in batch:
    path = str(a.package_name)
    bp = unreal.load_asset(path)
    if bp is None or not isinstance(bp, unreal.Blueprint):
        report["skipped"].append({"path": path, "why": "not a Blueprint"})
        continue
    gen = unreal.EditorAssetLibrary.load_blueprint_class(path)
    if gen is None or not unreal.MathLibrary.class_is_child_of(gen, unreal.Actor):
        continue  # function libraries, widgets, components: no actor component tree
    tree = component_tree(bp)
    report["checked"] += 1
    unparented = [c for c in tree if c["scene"] and c["parent"] == ""]
    root = next((c for c in tree if c["root"]), None)
    flags = []
    if len(unparented) > 1:
        flags.append("multi_root")
    if root is not None and root["primitive"] and not root["inherited"]:
        flags.append("visual_root")
        if vec_nonzero(root["_loc"]) or rot_nonzero(root["_rot"]):
            flags.append("offset_root")
    for c in tree:
        c.pop("_loc")
        c.pop("_rot")
    if flags:
        report["flagged"].append({"path": path, "flags": flags, "root": root["name"] if root else None,
                                  "unparented": [c["name"] for c in unparented], "components": tree})

out_dir = os.path.join(unreal.Paths.project_saved_dir(), "Audit")
if not os.path.isdir(out_dir):
    os.makedirs(out_dir)
out_path = os.path.join(out_dir, "scs_roots_%d.json" % int(time.time()))
open(out_path, "w", encoding="utf-8").write(json.dumps(report, indent=2))

print("AUDIT %s: %d Blueprints, checked %d actor Blueprints (offset %d), flagged %d" % (
    ROOT, len(assets), report["checked"], OFFSET, len(report["flagged"])))
for f in report["flagged"]:
    print("FLAG %s  [%s]  root=%s  unparented=%s" % (f["path"], ",".join(f["flags"]), f["root"], ",".join(f["unparented"])))
    for c in f["components"]:
        print("    %s%s (%s) parent=%s loc=%s rot=%s" % ("* " if c["root"] else "  ", c["name"], c["class"],
                                                      c["parent"] or "-", c["rel_loc"], c["rel_rot"]))
if OFFSET + LIMIT < len(assets):
    print("MORE: rerun with AUDIT_OFFSET=%d" % (OFFSET + LIMIT))
print("REPORT " + out_path)
