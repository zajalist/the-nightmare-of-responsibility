"""AAA pass, settings (Hayba, in place): the page rows arrive with an 8 px rise and a 0.24 s ease-out fade when the
screen opens and on every page change (utility screen: no sand). Settings can open over the paused game, where world
timers stop, so it runs on widget Tick like WBP_Pause: a real-time gap over 0.25 s marks a fresh open; ShowPage
restarts the clock too.
  python Tools/Unreal/ui/aaa_settings.py"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

P = '/Game/FoA/UI/Widgets/Menus/WBP_Settings'
KML = '/Script/Engine.KismetMathLibrary'


def c(cmd, **p):
    r = hc.call(cmd, p)
    d = r.get('data') or {}
    print(cmd, p.get('graph_name', ''), r.get('ok'), d.get('applied', ''), d.get('failed_index', ''),
          d.get('error') or r.get('error') or '', json.dumps(d.get('compile') or '')[:160])
    return d


for v in ('SetT', 'LastTick'):
    c('blueprint_add_variable', path=P, variable_name=v, variable_type='real', default_value='0.0',
      category='Settings|Motion', update_existing=True)
eg = hc.call('blueprint_inspect_graph', {'path': P, 'graph_name': 'EventGraph'})['data']
if any(n['title'].startswith('Event Tick') for n in eg['nodes']):
    sys.exit('Tick already built')
# ShowPage restarts the page motion
sp = hc.call('blueprint_inspect_graph', {'path': P, 'graph_name': 'ShowPage'})['data']
entry = next(n['node_id'] for n in sp['nodes'] if n['title'] == 'ShowPage')
nxt = [e for e in sp['edges'] if e['from_node'] == entry and e['from_pin'] == 'then']
ops = [{'op': 'disconnect', 'node_id': entry, 'pin_name': 'then', 'to_node': e['to_node'], 'to_pin': e['to_pin']} for e in nxt]
ops += [{'op': 'add_node', 'ref': 'z', 'node_type': 'variable_set', 'variable_name': 'SetT', 'x': 120, 'y': -380},
        {'op': 'set_pin', 'node_id': 'z', 'pin_name': 'SetT', 'value': '0.0'},
        {'op': 'connect', 'from_node': entry, 'from_pin': 'then', 'to_node': 'z', 'to_pin': 'execute'}]
ops += [{'op': 'connect', 'from_node': 'z', 'from_pin': 'then', 'to_node': e['to_node'], 'to_pin': e['to_pin']} for e in nxt]
ops += [{'op': 'comment', 'title': 'Restart page motion', 'node_ids': ['z'], 'color': [0.30, 0.22, 0.10]}]
c('blueprint_graph_batch', path=P, graph_name='ShowPage', ops=ops)
ops = [
    {'op': 'add_event', 'ref': 'tick', 'event_name': 'Tick', 'x': 0, 'y': 2400},
    {'op': 'add_node', 'ref': 'now', 'node_type': 'call_function', 'function_name': '/Script/Engine.GameplayStatics:GetRealTimeSeconds', 'x': 200, 'y': 2600},
    {'op': 'add_node', 'ref': 'last', 'node_type': 'variable_get', 'variable_name': 'LastTick', 'x': 200, 'y': 2680},
    {'op': 'add_node', 'ref': 'gap', 'node_type': 'call_function', 'function_name': f'{KML}:Subtract_DoubleDouble', 'x': 420, 'y': 2600},
    {'op': 'add_node', 'ref': 'fresh', 'node_type': 'call_function', 'function_name': f'{KML}:Greater_DoubleDouble', 'x': 620, 'y': 2600},
    {'op': 'set_pin', 'node_id': 'fresh', 'pin_name': 'B', 'value': '0.25'},
    {'op': 'add_node', 'ref': 'st', 'node_type': 'variable_get', 'variable_name': 'SetT', 'x': 420, 'y': 2760},
    {'op': 'add_node', 'ref': 'adv', 'node_type': 'call_function', 'function_name': f'{KML}:Add_DoubleDouble', 'x': 620, 'y': 2760},
    {'op': 'add_node', 'ref': 'sel', 'node_type': 'call_function', 'function_name': f'{KML}:SelectFloat', 'x': 820, 'y': 2680},
    {'op': 'set_pin', 'node_id': 'sel', 'pin_name': 'A', 'value': '0.0'},
    {'op': 'add_node', 'ref': 'sett', 'node_type': 'variable_set', 'variable_name': 'SetT', 'x': 1040, 'y': 2400},
    {'op': 'add_node', 'ref': 'setl', 'node_type': 'variable_set', 'variable_name': 'LastTick', 'x': 1280, 'y': 2400},
    {'op': 'add_node', 'ref': 'live', 'node_type': 'call_function', 'function_name': f'{KML}:LessEqual_DoubleDouble', 'x': 1280, 'y': 2600},
    {'op': 'set_pin', 'node_id': 'live', 'pin_name': 'B', 'value': '0.4'},
    {'op': 'add_node', 'ref': 'br', 'node_type': 'branch', 'x': 1520, 'y': 2400},
    {'op': 'connect', 'from_node': 'now', 'from_pin': 'ReturnValue', 'to_node': 'gap', 'to_pin': 'A'},
    {'op': 'connect', 'from_node': 'last', 'from_pin': 'LastTick', 'to_node': 'gap', 'to_pin': 'B'},
    {'op': 'connect', 'from_node': 'gap', 'from_pin': 'ReturnValue', 'to_node': 'fresh', 'to_pin': 'A'},
    {'op': 'connect', 'from_node': 'st', 'from_pin': 'SetT', 'to_node': 'adv', 'to_pin': 'A'},
    {'op': 'connect', 'from_node': 'tick', 'from_pin': 'InDeltaTime', 'to_node': 'adv', 'to_pin': 'B'},
    {'op': 'connect', 'from_node': 'adv', 'from_pin': 'ReturnValue', 'to_node': 'sel', 'to_pin': 'B'},
    {'op': 'connect', 'from_node': 'fresh', 'from_pin': 'ReturnValue', 'to_node': 'sel', 'to_pin': 'bPickA'},
    {'op': 'connect', 'from_node': 'sel', 'from_pin': 'ReturnValue', 'to_node': 'sett', 'to_pin': 'SetT'},
    {'op': 'connect', 'from_node': 'tick', 'from_pin': 'then', 'to_node': 'sett', 'to_pin': 'execute'},
    {'op': 'connect', 'from_node': 'now', 'from_pin': 'ReturnValue', 'to_node': 'setl', 'to_pin': 'LastTick'},
    {'op': 'connect', 'from_node': 'sett', 'from_pin': 'then', 'to_node': 'setl', 'to_pin': 'execute'},
    {'op': 'connect', 'from_node': 'sett', 'from_pin': 'Output_Get', 'to_node': 'live', 'to_pin': 'A'},
    {'op': 'connect', 'from_node': 'live', 'from_pin': 'ReturnValue', 'to_node': 'br', 'to_pin': 'Condition'},
    {'op': 'connect', 'from_node': 'setl', 'from_pin': 'then', 'to_node': 'br', 'to_pin': 'execute'},
    # a = easeOut3(clamp(SetT / 0.24)); Switch_Pages opacity a, rises from 8 px below
    {'op': 'add_node', 'ref': 'dv', 'node_type': 'call_function', 'function_name': f'{KML}:Divide_DoubleDouble', 'x': 1760, 'y': 2600},
    {'op': 'set_pin', 'node_id': 'dv', 'pin_name': 'B', 'value': '0.24'},
    {'op': 'connect', 'from_node': 'sett', 'from_pin': 'Output_Get', 'to_node': 'dv', 'to_pin': 'A'},
    {'op': 'add_node', 'ref': 'cl', 'node_type': 'call_function', 'function_name': f'{KML}:FClamp', 'x': 1930, 'y': 2600},
    {'op': 'set_pin', 'node_id': 'cl', 'pin_name': 'Min', 'value': '0.0'},
    {'op': 'set_pin', 'node_id': 'cl', 'pin_name': 'Max', 'value': '1.0'},
    {'op': 'connect', 'from_node': 'dv', 'from_pin': 'ReturnValue', 'to_node': 'cl', 'to_pin': 'Value'},
    {'op': 'add_node', 'ref': 'ea', 'node_type': 'call_function', 'function_name': f'{KML}:Ease', 'x': 2100, 'y': 2600},
    {'op': 'set_pin', 'node_id': 'ea', 'pin_name': 'A', 'value': '0.0'},
    {'op': 'set_pin', 'node_id': 'ea', 'pin_name': 'B', 'value': '1.0'},
    {'op': 'set_pin', 'node_id': 'ea', 'pin_name': 'EasingFunc', 'value': 'EaseOut'},
    {'op': 'set_pin', 'node_id': 'ea', 'pin_name': 'BlendExp', 'value': '3.0'},
    {'op': 'connect', 'from_node': 'cl', 'from_pin': 'ReturnValue', 'to_node': 'ea', 'to_pin': 'Alpha'},
    {'op': 'add_node', 'ref': 'pg', 'node_type': 'variable_get', 'variable_name': 'Switch_Pages', 'x': 2100, 'y': 2520},
    {'op': 'add_node', 'ref': 'op', 'node_type': 'call_function', 'function_name': '/Script/UMG.Widget:SetRenderOpacity', 'x': 2300, 'y': 2400},
    {'op': 'connect', 'from_node': 'pg', 'from_pin': 'Switch_Pages', 'to_node': 'op', 'to_pin': 'self'},
    {'op': 'connect', 'from_node': 'ea', 'from_pin': 'ReturnValue', 'to_node': 'op', 'to_pin': 'InOpacity'},
    {'op': 'connect', 'from_node': 'br', 'from_pin': 'then', 'to_node': 'op', 'to_pin': 'execute'},
    {'op': 'add_node', 'ref': 'ri', 'node_type': 'call_function', 'function_name': f'{KML}:Lerp', 'x': 2300, 'y': 2680},
    {'op': 'set_pin', 'node_id': 'ri', 'pin_name': 'A', 'value': '8.0'},
    {'op': 'set_pin', 'node_id': 'ri', 'pin_name': 'B', 'value': '0.0'},
    {'op': 'connect', 'from_node': 'ea', 'from_pin': 'ReturnValue', 'to_node': 'ri', 'to_pin': 'Alpha'},
    {'op': 'add_node', 'ref': 'v2', 'node_type': 'call_function', 'function_name': f'{KML}:MakeVector2D', 'x': 2480, 'y': 2680},
    {'op': 'connect', 'from_node': 'ri', 'from_pin': 'ReturnValue', 'to_node': 'v2', 'to_pin': 'Y'},
    {'op': 'add_node', 'ref': 'tr', 'node_type': 'call_function', 'function_name': '/Script/UMG.Widget:SetRenderTranslation', 'x': 2560, 'y': 2400},
    {'op': 'connect', 'from_node': 'pg', 'from_pin': 'Switch_Pages', 'to_node': 'tr', 'to_pin': 'self'},
    {'op': 'connect', 'from_node': 'v2', 'from_pin': 'ReturnValue', 'to_node': 'tr', 'to_pin': 'Translation'},
    {'op': 'connect', 'from_node': 'op', 'from_pin': 'then', 'to_node': 'tr', 'to_pin': 'execute'},
    {'op': 'comment', 'title': 'Settings clock', 'node_ids': ['tick', 'now', 'last', 'gap', 'fresh', 'st', 'adv', 'sel', 'sett', 'setl', 'live', 'br'],
     'color': [0.10, 0.20, 0.35]},
    {'op': 'comment', 'title': 'Rows rise in', 'node_ids': ['dv', 'cl', 'ea', 'pg', 'op', 'ri', 'v2', 'tr'], 'color': [0.30, 0.22, 0.10]},
    {'op': 'fit_comments'},
]
c('blueprint_graph_batch', path=P, graph_name='EventGraph', ops=ops, compile=True, save=True)
