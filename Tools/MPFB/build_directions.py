"""Build one heavier-teen direction with MPFB, game_engine rig, auto-fitted MakeHuman clothes, and render the pick-sheet stills.
  blender.exe -b --python Tools/MPFB/build_directions.py -- <A|B|C> [hair=<asset>] [brows=<asset>] [tag=<name>] [shots=all|front|none]
(or Tools/MPFB/run_blender.ps1 Tools/MPFB/build_directions.py A, which runs it at Idle priority)
Writes P:/FoA-Assets/character/mpfb/directions/<X>.blend and Saved/CharacterShots/mpfb/<X>_{front,tq,body}.png.
Every asset is CC0 (MakeHuman system assets and community packs: see P:/FoA-Assets/character/mpfb/SOURCES.txt).
Clothes are MakeHuman .mhclo assets: MPFB fits them to the body shape, hides the skin under them (delete groups) and
skins them to the same rig, so nothing here is hand- or AI-fitted."""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
from mpfb_common import ASSETS, SHOTS, args, ensure_dir, mpfb  # noqa: E402

HumanService = mpfb("services.humanservice", "HumanService")
TargetService = mpfb("services.targetservice", "TargetService")
AssetService = mpfb("services.assetservice", "AssetService")
LocationService = mpfb("services.locationservice", "LocationService")
NodeService = mpfb("services.nodeservice", "NodeService")
ObjectService = mpfb("services.objectservice", "ObjectService")

TEE, PANTS, SOCKS = "elvs_crude_t-shirt_male", "toigo_harem_pants", "joepal_crude_low_socks"  # harem pants read as pyjama bottoms
# MakeHuman age: 0.1875 = 11 y, 0.5 = 25 y. Its 11-year target is very childlike, so ~0.37 reads as a late teen.
DIRECTIONS = {
    "A": dict(
        label="A  Soft and round, freckled, messy mop, pale eyes",
        macro=dict(gender=1.0, age=0.41, muscle=0.35, weight=0.95, proportions=0.35, height=0.62,
                   race=dict(caucasian=0.9, african=0.05, asian=0.05)),
        targets={"head/head-round": 0.55, "head/head-fat-incr": 0.5, "neck/neck-double-incr": 0.45,
                 "cheek/l-cheek-volume-incr": 0.5, "cheek/r-cheek-volume-incr": 0.5, "nose/nose-volume-incr": 0.25,
                 "nose/nose-point-up": 0.3, "eyes/l-eye-bag-incr": 0.4,
                 "eyes/r-eye-bag-incr": 0.4, "asym/asym-ear-2-l": 0.7, "asym/asym-eye-3-r": 0.4,
                 "mouth/mouth-lowerlip-volume-incr": 0.3},
        heft=1.0, skin="toigo_light_skin_male_freckles", brows="mindfront_eyebrows_05", hair="short02",
        iris=((0.36, 0.45, 0.52, 1), (0.2, 0.27, 0.33, 1))),
    "B": dict(
        label="B  Big and tall, broad square face, close crop, dark eyes",
        macro=dict(gender=1.0, age=0.43, muscle=0.5, weight=0.92, proportions=0.45, height=0.75,
                   race=dict(caucasian=0.1, african=0.85, asian=0.05)),
        targets={"head/head-square": 0.5, "chin/chin-width-incr": 0.4, "neck/neck-scale-horiz-incr": 0.4,
                 "neck/neck-double-incr": 0.3, "torso/torso-scale-horiz-incr": 0.25, "eyebrows/eyebrows-trans-down": 0.3,
                 "nose/nose-flaring-incr": 0.3, "mouth/mouth-upperlip-volume-incr": 0.2, "asym/asym-brown-1-l": 0.6,
                 "asym/asym-jaw-2-r": 0.4},
        heft=1.15, skin="young_african_male", hair_tint=(0.13, 0.11, 0.1), brows="mindfront_eyebrows_06", hair="short01",
        iris=((0.16, 0.10, 0.06, 1), (0.08, 0.05, 0.03, 1))),
    "C": dict(
        label="C  Stocky and pear-shaped, tired heavy-lidded eyes behind glasses, jowls",
        macro=dict(gender=1.0, age=0.4, muscle=0.4, weight=0.92, proportions=0.3, height=0.64,
                   race=dict(caucasian=0.25, african=0.05, asian=0.7)),
        targets={"hip/hip-scale-horiz-incr": 0.4, "head/head-rectangular": 0.4, "chin/chin-width-incr": 0.35, "nose/nose-volume-incr": 0.35,
                 "neck/neck-double-incr": 0.5, "eyes/l-eye-eyefold-down": 0.6, "eyes/r-eye-eyefold-down": 0.6,
                 "eyes/l-eye-bag-incr": 0.6, "eyes/r-eye-bag-incr": 0.6, "mouth/mouth-angles-down": 0.3,
                 "asym/asym-eye-5-l": 0.6, "asym/asym-mouth-1-r": 0.5, "cheek/l-cheek-volume-incr": 0.4,
                 "cheek/r-cheek-volume-incr": 0.4},
        heft=1.15, skin="young_asian_male", brows="mindfront_eyebrows_08", hair="culturalibre_hair_02", extras=("frankyaye_glasses_library_male",),
        iris=((0.24, 0.17, 0.11, 1), (0.13, 0.09, 0.06, 1))),
}


