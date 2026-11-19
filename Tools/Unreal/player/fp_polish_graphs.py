"""First-person camera weight (anim lane, Hayba graph batch on BP_FoAPlayer.UpdateFirstPersonVisibility).
Turn lean: the head camera rolls into a turn by up to 1.2 deg at 150 deg/s of yaw, eased in and out (FInterpTo 5), so
a fast mouse turn has weight without input lag (pitch and yaw stay exactly the control rotation). Scaled by
(1 - MPC_Dream.ReduceMotion): Reduce Motion turns it off. The control rotation never gets the roll.
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/fp_polish_graphs.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
F = 'UpdateFirstPersonVisibility'
K = '/Script/Engine.KismetMathLibrary:'
MPC = '/Game/FoA/PostProcess/MPC_Dream.MPC_Dream'
GAIN, LIMIT, SPEED = 0.008, 1.2, 5.0

assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
for v in ('PrevViewYaw', 'CamRoll'):
    r = h.call('blueprint_add_variable', dict(path=P, variable_name=v, variable_type='float', default_value='0',
                                              instance_editable=False, update_existing=True, category='Camera'))
    assert r.get('ok'), r
nodes, edges = inspect(P, F)
if any(n['title'] == 'Set CamRoll' for n in nodes):
    sys.exit('turn lean already built')
setview = find(nodes, 'Set FPViewRotation')
branch = find(nodes, 'Branch')  # the first-person branch right before SetControlRotation
look = find(nodes, 'Set World Rotation')
into = next(e for e in edges if e['to_node'] == branch and e['to_pin'] == 'execute')  # whatever runs right before it
feed = next(e for e in edges if e['to_node'] == look and e['to_pin'] == 'NewRotation')
b = Batch(P, F)
b.cut(into['from_node'], into['from_pin'], branch, 'execute')
b.cut(feed['from_node'], feed['from_pin'], look, 'NewRotation')
b.get('viewnow', 'FPViewRotation', 1450, 2100)  # the variable, so a later view edit (interaction look) is seen
b.fn('view', K + 'BreakRotator', 1700, 2100); b.link('viewnow', 'FPViewRotation', 'view', 'InRot')
b.get('prev', 'PrevViewYaw', 1700, 2300)
b.fn('dyaw', K + 'Subtract_DoubleDouble', 1950, 2100); b.link('view', 'Yaw', 'dyaw', 'A'); b.link('prev', 'PrevViewYaw', 'dyaw', 'B')
b.fn('wrap', K + 'NormalizeAxis', 2200, 2100); b.link('dyaw', 'ReturnValue', 'wrap', 'Angle')
b.fn('dt', '/Script/Engine.GameplayStatics:GetWorldDeltaSeconds', 1950, 2400)
b.fn('safe', K + 'FMax', 2200, 2400, B=0.001); b.link('dt', 'ReturnValue', 'safe', 'A')
b.fn('rate', K + 'Divide_DoubleDouble', 2450, 2100); b.link('wrap', 'ReturnValue', 'rate', 'A'); b.link('safe', 'ReturnValue', 'rate', 'B')
b.fn('gain', K + 'Multiply_DoubleDouble', 2700, 2100, B=GAIN); b.link('rate', 'ReturnValue', 'gain', 'A')
b.fn('lim', K + 'FClamp', 2950, 2100, Min=-LIMIT, Max=LIMIT); b.link('gain', 'ReturnValue', 'lim', 'Value')
b.fn('rm', '/Script/Engine.KismetMaterialLibrary:GetScalarParameterValue', 2700, 2400, Collection=MPC, ParameterName='ReduceMotion')
b.fn('keep', K + 'Subtract_DoubleDouble', 2950, 2400, A=1.0); b.link('rm', 'ReturnValue', 'keep', 'B')
b.fn('target', K + 'Multiply_DoubleDouble', 3200, 2100); b.link('lim', 'ReturnValue', 'target', 'A'); b.link('keep', 'ReturnValue', 'target', 'B')
b.get('roll', 'CamRoll', 3200, 2400)
b.fn('ease', K + 'FInterpTo', 3450, 2100, InterpSpeed=SPEED)
b.link('roll', 'CamRoll', 'ease', 'Current'); b.link('target', 'ReturnValue', 'ease', 'Target'); b.link('safe', 'ReturnValue', 'ease', 'DeltaTime')
b.set('setroll', 'CamRoll', 3700, 1900); b.link('ease', 'ReturnValue', 'setroll', 'CamRoll')
b.set('setprev', 'PrevViewYaw', 3950, 1900); b.link('view', 'Yaw', 'setprev', 'PrevViewYaw')
b.link(into['from_node'], into['from_pin'], 'setroll', 'execute'); b.chain('setroll', 'setprev'); b.link('setprev', 'then', branch, 'execute')
b.fn('lean', K + 'MakeRotator', 4200, 2100)
b.link('view', 'Pitch', 'lean', 'Pitch'); b.link('view', 'Yaw', 'lean', 'Yaw'); b.link('setroll', 'Output_Get', 'lean', 'Roll')
b.link('lean', 'ReturnValue', look, 'NewRotation')
b.comment('Turn lean', ['viewnow', 'view', 'prev', 'dyaw', 'wrap', 'dt', 'safe', 'rate', 'gain', 'lim', 'rm', 'keep', 'target', 'roll',
                        'ease', 'setroll', 'setprev', 'lean'])
b.run()
