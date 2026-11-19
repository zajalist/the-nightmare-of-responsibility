"""Offline look-dev of the exported fireplace with an approximation of M_FP_Master's wear logic (B&W EEVEE render).
  powershell -File P:/FoA-Tools/blender_scripts/run_blender.ps1 -Script P:/FoA/Tools/Fireplace/lookdev_blender.py
Writes P:/FoA-Tools/_work/fp_lookdev_{wide,insert}.png. Only for judging masks/values before the editor is free."""
import math
import os
import sys

sys.path.insert(0, r"P:\FoA-Tools\blender_scripts")
import bpy  # noqa: E402

import foa_common as C  # noqa: E402

SRC, TEX = r"P:\FoA-Assets\blender\Fireplace", r"P:\FoA-Assets\procedural\fireplace"
BRICK = r"P:\FoA-Assets\polyhaven\textures\medieval_red_brick\medieval_red_brick_diff_2k.jpg"


def img(path, linear=True):
    i = bpy.data.images.load(path, check_existing=True)
    if linear:
        i.colorspace_settings.name = 'Non-Color'
    return i


def worn(mat, mask_png, base, wear_col, wear_rough, grime_col, grime_rough, rough, metal=0.0, wear_metal=0.0, amount=0.45, sharp=6.0):
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    uv1 = nt.nodes.new("ShaderNodeUVMap")
    owner = next(o for o in bpy.data.objects if o.type == 'MESH' and mat.name in [m.name for m in o.data.materials])
    uv1.uv_map = owner.data.uv_layers[1].name  # the glTF importer renames UV1
    mtex = nt.nodes.new("ShaderNodeTexImage")
    mtex.image = img(mask_png)
    nt.links.new(uv1.outputs[0], mtex.inputs[0])
    gtex = nt.nodes.new("ShaderNodeTexImage")
    gtex.image = img(os.path.join(TEX, "T_FP_Grunge.png"))
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(mtex.outputs[0], sep.inputs[0])
    gsep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(gtex.outputs[0], gsep.inputs[0])

    def math_(op, a, b=None, clamp=False):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation, n.use_clamp = op, clamp
        for k, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[k].default_value = v
            else:
                nt.links.new(v, n.inputs[k])
        return n.outputs[0]

    convex = math_('MULTIPLY', sep.outputs[1], sep.outputs[2])
    edge = math_('MULTIPLY', convex, math_('ADD', gsep.outputs[1], 0.5))
    wear = math_('MULTIPLY', math_('SUBTRACT', edge, 1.0 - amount), sharp, clamp=True)
    grime = math_('MULTIPLY', math_('ADD', math_('SUBTRACT', 1.0, sep.outputs[2]), math_('MULTIPLY', math_('SUBTRACT', 1.0, sep.outputs[0]), 0.5)),
                  math_('ADD', gsep.outputs[1], 0.6), clamp=True)

    def mix(a, b, f):
        n = nt.nodes.new("ShaderNodeMix")
        n.data_type = 'RGBA'
        n.inputs[6].default_value = (*a, 1) if isinstance(a, tuple) else (0, 0, 0, 1)
        if not isinstance(a, tuple):
            nt.links.new(a, n.inputs[6])
        n.inputs[7].default_value = (*b, 1)
        nt.links.new(f, n.inputs[0])
        return n.outputs[2]

    col = mix(mix(base, wear_col, wear), grime_col, grime)
    ao = nt.nodes.new("ShaderNodeMix")
    ao.data_type = 'RGBA'
    ao.blend_type = 'MULTIPLY'
    ao.inputs[0].default_value = 0.6
    nt.links.new(col, ao.inputs[6])
    nt.links.new(mtex.outputs[0], ao.inputs[7])  # AO lives in R: close enough for a look-dev
    nt.links.new(ao.outputs[2], bsdf.inputs["Base Color"])
    r = math_('ADD', math_('MULTIPLY', wear, wear_rough - rough), rough)
    r = math_('ADD', math_('MULTIPLY', grime, grime_rough - rough), r)
    nt.links.new(r, bsdf.inputs["Roughness"])
    nt.links.new(math_('ADD', math_('MULTIPLY', wear, wear_metal - metal), metal), bsdf.inputs["Metallic"])


def main():
    C.reset()
    for n in ("SM_FP_Surround", "SM_FP_Insert", "SM_FP_Firebox", "SM_FP_Hearth", "SM_FP_Coal"):
        bpy.ops.import_scene.gltf(filepath=os.path.join(SRC, n + ".gltf"))
    M = bpy.data.materials
    worn(M["Paint"], os.path.join(TEX, "T_FP_Mask_Surround.png"), (0.50, 0.485, 0.45), (0.11, 0.08, 0.055), 0.75,
         (0.19, 0.15, 0.085), 0.7, 0.42)
    worn(M["Iron"], os.path.join(TEX, "T_FP_Mask_Insert.png"), (0.04, 0.04, 0.042), (0.5, 0.5, 0.51), 0.22,
         (0.07, 0.035, 0.018), 0.92, 0.48, metal=0.75, wear_metal=1.0, amount=0.55, sharp=5.0)
    worn(M["Slate"], os.path.join(TEX, "T_FP_Mask_Hearth.png"), (0.034, 0.035, 0.038), (0.12, 0.12, 0.13), 0.4,
         (0.02, 0.02, 0.02), 0.8, 0.5, amount=0.6, sharp=4.0)
    nt = M["Tiles"].node_tree
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img(os.path.join(TEX, "T_FP_Hearth_BaseColor.png"), linear=False)
    nt.links.new(t.outputs[0], nt.nodes["Principled BSDF"].inputs["Base Color"])
    nt = M["Brick"].node_tree
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img(BRICK, linear=False)
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = next(o for o in bpy.data.objects if o.name.startswith("SM_FP_Firebox")).data.color_attributes[0].name
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type, mul.blend_type = 'RGBA', 'MULTIPLY'
    mul.inputs[0].default_value = 1.0
    nt.links.new(t.outputs[0], mul.inputs[6])
    nt.links.new(vc.outputs[0], mul.inputs[7])
    nt.links.new(mul.outputs[2], nt.nodes["Principled BSDF"].inputs["Base Color"])
    for name, col, rough in (("Coal", (0.018, 0.017, 0.016), 0.55), ("Ash", (0.3, 0.29, 0.275), 1.0), ("Soot", (0.004,) * 3, 1.0)):
        b = M[name].node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = (*col, 1)
        b.inputs["Roughness"].default_value = rough
    C.preview_setup(cam_loc=(2.4, -1.0, 1.55), target=(0.0, 0.0, 0.62), lens=40, floor=True, bw=True,
                    key=(1.6, -2.6, 1.6), key_power=350, grey=0.05)
    for (y0, y1, z0, z1) in ((-0.8, -0.23, 0, 3), (0.23, 0.8, 0, 3), (-0.23, 0.23, 0.8, 3)):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(-0.002, (y0 + y1) / 2, (z0 + z1) / 2), rotation=(0, math.pi / 2, 0))
        o = bpy.context.active_object
        o.scale = (z1 - z0, y1 - y0, 1)
        o.data.materials.append(C.material("_Plaster", (0.45, 0.43, 0.4), 0.0, 0.9))
    C.render(r"P:\FoA-Tools\_work\fp_lookdev_wide.png")
    cam = bpy.context.scene.camera
    cam.location = (0.95, -0.42, 0.75)
    C.look_at(cam, (0.0, 0.0, 0.45))
    C.render(r"P:\FoA-Tools\_work\fp_lookdev_insert.png")


main()