# MakeHuman's default eyes are wide open, which reads as a stare; drop the lids a little on every direction.
RELAXED_EYES = {"eyes/l-eye-height2-decr": 0.35, "eyes/r-eye-height2-decr": 0.35,
                "eyes/l-eye-eyefold-down": 0.3, "eyes/r-eye-eyefold-down": 0.3}


# MakeHuman's weight slider tops out at "chubby"; these carry it to a clearly heavier build (scaled per direction).
HEFT = {"stomach/stomach-pregnant-incr": 0.45, "torso/torso-scale-depth-incr": 0.35, "torso/measure-waist-circ-incr": 0.5,
        "hip/hip-scale-horiz-incr": 0.2, "buttocks/buttocks-volume-incr": 0.3, "neck/neck-scale-horiz-incr": 0.3,
        "arms/l-upperarm-fat-incr": 0.5, "arms/r-upperarm-fat-incr": 0.5, "arms/l-lowerarm-fat-incr": 0.3,
        "arms/r-lowerarm-fat-incr": 0.3, "legs/l-upperleg-fat-incr": 0.5, "legs/r-upperleg-fat-incr": 0.5,
        "legs/l-lowerleg-fat-incr": 0.3, "legs/r-lowerleg-fat-incr": 0.3}


def find(name, subdir, ext="mhclo"):
    path = AssetService.find_asset_absolute_path(f"{name}.{ext}", asset_subdir=subdir)
    if path is None:
        raise FileNotFoundError(f"{name}.{ext} not in {subdir}: install its CC0 pack (Tools/MPFB/install_packs.py)")
    return path


def build(d):
    bpy.ops.wm.read_homefile(use_empty=True)
    body = HumanService.create_human(macro_detail_dict=d["macro"])
    root = LocationService.get_mpfb_data("targets")
    for t, w in {**RELAXED_EYES, **{k: v * d.get("heft", 1.0) for k, v in HEFT.items()}, **d["targets"]}.items():
        TargetService.load_target(body, os.path.join(root, t + ".target.gz"), weight=w)
    HumanService.set_character_skin(find(d["skin"], "skins", "mhmat"), body, skin_type="GAMEENGINE")
    rig = HumanService.add_builtin_rig(body, "game_engine")
    parts = [("eyes", "low-poly", "PROCEDURAL_EYES"), ("eyebrows", d["brows"], "GAMEENGINE"),
             ("eyelashes", "eyelashes02", "GAMEENGINE"), ("teeth", "teeth_base", "GAMEENGINE"),
             ("tongue", "tongue01", "GAMEENGINE"), ("hair", d["hair"], "GAMEENGINE")]
    for kind, name, mat in parts:
        obj = HumanService.add_mhclo_asset(find(name, kind), body, asset_type=kind, material_type=mat)
        if kind == "eyes":
            g = NodeService.find_first_node_by_type_name(obj.material_slots[0].material.node_tree, "ShaderNodeGroup")
            NodeService.set_socket_default_values(g, {"IrisMinorColor": d["iris"][0], "IrisMajorColor": d["iris"][1]})
    for name in (TEE, PANTS, SOCKS) + d.get("extras", ()):  # start outfit: sleep tee, loose pants, socks
        HumanService.add_mhclo_asset(find(name, "clothes"), body, asset_type="Clothes", material_type="GAMEENGINE")
    for obj in rig.children:
        if any(k in obj.name for k in ("eyebrow", "eyelash", d["hair"])):
            for slot in obj.material_slots:
                if slot.material and hasattr(slot.material, "surface_render_method"):
                    slot.material.surface_render_method = "DITHERED"
    if "hair_tint" in d:
        tint_hair(next(o for o in rig.children if d["hair"] in o.name), d["hair_tint"])
    bpy.context.view_layer.update()
    rig.location.z -= extent(body)[0]  # body targets shift the feet off the floor that create_human set
    return body, rig


