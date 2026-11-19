"""Fit proof: pose a built character on its game_engine rig (idle, walk mid-stride, sit, arms raised) and render each,
so the auto-fitted MakeHuman clothes can be checked for stretching and skin poking through. Never saves the .blend.
  blender.exe -b <character.blend> --python Tools/MPFB/pose_sheet.py -- <tag>
Writes Saved/CharacterShots/mpfb/<tag>_pose_{idle,walk,sit,raise}.png; compose with direction_sheet.py poses <tag>."""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
from mpfb_common import SHOTS, args, ensure_dir  # noqa: E402

rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = next(o for o in rig.children if o.type == "MESH" and o.data.shape_keys and len(o.data.shape_keys.key_blocks) > 5)
pose = rig.pose.bones


def v(x, y, z):  # armature space: -Y is the character's front, +X his left
    return Vector((x, y, z)).normalized()


def aim(name, want):
    """Turn a pose bone so head->tail points along `want`."""
    pb = pose[name]
    bpy.context.view_layer.update()
    cur = (pb.tail - pb.head).normalized()
    if cur.angle(want) < 1e-4:
        return
    r = Matrix.Translation(pb.head) @ Matrix.Rotation(cur.angle(want), 4, cur.cross(want).normalized()) @ Matrix.Translation(-pb.head)
    pb.matrix = r @ pb.matrix


def arms(l_up, l_low, r_up, r_low):
    for n, d in (("upperarm_l", l_up), ("lowerarm_l", l_low), ("upperarm_r", r_up), ("lowerarm_r", r_low)):
        aim(n, d)


def legs(l_th, l_calf, r_th, r_calf):
    for n, d in (("thigh_l", l_th), ("calf_l", l_calf), ("thigh_r", r_th), ("calf_r", r_calf)):
        aim(n, d)


def reset():
    for pb in pose:
        pb.matrix_basis = Matrix.Identity(4)
    rig.location.z = 0.0
    bpy.context.view_layer.update()


def ground():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    m = ev.to_mesh()
    low = min((body.matrix_world @ p.co).z for p in m.vertices)
    ev.to_mesh_clear()
    rig.location.z -= low
    bpy.context.view_layer.update()


DOWN_L, DOWN_R = v(0.19, 0, -1), v(-0.19, 0, -1)
POSES = {
    "idle": lambda: arms(DOWN_L, v(0.1, -0.12, -1), DOWN_R, v(-0.1, -0.12, -1)),
    "walk": lambda: (legs(v(0.03, -0.45, -1), v(0, -0.12, -1), v(-0.03, 0.38, -1), v(0, 0.75, -1)),
                     arms(v(0.19, 0.35, -1), v(0.12, 0.1, -1), v(-0.19, -0.4, -1), v(-0.1, -0.75, -1))),
    "sit": lambda: (legs(v(0.12, -1, -0.04), v(0.04, -0.12, -1), v(-0.12, -1, -0.04), v(-0.04, -0.12, -1)),
                    arms(v(0.2, -0.35, -1), v(0.05, -1, -0.25), v(-0.2, -0.35, -1), v(-0.05, -1, -0.25))),
    "raise": lambda: arms(v(0.3, 0, 1), v(0.18, -0.05, 1), v(-0.3, 0, 1), v(-0.18, -0.05, 1)),
}
VIEW = {"idle": 25, "walk": 75, "sit": 55, "raise": 20}

tag = args()[0]
out = ensure_dir(SHOTS)
cam = bpy.context.scene.camera
height = 0.0
for name, apply in POSES.items():
    reset()
    apply()
    ground()
    bpy.context.view_layer.update()
    seat = None
    if name == "sit":  # a plain box under him, so the pose reads; deleted right after the shot
        hip = rig.matrix_world @ pose["thigh_l"].head
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, hip.y + 0.12, (hip.z - 0.09) / 2))
        seat = bpy.context.active_object
        seat.scale = (0.6, 0.5, hip.z - 0.09)
    height = max(height, (rig.matrix_world @ pose["head"].tail).z)
    target = Vector((0, 0, 0.92 if name != "sit" else 0.62))
    yaw = math.radians(VIEW[name])
    dist = 3.4
    cam.data.lens = 50
    cam.location = target + Vector((math.sin(yaw) * dist, -math.cos(yaw) * dist, 0.15))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.render.filepath = f"{out}/{tag}_pose_{name}.png"
    bpy.ops.render.render(write_still=True)
    print("wrote", bpy.context.scene.render.filepath)
    if seat:
        bpy.data.objects.remove(seat)
