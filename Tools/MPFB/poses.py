"""Test poses on MPFB's game_engine rig (armature space: -Y is the character's front, +X his left).
Used by the fit checks and proof renders; nothing here is saved into a character file."""
import math

import bpy
from mathutils import Matrix, Vector


def v(x, y, z):
    return Vector((x, y, z)).normalized()


def aim(rig, name, want):
    """Turn a pose bone so head->tail points along `want`."""
    pb = rig.pose.bones[name]
    bpy.context.view_layer.update()
    cur = (pb.tail - pb.head).normalized()
    if cur.angle(want) < 1e-4:
        return
    r = Matrix.Translation(pb.head) @ Matrix.Rotation(cur.angle(want), 4, cur.cross(want).normalized()) @ Matrix.Translation(-pb.head)
    pb.matrix = r @ pb.matrix


def turn(rig, name, deg, axis):
    """Rotate a pose bone about an armature-space axis through its head."""
    pb = rig.pose.bones[name]
    bpy.context.view_layer.update()
    r = Matrix.Translation(pb.head) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-pb.head)
    pb.matrix = r @ pb.matrix


def chain(rig, pairs):
    for name, d in pairs:
        aim(rig, name, d)


def spine(rig, deg, axis):
    for b in ("spine_01", "spine_02", "spine_03"):
        turn(rig, b, deg, axis)


DOWN = (("upperarm_l", v(0.19, 0, -1)), ("lowerarm_l", v(0.1, -0.12, -1)),
        ("upperarm_r", v(-0.19, 0, -1)), ("lowerarm_r", v(-0.1, -0.12, -1)))

POSES = {
    "rest": lambda r: None,
    "idle": lambda r: chain(r, DOWN),
    "walk": lambda r: chain(r, (("thigh_l", v(0.03, -0.45, -1)), ("calf_l", v(0, -0.12, -1)),
                               ("thigh_r", v(-0.03, 0.38, -1)), ("calf_r", v(0, 0.75, -1)),
                               ("upperarm_l", v(0.19, 0.35, -1)), ("lowerarm_l", v(0.12, 0.1, -1)),
                               ("upperarm_r", v(-0.19, -0.4, -1)), ("lowerarm_r", v(-0.1, -0.75, -1)))),
    "sit": lambda r: chain(r, (("thigh_l", v(0.12, -1, -0.04)), ("calf_l", v(0.04, -0.12, -1)),
                              ("thigh_r", v(-0.12, -1, -0.04)), ("calf_r", v(-0.04, -0.12, -1)),
                              ("upperarm_l", v(0.2, -0.35, -1)), ("lowerarm_l", v(0.05, -1, -0.25)),
                              ("upperarm_r", v(-0.2, -0.35, -1)), ("lowerarm_r", v(-0.05, -1, -0.25)))),
    "crouch": lambda r: (spine(r, 10, "X"),
                         chain(r, (("thigh_l", v(0.18, -1, -0.55)), ("calf_l", v(0.05, 0.75, -1)),
                                   ("thigh_r", v(-0.18, -1, -0.55)), ("calf_r", v(-0.05, 0.75, -1)),
                                   ("upperarm_l", v(0.2, -0.6, -1)), ("lowerarm_l", v(0.05, -1, -0.4)),
                                   ("upperarm_r", v(-0.2, -0.6, -1)), ("lowerarm_r", v(-0.05, -1, -0.4))))),
    "twist_l30": lambda r: (chain(r, DOWN), spine(r, 10, "Z")),
    "twist_r30": lambda r: (chain(r, DOWN), spine(r, -10, "Z")),
    "bend": lambda r: (chain(r, DOWN), spine(r, 13, "X")),
}


def reset(rig):
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    rig.location.z = 0.0
    bpy.context.view_layer.update()


def apply_pose(rig, body, name):
    """Pose from rest, then drop the rig so the lowest body point touches z=0."""
    reset(rig)
    POSES[name](rig)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    m = ev.to_mesh()
    low = min((body.matrix_world @ p.co).z for p in m.vertices)
    ev.to_mesh_clear()
    rig.location.z -= low
    bpy.context.view_layer.update()