def tint_hair(obj, rgb):
    """Multiply the hair's base-colour texture by rgb (short01's texture is a light grey-brown)."""
    for slot in obj.material_slots:
        nt = slot.material.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        link = bsdf.inputs["Base Color"].links[0]
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs[7].default_value = (*rgb, 1.0)
        nt.links.new(link.from_socket, mix.inputs[6])
        nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])


def extent(obj):
    """(lowest z, highest z) of the evaluated (shape-keyed, posed, masked) mesh."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    m = ev.to_mesh()
    zs = [(obj.matrix_world @ v.co).z for v in m.vertices]
    ev.to_mesh_clear()
    return min(zs), max(zs)


def relax_arms(rig, abduct=11):
    """A-pose to an arms-down idle: turn each upperarm onto straight-down, opened out by `abduct` degrees so the
    heavier torso doesn't swallow the arms. Computed from the bone direction, so it works for any body shape."""
    for side, out in (("l", 1), ("r", -1)):
        for bone, deg, fwd in (("upperarm", abduct, 0.0), ("lowerarm", abduct * 0.5, -0.12)):
            pb = rig.pose.bones[f"{bone}_{side}"]
            bpy.context.view_layer.update()
            v = (pb.tail - pb.head).normalized()
            want = Vector((out * math.sin(math.radians(deg)), fwd, -math.cos(math.radians(deg)))).normalized()
            r = Matrix.Translation(pb.head) @ Matrix.Rotation(v.angle(want), 4, v.cross(want).normalized()) @ Matrix.Translation(-pb.head)
            pb.matrix = r @ pb.matrix
            bpy.context.view_layer.update()


def stage():
    scn = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = eng
            break
        except TypeError:
            continue
    scn.render.resolution_x, scn.render.resolution_y = 900, 1100
    scn.render.film_transparent = False
    scn.view_settings.view_transform = "AgX"
    if hasattr(scn, "eevee"):
        scn.eevee.taa_render_samples = 64
    world = bpy.data.worlds.new("TMP_world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.11, 0.11, 0.115, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    scn.world = world
    lights = (("key", (-2.3, -1.3, 2.3), 320, 1.0), ("fill", (1.9, -1.8, 1.4), 45, 2.0), ("rim", (1.2, 2.0, 2.4), 260, 0.8))
    for name, loc, watts, size in lights:
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.size = watts, size
        obj = bpy.data.objects.new(name, data)
        scn.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (Vector((0, 0, 1.2)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scn.collection.objects.link(cam)
    scn.camera = cam
    return cam


def shoot(cam, target, dist, yaw_deg, lens, path):
    yaw = math.radians(yaw_deg)
    cam.data.lens = lens
    cam.location = target + Vector((math.sin(yaw) * dist, -math.cos(yaw) * dist, 0.0))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("wrote", path)


def main():
    a = args()
    key, opts = a[0], dict(x.split("=", 1) for x in a[1:] if "=" in x)
    d = dict(DIRECTIONS[key], **{k: v for k, v in opts.items() if k in ("hair", "brows", "skin")})
    tag = key + ("_" + opts["tag"] if "tag" in opts else "")
    body, rig = build(d)
    relax_arms(rig)
    if opts.get("shots", "all") != "none":
        cam = stage()
        out = ensure_dir(SHOTS)
        bpy.context.view_layer.update()
        eyes = ObjectService.find_object_of_type_amongst_nearest_relatives(body, "Eyes")
        face = sum((eyes.matrix_world @ Vector(c) for c in eyes.bound_box), Vector()) / 8 + Vector((0, 0, -0.03))
        height = extent(body)[1]
        shoot(cam, face, 1.1, 0, 85, f"{out}/{tag}_front.png")
        if opts.get("shots", "all") == "all":
            shoot(cam, face, 1.1, 35, 85, f"{out}/{tag}_tq.png")
            shoot(cam, Vector((0, 0, height * 0.5)), height * 1.8, 25, 50, f"{out}/{tag}_body.png")
    if "tag" not in opts:  # variants are look tests only; the direction file is the untagged build
        blend = os.path.join(ensure_dir(os.path.join(ASSETS, "directions")), f"{key}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend)
        # also an MPFB preset, so the user can start from it with New human > Presets
        HumanService.serialize_to_json_file(body, os.path.join(LocationService.get_user_config(), f"human.FoA_{key}.json"), save_clothes=True)
        print("saved", blend, "height_m", round(extent(body)[1], 3))


main()
