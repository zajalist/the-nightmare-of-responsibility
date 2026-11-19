"""The right-hand grips solved in the Blender twin (Tools/Rig/*_twin.py, mesh-level checks, game mm) as the Teen finger
pose library: AS_FoA_TeenGrip_<Name>_R on SK_Teen_Body's native skeleton, after retargeting. Ordinary grips change
only the right fingers. Key includes its planted stance; each screwdriver clip includes the calibrated full-body
ratchet stroke, evaluated by ScrewGripTime.
Offline (no editor) it writes Saved/AnimShots/grip_bake.json, with the grip's finger locals and, for the in-game IK:
- hand_in_object: hand_r in the object's frame, game cm (the twin body is 180 cm and held objects sit at 1/BODY_SCALE,
  so every twin position times BODY_SCALE is the game; the object's scale becomes 1);
- root_in_object: where the Body's component origin stands, in the same frame (the warp to Stand).
Self-checks (assert): every finger bone solved and unit length, the hand within 25 cm of the object frame, and hand and
object composed back to the twin's hand to 0.01 cm.
  python Tools/Unreal/player/bake_grips.py
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/bake_grips.py   (after the hold)"""
import json
import os
import sys
from pathlib import Path

try:
    import unreal
except ImportError:
    unreal = None

sys.path.insert(0, 'P:/FoA/Tools/Unreal/wakeup')
import wake_math as m  # noqa: E402

A = Path('P:/FoA/Saved/AnimShots')
OUT = '/Game/FoA/Characters/Player/Anims/Hands/AS_FoA_TeenGrip_{}_R'  # AS_FoA_Grip_Key_R / _Tool_R are the old Manny poses
BODY_SCALE = 170.0 / 180.0
GRIPS = {  # Every grip must pass its source and native bake gates.
    'Key': 'key_native_solution.json',
    'Knob': 'knob_grip_solution.json',
    'DrawerKnob': 'drawer_grip_solution.json',
    'Hanger': 'hanger_grip_solution.json',
    'Boot': 'boot_grip_solution.json',
    **{f'Screwdriver{i}': row['source'] for i,row in enumerate(json.loads((A/'screw_runtime.json').read_text()))},
}
ACCEPTED = {'Key': 'main locked it at review3 with these deviations: elbow 84, forearm 16 deg, fill 0.19'}
FINGERS = [f'{d}_0{i}_r' for d in ('thumb', 'index', 'middle', 'ring', 'pinky') for i in (1, 2, 3)]
MANIFEST = A / 'grip_bake.json'


def relative(obj, hand):
    """hand_r in the object's frame, game cm: both twin component-space transforms scaled to the game body."""
    oq, hq = m.qnorm(tuple(obj['quat'])), m.qnorm(tuple(hand[1]))
    ol, hl = m.mul(tuple(obj['loc']), BODY_SCALE), m.mul(tuple(hand[0]), BODY_SCALE)
    return m.qrot(m.qinv(oq), m.sub(hl, ol)), m.qmul(m.qinv(oq), hq)


def load(name, fn):
    sol = json.loads((A / fn).read_text())
    if 'key_ue' in sol:  # key_pinch_twin.py's own format
        k = sol['key_ue']
        sol = dict(pose=sol['pose'], hand_ue=[sol['hand_ue']['location'], sol['hand_ue']['rotation']],
                   object_ue=dict(loc=k['location'], quat=k['rotation'], scale=[k['scale']] * 3), twin=sol['twin'])
    if name in ACCEPTED:  # a coordinator-accepted deviation still needs clean clearance (hand, forearm, body)
        h = sol['twin']['hold']
        assert h['clear_min_mm'] >= 1.0 and h.get('body_clear', [0])[0] >= 1.0, f'{name}: clearance {h["clear_min_mm"]}, body {h.get("body_clear")}'
    else:
        assert sol['twin']['passed'], f'{name}: the twin solve did not pass'
    return sol


