"""Battle-garment clips, authored procedurally on each garment's own rig (rig lane, 2026-11-10).
  pwsh -File Tools/MPFB/run_blender.ps1 -Blend P:/FoA-Assets/character/garments/rig/SK_Garment_<G>.blend Tools/Rig/garment_anims.py garment=<G> [render=1]
Writes P:/FoA-Assets/character/garments/rig/anim/SK_Garment_<G>.fbx (armature + mesh + these takes) and the matching
.blend; never saves the source blend. The FBX keeps the source file name, so UE names the takes exactly like the
existing ones (SK_Garment_<G>Armature_<Take>) and the attack clip replaces the one PDA_Opponent.AttackAnim points at.
Takes (30 fps): Idle (60, loops: breathing bob, sway, hem/sleeve/leg flutter as waves running down each chain),
Telegraph (30, wind-up held with a tremble), the attack under its existing name (Lash / Kick / Hop / CoilStrike: wind-up,
strike with overshoot, follow-through), HitReact (18, recoil with the chains whipping after), Stun (60, loops: slumped,
woozy), Defeat (45, tremble then collapse; ends low and limp for the sand pour).
Pose language, all in the model's frame (it faces -Y, its left is +X): fwd = swing a bone's tip toward the front,
out = swing it toward its own side (+X on the left chains), twist = about the bone; children inherit."""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

A = dict(x.split("=", 1) for x in sys.argv[sys.argv.index("--") + 1:] if "=" in x)
G = A["garment"]
OUT = "P:/FoA-Assets/character/garments/rig/anim"
FPS = 30
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH")
PB = arm.pose.bones
CHAINS = {
    "Shirt": {"body": ["body_01", "body_02", "body_03"], "sl": ["sleeve_l_01", "sleeve_l_02", "sleeve_l_03", "sleeve_l_04"],
              "sr": ["sleeve_r_01", "sleeve_r_02", "sleeve_r_03", "sleeve_r_04"]},
    "Trousers": {"ll": ["leg_l_01", "leg_l_02", "leg_l_03", "leg_l_04"], "lr": ["leg_r_01", "leg_r_02", "leg_r_03", "leg_r_04"]},
    "Sock": {"sock": ["sock_01", "sock_02", "sock_03", "sock_04"]},
    "Tie": {"tie": ["tie_01", "tie_02", "tie_03", "tie_04", "tie_05", "tie_06"]},
}[G]
SIDE = {"sl": 1, "ll": 1, "sr": -1, "lr": -1}  # +1 = the model's left (+X)
ATTACK = {"Shirt": "Lash", "Trousers": "Kick", "Sock": "Hop", "Tie": "CoilStrike"}[G]
HEIGHT = (arm.matrix_world @ arm.data.bones["hub"].head_local).z
F_AXIS, S_AXIS = Vector((-1, 0, 0)), Vector((0, -1, 0))  # +fwd about -X moves a hanging tip to -Y; +out about -Y moves it to +X


# ---- small maths --------------------------------------------------------------------------------------------------
def s(t, cycles, phase=0.0):
    return math.sin(2 * math.pi * (cycles * t + phase))


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def back(x, k=1.7):  # ease-out with overshoot
    x = min(1.0, max(0.0, x)) - 1
    return 1 + x * x * ((k + 1) * x + k)


def spring(x, freq=2.5, damp=5.0):  # 1 -> 0 with a decaying wobble
    return math.exp(-damp * max(0.0, x)) * math.cos(2 * math.pi * freq * max(0.0, x))


# ---- posing -------------------------------------------------------------------------------------------------------
def head(b):
    return arm.matrix_world @ PB[b].matrix.to_translation()


def rot(b, axis, deg):
    if abs(deg) < 1e-4:
        return
    h = head(b)
    mw = arm.matrix_world
    r = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis.normalized()) @ Matrix.Translation(-h)
    PB[b].matrix = mw.inverted() @ r @ mw @ PB[b].matrix
    bpy.context.view_layer.update()


