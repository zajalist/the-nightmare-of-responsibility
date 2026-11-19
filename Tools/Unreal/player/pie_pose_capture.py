"""PIE pose capture for the grip twin replay (anim lane): the visible Teen Body's local bone transforms (parent bone
space) and held or touched objects relative to a hand bone, in the formats Tools/Rig reads:
- capture_phone(...) writes hand_twin.run_phone's solution JSON ({"hold": {bone: [loc, quat, scale]}, "out": {"attach"}});
- capture_grip(...) writes {"hold", "body_world", "objects": {name: {"world", "in_hand", "mesh"}}} for replay_pie_grip.py.
Called from the PIE proof scripts at their held shots. Read-only on the game world."""
import json
import time
from pathlib import Path

import unreal

PARENT = unreal.RelativeTransformSpace.RTS_PARENT_BONE_SPACE
WORLD = unreal.RelativeTransformSpace.RTS_WORLD


def request_shot(state, world, path):
    assert not state.get('pending_shot'), 'collect the previous frame first'
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    state['pending_shot'] = (time.time(), str(path))
    unreal.SystemLibrary.execute_console_command(world, f'Shot filename={path.as_posix()} -nosuffix')


def collect_shot(state):
    pending = state.get('pending_shot')
    if not pending:
        return True
    since, dest = pending
    path = Path(dest)
    if path.exists() and path.stat().st_mtime >= since and path.stat().st_size > 0:
        state.pop('pending_shot')
        return True
    assert time.time() - since < 5, 'PIE screenshot did not arrive: ' + dest
    return False


def _xf(t):
    return [[t.translation.x, t.translation.y, t.translation.z], [t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w],
            [t.scale3d.x, t.scale3d.y, t.scale3d.z]]


def local_pose(body):
    return {str(b): _xf(body.get_socket_transform(b, PARENT)) for b in body.get_all_socket_names()
            if body.get_bone_index(b) != -1}


def in_bone(body, bone, world_xf):
    """world_xf relative to the bone's world transform (its scale included: the Body shows at 170/180, so this is the
    attach offset BP_FoAPlayer would use)."""
    return world_xf.make_relative(body.get_socket_transform(bone, WORLD))


def capture_phone(body, phone_mesh, path):
    rel = in_bone(body, 'hand_l', phone_mesh.get_world_transform())
    out = dict(attach=dict(location=_xf(rel)[0], rotation=_xf(rel)[1]), source='PIE')
    with open(path, 'w') as f:
        json.dump(dict(hold=local_pose(body), out=out), f)
    return path


def capture_grip(body, objects, path, hand='hand_r'):
    """objects: {name: SceneComponent}; each is recorded in world and in the hand bone's frame, with its mesh path."""
    objs = {}
    for name, c in objects.items():
        wxf = c.get_world_transform()
        mesh = c.get_editor_property('static_mesh') if isinstance(c, unreal.StaticMeshComponent) else None
        objs[name] = dict(world=_xf(wxf), in_hand=_xf(in_bone(body, hand, wxf)), mesh=mesh.get_path_name() if mesh else None)
    with open(path, 'w') as f:
        json.dump(dict(hold=local_pose(body), body_world=_xf(body.get_world_transform()), hand=hand, objects=objs), f)
    return path
