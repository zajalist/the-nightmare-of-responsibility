"""Blender proof renders for the cloth lane (portable Blender, EEVEE, never saves a .blend).
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Cloth/render_proof.py <job> [outfit]
Jobs:
  polo_ba   polo close-up under one hard light, same idle pose: MPFB's current material | new material |
            new material + subdivision 1 (what the export should do)
  regions   each wrinkle channel engaged, weights forced 0 vs driven
  loop      arm reach + torso bend + knee loop, weights and phases driven by wrinkle_driver.py -> frames for a GIF
Output: P:/FoA/Saved/ClothShots/blender/<job>/*.png (colour; Tools/Cloth/compose.py makes the monochrome sheets)."""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, "P:/FoA/Tools/MPFB")
sys.path.insert(0, "P:/FoA/Tools/Cloth")
from load_teen import load_teen  # noqa: E402
from mpfb_common import args  # noqa: E402
import bake_wrinkles as bw  # noqa: E402  (posing helpers; its main() only runs as a script)
import wrinkle_driver as drv  # noqa: E402

BAKE = "P:/FoA-Assets/character/cloth/bake/"
SRC = "P:/FoA-Assets/character/cloth/src/"
MPFB_CLOTHES = "P:/FoA-Assets/_tools/blender-5.2.3-windows-x64/portable/extensions/.user/blender_org/mpfb/data/clothes/"
OUT = "P:/FoA/Saved/ClothShots/blender/"
CHANNELS = bw.CHANNELS

FABRICS = {  # garment -> look; micro tiles per UV unit come from px_per_m (bake json) / tile size
    "foa_polo_layered": dict(albedo=MPFB_CLOTHES + "foa_polo_layered/Polo_Base_Color.png",
                             macro=MPFB_CLOTHES + "foa_polo_layered/Polo_Normal_OpenGL.png",
                             micro=SRC + "waffle_pique_cotton/waffle_pique_cotton_nor_gl_2k.png",
                             uv_per_m=0.885, tile_m=0.06, micro_strength=0.4, rough=0.86, sheen=0.55, spec=0.35),
    "toigo_wool_pants": dict(albedo=MPFB_CLOTHES + "toigo_wool_pants/Pants_wool.png", macro=None,
                             micro=SRC + "caban/caban_nor_gl_2k.png",
                             uv_per_m=0.620, tile_m=0.20, micro_strength=0.6, rough=0.9, sheen=0.7, spec=0.3),
}


# ---------------------------------------------------------------- nodes
class G:
    def __init__(self, mat):
        self.nt = mat.node_tree
        self.x = -1600

    def node(self, kind, **props):
        n = self.nt.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        n.location = (self.x, 0)
        self.x += 40
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def math(self, op, a, b=None):
        n = self.node("ShaderNodeMath", operation=op)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                self.link(v, n.inputs[i])
        return n.outputs[0]

    def value(self, name, v=0.0):
        n = self.node("ShaderNodeValue", label=name, name=name)
        n.outputs[0].default_value = v
        return n.outputs[0]

    def tex(self, path, scale=None, alpha_packed=False):
        n = self.node("ShaderNodeTexImage")
        n.image = bpy.data.images.load(path, check_existing=True)
        n.image.colorspace_settings.name = "Non-Color"
        if alpha_packed:
            n.image.alpha_mode = "CHANNEL_PACKED"
        if scale:
            uv = self.node("ShaderNodeTexCoord")
            m = self.node("ShaderNodeMapping")
            m.inputs["Scale"].default_value = (scale, scale, 1)
            self.link(uv.outputs["UV"], m.inputs["Vector"])
            self.link(m.outputs[0], n.inputs["Vector"])
        return n

    def xy(self, color_socket):
        """Decode an RGB(A) normal colour into separate x, y sockets in -1..1."""
        sep = self.node("ShaderNodeSeparateColor")
        self.link(color_socket, sep.inputs[0])
        return [self.decode(sep.outputs[i]) for i in (0, 1)]

    def decode(self, s):
        """0..1 -> -1..1"""
        n = self.node("ShaderNodeMath", operation="MULTIPLY_ADD")
        self.link(s, n.inputs[0])
        n.inputs[1].default_value, n.inputs[2].default_value = 2.0, -1.0
        return n.outputs[0]