def apply(pose):
    """pose: {"hub": (dx, dy, dz, fwd, out, yaw), bone: (fwd, out, twist)} -> armature, parents before children."""
    for pb in PB:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    dx, dy, dz, hf, ho, hy = pose.get("hub", (0, 0, 0, 0, 0, 0))
    mw = arm.matrix_world
    PB["hub"].matrix = mw.inverted() @ Matrix.Translation(Vector((dx, dy, dz))) @ mw @ PB["hub"].matrix
    bpy.context.view_layer.update()
    rot("hub", Vector((0, 0, 1)), hy)
    rot("hub", F_AXIS * -1, hf)  # leaning the whole garment: +fwd tips its top toward the front
    rot("hub", S_AXIS, ho)
    for b in [x.name for x in arm.data.bones]:
        if b in pose and b != "hub":
            f, o, tw = pose[b]
            rot(b, F_AXIS, f)
            rot(b, S_AXIS, o)
            if tw:
                rot(b, (arm.matrix_world @ PB[b].tail) - head(b), tw)


def add(pose, bone, f=0.0, o=0.0, tw=0.0):
    a = pose.get(bone, (0.0, 0.0, 0.0))
    pose[bone] = (a[0] + f, a[1] + o, a[2] + tw)


def add_hub(pose, dx=0, dy=0, dz=0, f=0, o=0, y=0):
    a = pose.get("hub", (0, 0, 0, 0, 0, 0))
    pose["hub"] = (a[0] + dx, a[1] + dy, a[2] + dz, a[3] + f, a[4] + o, a[5] + y)


def chain_wave(pose, t, amp_f, amp_o, cycles, lag=0.12, grow=0.6, phase=0.0):
    """A wave running down every chain: the root bone moves first, each next bone later and wider (cloth flutter)."""
    for key, bones in CHAINS.items():
        side = SIDE.get(key, 1)
        for i, b in enumerate(bones):
            g = 1 + grow * i
            add(pose, b, amp_f * g * s(t, cycles, phase - lag * i), side * amp_o * g * s(t, cycles, phase + 0.25 - lag * i))


def idle_layer(pose, t, k=1.0):
    """Never still: a slow bob and sway, plus two flutter waves (2 and 3 cycles per loop) running down each chain."""
    add_hub(pose, dz=0.012 * k * s(t, 1), f=2.5 * k * s(t, 1, 0.25), o=1.5 * k * s(t, 1, 0.5), y=3.0 * k * s(t, 1, 0.1))
    chain_wave(pose, t, 3.5 * k, 2.0 * k, 2)
    chain_wave(pose, t, 1.5 * k, 1.0 * k, 3, lag=0.18, phase=0.3)


# ---- per garment: wind-up W and strike S, as functions of an amount 0..1 -------------------------------------------
def windup(pose, e):
    if G == "Shirt":
        add_hub(pose, dy=0.05 * e, f=-12 * e)
        for b in CHAINS["body"]:
            add(pose, b, -6 * e)
        for key in ("sl", "sr"):
            side = SIDE[key]
            for i, b in enumerate(CHAINS[key]):
                add(pose, b, -25 * e / (1 + i), side * (30 * e if i == 0 else 8 * e))
    elif G == "Trousers":
        add_hub(pose, dz=-0.03 * e, f=-8 * e)
        add(pose, "leg_r_01", -38 * e); add(pose, "leg_r_02", 30 * e); add(pose, "leg_r_03", 10 * e)
        add(pose, "leg_l_01", 12 * e); add(pose, "leg_l_02", -14 * e)
    elif G == "Sock":  # coil: every link curls the same way, the tip tucks in
        add_hub(pose, dz=-0.06 * e, dy=0.03 * e)
        for i, b in enumerate(CHAINS["sock"]):
            add(pose, b, (25 + 12 * i) * e)
    else:  # Tie: coil, twisting as it winds
        add_hub(pose, dz=-0.04 * e)
        for i, b in enumerate(CHAINS["tie"]):
            add(pose, b, (14 + 4 * i) * e, 0, 18 * e)