def build():
    out = {}
    for name, fn in GRIPS.items():
        sol = load(name, fn)
        fingers = {b: m.qnorm(tuple(sol['pose'][b])) for b in FINGERS}
        assert all(abs(sum(x * x for x in sol['pose'][b]) - 1) < 1e-3 for b in FINGERS), name
        frame = sol.get('anchor_ue', sol['object_ue'])  # the drawer: the knob head, not the commode's floor origin
        loc, q = relative(frame, sol['hand_ue'])
        assert m.length(loc) < 25.0, (name, 'hand_r is %.1f cm from the object frame' % m.length(loc))
        oq, ol = m.qnorm(tuple(frame['quat'])), m.mul(tuple(frame['loc']), BODY_SCALE)
        back = m.add(ol, m.qrot(oq, loc))  # compose again: object * hand_in_object = the twin's hand, scaled
        assert m.length(m.sub(back, m.mul(tuple(sol['hand_ue'][0]), BODY_SCALE))) < 0.01, name
        root = m.qrot(m.qinv(oq), m.sub((0.0, 0.0, 0.0), ol))
        out[name] = dict(source=fn, fingers=fingers, hand_in_object=dict(loc=loc, quat=q), root_in_object=root,
                         object_frame=frame, note=sol['twin'].get('knob', {}).get('note', ''))
        if name == 'Key' or name.startswith('Screwdriver'):
            sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
            from measure_grip_pose import reference_hierarchy
            ref, parents = reference_hierarchy()
            local = {b: [v[0], sol['pose'].get(b, v[1]), v[2]] for b, v in ref['local'].items()}
            world = m.Pose(local, parents).world()
            delta = m.sub(sol['hand_ue'][0], world['hand_r'][0])
            parent_q = world[parents['pelvis']][1]
            local['pelvis'][0] = m.add(local['pelvis'][0], m.qrot(m.qinv(parent_q), delta))
            assert m.length(m.sub(m.Pose(local, parents).world()['hand_r'][0], sol['hand_ue'][0])) < 0.001
            out[name]['stance'] = local
            if name.startswith('Screwdriver'):
                motion = A / fn.replace('_native_solution.json','_turn.json')
                turn = json.loads(motion.read_text())
                assert len(turn['frames']) == 31
                assert all(c['wrist'] <= 20 and c['inline'] <= 20 and c['hand_error_mm'] < .01 for c in turn['checks'])
                out[name]['motion'] = str(motion)
            if name == 'Key' or name.startswith('Screwdriver'):
                sys.path.insert(0,'P:/FoA/Tools/Rig')
                from ue_hand import Hand
                from measure_grip_pose import finger_limits, wrist_rotation
                hand=Hand(A/'review/key_before_native_fixture.json')
                local=hand.untwist_forearm(local,'r')
                out[name]['stance']=local
                assert wrist_rotation(local,hand.ref,'r')['wrist_axial_pass'], name
                if name.startswith('Screwdriver'):
                    assert all(wrist_rotation(p,hand.ref,'r')['wrist_axial_pass'] for p in turn['frames']), name
                assert finger_limits(local,hand.ref,'r')['joints_pass'], name
                assert all(hand.curl_motion(local,d,j,'r')>0 for d in ('thumb','index','middle','ring','pinky') for j in (2,3)), 'Key: outward or flat hinge'
        print('GRIP', name, 'hand_in_object', [round(x, 2) for x in loc], 'root_in_object', [round(x, 1) for x in root])
    return out


def write(name, fingers, stance=None, motion=None):
    ap = unreal.AnimPoseExtensions
    body = unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body')
    skel = body.get_editor_property('skeleton')
    ref = ap.get_reference_pose(skel)
    path = OUT.format(name)
    seq = unreal.load_asset(path)
    if not seq:
        f = unreal.AnimSequenceFactory()
        f.set_editor_property('target_skeleton', skel)
        f.set_editor_property('preview_skeletal_mesh', body)
        seq = unreal.AssetToolsHelpers.get_asset_tools().create_asset(path.rsplit('/', 1)[1], path.rsplit('/', 1)[0], unreal.AnimSequence, f)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
    ctrl = seq.get_editor_property('controller')
    ctrl.open_bracket('Grip ' + name, False)
    ctrl.set_frame_rate(unreal.FrameRate(30, 1), False)
    frames = json.loads(Path(motion).read_text())['frames'] if motion else None
    ctrl.set_number_of_frames(unreal.FrameNumber(len(frames)-1 if frames else 1), False)
    for b in (stance if stance else FINGERS):
        t = ap.get_bone_pose(ref, b, unreal.AnimPoseSpaces.LOCAL)
        try:
            ctrl.add_bone_curve(b, False)
        except Exception:  # already tracked
            pass
        q = unreal.Quat(*(stance[b][1] if stance else fingers[b]))
        if stance:
            t.translation = unreal.Vector(*stance[b][0])
        if frames:
            ctrl.set_bone_track_keys(b, [unreal.Vector(*p[b][0]) for p in frames],
                                    [unreal.Quat(*p[b][1]) for p in frames], [t.scale3d]*len(frames), False)
        else:
            ctrl.set_bone_track_keys(b, [t.translation] * 2, [q] * 2, [t.scale3d] * 2, False)
    ctrl.close_bracket(False)
    seq.set_editor_property('enable_root_motion', False)
    assert unreal.EditorAssetLibrary.save_loaded_asset(seq, False), path


if unreal:  # the editor only writes what the offline run checked
    man = json.loads(MANIFEST.read_text())
    for name, g in man.items():
        if os.environ.get('FOA_GRIP') and not (name == os.environ['FOA_GRIP'] or os.environ['FOA_GRIP']=='Screwdriver' and name.startswith('Screwdriver')):
            continue
        write(name, {b: tuple(q) for b, q in g['fingers'].items()}, g.get('stance'), g.get('motion'))
        print('GRIP_BAKED', name, OUT.format(name))
else:
    MANIFEST.write_text(json.dumps(build(), indent=1))
    print('wrote', MANIFEST)
