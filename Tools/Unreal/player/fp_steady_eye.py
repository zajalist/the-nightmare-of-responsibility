"""First-person steady eye (main 2026-11-10, walk sink: FP eye within +-1.5 cm walking and running). Hayba graph batch.
Cause (walk_sink3 + walk_clip_bob.py): nothing sinks. The live GASP relaxed walk loop carries a 10.6 cm pelvis/head
bob (10.6 in the clip, ~10.4 in PIE; stride warping off and foot IK off change nothing), and FollowCamera rides the
head socket, so the eye swung ~15 cm per step. fp_lookdown_graphs.py's clamp was never applied and would still
leave ~7 cm with a flat-topped bob.
SteadyFPEye(), called at the end of UpdateFirstPersonVisibility (every Tick): camera = the head-socket eye landmark in
x/y; z = the capsule's z (eased at 10, held within 5 cm: rug step-ups pop it ~3 cm) + an eye height above the capsule:
- standing (ground speed under 10): FPEyeHeightB follows the real eye height at 12 (kneels, stand-ups, idle breathing);
- moving: FPEyeHeightB holds, and the height is that standing height plus BOB_K of the real bob around it (main: a
  subtle 1-1.5 cm bob at step frequency reads as walking without the nausea; the real steps keep it in phase),
  blended in by ground speed 10..60;
- FPEyeHeightA eases the result at 15 (no pops when starting or stopping).
v1 (two FInterpTo stages on the live height, walk_sink4 02:01) left 2.4-9.5 cm: the first step of a start dips the head
11 cm for ~0.5 s and the filter followed it.
Idempotent (rebuilds its own function, hooks once).
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/fp_steady_eye.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
PC = P + '.BP_FoAPlayer_C'
F, FN = 'UpdateFirstPersonVisibility', 'SteadyFPEye'
K = '/Script/Engine.KismetMathLibrary:'
EYE = '0,-3.530588955620998,11.768322164387774'  # head-space eye landmark (first_person_graphs.py AttachFirstPersonCamera)
STAND_SPEED, SMOOTH_SPEED, BOB_K = 12.0, 15.0, 0.12  # standing height tracking, output easing, share of the real bob kept
STEP_SPEED, STEP_CM = 10.0, 5.0  # capsule height easing and its bound

assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
lease = h.lease_acquire('anim', ['asset:/Game/FoA/Characters/Player'], ttl_s=60)
try:
    for v in ('FPEyeHeightA', 'FPEyeHeightB', 'FPActorZ'):
        r = h.call('blueprint_add_variable', dict(path=P, variable_name=v, variable_type='float', default_value='0',
                                                  instance_editable=False, update_existing=True, category='Camera'))
        assert r.get('ok'), r
    if not h.call('blueprint_inspect_graph', dict(path=P, graph_name=FN)).get('ok'):
        r = h.call('blueprint_add_function', dict(path=P, function_name=FN, inputs=[]))
        assert r.get('ok'), r
    nodes, _ = inspect(P, FN)
    e = find(nodes, FN)
    b = Batch(P, FN)
    old = [n['node_id'] for n in nodes if n['node_id'] != e]
    if old:
        b.ops.append(dict(op='remove', node_ids=old))
    b.get('face', 'Face', 0, 300)
    b.fn('headxf', '/Script/Engine.SceneComponent:GetSocketTransform', 250, 300, InSocketName='head', TransformSpace='RTS_World')
    b.link('face', 'Face', 'headxf', 'self')
    b.fn('eyew', K + 'TransformLocation', 550, 300, Location=EYE); b.link('headxf', 'ReturnValue', 'eyew', 'T')
    b.fn('eyes', K + 'BreakVector', 800, 300); b.link('eyew', 'ReturnValue', 'eyes', 'InVec')
    b.fn('me', '/Script/Engine.Actor:K2_GetActorLocation', 550, 550)
    b.fn('mes', K + 'BreakVector', 800, 550); b.link('me', 'ReturnValue', 'mes', 'InVec')
    b.fn('height', K + 'Subtract_DoubleDouble', 1050, 400); b.link('eyes', 'Z', 'height', 'A'); b.link('mes', 'Z', 'height', 'B')
    b.fn('vel', '/Script/Engine.Actor:GetVelocity', 550, 750)
    b.fn('gspeed', K + 'VSizeXY', 800, 750); b.link('vel', 'ReturnValue', 'gspeed', 'A')
    b.fn('moving', K + 'MapRangeClamped', 1050, 750, InRangeA=10.0, InRangeB=60.0, OutRangeA=0.0, OutRangeB=1.0)
    b.link('gspeed', 'ReturnValue', 'moving', 'Value')
    b.fn('still', K + 'Less_DoubleDouble', 1050, 1100, B=10.0); b.link('gspeed', 'ReturnValue', 'still', 'A')
    b.fn('dt', '/Script/Engine.GameplayStatics:GetWorldDeltaSeconds', 1050, 950)
    # FPEyeHeightB: the standing eye height (tracks only while still; FInterpTo with speed 0 would snap, so Select holds it)
    b.get('ref', 'FPEyeHeightB', 1350, 600)
    b.fn('fresh1', K + 'NearlyEqual_FloatFloat', 1350, 800, B=0.0, ErrorTolerance=0.001); b.link('ref', 'FPEyeHeightB', 'fresh1', 'A')
    b.fn('start1', K + 'SelectFloat', 1600, 700); b.link('height', 'ReturnValue', 'start1', 'A'); b.link('ref', 'FPEyeHeightB', 'start1', 'B')
    b.link('fresh1', 'ReturnValue', 'start1', 'bPickA')  # first tick: start at the real height
    b.fn('track', K + 'FInterpTo', 1850, 500, InterpSpeed=STAND_SPEED); b.link('start1', 'ReturnValue', 'track', 'Current')
    b.link('height', 'ReturnValue', 'track', 'Target'); b.link('dt', 'ReturnValue', 'track', 'DeltaTime')
    b.fn('hold', K + 'SelectFloat', 2100, 600); b.link('track', 'ReturnValue', 'hold', 'A'); b.link('start1', 'ReturnValue', 'hold', 'B')
    b.link('still', 'ReturnValue', 'hold', 'bPickA')
    b.set('set1', 'FPEyeHeightB', 2350, 0); b.link('hold', 'ReturnValue', 'set1', 'FPEyeHeightB')
    # moving: the standing height plus BOB_K of the real bob, blended in by speed
    b.fn('bob', K + 'Subtract_DoubleDouble', 2350, 500); b.link('height', 'ReturnValue', 'bob', 'A'); b.link('set1', 'Output_Get', 'bob', 'B')
    b.fn('kept', K + 'Multiply_DoubleDouble', 2600, 500, B=BOB_K); b.link('bob', 'ReturnValue', 'kept', 'A')
    b.fn('walkh', K + 'Add_DoubleDouble', 2850, 500); b.link('set1', 'Output_Get', 'walkh', 'A'); b.link('kept', 'ReturnValue', 'walkh', 'B')
    b.fn('want', K + 'Lerp', 3100, 500); b.link('height', 'ReturnValue', 'want', 'A'); b.link('walkh', 'ReturnValue', 'want', 'B')
    b.link('moving', 'ReturnValue', 'want', 'Alpha')
    # FPEyeHeightA: the eased output
    b.get('cur0', 'FPEyeHeightA', 3100, 800)
    b.fn('fresh0', K + 'NearlyEqual_FloatFloat', 3100, 1000, B=0.0, ErrorTolerance=0.001); b.link('cur0', 'FPEyeHeightA', 'fresh0', 'A')
    b.fn('start0', K + 'SelectFloat', 3350, 800); b.link('want', 'ReturnValue', 'start0', 'A'); b.link('cur0', 'FPEyeHeightA', 'start0', 'B')
    b.link('fresh0', 'ReturnValue', 'start0', 'bPickA')
    b.fn('lp0', K + 'FInterpTo', 3600, 500, InterpSpeed=SMOOTH_SPEED); b.link('start0', 'ReturnValue', 'lp0', 'Current')
    b.link('want', 'ReturnValue', 'lp0', 'Target'); b.link('dt', 'ReturnValue', 'lp0', 'DeltaTime')
    b.set('set0', 'FPEyeHeightA', 3850, 0); b.link('lp0', 'ReturnValue', 'set0', 'FPEyeHeightA')
    # the capsule's own height, eased (step-ups onto a rug pop it ~3 cm), never more than STEP_CM from the real one (stairs, teleports)
    b.get('cura', 'FPActorZ', 4100, 900)
    b.fn('fresha', K + 'NearlyEqual_FloatFloat', 4100, 1100, B=0.0, ErrorTolerance=0.001); b.link('cura', 'FPActorZ', 'fresha', 'A')
    b.fn('starta', K + 'SelectFloat', 4350, 1000); b.link('mes', 'Z', 'starta', 'A'); b.link('cura', 'FPActorZ', 'starta', 'B')
    b.link('fresha', 'ReturnValue', 'starta', 'bPickA')
    b.fn('lpa', K + 'FInterpTo', 4600, 900, InterpSpeed=STEP_SPEED); b.link('starta', 'ReturnValue', 'lpa', 'Current')
    b.link('mes', 'Z', 'lpa', 'Target'); b.link('dt', 'ReturnValue', 'lpa', 'DeltaTime')
    b.fn('lo', K + 'Subtract_DoubleDouble', 4600, 1150, B=STEP_CM); b.link('mes', 'Z', 'lo', 'A')
    b.fn('hi', K + 'Add_DoubleDouble', 4600, 1300, B=STEP_CM); b.link('mes', 'Z', 'hi', 'A')
    b.fn('cla', K + 'FClamp', 4850, 1000); b.link('lpa', 'ReturnValue', 'cla', 'Value'); b.link('lo', 'ReturnValue', 'cla', 'Min')
    b.link('hi', 'ReturnValue', 'cla', 'Max')
    b.set('seta', 'FPActorZ', 5100, 0); b.link('cla', 'ReturnValue', 'seta', 'FPActorZ')
    b.fn('z', K + 'Add_DoubleDouble', 5350, 400); b.link('seta', 'Output_Get', 'z', 'A'); b.link('set0', 'Output_Get', 'z', 'B')
    b.fn('steady', K + 'MakeVector', 5600, 300); b.link('eyes', 'X', 'steady', 'X'); b.link('eyes', 'Y', 'steady', 'Y')
    b.link('z', 'ReturnValue', 'steady', 'Z')
    b.get('cam', 'FollowCamera', 5600, 550)
    b.fn('place', '/Script/Engine.SceneComponent:K2_SetWorldLocation', 5900, 0, bSweep='false', bTeleport='true')
    b.link('cam', 'FollowCamera', 'place', 'self'); b.link('steady', 'ReturnValue', 'place', 'NewLocation')
    b.link(e, 'then', 'set1', 'execute'); b.chain('set1', 'set0', 'seta', 'place')
    b.comment('Steady eye: head landmark in x/y; height = standing eye height + 12% of the real bob while moving',
              ['face', 'headxf', 'eyew', 'eyes', 'me', 'mes', 'height', 'vel', 'gspeed', 'moving', 'still', 'dt', 'ref', 'fresh1', 'start1',
               'track', 'hold', 'set1', 'bob', 'kept', 'walkh', 'want', 'cur0', 'fresh0', 'start0', 'lp0', 'set0', 'cura', 'fresha', 'starta', 'lpa', 'lo', 'hi', 'cla', 'seta', 'z', 'steady',
               'cam', 'place'])
    b.run()
    nodes, edges = inspect(P, F)
    if not any(n['title'].replace(' ', '') == FN for n in nodes):
        head = next(n['node_id'] for n in nodes if n['title'].replace(' ', '') == 'UpdateHeadHidden')
        assert not any(x['from_node'] == head and x['from_pin'] == 'then' for x in edges), 'UpdateHeadHidden is no longer the chain end'
        b = Batch(P, F)
        b.fn('steadyeye', PC + ':' + FN, 5500, 2400); b.link(head, 'then', 'steadyeye', 'execute')
        b.run()
    nodes, edges = inspect(P, F)
    hook = next(n['node_id'] for n in nodes if n['title'].replace(' ', '') == FN)
    assert any(x['to_node'] == hook for x in edges), 'SteadyFPEye not on the exec chain'
    print('FP_STEADY_EYE hooked')
finally:
    h.release('anim', lease)