def madd(g, a, scale, b):  # a*scale + b, b may be None
    n = g.node("ShaderNodeMath", operation="MULTIPLY_ADD")
    g.link(a, n.inputs[0])
    if isinstance(scale, (int, float)):
        n.inputs[1].default_value = scale
    else:
        g.link(scale, n.inputs[1])
    if b is None:
        n.inputs[2].default_value = 0.0
    else:
        g.link(b, n.inputs[2])
    return n.outputs[0]


def build_material(garment, look, wrinkles=True):
    mat = bpy.data.materials.new("FoA_" + garment)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    g = G(mat)
    out = g.node("ShaderNodeOutputMaterial")
    bsdf = g.node("ShaderNodeBsdfPrincipled")
    g.link(bsdf.outputs[0], out.inputs[0])
    alb = g.tex(look["albedo"])
    alb.image.colorspace_settings.name = "sRGB"
    g.link(alb.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = look["rough"]
    bsdf.inputs["Specular IOR Level"].default_value = look["spec"]
    bsdf.inputs["Sheen Weight"].default_value = look["sheen"]
    bsdf.inputs["Sheen Roughness"].default_value = 0.5

    # micro (tiled knit/weave) + macro (garment seams) + wrinkles, blended by adding tangent-space slopes
    tiles = look["uv_per_m"] ** -1 / look["tile_m"]
    mx, my = g.xy(g.tex(look["micro"], scale=tiles).outputs["Color"])
    x, y = g.math("MULTIPLY", mx, look["micro_strength"]), g.math("MULTIPLY", my, look["micro_strength"])
    if look["macro"]:
        ax, ay = g.xy(g.tex(look["macro"]).outputs["Color"])
        x, y = g.math("ADD", x, ax), g.math("ADD", y, ay)
    if wrinkles:
        folds = g.tex(BAKE + garment + "_folds_gl.png", alpha_packed=True)
        mask = g.tex(BAKE + garment + "_mask.png", alpha_packed=True)
        sx, sy = g.xy(folds.outputs["Color"])                 # RG: slope of sin(theta)
        fsep = g.node("ShaderNodeSeparateColor")
        g.link(folds.outputs["Color"], fsep.inputs[0])
        cx, cy = g.decode(fsep.outputs[2]), g.decode(folds.outputs["Alpha"])   # BA: slope of cos(theta)
        msep = g.node("ShaderNodeSeparateColor")
        g.link(mask.outputs["Color"], msep.inputs[0])
        mch = [msep.outputs[0], msep.outputs[1], msep.outputs[2], mask.outputs["Alpha"]]
        side = g.node("ShaderNodeAttribute", attribute_name="foa_side").outputs["Fac"]
        W = P = M = None
        for i, ch in enumerate(CHANNELS):
            w = g.node("ShaderNodeMix", data_type="FLOAT")
            p = g.node("ShaderNodeMix", data_type="FLOAT")
            for n_, kind in ((w, "w"), (p, "p")):
                g.link(side, n_.inputs[0])
                g.link(g.value(kind + "R_" + ch), n_.inputs[2])
                g.link(g.value(kind + "L_" + ch), n_.inputs[3])
            W = madd(g, mch[i], w.outputs[0], W)
            P = madd(g, mch[i], p.outputs[0], P)
            M = mch[i] if M is None else g.math("ADD", M, mch[i])
        phi = g.math("DIVIDE", P, g.math("MAXIMUM", M, 0.001))
        cphi, sphi = g.math("COSINE", phi), g.math("SINE", phi)
        k = g.math("MULTIPLY", W, g.value("Wrinkle_Intensity", 1.0))
        k.node.name = "WRK_K"   # the driven per-pixel weight, shown by the maskviz job
        wx = g.math("MULTIPLY", g.math("ADD", g.math("MULTIPLY", sx, cphi), g.math("MULTIPLY", cx, sphi)), k)
        wy = g.math("MULTIPLY", g.math("ADD", g.math("MULTIPLY", sy, cphi), g.math("MULTIPLY", cy, sphi)), k)
        x, y = g.math("ADD", x, wx), g.math("ADD", y, wy)
    comb = g.node("ShaderNodeCombineXYZ")
    g.link(x, comb.inputs[0])
    g.link(y, comb.inputs[1])
    comb.inputs[2].default_value = 1.0
    nrm = g.node("ShaderNodeVectorMath", operation="NORMALIZE")
    g.link(comb.outputs[0], nrm.inputs[0])
    enc = g.node("ShaderNodeVectorMath", operation="MULTIPLY_ADD")
    g.link(nrm.outputs[0], enc.inputs[0])
    enc.inputs[1].default_value = (0.5, 0.5, 0.5)
    enc.inputs[2].default_value = (0.5, 0.5, 0.5)
    nm = g.node("ShaderNodeNormalMap", space="TANGENT")
    g.link(enc.outputs[0], nm.inputs["Color"])
    g.link(nm.outputs[0], bsdf.inputs["Normal"])
    return mat


# ---------------------------------------------------------------- scene
def side_attribute(obj, rest):
    attr = obj.data.attributes.new("foa_side", "FLOAT", "POINT")
    attr.data.foreach_set("value", [min(1.0, max(0.0, (p[0] + 0.03) / 0.06)) for p in rest])


def show_weight(mats):
    """Swap the surface for an emission of the driven wrinkle weight (white = folds at full strength)."""
    for m in mats:
        nt = m.node_tree
        em = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(nt.nodes["WRK_K"].outputs[0], em.inputs["Strength"])
        nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs[0])