def strike(pose, e):
    if G == "Shirt":  # lunge, sleeves flung forward and out
        add_hub(pose, dy=-0.16 * e, dz=0.03 * e, f=26 * e)
        for i, b in enumerate(CHAINS["body"]):
            add(pose, b, 8 * e * (1 + 0.3 * i))
        for key in ("sl", "sr"):
            side = SIDE[key]
            for i, b in enumerate(CHAINS[key]):
                add(pose, b, (70 if i == 0 else 12) * e, side * (18 if i == 0 else -4) * e)
    elif G == "Trousers":  # the right leg kicks up and forward, the body leans back into it
        add_hub(pose, dy=-0.05 * e, dz=0.06 * e, f=-16 * e)
        add(pose, "leg_r_01", 88 * e); add(pose, "leg_r_02", -12 * e); add(pose, "leg_r_03", 18 * e); add(pose, "leg_r_04", 22 * e)
        add(pose, "leg_l_01", -6 * e); add(pose, "leg_l_02", 16 * e)
    elif G == "Sock":  # snap: it springs straight and flicks its toe at the target
        add_hub(pose, dy=-0.14 * e, dz=0.08 * e, f=22 * e)
        for i, b in enumerate(CHAINS["sock"]):
            add(pose, b, (-18, -8, 10, 35)[i] * e)
    else:  # Tie: whip, the lower links lashing forward one after another
        add_hub(pose, dy=-0.1 * e, f=14 * e)
        for i, b in enumerate(CHAINS["tie"]):
            add(pose, b, (5, 20, 30, 36, 40, 45)[i] * e, 0, -10 * e)


def cinch(pose, e):
    """Tie only: the knot-cinch after the whip; the top twists tight and the tail jerks up."""
    add(pose, "tie_01", -8 * e, 0, 45 * e); add(pose, "tie_02", -18 * e, 0, 20 * e)
    for b in CHAINS["tie"][2:]:
        add(pose, b, -10 * e)


# ---- clips --------------------------------------------------------------------------------------------------------
def clip_idle(t):
    p = {}
    idle_layer(p, t)
    return p


def clip_telegraph(t):
    p = {}
    e = ease(t / 0.7)
    windup(p, e)
    idle_layer(p, t * 0.5, 0.5)
    chain_wave(p, t, 1.6 * e, 0.8 * e, 9, lag=0.05)  # tension tremble
    return p


def clip_attack(t):
    p = {}
    w = ease(t / 0.25) * (1 - ease((t - 0.25) / 0.12))
    windup(p, w)
    lead = (t - 0.25) / 0.15
    hit = back(lead) if t >= 0.25 else 0.0
    settle = spring((t - 0.45) / 0.55, 1.8, 3.5) if t >= 0.45 else 1.0
    strike(p, hit * settle)
    if G == "Tie":
        c = ease((t - 0.55) / 0.12) * (1 - ease((t - 0.8) / 0.18))
        cinch(p, c)
    follow = max(0.0, t - 0.4)
    chain_wave(p, t, 9 * math.exp(-4 * follow) * (t > 0.4), 4 * math.exp(-4 * follow) * (t > 0.4), 3, lag=0.1)
    idle_layer(p, t, 0.3)
    return p


def clip_hit(t):
    p = {}
    k = spring(t, 2.2, 4.5)
    add_hub(p, dy=0.06 * k, dz=-0.02 * abs(k), f=-16 * k, y=8 * k)
    for key, bones in CHAINS.items():
        for i, b in enumerate(bones):
            lagged = spring(t - 0.04 * (i + 1), 2.2, 4.5) if t > 0.04 * (i + 1) else 0.0
            add(p, b, 10 * (1 + 0.5 * i) * lagged)
    idle_layer(p, t * 0.3, 0.3)
    return p


