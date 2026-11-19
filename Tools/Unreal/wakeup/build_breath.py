"""Sleep breathing on the user's lying pose (AS_FoA_Wake_Lying), keeping the pose itself exactly.
  $env:HAYBA_AGENT_ID='anim'; $env:FOA_AREAS='Cinematics'; python Tools/Unreal/ue_remote.py Tools/Unreal/wakeup/build_breath.py
The clip is one static frame (integrate_manual_sleep.py). This adds a 4.5 s supine breath, two cycles over its 270
frames so it loops seamlessly: inhale 1.6 s, exhale 2.2 s, 0.7 s rest at the bottom (frame 0 = the user's pose).
Only rotations, because the Teen retarget carries rotations, not spine translations:
- spine_02 and spine_04 bend as a bow about the body's lateral axis: the lower chest rises ~0.8 cm while neck_01
  keeps its height and the neck/head keep their world orientation, so his head never lifts off the pillow;
- both clavicles lift 1.2 deg and the upper arms counter-rotate, so the shoulders rise but the arms lie still.
Backs up the asset first, then re-evaluates the clip and asserts: frame 0 is unchanged, head drift < 0.15 cm, chest
rise 0.5-1.2 cm. Report: Saved/AnimShots/breath_built.json."""
import datetime
import json
import math
import shutil
import sys
from pathlib import Path

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/wakeup')
import importlib  # noqa: E402

import wake_math as m  # noqa: E402

importlib.reload(m)
AP = unreal.AnimPoseExtensions
WORLD, LOCAL = unreal.AnimPoseSpaces.WORLD, unreal.AnimPoseSpaces.LOCAL
PATH = '/Game/FoA/Cinematics/WakeUp/AS_FoA_Wake_Lying'
PERIOD, N = 135, 270
CHEST_DEG, SHRUG_DEG = 3.0, 1.2
UP = (0.0, 0.0, 1.0)

clip = unreal.load_asset(PATH)
assert clip and clip.get_play_length() > 8.9, 'expected the 9 s static sleep clip'
opts = unreal.AnimPoseEvaluationOptions()
opts.evaluation_type = unreal.AnimDataEvalType.RAW
pose = AP.get_anim_pose_at_frame(clip, 0, opts)
names = [str(n) for n in AP.get_bone_names(pose)]


def xf(t):
    r = t.rotation
    return (t.translation.x, t.translation.y, t.translation.z), (r.x, r.y, r.z, r.w)


W0 = {b: xf(AP.get_bone_pose(pose, b, WORLD)) for b in names}
L0 = {b: AP.get_bone_pose(pose, b, LOCAL) for b in names}
assert all(b in names for b in ('spine_02', 'spine_04', 'neck_01', 'head', 'clavicle_l', 'clavicle_r', 'upperarm_l', 'upperarm_r'))


def breath(f):
    """0 at rest, 1 at full inhale: eased rise 48 f, eased fall 66 f, rest 21 f."""
    u = f % PERIOD
    if u < 48:
        return m.smooth(u / 48.0)
    if u < 114:
        return 1.0 - m.smooth((u - 48) / 66.0)
    return 0.0


pos = lambda b: W0[b][0]  # noqa: E731
lat = m.norm(m.cross(m.sub(pos('neck_01'), pos('spine_02')), UP))  # +angle tilts the spine toward up
n = pos('neck_01')
v1 = m.cross(lat, m.sub(n, pos('spine_02')))[2]
v3 = m.cross(lat, m.sub(n, pos('spine_04')))[2]
assert abs(v3) > 1.0, ('spine_04 too close to neck_01 for the bow', v3)
a1 = CHEST_DEG
a3 = -a1 * v1 / v3
a5 = -(a1 + a3)
plan = {'spine_02': (lat, a1), 'spine_04': (lat, a3), 'neck_01': (lat, a5)}
for s in ('l', 'r'):
    ax = m.norm(m.cross(m.sub(pos('upperarm_' + s), pos('clavicle_' + s)), UP))
    plan['clavicle_' + s] = (ax, SHRUG_DEG)
    plan['upperarm_' + s] = (ax, -SHRUG_DEG)


