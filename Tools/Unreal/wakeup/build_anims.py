"""Wake-up animation and placement (run inside the editor):
  python Tools/Unreal/ue_remote.py Tools/Unreal/wakeup/build_anims.py [FOA_DRY=1] [FOA_KEEP_SEAT=1]
1. Reads the room (bed, nightstand, SandClock_WakeUp, mattress traces, the duvet dent centre) and the player rig.
2. Places the bed-edge sit so the mocap grab lands on the clock, sits the lying body in the dent, and derives the shots.
3. Writes /Game/FoA/Cinematics/WakeUp/AS_FoA_Wake_EdgeReach (with the snooze slap; FOA_SLAP=0 for the old reach) (edge_clip.py composite, Manny skeleton, 30 fps) unless
   FOA_DRY=1, and Saved/WakeUp/placement.json for Tools/Unreal/cine/build_ls_wakeup.py."""
import math
import os
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/wakeup")
import importlib  # noqa: E402

import wake_common as W  # noqa: E402

importlib.reload(W)
m, edge_clip = W.m, W.edge_clip
EAL = unreal.EditorAssetLibrary
DRY = os.environ.get("FOA_DRY") == "1"
INSET = 15.0       # pelvis this far in from the mattress edge
DENT = (270.0, -191.0)  # player lane's M_FoA_BeddingSettle BodyCenter (contract: dent centre)
HIP_SURFACE_DEPTH = 14.0  # Original MH skinned hip underside is14cm below its pelvis joint; measured leg-skin cache.
SEAT_SINK = 7.0    # a seated body presses this far into mattress and duvet
KEEP = os.environ.get("FOA_KEEP_SEAT") == "1"  # reuse the solved seat in placement.json
SLAP = os.environ.get("FOA_SLAP", "1") == "1"  # the snooze slap (palm down on the lid) instead of the PickUp reach
SLAP_T = {"contact": 1.50, "drop": 0.25, "press": 0.35}  # into the3.5s gesture:23.80+1.50=25.30


def v3(t):
    return [round(c, 2) for c in t]


def room():
    """Bed geometry (bounds, head end, sitting side), nightstand, clock and lantern, from Hayba's actor list."""
    A = W.room_actors()
    find = lambda pred: next((v for k, v in A.items() if pred(k.lower())), None)  # noqa: E731
    bed_b = W.native_bounds(A.get("Bed"))
    assert bed_b, "no Bed (StaticMeshActor) in FOA_ROOM"
    bo, be = bed_b
    long_x = be[0] >= be[1]
    ax = (1.0, 0.0, 0.0) if long_x else (0.0, 1.0, 0.0)
    lat = (0.0, 1.0, 0.0) if long_x else (1.0, 0.0, 0.0)
    half_long, half_lat = (be[0], be[1]) if long_x else (be[1], be[0])
    night_i = find(lambda k: k.startswith("nightstand"))
    night = W.native_bounds(night_i) or ((tuple(night_i["location"]), (22.0, 22.0, 30.0)) if night_i else None)
    clock_i = A.get("SandClock_WakeUp")
    clock = tuple(clock_i["location"]) if clock_i else None
    ref = clock or (night[0] if night else None)
    if ref:
        d = m.sub(ref, bo)
        head = 1.0 if m.dot(d, ax) >= 0 else -1.0
        side = 1.0 if m.dot(d, lat) >= 0 else -1.0
    else:  # head against the nearer wall, sit toward the room centre
        head = 1.0 if m.dot(bo, ax) >= 0 else -1.0
        side = -1.0 if m.dot(bo, lat) >= 0 else 1.0
    lantern_i = find(lambda k: "lantern" in k) or find(lambda k: "ceilinglight" in k.replace("_", ""))
    out = {"bed_o": bo, "bed_e": be, "ax": m.mul(ax, head), "lat": m.mul(lat, side), "half_long": half_long,
           "half_lat": half_lat, "night": night, "clock": clock, "has_clock": bool(clock),
           "lantern": tuple(lantern_i["location"]) if lantern_i else None}
    print("room: bed", v3(bo), v3(be), "head dir", v3(out["ax"]), "sit side", v3(out["lat"]), "night", night,
          "clock", clock, "lantern", out["lantern"])
    return out


def edge_point(R, s, inset):
    """Point on the sitting side, s cm along the bed from its centre toward the head, `inset` cm in from the edge."""
    return m.add(m.add(R["bed_o"], m.mul(R["ax"], s)), m.mul(R["lat"], R["half_lat"] - inset))


