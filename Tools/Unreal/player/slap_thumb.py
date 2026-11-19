"""Wake slap: the right thumb on the Teen side (main 2026-11-10; hit7 showed the Manny-side thumb edits still hanging the
thumb below the palm after the Manny -> Teen retarget). Applied after the retarget, so the thumb sits alongside the
index whatever the retarget does to it. v1 used rig's Teen rest + curl 5/8/10, but the Teen rest thumb already points
36 deg to the palm side (teen_ref_pose.json), so hit_insert8 still showed it hanging under the flat palm. v2: thumb_01
turned (shortest arc, in the hand frame) so the thumb lies 3 deg off the palm plane at 20 deg from the fingers on the
index side (alongside the index); thumb_02 / 03 keep a small tip curl (+5 / +8, rig's axis). `python slap_thumb.py check` verifies it offline
on the exported Teen reference pose. Steps, in order:
  assets  (editor Python) AS_FoA_Slap_Thumb_R (SK_Teen_Body skeleton, the three thumb bones) and the float curve
          FoA_SlapThumb on AS_FoA_Wake_EdgeReach: 0, up to 1 over the reach start, held through the slap, 0 after the
          withdraw. build_anims.py rewrites only bone tracks, so a re-bake keeps the curve (re-run this if the timing moves).
            python Tools/Unreal/ue_remote.py Tools/Unreal/player/slap_thumb.py FOA_AREAS=Characters FOA_STEP=assets
  layer   (editor Python) ABP_FoAPlayer_MH: Layered blend per bone on thumb_01_r (local space) right after the phone
          layer, the pose at SlapThumbWeight. Compile and save with Hayba afterwards.
            python Tools/Unreal/ue_remote.py Tools/Unreal/player/slap_thumb.py FOA_AREAS=Characters FOA_STEP=layer
  push    (Hayba) BP_FoAPlayer.UpdateSlapThumb: SlapThumbWeight = the source mesh's FoA_SlapThumb curve, every tick,
          called after SteadyFPEye at the end of UpdateFirstPersonVisibility (fp_steady_eye.py first).
            $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/slap_thumb.py push"""
import math
import os
import sys

STEP = os.environ.get('FOA_STEP') or (sys.argv[1] if len(sys.argv) > 1 else '')
POSE = '/Game/FoA/Characters/Player/Anims/Hands/AS_FoA_Slap_Thumb_R'
MH = '/Game/FoA/Characters/Player/ABP_FoAPlayer_MH'
CURVE = 'FoA_SlapThumb'
CURL = {'thumb_02_r': 5.0, 'thumb_03_r': 8.0}  # tip curl on top of rest, about local -X (rig: pose_sheet.set_thumb)
PALM_DEG, SPREAD_DEG = 3.0, 20.0  # the thumb's direction: this far to the palm side of the palm plane, this far from the fingers
if os.environ.get('FOA_SLAP_TEST') == '1':  # render A/B only: the thumb 60 deg to the BACK of the hand, unmistakable if the layer renders
    PALM_DEG = -60.0
# (v2 had 35: in game it lay 5 deg off the palm at 33 deg, which the Cam_Hit angle foreshortens into a stub 'hanging' under the
# palm, hit_insert10. 20 is as close to the index as its base allows: 1.62 cm between the thumb and index bone lines.)
RAMP = ((0.0, 0.0), (0.20, 0.0), (0.50, 1.0), (2.80, 1.0), (3.20, 0.0))  # seconds after the edge hold (contact at +1.50)


def curl_q(q, deg):
    """q (x, y, z, w) then deg about the bone's own -X (Hamilton product q * axis_angle(-X, deg))."""
    s, c = math.sin(math.radians(deg) / 2), math.cos(math.radians(deg) / 2)
    bx, by, bz, bw = -s, 0.0, 0.0, c
    x, y, z, w = q
    return (w * bx + x * bw + y * bz - z * by, w * by - x * bz + y * bw + z * bx, w * bz + x * by - y * bx + z * bw, w * bw - x * bx - y * by - z * bz)


