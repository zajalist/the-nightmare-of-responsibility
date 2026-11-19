"""FBX round trip for the SK_Teen_* pieces: load an as-imported FBX back into the exact state export_ue.py exported
from (centimetre data, object scale 1, scene unit scale 0.01) and write it again with export_ue.py's settings, so the
only differences in a re-export are the ones we make."""
import bpy


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials):
        for x in list(coll):
            if not x.users:
                coll.remove(x)


def load(path, tag=""):
    """Import one SK_Teen FBX; returns (armature, [meshes]) in centimetres with identity object scale."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path, use_custom_normals=True, use_image_search=False)
    new = [o for o in bpy.data.objects if o not in before]
    rig = next(o for o in new if o.type == "ARMATURE")
    meshes = [o for o in new if o.type == "MESH"]
    s = rig.scale[0]
    assert abs(s - 0.01) < 1e-6 or abs(s - 1.0) < 1e-6, ("unexpected import scale", tuple(rig.scale))
    for o in [rig] + meshes:
        if o.parent is None:
            o.location /= s
        o.scale = (1, 1, 1) if o.parent is None else o.scale
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 0.01
    bpy.context.view_layer.update()
    if tag:
        for o in new:
            o["foa_src"] = tag
    return rig, meshes


def export(rig, obj, path):
    """export_ue.export_fbx, verbatim settings."""
    import os
    name = os.path.splitext(os.path.basename(path))[0]
    obj.name = name
    rig.name = rig.data.name = "Armature"
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"ARMATURE", "MESH"},
                             add_leaf_bones=False, bake_anim=False, apply_scale_options="FBX_SCALE_ALL",
                             use_armature_deform_only=True, mesh_smooth_type="FACE",
                             path_mode="COPY", embed_textures=True)


def snapshot(rig, mesh):
    """World-space rest data for comparisons: bone matrices, vertex positions, normals, weights."""
    bpy.context.view_layer.update()
    bones = {b.name: rig.matrix_world @ b.matrix_local for b in rig.data.bones}
    me = mesh.data
    verts = [mesh.matrix_world @ v.co for v in me.vertices]
    names = {g.index: g.name for g in mesh.vertex_groups}
    weights = [{names[g.group]: g.weight for g in v.groups if g.weight > 1e-5} for v in me.vertices]
    normals = [tuple(n.vector) for n in me.corner_normals] if hasattr(me, "corner_normals") else []
    return {"bones": bones, "verts": verts, "weights": weights, "normals": normals,
            "materials": [s.material.name if s.material else None for s in mesh.material_slots],
            "shape_keys": [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else []}
