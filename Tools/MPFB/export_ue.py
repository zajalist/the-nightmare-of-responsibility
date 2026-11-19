"""Export the MPFB teen for Unreal: one FBX per piece on one armature, plus downsized textures and a manifest.
  pwsh -File Tools/MPFB/run_blender.ps1 -Blend <wake_layered.blend> Tools/MPFB/export_ue.py <out_dir> [extra=<suit_layered.blend>]
Inputs are the layered builds from layer_garments.py (same body, two outfits). Works in memory and never saves.
Pieces (all on SKEL_Teen):
  SK_Teen_Body   body with the body targets baked in. Skin under each garment isn't deleted: its faces sit in
                 "Skin_under_<garments>" material slots that BP_FoAPlayer hides while those garments are worn.
  SK_Teen_Head   head faces + eyes, brows, lashes, teeth, tongue, card hair, with ARKit-style face-unit morphs
                 (faceunits01, CC0). Stencil 4 in UE for the face slip; runs ABP_FoA_TeenHead (anim lane).
  SK_Teen_Polo/Pants/Socks (wake), SK_Teen_Suit/Shoes (suit). An inner garment's faces hidden under an outer one
                 (Hidden_by.*) sit in "<material>_under_<outer>" slots, hidden while the outer is worn.
The armature is exported as "Armature" (UE adds no extra root bone); its root bone is renamed "root"."""
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(__file__))
from mpfb_common import args, ensure_dir, mpfb  # noqa: E402

ObjectService = mpfb("services.objectservice", "ObjectService")
FaceService = mpfb("services.faceservice", "FaceService")
ARKIT = mpfb("services.faceservice", "ARKIT_FACEUNITS")

HEAD_PARTS = ("Eyes", "Eyebrows", "Eyelashes", "Teeth", "Tongue", "Hair")
NAMES = {"foa_polo_layered": "Polo", "toigo_wool_pants": "Pants", "joepal_crude_low_socks": "Socks",
         "male_elegantsuit01": "Suit", "shoes03": "Shoes"}
TEX_MAX = {"Body": 2048, "Head": 2048}  # everything else 1024


def mpfb_type(obj):
    return ObjectService.get_object_type(obj)


def short(obj_or_name):
    name = obj_or_name if isinstance(obj_or_name, str) else obj_or_name.name
    return name.split(".", 1)[-1]


def co(keyblock, n):
    a = np.empty(n * 3, dtype=np.float32)
    keyblock.data.foreach_get("co", a)
    return a


def bake_shape(obj):
    """Bake every modelling target into the mesh; keep only the face units, re-based on the baked shape."""
    keys = obj.data.shape_keys
    if not keys:
        return 0
    n = len(obj.data.vertices)
    kb = keys.key_blocks
    basis = co(kb[0], n)
    deltas = {k.name: co(k, n) - basis for k in kb if k.name in ARKIT}
    for k in kb:
        if k.name in ARKIT:
            k.value = 0.0
    mixed = co(obj.shape_key_add(name="__mix", from_mix=True), n)
    obj.shape_key_clear()
    obj.data.vertices.foreach_set("co", mixed)
    if deltas:
        obj.shape_key_add(name="Basis")
        for name, d in deltas.items():
            key = obj.shape_key_add(name=name, from_mix=False)
            key.data.foreach_set("co", mixed + d)
            key.value = 0.0  # Blender 5.2 creates these at 1; neutral previews must not sum all 52 expressions.
    obj.data.update()
    return len(deltas)


def edit_delete(obj, verts):
    bpy.context.view_layer.objects.active = obj
    for v in obj.data.vertices:
        v.select = v.index in verts
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="VERT")
    bpy.ops.mesh.delete(type="VERT")
    bpy.ops.object.mode_set(mode="OBJECT")


def drop_helpers(body):
    gi = body.vertex_groups["body"].index
    helpers = {v.index for v in body.data.vertices if not any(g.group == gi and g.weight > 0 for g in v.groups)}
    edit_delete(body, helpers)
    for vg in list(body.vertex_groups):
        if vg.name.startswith(("helper-", "joint-")) or vg.name in ("Mid", "Left", "Right", "body", "HelperGeometry", "JointCubes"):
            body.vertex_groups.remove(vg)
    return len(helpers)