def thumb_pose(world, local):
    """{bone: local quat} for thumb_01..03_r from the Teen reference pose (world / local: bone -> (pos, quat))."""
    import sys as _s
    _s.path.insert(0, 'P:/FoA/Tools/Unreal/wakeup')
    import wake_math as m
    pos = lambda b: world[b + '_r'][0]  # noqa: E731
    f = m.norm(m.sub(pos('middle_01'), pos('hand')))
    a = m.norm(m.sub(pos('index_01'), pos('pinky_01')))
    a = m.norm(m.sub(a, m.mul(f, m.dot(a, f))))  # across the palm toward the index, square to the fingers
    n = m.norm(m.cross(f, a))
    tip = m.sub(pos('middle_03'), pos('middle_02'))  # n must point to the palm side: a middle curl moves the tip along it
    if m.dot(m.sub(m.qrot(m.qaxis(m.qrot(world['middle_02_r'][1], (-1.0, 0.0, 0.0)), 30.0), tip), tip), n) < 0:
        n = m.mul(n, -1.0)
    t = m.norm(m.sub(pos('thumb_03'), pos('thumb_01')))
    c, sn = math.cos(math.radians(PALM_DEG)), math.sin(math.radians(PALM_DEG))
    want = m.norm(m.add(m.mul(m.add(m.mul(f, math.cos(math.radians(SPREAD_DEG))), m.mul(a, math.sin(math.radians(SPREAD_DEG)))), c), m.mul(n, sn)))
    lift = m.from_to(t, want)  # world-space turn of the whole thumb
    parent = world['hand_r'][1]
    q1 = m.qnorm(m.qmul(m.qinv(parent), m.qmul(lift, world['thumb_01_r'][1])))
    out = {'thumb_01_r': q1}
    for b, deg in CURL.items():
        out[b] = curl_q(local[b][1], deg)
    return out, dict(f=f, a=a, n=n)


def fk_thumb(world, local, pose):
    """thumb_01 -> thumb_03 direction with the new local rotations (offline check)."""
    import sys as _s
    _s.path.insert(0, 'P:/FoA/Tools/Unreal/wakeup')
    import wake_math as m
    qw = m.qmul(world['hand_r'][1], pose['thumb_01_r'])
    p2 = m.add(world['thumb_01_r'][0], m.qrot(qw, local['thumb_02_r'][0]))
    qw2 = m.qmul(qw, pose['thumb_02_r'])
    p3 = m.add(p2, m.qrot(qw2, local['thumb_03_r'][0]))
    return m.norm(m.sub(p3, world['thumb_01_r'][0]))


assert all(abs(a - b) < 1e-9 for a, b in zip(curl_q((0, 0, 0, 1), 0.0), (0, 0, 0, 1)))  # self-check: zero curl keeps rest
assert abs(curl_q((0, 0, 0, 1), 90.0)[0] + math.sin(math.radians(45))) < 1e-9  # 90 deg about -X from identity

