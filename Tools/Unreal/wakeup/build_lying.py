"""AS_FoA_Wake_Lying: LS_WakeUp's lying hold (0 to 19.7 s), baked in-editor from UAL_LayToIdle frame 0 (CC0).
  $env:FOA_AREAS='Cinematics'; python Tools/Unreal/ue_remote.py Tools/Unreal/wakeup/build_lying.py [FOA_DRY=1]
v2 (anim lane): every contact is solved against the traced bedding: heels on the duvet with relaxed 12 deg knees, the
right palm on his stomach, the left arm loose by his side, the head lifted onto the pillow by spine_05/neck flexion
with the face to the ceiling, chin tucked 14 deg and turned 12 deg to the nightstand. v1 floated the knees 20 cm
over the bed and cranked the neck back. Then a slow 4.5 s breath.
9 s, two whole breaths, so it loops seamlessly. After the static support pose is solved, only the upper torso breathes."""
import math
import os
import sys
import json
from pathlib import Path

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/wakeup")
import importlib  # noqa: E402

import wake_common as W  # noqa: E402

importlib.reload(W)
m = W.m
EAL = unreal.EditorAssetLibrary
SRC = W.UAL + "UAL_LayToIdle"
OUT = W.WAKE + "/AS_FoA_Wake_Lying"
LEN, PERIOD = 9.0, 4.5
BREATH = 6.0  # deg at the peak: about 0.9 cm of chest rise (2.5 gave 0.37 cm, invisible at 50 mm)
UP = (0.0, 0.0, 1.0)  # the clip lies on its own floor: component up is off the bed
HIP = 14.0          # pelvis joint over the duvet (build_anims.HIP_SURFACE_DEPTH, clip units)
HEEL, BELLY, SKULL = 7.0, 24.0, .4  # Measured Teen response: 1.62x source head lift; compensate the 7.2 cm pillow gap and slope.
KNEE_BEND, CHIN, TURN = 12.0, 14.0, 12.0  # degrees: relaxed knees, chin toward the chest, head turned to the nightstand
SCALE = 0.9444444444444444  # placement rig mesh_scale (clip cm -> world cm)
PEL_X, DUVET_AT_PELVIS = 261.7, 62.1  # placement.json lay.pelvis x and its duvet trace
# duvet top along the bed (world x, z), traced by build_anims.py; the pillow is the 77 cm run at the head end
PROFILE = [(185, 61.5), (190, 61.5), (210, 64.6), (230, 62.9), (250, 62.0), (270, 62.1), (290, 66.1), (310, 64.8),
           (322, 72.0), (330, 77.0), (350, 77.0)]
TURN_SIGN = 1.0  # +: toward clip +X (his left); dry-run the face print and flip if the nightstand is on his right
FACE_LOCAL = CROWN_LOCAL = None