def split_head(body, rig):
    """Separate the faces whose vertices mostly follow the head bone into their own object."""
    # Preserve the original smooth surface across the new neck boundary.
    body.data.normals_split_custom_set([n.vector.copy() for n in body.data.corner_normals])
    bones = {b.name for b in rig.data.bones}
    names = {vg.index: vg.name for vg in body.vertex_groups if vg.name in bones}
    head_v = set()
    for v in body.data.vertices:
        best = max(((g.weight, names[g.group]) for g in v.groups if g.group in names), default=(0, None))
        if best[1] == "head":
            head_v.add(v.index)
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for p in body.data.polygons:
        p.select = sum(i in head_v for i in p.vertices) * 2 > len(p.vertices)
    before = set(bpy.data.objects)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    new = [o for o in bpy.data.objects if o not in before]  # the separated piece (selection may hold others)
    assert len(new) == 1, f"head split made {len(new)} objects"
    bpy.ops.object.select_all(action="DESELECT")
    return new[0]


def slot_by_groups(obj, prefix, base_name, label):
    """Faces touching vertices of `prefix`* groups move to a copy of their material named
    '<base>_<label>_<group suffixes>' (what a Mask on those groups hid); then the groups are dropped."""
    groups = {vg.index: vg.name[len(prefix):] for vg in obj.vertex_groups if vg.name.startswith(prefix)}
    if not groups:
        return []
    member = [frozenset(g.group for g in v.groups if g.group in groups and g.weight > 0) for v in obj.data.vertices]
    made = {}
    for p in obj.data.polygons:
        sig = frozenset().union(*(member[i] for i in p.vertices))
        if not sig:
            continue
        src = obj.material_slots[p.material_index].material
        name = f"{base_name or src.name}_{label}_" + "+".join(sorted(short(groups[g]) for g in sig))
        if name not in made:
            m = src.copy()
            m.name = name
            obj.data.materials.append(m)
            made[name] = len(obj.data.materials) - 1
        p.material_index = made[name]
    for vg in [vg for vg in obj.vertex_groups if vg.name.startswith(prefix)]:
        obj.vertex_groups.remove(vg)
    return sorted(made)


def append_outfit(extra, rig, body):
    """Bring the other outfit's garments (and its body's Delete.* groups, by index: same base mesh) into this scene."""
    with bpy.data.libraries.load(extra, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n == "Human" or n.startswith("Human.")]
    other_body = next(o for o in dst.objects if o and o.name.startswith("Human") and mpfb_type(o) == "Basemesh")
    assert len(other_body.data.vertices) == len(body.data.vertices), "the two outfits must share the base mesh"
    copied = []
    for vg in other_body.vertex_groups:
        if not vg.name.startswith("Delete."):
            continue
        g = body.vertex_groups.get(vg.name) or body.vertex_groups.new(name=vg.name)
        for v in other_body.data.vertices:
            for e in v.groups:
                if e.group == vg.index and e.weight > 0:
                    g.add([v.index], e.weight, "REPLACE")
        copied.append(vg.name)
    garments = []
    for o in dst.objects:
        if o and o is not other_body and o.type == "MESH" and mpfb_type(o) == "Clothes":
            bpy.context.scene.collection.objects.link(o)
            o.parent = rig
            o.matrix_world.identity()
            for m in o.modifiers:
                if m.type == "ARMATURE":
                    m.object = rig
            garments.append(o)
    for o in dst.objects:  # drop the rest of the other build (its body, rig, hair...)
        if o and o not in garments:
            bpy.data.objects.remove(o)
    return garments, copied


def export_textures(obj, piece, out):
    """Downsize every image the materials use, write it to textures/, and point the material at the copy so the
    FBX embeds the game-size texture. Returns {material: {"base": file, "normal": file}}."""
    res, cap = {}, TEX_MAX.get(piece, 1024)
    for slot in obj.material_slots:
        m = slot.material
        if not m or not m.node_tree:
            continue
        entry = {}
        for node in m.node_tree.nodes:
            if node.type != "TEX_IMAGE" or not node.image:
                continue
            img = node.image
            name = f"T_Teen_{os.path.splitext(img.name)[0]}".replace(" ", "_").replace(".", "_")
            path = os.path.join(out, "textures", name + ".png")
            if not os.path.exists(path):
                copy = img.copy()
                w, h = copy.size
                if max(w, h) > cap:
                    copy.scale(int(w * cap / max(w, h)), int(h * cap / max(w, h)))
                copy.filepath_raw, copy.file_format = path, "PNG"
                copy.save()
                bpy.data.images.remove(copy)
            node.image = bpy.data.images.load(path, check_existing=True)
            entry[node.label or node.name] = os.path.basename(path)
        res[m.name] = entry
    return res


def export_fbx(rig, obj, path):
    obj.name = os.path.splitext(os.path.basename(path))[0]  # FBX names are case-insensitive in UE: Head would rename bone head
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"ARMATURE", "MESH"},
                             add_leaf_bones=False, bake_anim=False, apply_scale_options="FBX_SCALE_ALL",
                             use_armature_deform_only=True, mesh_smooth_type="FACE",
                             path_mode="COPY", embed_textures=True)