if STEP == 'assets':
    import unreal
    import warnings
    warnings.simplefilter('ignore')  # 'track already exists' on a re-run fills ue_remote's output budget before the result line
    sys.path.insert(0, 'P:/FoA/Tools/Unreal/wakeup')
    import wake_cues  # noqa: E402  (engine-free timeline)
    EAL, AL, AP = unreal.EditorAssetLibrary, unreal.AnimationLibrary, unreal.AnimPoseExtensions
    body = unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body')
    skel = body.get_editor_property('skeleton')
    ref = AP.get_reference_pose(skel)
    seq = unreal.load_asset(POSE)
    if not seq:
        f = unreal.AnimSequenceFactory()
        f.set_editor_property('target_skeleton', skel)
        f.set_editor_property('preview_skeletal_mesh', body)
        seq = unreal.AssetToolsHelpers.get_asset_tools().create_asset(POSE.rsplit('/', 1)[1], POSE.rsplit('/', 1)[0], unreal.AnimSequence, f)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
    ctrl = seq.get_editor_property('controller')
    ctrl.open_bracket('Slap thumb', False)
    ctrl.set_frame_rate(unreal.FrameRate(30, 1), False)
    ctrl.set_number_of_frames(unreal.FrameNumber(1), False)
    xf = lambda b, sp: (lambda t: ((t.translation.x, t.translation.y, t.translation.z), (t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w)))(AP.get_bone_pose(ref, b, sp))  # noqa: E731
    need = [f'{d}_0{k}_r' for d in ('thumb', 'index', 'middle', 'pinky') for k in (1, 2, 3)] + ['hand_r']
    pose, _ = thumb_pose({b: xf(b, unreal.AnimPoseSpaces.WORLD) for b in need}, {b: xf(b, unreal.AnimPoseSpaces.LOCAL) for b in need})
    for b, q in pose.items():
        t = AP.get_bone_pose(ref, b, unreal.AnimPoseSpaces.LOCAL)
        try:
            ctrl.add_bone_curve(b, False)
        except Exception:  # noqa: BLE001  (already tracked)
            pass
        ctrl.set_bone_track_keys(b, [t.translation] * 2, [unreal.Quat(*q)] * 2, [t.scale3d] * 2, False)
    ctrl.close_bracket(False)
    seq.set_editor_property('enable_root_motion', False)
    assert EAL.save_loaded_asset(seq, False)
    edge = unreal.load_asset('/Game/FoA/Cinematics/WakeUp/AS_FoA_Wake_EdgeReach')
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(edge)
    hold, length = wake_cues.T['edge_hold'], edge.get_play_length()
    keys = [(min(hold + dt, length), v) for dt, v in RAMP]
    assert keys[-1][0] > keys[-2][0], ('the clip ends before the thumb blends out', hold, length)
    if AL.does_curve_exist(edge, CURVE, unreal.RawCurveTrackTypes.RCT_FLOAT):
        AL.remove_curve(edge, CURVE, False)
    AL.add_curve(edge, CURVE, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
    AL.add_float_curve_keys(edge, CURVE, [k[0] for k in keys], [k[1] for k in keys])
    assert EAL.save_loaded_asset(edge, False)
    print('SLAP_THUMB assets', POSE, 'curve keys', [(round(t, 2), v) for t, v in keys], 'clip %.2f s' % length)

elif STEP == 'check':  # offline, on Saved/AnimShots/teen_ref_pose.json (export_teen_ref.py)
    import json
    d = json.load(open('P:/FoA/Saved/AnimShots/teen_ref_pose.json'))
    W = {b: (tuple(v[0]), tuple(v[1])) for b, v in d['world'].items()}
    L = {b: (tuple(v[0]), tuple(v[1])) for b, v in d['local'].items()}
    pose, fr = thumb_pose(W, L)
    dot = lambda u, v: sum(x * y for x, y in zip(u, v))  # noqa: E731
    for label, t in (('rest', None), ('slap', fk_thumb(W, L, pose))):
        if t is None:
            t = fk_thumb(W, L, {b: L[b][1] for b in ('thumb_01_r', 'thumb_02_r', 'thumb_03_r')})
        palm = math.degrees(math.asin(dot(t, fr['n'])))
        spread = math.degrees(math.atan2(dot(t, fr['a']), dot(t, fr['f'])))
        print('SLAP_THUMB %s: %.1f deg to the palm side, %.1f deg from the fingers toward the index' % (label, palm, spread))
    assert 0.0 <= palm <= 10.0 and 12.0 <= spread <= 28.0, (palm, spread)

elif STEP == 'layer':
    import unreal
    exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())

    def link(a, ap, b, bp):
        assert PIN.try_create_connection(Graph.pin(a, ap, 'out'), Graph.pin(b, bp, 'in')), (ap, bp)

    ensure_vars(MH, [('SlapThumbWeight', ptype('real'), '0.0', 'Slap', False)])
    bp = unreal.load_asset(MH)
    seq, phone = unreal.load_asset(POSE), unreal.load_asset('/Game/FoA/Characters/Player/Anims/Hands/AS_FoA_Grip_Phone_L')
    assert seq and phone
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    ed = GE.get_graph_editor_by_name(bp, 'AnimGraph')
    nodes = list(ed.list_all_nodes())
    evals = lambda s: [n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_SequenceEvaluator'  # noqa: E731
                       and n.get_editor_property('node').get_editor_property('sequence') == s]
    owner = lambda n: PIN.get_owning_node(next(iter(PIN.list_connected_pins(Graph.pin(n, 'Pose', 'out')))))  # noqa: E731
    if evals(seq):
        player = evals(seq)[0]
        layer = owner(player)
    else:
        prev = owner(evals(phone)[0])  # the phone layer (phone_grip_layer.py)
        out = Graph.pin(prev, 'Pose', 'out')
        after = list(PIN.list_connected_pins(out))
        assert len(after) == 1, len(after)
        pos = BEL.get_node_pos(prev)
        PIN.break_pin_links(out)
        blend = next(str(n) for n in ed.list_available_nodes([]) if 'layeredblendperbone' in str(n).replace(' ', '').lower())
        layer = ed.create_node_from_name(blend, V2(pos.x + 350, pos.y), [])
        player = ed.create_node_from_name("Animation|Sequences|Evaluate'AS_FoA_Slap_Thumb_R'", V2(pos.x + 50, pos.y + 300), [])
        assert layer and player and player.get_class().get_name() == 'AnimGraphNode_SequenceEvaluator', (layer, player)
        link(prev, 'Pose', layer, 'BasePose')
        link(player, 'Pose', layer, 'BlendPoses_0')
        assert PIN.try_create_connection(Graph.pin(layer, 'Pose', 'out'), after[0])
    n = player.get_editor_property('node')
    n.set_editor_property('sequence', seq)
    player.set_editor_property('node', n)
    n = layer.get_editor_property('node')
    setups = list(n.get_editor_property('layer_setup'))
    setup = setups[0] if setups else unreal.InputBlendPose()
    f = unreal.BranchFilter()
    f.set_editor_property('bone_name', 'thumb_01_r')
    f.set_editor_property('blend_depth', 0)
    setup.set_editor_property('branch_filters', [f])
    n.set_editor_property('layer_setup', [setup])
    layer.set_editor_property('node', n)
    pos = BEL.get_node_pos(layer)
    old = [v for v in ed.list_all_nodes() if BEL.get_node_title(v).replace(' ', '') == 'GetSlapThumbWeight']
    v = old[0] if old else ed.add_get_member_variable_node('SlapThumbWeight', '')
    BEL.set_node_pos(v, P(pos.x - 320, pos.y + 440))
    PIN.break_pin_links(Graph.pin(layer, 'BlendWeights_0', 'in'))
    link(v, 'SlapThumbWeight', layer, 'BlendWeights_0')
    for c in list(ed.list_comment_nodes()):
        if BEL.get_comment_text(c) == 'Right thumb at rest in the wake slap':
            ed.remove_comment_node(c)
    c = ed.add_comment_to_nodes('Right thumb at rest in the wake slap', [layer, player], 48)
    BEL.set_comment_color(c, C_VISUAL)
    house_comment_flags(c)
    compile_save(MH)
    print('SLAP_THUMB layer thumb_01_r')

