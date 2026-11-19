"""Phone hold: put the left wrist where the PALM meets the phone's Palm_L socket (world's mesh), instead of a guessed
offset from the screen. wrist = Palm_L(world) - HandRotation * (1.935, -6.298, 0.318): the measured wrist-to-palm offset
in hand_l space that environment contact already uses. Rewires every consumer of the old 'wrist' node in
BP_FoAPlayer.UpdatePhoneHold (IK target, elbow pole, forearm shaft).
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/phone_palm_wrist.py"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
F = 'UpdatePhoneHold'
K = '/Script/Engine.KismetMathLibrary:'
assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
nodes, edges = inspect(P, F)
byid = {n['node_id']: n for n in nodes}
if not any(n['title'] == 'Get Socket Location' and any(p.get('default_value') == 'Palm_L' for p in n.get('pins', [])) for n in nodes):
    hand = next(e['from_node'] for e in edges if byid[e['to_node']]['title'] == 'Set EnvironmentHandRotation' and e['to_pin'] == 'EnvironmentHandRotation')
    old = next(e['from_node'] for e in edges if byid[e['to_node']]['title'] == 'Set EnvironmentHandTarget' and e['to_pin'] == 'EnvironmentHandTarget')
    smc = next(n['node_id'] for n in nodes if n['title'].startswith('Cast To StaticMeshComponent'))
    users = [e for e in edges if e['from_node'] == old and e['from_pin'] == 'ReturnValue']
    b = Batch(P, F)
    b.fn('palm', '/Script/Engine.SceneComponent:GetSocketLocation', 5100, 1800, InSocketName='Palm_L')
    b.link(smc, 'AsStatic Mesh Component', 'palm', 'self')
    b.fn('reach', K + 'GreaterGreater_VectorRotator', 5100, 2000, A='1.935470523,-6.297890748,.318129632'); b.link(hand, 'ReturnValue', 'reach', 'B')
    b.fn('wrist2', K + 'Subtract_VectorVector', 5400, 1900); b.link('palm', 'ReturnValue', 'wrist2', 'A'); b.link('reach', 'ReturnValue', 'wrist2', 'B')
    for e in users:
        b.cut(old, 'ReturnValue', e['to_node'], e['to_pin']); b.link('wrist2', 'ReturnValue', e['to_node'], e['to_pin'])
    b.ops.append(dict(op='remove', node_ids=[old]))
    b.comment('Palm on the phone back', ['palm', 'reach', 'wrist2'])
    b.run()
print('PALM_WRIST_DONE (set PhoneHandRot with set_phone_defaults.py)')
