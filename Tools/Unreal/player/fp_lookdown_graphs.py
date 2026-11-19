"""First person: a steady eye and your own body when you look down (anim lane, Hayba graph batch on UpdateFirstPersonVisibility).
The head camera sits at the eye landmark of the Face head socket, and the pitch was clamped at -65, so the bottom of
the view stopped short of his chest and feet (the floor in front of him only). Now:
- the down-pitch limit is -80;
- as the view pitches below -25 deg the camera slides forward along his facing, up to 14 cm at -70, so it looks over
  the chest (polo, hands, legs, feet) instead of down through the inside of the neck.
The base point is recomputed every tick from the head socket (no accumulation). Its height is steadied: the eye height
above the capsule is split into a slow posture part (EyeHeightSmooth, FInterpTo 2.5: crouch, lean, stand) and the fast
bob, which is clamped to +-2.5 cm (a 3-5 cm walk bob) and to +-0.6 cm under Reduce Motion (MPC_Dream).
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/fp_lookdown_graphs.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
F = 'UpdateFirstPersonVisibility'
K = '/Script/Engine.KismetMathLibrary:'
EYE = '0,-3.530588955620998,11.768322164387774'  # head-space eye landmark (first_person_graphs.py)
MAX_CM, START, SPAN, PITCH_MIN = 14.0, 25.0, 45.0, -80.0
BOB_CM, POSTURE_SPEED = 2.5, 2.5
MPC = '/Game/FoA/PostProcess/MPC_Dream.MPC_Dream'

assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
r = h.call('blueprint_add_variable', dict(path=P, variable_name='EyeHeightSmooth', variable_type='float', default_value='0',
                                          instance_editable=False, update_existing=True, category='Camera'))
assert r.get('ok'), r
nodes, edges = inspect(P, F)
if any(n['title'] == 'Set World Location' for n in nodes):
    sys.exit('look-down already built')
byid = {n['node_id']: n for n in nodes}
look = find(nodes, 'Set World Rotation')
nxt = next(e for e in edges if e['from_node'] == look and e['from_pin'] == 'then')
# the pitch clamp of the free view: the FClamp fed by NormalizeAxis (the yaw clamp is fed by Delta (Rotator))
norm = next(e['to_node'] for e in edges if byid[e['to_node']]['title'] == 'NormalizeAxis' and e['from_pin'] == 'Pitch')
clamp = next(e['to_node'] for e in edges if e['from_node'] == norm and byid[e['to_node']]['title'] == 'Clamp (Float)')
b = Batch(P, F)
b.pin(clamp, 'Min', PITCH_MIN)
b.cut(look, 'then', nxt['to_node'], nxt['to_pin'])
b.get('viewld', 'FPViewRotation', 4600, 700)
b.fn('pld', K + 'BreakRotator', 4850, 700); b.link('viewld', 'FPViewRotation', 'pld', 'InRot')
b.fn('negp', K + 'Multiply_DoubleDouble', 5100, 700, B=-1.0); b.link('pld', 'Pitch', 'negp', 'A')
b.fn('past', K + 'Subtract_DoubleDouble', 5350, 700, B=START); b.link('negp', 'ReturnValue', 'past', 'A')
b.fn('frac', K + 'Divide_DoubleDouble', 5600, 700, B=SPAN); b.link('past', 'ReturnValue', 'frac', 'A')
b.fn('w01', K + 'FClamp', 5850, 700, Min=0.0, Max=1.0); b.link('frac', 'ReturnValue', 'w01', 'Value')
b.fn('slide', K + 'Multiply_DoubleDouble', 6100, 700, B=MAX_CM); b.link('w01', 'ReturnValue', 'slide', 'A')
b.fn('fwd', '/Script/Engine.Actor:GetActorForwardVector', 6100, 900)
b.fn('ahead', K + 'Multiply_VectorFloat', 6350, 800); b.link('fwd', 'ReturnValue', 'ahead', 'A'); b.link('slide', 'ReturnValue', 'ahead', 'B')
b.get('faceld', 'Face', 5600, 1050)
b.fn('headxf', '/Script/Engine.SceneComponent:GetSocketTransform', 5850, 1050, InSocketName='head', TransformSpace='RTS_World')
b.link('faceld', 'Face', 'headxf', 'self')
b.fn('eyew', K + 'TransformLocation', 6100, 1050, Location=EYE); b.link('headxf', 'ReturnValue', 'eyew', 'T')
b.fn('place', K + 'Add_VectorVector', 6600, 900); b.link('eyew', 'ReturnValue', 'place', 'A'); b.link('ahead', 'ReturnValue', 'place', 'B')
# steady eye height: actor z + slow posture height + clamped bob
b.fn('me', '/Script/Engine.Actor:K2_GetActorLocation', 6350, 1300)
b.fn('eyes', K + 'BreakVector', 6600, 1100); b.link('place', 'ReturnValue', 'eyes', 'InVec')
b.fn('mes', K + 'BreakVector', 6600, 1300); b.link('me', 'ReturnValue', 'mes', 'InVec')
b.fn('height', K + 'Subtract_DoubleDouble', 6850, 1200); b.link('eyes', 'Z', 'height', 'A'); b.link('mes', 'Z', 'height', 'B')
b.get('hs', 'EyeHeightSmooth', 6850, 1400)
b.fn('dtl', '/Script/Engine.GameplayStatics:GetWorldDeltaSeconds', 6850, 1550)
b.fn('posture', K + 'FInterpTo', 7100, 1300, InterpSpeed=POSTURE_SPEED)
b.fn('fresh', K + 'NearlyEqual_FloatFloat', 6850, 1700, B=0.0, ErrorTolerance=0.001); b.link('hs', 'EyeHeightSmooth', 'fresh', 'A')
b.fn('start', K + 'SelectFloat', 7100, 1550); b.link('height', 'ReturnValue', 'start', 'A'); b.link('hs', 'EyeHeightSmooth', 'start', 'B')
b.link('fresh', 'ReturnValue', 'start', 'bPickA')  # first tick: start at the real eye height, no rise from the capsule
b.link('start', 'ReturnValue', 'posture', 'Current'); b.link('height', 'ReturnValue', 'posture', 'Target'); b.link('dtl', 'ReturnValue', 'posture', 'DeltaTime')
b.fn('rmld', '/Script/Engine.KismetMaterialLibrary:GetScalarParameterValue', 7100, 600, Collection=MPC, ParameterName='ReduceMotion')
b.set('seths', 'EyeHeightSmooth', 7350, 600); b.link('posture', 'ReturnValue', 'seths', 'EyeHeightSmooth')
b.fn('bob', K + 'Subtract_DoubleDouble', 7350, 1200); b.link('height', 'ReturnValue', 'bob', 'A'); b.link('seths', 'Output_Get', 'bob', 'B')
b.fn('lim', K + 'Lerp', 7350, 1450, A=BOB_CM, B=BOB_CM * 0.24); b.link('rmld', 'ReturnValue', 'lim', 'Alpha')
b.fn('neglim', K + 'Multiply_DoubleDouble', 7600, 1450, B=-1.0); b.link('lim', 'ReturnValue', 'neglim', 'A')
b.fn('bobc', K + 'FClamp', 7600, 1200); b.link('bob', 'ReturnValue', 'bobc', 'Value')
b.link('neglim', 'ReturnValue', 'bobc', 'Min'); b.link('lim', 'ReturnValue', 'bobc', 'Max')
b.fn('z1', K + 'Add_DoubleDouble', 7850, 1200); b.link('mes', 'Z', 'z1', 'A'); b.link('seths', 'Output_Get', 'z1', 'B')
b.fn('z2', K + 'Add_DoubleDouble', 8100, 1200); b.link('z1', 'ReturnValue', 'z2', 'A'); b.link('bobc', 'ReturnValue', 'z2', 'B')
b.fn('steady', K + 'MakeVector', 8350, 1100); b.link('eyes', 'X', 'steady', 'X'); b.link('eyes', 'Y', 'steady', 'Y'); b.link('z2', 'ReturnValue', 'steady', 'Z')
b.get('camld', 'FollowCamera', 8350, 1350)
b.fn('setcam', '/Script/Engine.SceneComponent:K2_SetWorldLocation', 8600, 600, bSweep='false', bTeleport='true')
b.link('camld', 'FollowCamera', 'setcam', 'self'); b.link('steady', 'ReturnValue', 'setcam', 'NewLocation')
b.link(look, 'then', 'rmld', 'execute'); b.chain('rmld', 'seths', 'setcam'); b.link('setcam', 'then', nxt['to_node'], nxt['to_pin'])
b.comment('Steady eye, look down over the chest', ['viewld', 'pld', 'negp', 'past', 'frac', 'w01', 'slide', 'fwd', 'ahead', 'faceld',
                                                   'headxf', 'eyew', 'place', 'me', 'eyes', 'mes', 'height', 'hs', 'fresh', 'start', 'dtl', 'posture',
                                                   'rmld', 'seths', 'bob', 'lim', 'neglim', 'bobc', 'z1', 'z2', 'steady', 'camld', 'setcam'])
b.run()

# the camera manager's own limit (AttachFirstPersonCamera sets ViewPitchMin -65) must allow the same -80
nodes, edges = inspect(P, 'AttachFirstPersonCamera')
setmin = next(n['node_id'] for n in nodes if n['title'].replace(' ', '') == 'SetViewPitchMin')
b = Batch(P, 'AttachFirstPersonCamera')
b.pin(setmin, 'ViewPitchMin', PITCH_MIN)
b.run()