def local_delta(b, deg):
    """Local-space rotation whose world effect is a rotation of `deg` about plan[b]'s axis at bone b. The upper arms
    also undo the chest's net tilt (spine_02 + spine_04), so the arms keep their world orientation and the hands only
    ride the shoulder (the arm lying on the duvet stays on it)."""
    qw = W0[b][1]
    d = m.qaxis(plan[b][0], deg)
    if b.startswith('upperarm_'):
        breath_w = deg / plan[b][1]  # this frame's breath weight, 0..1
        d = m.qmul(m.qaxis(lat, -(a1 + a3) * breath_w), d)
    return m.qnorm(m.qmul(m.qinv(qw), m.qmul(d, qw)))


stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
bk = Path('P:/FoA/Saved/Backups/breath') / stamp
bk.mkdir(parents=True, exist_ok=True)
shutil.copy2('P:/FoA/Content/FoA/Cinematics/WakeUp/AS_FoA_Wake_Lying.uasset', bk / 'AS_FoA_Wake_Lying.uasset')
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(clip)
ctrl = clip.get_editor_property('controller')
ctrl.open_bracket('Sleep breathing', False)
try:
    for b, (axis, amp) in plan.items():
        t0 = L0[b]
        q0 = (t0.rotation.x, t0.rotation.y, t0.rotation.z, t0.rotation.w)
        rots = []
        for f in range(N + 1):
            dq = local_delta(b, amp * breath(f))
            q = m.qnorm(m.qmul(q0, dq))
            rots.append(unreal.Quat(*q))
        ctrl.set_bone_track_keys(b, [t0.translation] * (N + 1), rots, [t0.scale3d] * (N + 1), False)
finally:
    ctrl.close_bracket(False)


def at(f, b):
    return AP.get_bone_pose(AP.get_anim_pose_at_frame(clip, f, opts), b, WORLD).translation


peak = 48
drift0 = max((at(0, b) - unreal.Vector(*pos(b))).length() for b in names)
head_drift = max((at(f, 'head') - unreal.Vector(*pos('head'))).length() for f in (24, 48, 80))
chest = (at(peak, 'spine_04') - unreal.Vector(*pos('spine_04'))).z
hand = {s: round((at(peak, 'hand_' + s) - unreal.Vector(*pos('hand_' + s))).length(), 2) for s in ('l', 'r')}
report = dict(clip=PATH, backup=str(bk), angles=dict(spine_02=a1, spine_04=round(a3, 3), neck_01=round(a5, 3), shrug=SHRUG_DEG),
              frame0_drift_cm=round(drift0, 4), head_drift_cm=round(head_drift, 3), chest_rise_cm=round(chest, 3), hand_move_cm=hand)
print('BREATH', json.dumps(report))
bad = [msg for ok, msg in ((drift0 < 0.01, 'frame 0 must stay the user pose'), (head_drift < 0.15, 'head must stay on the pillow'),
                           (0.5 < chest < 1.2, 'chest rise out of range'),
                           (max(hand.values()) < 0.8, 'hands must ride the breath, not swing')) if not ok]
if bad:  # put the static pose back in memory, never save a failed breath
    ctrl.open_bracket('Undo sleep breathing', False)
    for b in plan:
        t0 = L0[b]
        ctrl.set_bone_track_keys(b, [t0.translation] * (N + 1), [t0.rotation] * (N + 1), [t0.scale3d] * (N + 1), False)
    ctrl.close_bracket(False)
    raise AssertionError(bad)
unreal.EditorAssetLibrary.save_loaded_asset(clip, False)
Path('P:/FoA/Saved/AnimShots/breath_built.json').write_text(json.dumps(report, indent=1))
print('BREATH_SAVED')