def profile(x):
    pts = sorted(PROFILE)
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        if x <= x1:
            return z0 + (z1 - z0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


def main():
    global FACE_LOCAL, CROWN_LOCAL, PEL_X, DUVET_AT_PELVIS
    if os.environ.get('FOA_DRY')!='1' and os.environ.get('FOA_ALLOW_LYING_REBAKE')!='1':
        raise RuntimeError('Manual pose handoff: lying animation rebuild is paused. Preserve the user-edited pose; only set FOA_ALLOW_LYING_REBAKE=1 after explicitly integrating those edits.')
    lay = W.load_placement()['lay']
    PEL_X, DUVET_AT_PELVIS = lay['pelvis'][0], lay['duvet']
    src = unreal.load_asset(SRC)
    A = W.UeAdapter({"lay": src})
    # head-local face and crown directions from the reference pose (the Manny stands facing +Y, crown +Z)
    ref = unreal.AnimPoseExtensions.get_reference_pose(src.get_editor_property("skeleton"))
    rq = unreal.AnimPoseExtensions.get_bone_pose(ref, "head", unreal.AnimPoseSpaces.WORLD).rotation
    inv = m.qinv((rq.x, rq.y, rq.z, rq.w))
    FACE_LOCAL, CROWN_LOCAL = m.qrot(inv, (0.0, 1.0, 0.0)), m.qrot(inv, (0.0, 0.0, 1.0))
    p = A.pose_at("lay", 0.0)
    relaxed = W.UeAdapter({'rest':unreal.load_asset(W.UAL+'UAL_PickUp_Table')}).pose_at('rest',0.0)
    for bone in W.edge_clip.finger_bones(A.names,'r'):
        pos,_ = A.lget(p,bone)
        open_q = unreal.AnimPoseExtensions.get_bone_pose(ref,bone,unreal.AnimPoseSpaces.LOCAL).rotation
        A.lset(p,bone,pos,m.qslerp(A.lget(relaxed,bone)[1],tuple(open_q.to_tuple()),.65))
    # Every support is placed against the real bedding (anim lane, 2026-11-07). Clip space: the body lies along +Y (feet)
    # with its back to -Z; the placement (build_anims.py) puts the pelvis joint HIP cm over the duvet, so the duvet plane
    # in clip space is pelvis.z - HIP, raised along the bed by the traced profile (the pillow is +15 cm at the head end).
    w0 = p.world()
    pel = w0["pelvis"][0]
    duvet = pel[2] - HIP

    def surface(y):  # clip-space duvet height under body position y
        x_world = PEL_X - (y - pel[1]) * SCALE
        return duvet + (profile(x_world) - DUVET_AT_PELVIS) / SCALE

    # Straight, relaxed legs. Bed-end clearance belongs to the whole lying body's placement.
    placement=W.load_placement();rig=placement['rig']
    # Canonical sock skin, measured against source ankles in the straight Teen pose.
    heel_skin_offsets={'l':(-8.72783,-.36625,-11.06978),'r':(-9.51343,-.12945,-10.93108)}
    for side, spread in (("l", 17.0), ("r", -14.0)):
        thigh, calf, foot = (b + "_" + side for b in ("thigh", "calf", "foot"))
        hip, hq = A.wget(p, thigh); knee, kq = A.wget(p, calf); ankle, aq = A.wget(p, foot)
        a, b = m.length(m.sub(knee, hip)), m.length(m.sub(ankle, knee))
        reach = math.sqrt(a * a + b * b + 2 * a * b * math.cos(math.radians(KNEE_BEND)))
        z = surface(hip[1] + reach) + HEEL
        dz, dx = z - hip[2], spread - hip[0]
        target = (spread, hip[1] + math.sqrt(max(reach * reach - dz * dz - dx * dx, 1.0)), z)
        for _ in range(3):
            world_ankle=W.comp_to_world(target,lay['loc'],lay['yaw'],rig)
            offset=heel_skin_offsets[side]
            support=W.trace_down(world_ankle[0]+offset[0],world_ankle[1]+offset[1])
            assert support is not None and 45<support<85,('heel support',side,support)
            corrected=(world_ankle[0],world_ankle[1],support-offset[2]+.3)
            z=W.world_to_comp(corrected,lay['loc'],lay['yaw'],rig)[2]
            dz=z-hip[2]
            target=(spread,hip[1]+math.sqrt(max(reach*reach-dz*dz-dx*dx,1.0)),z)
        pole = m.add(hip, (spread * .6, 30.0, 40.0))
        q1, q2, reached = m.two_bone(hip, knee, ankle, target, pole)
        A.wset(p, thigh, hip, m.qnorm(m.qmul(q1, hq)))
        at, kq = A.wget(p, calf); A.wset(p, calf, at, m.qnorm(m.qmul(q2, kq)))
        A.wset(p, foot, A.wget(p, foot)[0], aq)
        assert m.length(m.sub(A.wget(p, foot)[0], target)) < 0.5, (side, reached, target)
        print("leg", side, "knee", [round(c, 1) for c in A.wget(p, calf)[0]], "ankle", [round(c, 1) for c in target])

    def place_hand(side, target, pole, fingers, thumb):
        """Two-bone arm onto target, then the hand turned so its fingers and thumb side point where asked."""
        upper, lower, hand = (b + "_" + side for b in ("upperarm", "lowerarm", "hand"))
        sh, sq = A.wget(p, upper); el, eq = A.wget(p, lower); wr, wq = A.wget(p, hand)
        q1, q2, reached = m.two_bone(sh, el, wr, target, m.add(sh, pole))
        A.wset(p, upper, sh, m.qnorm(m.qmul(q1, sq)))
        ep, eq = A.wget(p, lower); A.wset(p, lower, ep, m.qnorm(m.qmul(q2, eq)))
        hp, hq = A.wget(p, hand)
        if fingers is None:
            fingers = m.norm(m.sub(hp, A.wget(p, lower)[0]))
            thumb = m.mul(m.norm(m.cross(UP, fingers)), -1.0 if side == 'r' else 1.0)
        w = p.world()
        f = m.sub(w["middle_01_" + side][0], hp)
        t = m.sub(w["index_01_" + side][0], w["pinky_01_" + side][0])
        A.wset(p, hand, hp, m.qnorm(m.qmul(m.align(f, t, fingers, thumb), hq)))
        assert m.length(m.sub(A.wget(p, hand)[0], target)) < 0.5, (side, reached, target)
        if side == 'r':
            f = m.norm(m.sub(A.wget(p,'middle_01_r')[0],hp))
            arm = m.norm(m.sub(hp,A.wget(p,lower)[0]))
            assert m.dot(f,arm) > math.cos(math.radians(10)), 'Sleeping wrist must follow the forearm'
        print("hand", side, [round(c, 1) for c in target])

    # neck and head: flex onto the pillow (spine_05, neck_01, neck_02), then aim the face at the ceiling, a little
    # toward his feet (chin tucked, never cranked back) and turned toward the nightstand
    w = p.world()
    head_target_z = surface(w["head"][0][1]) + SKULL
    lat = m.norm(m.sub(w["clavicle_l"][0], w["clavicle_r"][0]))
    sign = 1.0
    for _ in range(6):
        before = p.world()["head"][0][2]
        lift = head_target_z - before
        if abs(lift) < 0.3:
            break
        for bone, share in (("spine_05", 0.25), ("neck_01", 0.4), ("neck_02", 0.35)):
            pos, q = A.wget(p, bone)
            arm_len = m.length(m.sub(p.world()["head"][0], pos))
            deg = math.degrees(math.asin(max(-1.0, min(1.0, lift * share / max(arm_len, 1.0)))))
            A.wset(p, bone, pos, m.qnorm(m.qmul(m.qaxis(m.mul(lat, sign), deg), q)))
        if abs(head_target_z - p.world()["head"][0][2]) > abs(lift):  # wrong way round: undo by flipping the axis
            sign = -sign
    hp, hq = A.wget(p, "head")
    face_now, crown_now = m.qrot(hq, FACE_LOCAL), m.qrot(hq, CROWN_LOCAL)
    want_face = m.norm(m.add(m.mul(UP, math.cos(math.radians(CHIN))), (0.0, math.sin(math.radians(CHIN)), 0.0)))
    want_face = m.qrot(m.qaxis((0.0, 1.0, 0.0), TURN_SIGN * TURN), want_face)
    want_crown = m.norm(m.cross(m.cross(want_face, (0.0, -1.0, 0.0)), want_face))
    A.wset(p, "head", hp, m.qnorm(m.qmul(m.align(face_now, crown_now, want_face, want_crown), hq)))
    print("head z %.1f (pillow %.1f + %.1f), face %s" % (p.world()["head"][0][2], surface(hp[1]), SKULL,
          [round(c, 2) for c in m.qrot(A.wget(p, "head")[1], FACE_LOCAL)]))
    # The spine correction must precede hand support; otherwise it lifts a planted arm.
    belly = (pel[0] - 6.0, pel[1] - 13.0, duvet + BELLY - 3.0)
    place_hand("r", belly, (-40.0, 15.0, -25.0), None, None)
    side_l = (pel[0] + 31.0, pel[1] - 8.0, surface(pel[1] - 8.0) + 3.0)
    wrist_world=W.comp_to_world(side_l,lay['loc'],lay['yaw'],rig)
    # Measured actual Teen palm surface relative to the source wrist, not its bone origin.
    palm_offset=(-8.25833,.72290,3.89432)
    support=W.trace_down(wrist_world[0]+palm_offset[0],wrist_world[1]+palm_offset[1])
    assert support is not None and 45<support<85,('resting palm support',support)
    side_l=W.world_to_comp((wrist_world[0],wrist_world[1],support-palm_offset[2]+.3),lay['loc'],lay['yaw'],rig)
    place_hand("l", side_l, (35.0, 10.0, -25.0), (0.15, 1.0, -0.1), (-1.0, 0.0, 0.0))
    w = p.world()
    # breath axis: lifts spine_05 off the bed when spine_03 turns about it
    body = m.norm(m.sub(w["spine_05"][0], w["spine_03"][0]))
    axis = m.norm(m.cross(body, UP))
    probe = m.qrot(m.qaxis(axis, 5.0), m.sub(w["spine_05"][0], w["spine_03"][0]))
    if probe[2] < w["spine_05"][0][2] - w["spine_03"][0][2]:
        axis = m.mul(axis, -1.0)
    base = p.copy()

    def breathe(a, k):  # a bump at the chest: spine_04 turns back k times, spine_05 restores the neck's angle
        f = base.copy()
        for bone, s in (("spine_03", 1.0), ("spine_04", -k), ("spine_05", k - 1.0)):
            pos, q = A.wget(f, bone)
            A.wset(f, bone, pos, m.qnorm(m.qmul(m.qaxis(axis, s * a), q)))
        return f

    head0 = base.world()["head"][0]
    k = min((x / 20.0 for x in range(20, 81)), key=lambda kk: m.length(m.sub(breathe(BREATH, kk).world()["head"][0], head0)))
    n = int(round(LEN * W.FPS))
    frames = [breathe(BREATH * 0.5 * (1.0 - math.cos(2.0 * math.pi * (i / float(W.FPS)) / PERIOD)), k) for i in range(n + 1)]
    print("counter-turn factor k = %.2f" % k)
    peak, rest = frames[int(PERIOD * W.FPS / 2)].world(), base.world()
    lift = peak["spine_04"][0][2] - rest["spine_04"][0][2]
    bob = m.length(m.sub(peak["head"][0], rest["head"][0]))
    print("breath: chest rises %.2f cm, head moves %.2f cm at the peak, %d frames" % (lift, bob, n + 1))
    assert 0.3 < lift < 1.5 and bob < 0.3, "breath out of range"
    if os.environ.get("FOA_DRY") == "1":
        return
    seq = unreal.load_asset(OUT) or EAL.duplicate_asset(SRC, OUT)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
    unreal.AnimationLibrary.remove_all_animation_notify_tracks(seq)
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("Wake lying hold", False)
    ctrl.set_frame_rate(unreal.FrameRate(W.FPS, 1), False)
    ctrl.set_number_of_frames(unreal.FrameNumber(n), False)
    for b in A.names:
        loc = [f.local[b] for f in frames]
        ctrl.set_bone_track_keys(b, [unreal.Vector(*x[0]) for x in loc], [unreal.Quat(*x[1]) for x in loc],
                                 [unreal.Vector(*x[2]) for x in loc], False)
    ctrl.close_bracket(False)
    seq.set_editor_property("enable_root_motion", False)
    assert EAL.save_loaded_asset(seq, False), 'Lying animation save failed'
    support={b:dict(position=A.wget(base,b)[0],rotation=A.wget(base,b)[1])
             for b in ('pelvis','spine_03','spine_05','neck_01','head','calf_l','calf_r','foot_l','foot_r',
                       'lowerarm_l','lowerarm_r','hand_l','hand_r')}
    Path('P:/FoA/Saved/WakeUp/lying_support_source.json').write_text(json.dumps(dict(asset=OUT,
        duration=LEN,chest_lift_cm=lift,head_motion_cm=bob,source_component_pose=support),indent=1))
    print("wrote", OUT, "%.2f s" % seq.get_play_length())


main()