def set_weights(mats, wl, wr, pl, pr, intensity=1.0):
    for m in mats:
        nodes = m.node_tree.nodes
        for i, ch in enumerate(CHANNELS):
            for name, v in (("wL_", wl[i]), ("wR_", wr[i]), ("pL_", pl[i]), ("pR_", pr[i])):
                nodes[name + ch].outputs[0].default_value = v
        nodes["Wrinkle_Intensity"].outputs[0].default_value = intensity


def heads(rig):
    return {pb.name: tuple(pb.head * 100) for pb in rig.pose.bones}


def setup_stage(target, cam_loc, lens=60):
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            continue
    sc.render.resolution_x = sc.render.resolution_y = 900
    sc.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w") if not sc.world else sc.world
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.012, 0.012, 0.012, 1)
    sun = bpy.data.objects.new("Key", bpy.data.lights.new("Key", "SUN"))
    sun.data.energy = 4.0
    sun.data.angle = math.radians(0.8)
    sc.collection.objects.link(sun)
    tgt = bpy.data.objects.new("Target", None)
    tgt.location = target
    sc.collection.objects.link(tgt)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    cam.data.lens = lens
    cam.location = cam_loc
    sc.collection.objects.link(cam)
    for o, t in ((cam, tgt), (sun, tgt)):
        c = o.constraints.new("TRACK_TO")
        c.target, c.track_axis, c.up_axis = t, "TRACK_NEGATIVE_Z", "UP_Y"
    sc.camera = cam
    return sun