def main():
    a = args()
    out = ensure_dir(a[0])
    opts = dict(x.split("=", 1) for x in a[1:] if "=" in x)
    ensure_dir(os.path.join(out, "textures"))
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    body = ObjectService.find_object_of_type_amongst_nearest_relatives(rig, "Basemesh")
    for pb in rig.pose.bones:
        pb.matrix_basis.identity()
    rig.location = (0, 0, 0)
    extra_groups = []
    if opts.get("extra"):
        _, extra_groups = append_outfit(opts["extra"], rig, body)
    if not any(k.name == "eyeBlinkLeft" for k in (body.data.shape_keys.key_blocks if body.data.shape_keys else [])):
        FaceService.load_targets(body, load_microsoft_visemes=False, load_arkit_faceunits=True)
        FaceService.interpolate_targets(body)
    for o in rig.children:  # no subdivision in game; Mask modifiers become material slots below
        for m in list(o.modifiers):
            if m.type in ("SUBSURF", "MASK", "DATA_TRANSFER", "NODES"):
                o.modifiers.remove(m)
        if o is not body and o.data.shape_keys and mpfb_type(o) == "Clothes":
            o.shape_key_clear()  # face units interpolated onto clothes are noise
        elif o is not body and o.data.shape_keys:
            bake_shape(o)
    n_units = bake_shape(body)
    n_helpers = drop_helpers(body)
    head = split_head(body, rig)
    head.name = "Head"
    joins = [o for o in rig.children if mpfb_type(o) in HEAD_PARTS]
    bpy.ops.object.select_all(action="DESELECT")
    for o in joins:
        o.select_set(True)
    head.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.join()
    for vg in [vg for vg in head.vertex_groups if vg.name.startswith(("Delete.", "Hidden_by.", "Layer.", "Ride."))]:
        head.vertex_groups.remove(vg)
    with bpy.context.temp_override(object=head, active_object=head, selected_objects=[head]):
        bpy.ops.object.material_slot_remove_unused()
    body.name = "Body"
    body.material_slots[0].material.name = "Skin"
    skin_slots = slot_by_groups(body, "Delete.", "Skin", "under")
    rig.data.bones["Root"].name = "root"
    rig.name = rig.data.name = "Armature"
    pieces = {"Body": body, "Head": head}
    for o in list(rig.children):
        if o.type == "MESH" and o not in (body, head) and mpfb_type(o) == "Clothes":
            piece = NAMES.get(short(o), short(o))
            slot_by_groups(o, "Hidden_by.", None, "under")
            for vg in [vg for vg in o.vertex_groups if vg.name.startswith(("Layer.", "Ride.", "Delete."))]:
                o.vertex_groups.remove(vg)
            o.name = piece
            pieces[piece] = o
    # Centimetre-native rest data avoids UE importing a scale-100 skeleton, which breaks retarget translation.
    scale_cm = Matrix.Scale(100.0, 4)
    rig.data.transform(scale_cm)
    for obj in pieces.values():
        obj.data.transform(scale_cm, shape_keys=True)
        obj.location *= 100.0
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = .01
    bpy.context.view_layer.update()
    assert all(abs(s-1) < 1e-6 for s in rig.scale), 'Armature must carry no object scale'
    manifest = {"skeleton_root": "root", "units": "centimetres", "extra_body_groups": extra_groups, "pieces": {}}
    for piece, obj in pieces.items():
        asset = "SK_Teen_" + piece
        path = os.path.join(out, asset + ".fbx")
        textures = export_textures(obj, piece, out)
        export_fbx(rig, obj, path)
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        manifest["pieces"][asset] = {"fbx": os.path.basename(path), "tris": tris, "verts": len(obj.data.vertices),
                                     "slots": [s.material.name for s in obj.material_slots if s.material],
                                     "textures": textures,
                                     "morphs": [k.name for k in obj.data.shape_keys.key_blocks[1:]] if obj.data.shape_keys else []}
        print("wrote", path, "tris", tris, "slots", manifest["pieces"][asset]["slots"])
    manifest["skin_slots"] = skin_slots
    assert manifest["pieces"]["SK_Teen_Head"]["morphs"], "head has no face-unit morph targets"
    assert all(k in manifest["pieces"] for k in ("SK_Teen_Body", "SK_Teen_Head")), "missing body or head"
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    print("manifest", os.path.join(out, "manifest.json"), "face_units", n_units, "helpers_dropped", n_helpers,
          "skin_slots", skin_slots, "pieces", list(pieces))


if __name__ == '__main__':
    main()