elif STEP == 'push':
    sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
    import hayba_call as h  # noqa: E402
    from held_tool_graphs import Batch, inspect, find  # noqa: E402
    P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
    PC = P + '.BP_FoAPlayer_C'
    MC = MH + '.ABP_FoAPlayer_MH_C'
    F, FN = 'UpdateFirstPersonVisibility', 'UpdateSlapThumb'
    assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
    lease = h.lease_acquire('anim', ['asset:/Game/FoA/Characters/Player'], ttl_s=60)
    try:
        if not h.call('blueprint_inspect_graph', dict(path=P, graph_name=FN)).get('ok'):
            r = h.call('blueprint_add_function', dict(path=P, function_name=FN, inputs=[]))
            assert r.get('ok'), r
        nodes, _ = inspect(P, FN)
        e = find(nodes, FN)
        b = Batch(P, FN)
        old = [n['node_id'] for n in nodes if n['node_id'] != e]
        if old:
            b.ops.append(dict(op='remove', node_ids=old))
        b.get('mesh', 'Mesh', 0, 300)
        b.fn('src', '/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 250, 300); b.link('mesh', 'Mesh', 'src', 'self')
        b.fn('curve', '/Script/Engine.AnimInstance:GetCurveValue', 500, 300, CurveName=CURVE); b.link('src', 'ReturnValue', 'curve', 'self')
        b.get('body', 'Body', 0, 500)
        b.fn('anim', '/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 250, 500); b.link('body', 'Body', 'anim', 'self')
        b.node('mh', 'cast', 300, 0, class_path=MC); b.link('anim', 'ReturnValue', 'mh', 'Object')
        b.set('w', 'SlapThumbWeight', 650, 0, MC); b.link('mh', 'AsABP Fo APlayer MH', 'w', 'self'); b.link('curve', 'ReturnValue', 'w', 'SlapThumbWeight')
        b.chain(e, 'mh', 'w')
        b.comment('Wake slap thumb: the source clip\'s FoA_SlapThumb curve weights the Teen thumb layer',
                  ['mesh', 'src', 'curve', 'body', 'anim', 'mh', 'w'])
        b.run()
        nodes, edges = inspect(P, F)
        if not any(n['title'].replace(' ', '') == FN for n in nodes):
            steady = next(n['node_id'] for n in nodes if n['title'].replace(' ', '') == 'SteadyFPEye')
            assert not any(x['from_node'] == steady and x['from_pin'] == 'then' for x in edges), 'SteadyFPEye is no longer the chain end'
            b = Batch(P, F)
            b.fn('slapthumb', PC + ':' + FN, 5800, 2400); b.link(steady, 'then', 'slapthumb', 'execute')
            b.run()
        nodes, edges = inspect(P, F)
        hook = next(n['node_id'] for n in nodes if n['title'].replace(' ', '') == FN)
        assert any(x['to_node'] == hook for x in edges), 'UpdateSlapThumb not on the exec chain'
        print('SLAP_THUMB push hooked')
    finally:
        h.release('anim', lease)
else:
    sys.exit('FOA_STEP=assets|layer, or push|check')