def clip_stun(t):
    p = {}
    add_hub(p, dz=-0.08 * HEIGHT, f=18, o=6 * s(t, 1, 0.25), y=7 * s(t, 1))
    for key, bones in CHAINS.items():
        for i, b in enumerate(bones):
            add(p, b, 8 + 3 * s(t, 1, -0.1 * i), SIDE.get(key, 1) * 4)
    chain_wave(p, t, 2.0, 1.0, 1, lag=0.2)
    return p


def clip_defeat(t):
    p = {}
    shake = (1 - ease((t - 0.25) / 0.1)) * ease(t / 0.08)
    chain_wave(p, t, 5 * shake, 3 * shake, 11, lag=0.04)
    add_hub(p, y=6 * shake * s(t, 8))
    fall = ease((t - 0.3) / 0.6) ** 1.6
    add_hub(p, dz=-0.82 * HEIGHT * fall, f=38 * fall, o=10 * fall)
    for key, bones in CHAINS.items():
        side = SIDE.get(key, 1)
        for i, b in enumerate(bones):
            add(p, b, (28 if i % 2 == 0 else -18) * fall, side * 14 * fall)
    return p


CLIPS = [("Idle", 60, clip_idle), ("Telegraph", 30, clip_telegraph), (ATTACK, 36, clip_attack),
         ("HitReact", 18, clip_hit), ("Stun", 60, clip_stun), ("Defeat", 45, clip_defeat)]


def bake(name, frames, fn, loop):
    act = bpy.data.actions.new(name)
    arm.animation_data_create()
    arm.animation_data.action = act
    n = frames if loop else frames - 1
    for f in range(frames + (1 if loop else 0)):
        apply(fn((f % frames) / n if loop else f / n))
        for pb in PB:
            pb.keyframe_insert("rotation_quaternion", frame=f)
            pb.keyframe_insert("location", frame=f)
    act.use_fake_user = True
    return act


def main():
    os.makedirs(OUT, exist_ok=True)
    for a in list(bpy.data.actions):  # the shared old takes (all four in every file) are not this garment's
        bpy.data.actions.remove(a)
    for pb in PB:
        pb.rotation_mode = "QUATERNION"
    acts = [bake(n, fr, fn, n in ("Idle", "Stun")) for n, fr, fn in CLIPS]
    bpy.context.scene.render.fps = FPS
    arm.animation_data.action = None
    for pb in PB:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = arm
    path = f"{OUT}/SK_Garment_{G}.fbx"
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"ARMATURE", "MESH"}, add_leaf_bones=False,
                             bake_anim=True, bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False,
                             bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0,
                             path_mode="COPY", embed_textures=False)
    bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/SK_Garment_{G}_anim.blend", copy=True)
    print("GARMENT_ANIMS", G, [(a.name, tuple(a.frame_range)) for a in acts], path)
    if A.get("render") == "1":
        strips(acts)


def strips(acts):
    """Workbench frames per take for the review sheet: 6 evenly spaced frames, front-3/4 view."""
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x = sc.render.resolution_y = 360
    sh = sc.display.shading
    sh.light, sh.color_type, sh.single_color = "STUDIO", "SINGLE", (0.8, 0.78, 0.75)
    sh.show_cavity = True
    sh.background_type, sh.background_color = "VIEWPORT", (0.07, 0.07, 0.08)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    tgt = Vector((0, -0.1, HEIGHT * 0.55))
    eye = tgt + Vector((0.9, -1.6, 0.35)).normalized() * (HEIGHT * 2.9 + 0.6)
    cam.location = eye
    cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
    for a in acts:
        arm.animation_data.action = a
        lo, hi = a.frame_range
        for k in range(6):
            sc.frame_set(int(lo + (hi - lo) * k / 5))
            sc.render.filepath = f"{OUT}/strips/{G}_{a.name}_{k}.png"
            bpy.ops.render.render(write_still=True)


main()