def main():
    rig = W.player_rig()
    H = rig["half_height"]
    print("rig", rig)
    clips = {k: unreal.load_asset(W.UAL + n) for k, n in (("sit", "UAL_Sitting_Idle_Loop"), ("pick", "UAL_PickUp_Table"),
                                                             ("exit", "UAL_Sitting_Exit"), ("lay", "UAL_LayToIdle"))}
    A = W.UeAdapter(clips)
    reference=unreal.AnimPoseExtensions.get_reference_pose(clips['sit'].get_editor_property('skeleton'))
    open_hand=m.Pose({b:A._xf(unreal.AnimPoseExtensions.get_bone_pose(reference,b,W.LOCAL)) for b in A.names},A.parent)
    F, L, U = W.comp_dirs(rig)
    R = room()

    # ---- the seat: mattress height at the sitting edge, planted-hand targets in component space
    seat_w = edge_point(R, R["half_long"] * 0.25, INSET)
    mz = W.trace_down(seat_w[0], seat_w[1])
    assert mz is not None, "trace found no mattress at the bed edge"
    mlab = "trace"
    sit0 = A.pose_at("sit", 0.0)
    pel_c = A.wget(sit0, "pelvis")[0]
    seat_clip = pel_c[2] - 10.0  # the clip's own seat height (pelvis about 10 cm above the seat)
    print("mattress top %.1f (%s), clip seat %.1f -> hips sink %.1f cm" % (mz, mlab, seat_clip, mz - seat_clip))
    plant = {s: m.add(m.add(pel_c, m.mul(L, sg * 26.0)), m.add(m.mul(F, 8.0), (0.0, 0.0, mz + 3.0 - pel_c[2])))
             for s, sg in (("l", 1.0), ("r", -1.0))}
    spine = [b for b in ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01", "neck_02", "head")
             if b in A.names]
    cfg = {"sit": "sit", "pick": "pick", "exit": "exit", "sit_len": clips["sit"].get_play_length(),
           "pick_len": clips["pick"].get_play_length(), "exit_len": clips["exit"].get_play_length(),
           "exit_rate": W.T["exit_rate"], "release": (0.28, 0.58), "T_hold": W.T["edge_hold"],
           "T_reach": W.T["edge_reach"], "T_breath": W.T["edge_breath"], "F": F, "L": L, "U": U, "plant": plant,
           "reach_side": "l", "spine": spine, "palm_out_deg": 20.0,
           "slouch_bones": [b for b in ("spine_01", "spine_02", "spine_03") if b in A.names], 'open_hand_pose':open_hand}
    E = edge_clip.Edge(A, cfg)
    # Lift the hips toward the mattress (leaving a soft-mattress sink), as far as still lets both hands rest on it.
    want = max(0.0, mz - seat_clip - SEAT_SINK)
    for raise_cm in [want - i * 1.0 for i in range(int(want) + 1)] + [0.0]:
        E.c["seat_raise"] = max(0.0, raise_cm)
        try:
            E.auto_slouch(limit=8.0)
            break
        except ValueError:
            continue
    print("seat raise %.1f cm (wanted %.1f), hips sink %.1f cm, slouch %.0f deg" % (
        E.c["seat_raise"], want, mz - seat_clip - E.c["seat_raise"], E.slouch_deg))
    keep = KEEP and os.path.exists(W.PLACEMENT)
    slap = SLAP and R["has_clock"]
    g_c = None if keep else E.source_grab()

    # ---- solve the sit (position along the edge, yaw off square) so the mocap grab lands on the clock
    # (FOA_KEEP_SEAT=1 keeps the solved seat, so the two-shot, the stand and their cameras don't move)
    out_dir = R["lat"]
    assert R["has_clock"] or R["night"], "need SandClock_WakeUp or a Nightstand to aim the reach"
    turn = 1.0 if m.dot(m.qrot(W.yaw_q(10.0), out_dir), R["ax"]) > 0 else -1.0  # +phi turns toward the head end
    if R["has_clock"]:
        co = R["clock"]
        target = (co[0], co[1], co[2] + 9.0)  # pivot at the clock's base: wrist about its middle, fingers close round it
    else:
        no, ne = R["night"]
        target = None
    feet_c = [A.wget(sit0, b)[0] for b in ("foot_l", "foot_r", "ball_l", "ball_r")]
    best = None
    for si in ([] if keep else range(-10, 31)):
        s = R["half_long"] * si / 40.0
        if s > R["half_long"] - 45.0:  # keep the hips off the pillow
            continue
        for phi in range(-40, 41, 2):
            fw = m.qrot(W.yaw_q(turn * phi), out_dir)
            yaw = W.yaw_of(fw)
            pel_w = edge_point(R, s, INSET)
            loc = m.sub((pel_w[0], pel_w[1], 0.0), m.sub(W.comp_to_world(pel_c, (0.0, 0.0, 0.0), yaw, rig), (0.0, 0.0, 0.0)))
            loc = (loc[0], loc[1], H)
            grab = W.comp_to_world(g_c, loc, yaw, rig)
            if target is None:  # no clock yet: aim for the nightstand top, inset 7 cm
                tx = min(max(grab[0], no[0] - ne[0] + 7), no[0] + ne[0] - 7)
                ty = min(max(grab[1], no[1] - ne[1] + 7), no[1] + ne[1] - 7)
                tgt = (tx, ty, no[2] + ne[2] + 6.0)
            else:
                tgt = target
            cost = m.length(m.sub(grab, tgt)) + 0.15 * abs(phi)
            if R["night"]:
                no, ne = R["night"]
                for f in feet_c:
                    fwp = W.comp_to_world(f, loc, yaw, rig)
                    if abs(fwp[0] - no[0]) < ne[0] + 6 and abs(fwp[1] - no[1]) < ne[1] + 6:
                        cost += 200.0
            if best is None or cost < best[0]:
                best = (cost, s, phi, yaw, loc, tgt, grab)
    if keep:
        old = W.load_placement()["edge"]
        loc, yaw, tgt = tuple(old["loc"]), old["yaw"], tuple(old["clock"])
        print("sit kept from placement.json: loc %s yaw %.1f" % (v3(loc), yaw))
    else:
        cost, s, phi, yaw, loc, tgt, grab = best
        print("sit: s=%.0f phi=%d yaw=%.1f loc=%s grab miss %.1f cm, clock target %s" % (
            s, phi, yaw, v3(loc), m.length(m.sub(grab, tgt)), v3(tgt)))
    if slap:  # palm-down on the lid: its top centre from the clock's mesh bounds
        clock_actor=unreal.find_object(None,W.room_actors()['SandClock_WakeUp']['path'])
        splats=next(c for c in clock_actor.get_components_by_class(unreal.StaticMeshComponent) if c.get_name()=='Splats')
        bounds=splats.get_editor_property('static_mesh').get_bounding_box()
        # Component bounds include WPO padding and the separate pile can be larger.
        # Contact is the clock mesh's geometric top in its actual component frame.
        point=unreal.MathLibrary.transform_location(splats.get_world_transform(),unreal.Vector(0,0,bounds.max.z))
        # The bounds top (origin +22) is 7-9 cm above what the camera sees: hit_insert4 measured the white clock's top at
        # origin +15 and the sand clock's bells at origin +13, so the palm meets origin +14 and drives in from there.
        lid=(point.x,point.y,splats.get_world_location().z+14.0)
        tgt = lid
        ref = unreal.AnimPoseExtensions.get_reference_pose(clips["sit"].get_editor_property("skeleton"))
        hr = unreal.AnimPoseExtensions.get_bone_pose(ref, "head", W.WORLD).rotation
        cfg["slap"] = {"top": W.world_to_comp(lid, loc, yaw, rig), "t_contact": SLAP_T["contact"],
                       "drop": SLAP_T["drop"], "press": SLAP_T["press"], "sink": 5.0, "lift": 18.0, "palm_off": 6.0,
                       "palm_h": 2.5, "lean_deg": 12.0, "look_w": 0.7,
                       "face_local": m.qrot(m.qinv((hr.x, hr.y, hr.z, hr.w)), F)}
        cfg["clock"] = cfg["slap"]["top"]
        calibration_path='P:/FoA/Saved/WakeUp/teen_palm_calibration.json'
        if os.path.exists(calibration_path):
            import json
            correction=json.load(open(calibration_path))['world_offset_cm']
            comp_q=W.yaw_q(yaw+rig['mesh_rel'][1])
            cfg['slap']['retarget_offset']=m.mul(m.qrot(m.qinv(comp_q),correction),1/rig['mesh_scale'])
        p_hit = E.frame(cfg["T_hold"] + SLAP_T["contact"])
        compensated=m.add(cfg['slap']['top'],cfg['slap'].get('retarget_offset',(0,0,0)))
        miss = m.length(m.sub(E.palm_point(p_hit), compensated))
        print("slap: lid %s, contact at edge+%.2fs, palm misses the lid by %.1f cm" % (
            v3(lid), cfg["T_hold"] + SLAP_T["contact"], miss))
        assert miss < 3.0, "palm does not land on the lid"
        arm = m.norm(m.sub(A.wget(p_hit,'hand_l')[0],A.wget(p_hit,'lowerarm_l')[0]))
        fingers = m.norm(m.sub(A.wget(p_hit,'middle_01_l')[0],A.wget(p_hit,'hand_l')[0]))
        wrist_bend = math.degrees(math.acos(max(-1.0,min(1.0,m.dot(arm,fingers)))))
        assert wrist_bend < 35.0, ('contact wrist bend',wrist_bend)
        print('contact wrist bend %.1f degrees' % wrist_bend)
        # main, hit5: a slap, not a limp hand. On the impact frame the fingers lie flat (a touch bent back is fine),
        # fanned 5-8 deg apart, and the wrist stays fairly straight.
        Uc = E.U
        def fdir(d):
            return m.norm(m.sub(A.wget(p_hit, d + '_03_l')[0], A.wget(p_hit, d + '_01_l')[0]))
        droop = {d: math.degrees(math.asin(max(-1.0, min(1.0, -m.dot(fdir(d), Uc))))) for d in ('index', 'middle', 'ring', 'pinky')}
        def flat_angle(a_, b_):
            fa, fb = [m.norm(m.sub(x, m.mul(Uc, m.dot(x, Uc)))) for x in (fdir(a_), fdir(b_))]
            return math.degrees(math.acos(max(-1.0, min(1.0, m.dot(fa, fb)))))
        fan = [flat_angle(a_, b_) for a_, b_ in (('index', 'middle'), ('middle', 'ring'), ('ring', 'pinky'))]
        print('contact fingers: droop %s deg (down +), fan %s deg' % ({k: round(v, 1) for k, v in droop.items()}, [round(f, 1) for f in fan]))
        assert all(-9.0 < v < 6.0 for v in droop.values()), ('fingers not flat at contact', droop)
        assert all(8.0 < f < 14.0 for f in fan), ('finger fan at contact', fan)
        th = m.norm(m.sub(A.wget(p_hit, 'thumb_03_l')[0], A.wget(p_hit, 'thumb_01_l')[0]))
        thumb_down = math.degrees(math.asin(max(-1.0, min(1.0, -m.dot(th, Uc)))))
        print('contact thumb %.1f deg below the palm plane' % thumb_down)
        assert thumb_down < 20.0, ('the thumb hangs below the palm', thumb_down)
        assert wrist_bend < 15.0, ('wrist breaks at contact', wrist_bend)
        t_hit = cfg["T_hold"] + SLAP_T["contact"]
    else:
        cfg["clock"] = W.world_to_comp(tgt, loc, yaw, rig)
        warp = E.measure_warp()
        print("warp %s (%.1f cm), grab at edge+%.2fs" % (v3(warp), m.length(warp), W.T["edge_hold"] + E.t_grab))
        t_hit = W.T["edge_hold"] + E.t_grab

    # ---- the lying body: dent centre, head toward the head end, settled into the duvet
    lay0 = A.pose_at("lay", 0.0)
    pel_l, chest_l, head_l = (A.wget(lay0, b)[0] for b in ("pelvis", "spine_03", "head"))
    axis_c = m.sub(head_l, pel_l)
    yaw_l = W.yaw_of(R["ax"]) - W.yaw_of(W.comp_dir_to_world(axis_c, 0.0, rig))
    mid_c = m.lerp(pel_l, chest_l, 0.5)
    dz, dlab = W.trace_down(DENT[0], DENT[1]), "trace"
    mid_w0 = W.comp_to_world(mid_c, (0.0, 0.0, 0.0), yaw_l, rig)
    pelvis_zero = W.comp_to_world(pel_l, (0.0,0.0,0.0), yaw_l, rig)
    pelvis_height = dz + HIP_SURFACE_DEPTH * rig.get('mesh_scale',1.0)
    lay_loc = (DENT[0] - mid_w0[0], DENT[1] - mid_w0[1], pelvis_height-pelvis_zero[2])
    # The skin surface rests on the duvet. Local neck pose supplies pillow support without lowering the legs.
    pitch = 0.0
    q = W.actor_q(pitch, yaw_l)
    head_w = W.comp_to_world_q(head_l, lay_loc, q, rig)
    print("Flat mattress placement: pelvis %.1f, scaled hip clearance %.1f, head bone z %.1f" %
          (pelvis_height,HIP_SURFACE_DEPTH*rig.get('mesh_scale',1.0),head_w[2]))
    lows = sorted(A.wget(lay0, b)[0][2] for b in ("pelvis", "spine_01", "spine_03", "head", "calf_l", "calf_r"))
    hands = [round(A.wget(A.pose_at("lay", t), "hand_" + s_)[0][2], 1) for t in (0.0, 0.22, 0.44) for s_ in ("l", "r")]
    print("lying: duvet top %.1f (%s), yaw %.1f, head at %s; lowest bones %s; hand heights over the sit-up %s" % (
        dz, dlab, yaw_l, v3(head_w), [round(z, 1) for z in lows[:3]], hands))

    prof = [(round(x), round(W.trace_down(x, DENT[1]) or 0, 1)) for x in range(170, 371, 20)]
    print("surface along the bed (x, z):", prof)
    pel_w = W.comp_to_world(pel_c, loc, yaw, rig)
    data = {"rig": rig, "room": {k: R[k] for k in ("bed_o", "bed_e", "ax", "lat", "lantern", "has_clock")},
            "edge": {"loc": loc, "yaw": yaw, "pelvis": pel_w, "mattress": mz, "clock": tgt, "slouch": E.slouch_deg},
            "lay": {"loc": lay_loc, "yaw": yaw_l, "pitch": pitch, "head": head_w, "duvet": dz,
                    "pelvis": W.comp_to_world_q(pel_l, lay_loc, q, rig),
                    "head_end": W.comp_to_world_q(A.wget(A.pose_at("lay", W.SITUP_SPAN), "head")[0], lay_loc, q, rig)},
            "grab_t": W.T["edge"] + t_hit, "edge_len": E.duration()}
    if keep:
        # Reauthoring the arm must not undo the measured Teen bedding placement.
        data['lay']=W.load_placement()['lay']
    W.save_placement(data)
    print("placement saved", W.PLACEMENT)
    if DRY:
        return

    # ---- bake the composite to an AnimSequence (Manny skeleton)
    n = int(math.floor(E.duration() * W.FPS))
    frames = [E.frame(i / float(W.FPS)) for i in range(n + 1)]
    if slap:
        arm_frames = [p for i,p in enumerate(frames) if .35 <= i / float(W.FPS)-cfg['T_hold'] <= 2.7]
        elbow_height = max(m.dot(m.sub(A.wget(p,'lowerarm_l')[0],A.wget(p,'upperarm_l')[0]),U) for p in arm_frames)
        # v2 slap is raised from the top: the elbow may reach shoulder height, never a chicken wing above it
        assert elbow_height < 3, ('raised slap elbow',elbow_height)
        print('highest slap elbow %.2f cm relative to the shoulder' % elbow_height)
    seq = unreal.load_asset(W.EDGE_ANIM)
    if not seq:
        EAL.make_directory(W.WAKE)
        seq = EAL.duplicate_asset(W.UAL + "UAL_Sitting_Idle_Loop", W.EDGE_ANIM)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
    unreal.AnimationLibrary.remove_all_animation_notify_tracks(seq)
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("Wake edge composite", False)
    ctrl.set_frame_rate(unreal.FrameRate(W.FPS, 1), False)
    ctrl.set_number_of_frames(unreal.FrameNumber(n), False)
    for b in A.names:
        pos = [unreal.Vector(*f.local[b][0]) for f in frames]
        rot = [unreal.Quat(*f.local[b][1]) for f in frames]
        scl = [unreal.Vector(*f.local[b][2]) for f in frames]
        ctrl.set_bone_track_keys(b, pos, rot, scl, False)
    ctrl.close_bracket(False)
    seq.set_editor_property("enable_root_motion", False)
    EAL.save_loaded_asset(seq, False)
    print("wrote", W.EDGE_ANIM, "%d frames %.2fs" % (n + 1, seq.get_play_length()))


main()