def render(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("wrote", path)


def subdiv(obj, on):
    m = obj.modifiers.get("FoA_Subdiv")
    if on and not m:
        m = obj.modifiers.new("FoA_Subdiv", "SUBSURF")
        m.levels = m.render_levels = 1
        m.uv_smooth = "NONE"   # UVs stay linear inside each source face, so maps baked on the game mesh line up
    elif not on and m:
        obj.modifiers.remove(m)


def main():
    a = args()
    job = a[0] if a else "polo_ba"
    body, rig = load_teen()
    garments = {g: o for o in bpy.data.objects for g in FABRICS if o.type == "MESH" and o.name.endswith("." + g)}
    bw.reset_pose(rig)
    for g, o in garments.items():
        side_attribute(o, bw.world_coords(o))
    old = {g: o.data.materials[0] for g, o in garments.items()}
    new = {g: build_material(g, FABRICS[g]) for g in garments}
    polo = garments["foa_polo_layered"]
    out = OUT + job + "/"

    if job == "polo_ba":
        bw.pose_neutral(rig)
        sun = setup_stage(target=(0.16, 0.0, 1.30), cam_loc=(0.62, -0.78, 1.42), lens=70)
        sun.location = (2.6, 0.9, 2.0)   # hard key from the character's left, slightly behind: grazes chest and sleeve
        set_weights(new.values(), (0,) * 4, (0,) * 4, (0,) * 4, (0,) * 4)
        polo.data.materials[0] = old["foa_polo_layered"]
        render(out + "polo_1_before.png")
        polo.data.materials[0] = new["foa_polo_layered"]
        render(out + "polo_2_material.png")
        subdiv(polo, True)
        render(out + "polo_3_material_subdiv1.png")

    elif job in ("regions", "maskviz"):
        for g, o in garments.items():
            o.data.materials[0] = new[g]
            subdiv(o, True)
        for nm, fn in (("bind", bw.reset_pose), ("neutral", bw.pose_neutral)):
            fn(rig)
            print("ANGLES", nm, drv.angles(heads(rig)))
        shots = {  # channel: (pose, target, camera)
            "arm": (bw.POSES["arm"], (0.12, 0.0, 1.30), (0.95, -0.95, 1.55)),
            "arm_back": (bw.POSES["arm"], (0.10, 0.05, 1.30), (0.75, 1.15, 1.55)),
            "torso": (bw.POSES["torso"], (0.0, -0.05, 1.05), (0.55, -1.15, 1.25)),
            "knee": (bw.POSES["knee"], (0.15, 0.05, 0.50), (0.85, 0.95, 0.75)),
        }
        sun = setup_stage(target=(0, 0, 1.2), cam_loc=(1, -1, 1.4), lens=55)
        if job == "maskviz":
            show_weight(new.values())
        for name, (pose, tgt, cam) in shots.items():
            pose(rig)
            bpy.data.objects["Target"].location = tgt
            bpy.data.objects["Cam"].location = cam
            sun.location = Vector(cam) + Vector((0.8, 0.3, 1.5))
            wl, wr, pl, pr = drv.weights(heads(rig))
            print("WEIGHTS", name, [round(v, 2) for v in wl], [round(v, 2) for v in wr], drv.angles(heads(rig)))
            set_weights(new.values(), (0,) * 4, (0,) * 4, pl, pr)
            render(out + name + "_w0.png")
            for garment, material in new.items():
                set_weights([material], *drv.weights(heads(rig),garment=garment))
            render(out + name + "_w1.png")

    elif job == "loop":
        for g, o in garments.items():
            o.data.materials[0] = new[g]
            subdiv(o, True)
        sun = setup_stage(target=(0.10, -0.02, 1.22), cam_loc=(1.05, -1.25, 1.5), lens=50)
        sun.location = (2.4, -0.4, 2.8)
        n = int(a[1]) if len(a) > 1 else 24
        for f in range(n):
            t = 0.5 - 0.5 * math.cos(2 * math.pi * f / n)          # 0 -> 1 -> 0
            bw.pose_neutral(rig)
            bw.rotate(rig, "upperarm_l", (1, 0, 0), -75 * t)       # left arm reaches forward
            u, l = bw.bone_dir(rig, "upperarm_l"), bw.bone_dir(rig, "lowerarm_l")
            bw.rotate(rig, "lowerarm_l", u.cross(l), 70 * t)       # and bends the elbow
            bw.rotate(rig, "spine_01", (1, 0, 0), 14 * t)          # leans in
            bw.rotate(rig, "spine_03", (1, 0, 0), 8 * t)
            bw.rotate(rig, "thigh_r", (1, 0, 0), -35 * t)          # steps the right leg up
            bw.rotate(rig, "calf_r", (1, 0, 0), 60 * t)
            wl, wr, pl, pr = drv.weights(heads(rig), distance_cm=f / n * drv.STRIDE_CM)
            print("FRAME", f, [round(v, 2) for v in wl], [round(v, 2) for v in wr])
            for garment, material in new.items():
                set_weights([material], *drv.weights(heads(rig),distance_cm=f/n*drv.STRIDE_CM,garment=garment))
            render(out + "f%02d.png" % f)


main()
