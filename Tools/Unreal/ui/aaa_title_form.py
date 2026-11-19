"""AAA pass, title (Hayba, in place): the logotype forms from sand instead of fading.
FormStep ramps Ret_Title's effect-material Reveal 0 -> 1 over 1.5 s (60 Hz timer, ease-out ^4, stops itself).
Construct zeroes Reveal and arms FormStep; the widget fade shortens to 0.55 s from 0.1 s, the prompt arrives at 1.4 s.
  python Tools/Unreal/ui/aaa_title_form.py form|construct"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

T = '/Game/FoA/UI/Widgets/Menus/WBP_Title'
KML = '/Script/Engine.KismetMathLibrary'
KSL = '/Script/Engine.KismetSystemLibrary'


def c(cmd, **p):
    r = hc.call(cmd, p)
    d = r.get('data') or {}
    print(cmd, r.get('ok'), d.get('applied'), d.get('total'), d.get('failed_index'), d.get('error') or r.get('error'),
          json.dumps(d.get('compile'))[:200] if d.get('compile') else '', json.dumps(d.get('refs'))[:300])
    return d


def node(graph, title):
    d = hc.call('blueprint_inspect_graph', {'path': T, 'graph_name': graph}).get('data') or {}
    hits = [n['node_id'] for n in d.get('nodes', []) if n['title'].replace('\n', ' ').startswith(title)]
    assert hits, (graph, title)
    return hits


def form():
    c('blueprint_add_variable', path=T, variable_name='FormT', variable_type='real', default_value='0.0',
      category='Title|State', update_existing=True)
    entry = node('FormStep', 'FormStep')[0]
    gem = node('FormStep', 'GetEffectMaterial')[0]
    ops = [
        {'op': 'add_node', 'ref': 'get', 'node_type': 'variable_get', 'variable_name': 'FormT', 'x': 160, 'y': 160},
        {'op': 'add_node', 'ref': 'add', 'node_type': 'call_function', 'function_name': f'{KML}:Add_DoubleDouble', 'x': 352, 'y': 160},
        {'op': 'set_pin', 'node_id': 'add', 'pin_name': 'B', 'value': '0.0111'},
        {'op': 'add_node', 'ref': 'clamp', 'node_type': 'call_function', 'function_name': f'{KML}:FClamp', 'x': 544, 'y': 160},
        {'op': 'set_pin', 'node_id': 'clamp', 'pin_name': 'Min', 'value': '0.0'},
        {'op': 'set_pin', 'node_id': 'clamp', 'pin_name': 'Max', 'value': '1.0'},
        {'op': 'add_node', 'ref': 'set', 'node_type': 'variable_set', 'variable_name': 'FormT', 'x': 768, 'y': 0},
        {'op': 'add_node', 'ref': 'ease', 'node_type': 'call_function', 'function_name': f'{KML}:Ease', 'x': 1024, 'y': 200},
        {'op': 'set_pin', 'node_id': 'ease', 'pin_name': 'A', 'value': '0.0'},
        {'op': 'set_pin', 'node_id': 'ease', 'pin_name': 'B', 'value': '1.0'},
        {'op': 'set_pin', 'node_id': 'ease', 'pin_name': 'EasingFunc', 'value': 'EaseOut'},
        {'op': 'set_pin', 'node_id': 'ease', 'pin_name': 'BlendExp', 'value': '4.0'},
        {'op': 'add_node', 'ref': 'ret', 'node_type': 'variable_get', 'variable_name': 'Ret_Title', 'x': 480, 'y': 320},
        {'op': 'move', 'node_id': gem, 'x': 704, 'y': 320},
        {'op': 'add_node', 'ref': 'ssp', 'node_type': 'call_function',
         'function_name': '/Script/Engine.MaterialInstanceDynamic:SetScalarParameterValue', 'x': 1280, 'y': 0},
        {'op': 'set_pin', 'node_id': 'ssp', 'pin_name': 'ParameterName', 'value': 'Reveal'},
        {'op': 'add_node', 'ref': 'ge', 'node_type': 'call_function', 'function_name': f'{KML}:GreaterEqual_DoubleDouble', 'x': 1536, 'y': 200},
        {'op': 'set_pin', 'node_id': 'ge', 'pin_name': 'B', 'value': '1.0'},
        {'op': 'add_node', 'ref': 'br', 'node_type': 'branch', 'x': 1600, 'y': 0},
        {'op': 'add_node', 'ref': 'stop', 'node_type': 'call_function', 'function_name': f'{KSL}:K2_ClearTimer', 'x': 1856, 'y': 0},
        {'op': 'set_pin', 'node_id': 'stop', 'pin_name': 'FunctionName', 'value': 'FormStep'},
        {'op': 'connect', 'from_node': 'get', 'from_pin': 'FormT', 'to_node': 'add', 'to_pin': 'A'},
        {'op': 'connect', 'from_node': 'add', 'from_pin': 'ReturnValue', 'to_node': 'clamp', 'to_pin': 'Value'},
        {'op': 'connect', 'from_node': 'clamp', 'from_pin': 'ReturnValue', 'to_node': 'set', 'to_pin': 'FormT'},
        {'op': 'connect', 'from_node': entry, 'from_pin': 'then', 'to_node': 'set', 'to_pin': 'execute'},
        {'op': 'connect', 'from_node': 'set', 'from_pin': 'Output_Get', 'to_node': 'ease', 'to_pin': 'Alpha'},
        {'op': 'connect', 'from_node': 'ret', 'from_pin': 'Ret_Title', 'to_node': gem, 'to_pin': 'self'},
        {'op': 'connect', 'from_node': gem, 'from_pin': 'ReturnValue', 'to_node': 'ssp', 'to_pin': 'self'},
        {'op': 'connect', 'from_node': 'ease', 'from_pin': 'ReturnValue', 'to_node': 'ssp', 'to_pin': 'Value'},
        {'op': 'connect', 'from_node': 'set', 'from_pin': 'then', 'to_node': 'ssp', 'to_pin': 'execute'},
        {'op': 'connect', 'from_node': 'set', 'from_pin': 'Output_Get', 'to_node': 'ge', 'to_pin': 'A'},
        {'op': 'connect', 'from_node': 'ge', 'from_pin': 'ReturnValue', 'to_node': 'br', 'to_pin': 'Condition'},
        {'op': 'connect', 'from_node': 'ssp', 'from_pin': 'then', 'to_node': 'br', 'to_pin': 'execute'},
        {'op': 'connect', 'from_node': 'br', 'from_pin': 'True', 'to_node': 'stop', 'to_pin': 'execute'},
        {'op': 'comment', 'title': 'Logotype forms from sand',
         'node_ids': [entry, 'get', 'add', 'clamp', 'set', 'ease', 'ret', gem, 'ssp', 'ge', 'br', 'stop'],
         'color': [0.30, 0.22, 0.10]},
        {'op': 'fit_comments'},
    ]
    c('blueprint_graph_batch', path=T, graph_name='FormStep', ops=ops, compile=True, save=True)


def construct():
    hide_halo = node('EventGraph', 'SetRenderOpacity')  # three hides; the halo hide is the last before the timers
    fade_t, ready_t, prompt_t = node('EventGraph', 'Set Timer by Function Name')
    d = hc.call('blueprint_inspect_graph', {'path': T, 'graph_name': 'EventGraph'})['data']
    halo = next(e['from_node'] for e in d['edges'] if e['to_node'] == fade_t and e['to_pin'] == 'execute')
    assert halo in hide_halo
    timers = {n['node_id']: n for n in d['nodes'] if n['node_id'] in (fade_t, ready_t, prompt_t)}
    name = {k: next(p.get('default_value') for p in v['pins'] if p['name'] == 'FunctionName') for k, v in timers.items()}
    fade_t = next(k for k, v in name.items() if v == 'FadeInStep')
    prompt_t = next(k for k, v in name.items() if v == 'PromptStep')
    ops = [
        {'op': 'disconnect', 'node_id': halo, 'pin_name': 'then', 'to_node': fade_t, 'to_pin': 'execute'},
        {'op': 'add_node', 'ref': 'ret', 'node_type': 'variable_get', 'variable_name': 'Ret_Title', 'x': 1600, 'y': 352},
        {'op': 'add_node', 'ref': 'gem', 'node_type': 'call_function', 'function_name': '/Script/UMG.RetainerBox:GetEffectMaterial', 'x': 1600, 'y': 432},
        {'op': 'add_node', 'ref': 'zero', 'node_type': 'call_function',
         'function_name': '/Script/Engine.MaterialInstanceDynamic:SetScalarParameterValue', 'x': 1600, 'y': 192},
        {'op': 'set_pin', 'node_id': 'zero', 'pin_name': 'ParameterName', 'value': 'Reveal'},
        {'op': 'set_pin', 'node_id': 'zero', 'pin_name': 'Value', 'value': '0.0'},
        {'op': 'add_node', 'ref': 'arm', 'node_type': 'call_function', 'function_name': f'{KSL}:K2_SetTimer', 'x': 1888, 'y': 192},
        {'op': 'set_pin', 'node_id': 'arm', 'pin_name': 'FunctionName', 'value': 'FormStep'},
        {'op': 'set_pin', 'node_id': 'arm', 'pin_name': 'Time', 'value': '0.0167'},
        {'op': 'set_pin', 'node_id': 'arm', 'pin_name': 'bLooping', 'value': 'true'},
        {'op': 'set_pin', 'node_id': 'arm', 'pin_name': 'InitialStartDelay', 'value': '0.15'},
        {'op': 'connect', 'from_node': 'ret', 'from_pin': 'Ret_Title', 'to_node': 'gem', 'to_pin': 'self'},
        {'op': 'connect', 'from_node': 'gem', 'from_pin': 'ReturnValue', 'to_node': 'zero', 'to_pin': 'self'},
        {'op': 'connect', 'from_node': halo, 'from_pin': 'then', 'to_node': 'zero', 'to_pin': 'execute'},
        {'op': 'connect', 'from_node': 'zero', 'from_pin': 'then', 'to_node': 'arm', 'to_pin': 'execute'},
        {'op': 'connect', 'from_node': 'arm', 'from_pin': 'then', 'to_node': fade_t, 'to_pin': 'execute'},
        {'op': 'set_pin', 'node_id': fade_t, 'pin_name': 'InitialStartDelay', 'value': '0.1'},
        {'op': 'set_pin', 'node_id': prompt_t, 'pin_name': 'InitialStartDelay', 'value': '1.4'},
        {'op': 'comment', 'title': 'Arm the sand form', 'node_ids': ['ret', 'gem', 'zero', 'arm'], 'color': [0.30, 0.22, 0.10]},
    ]
    c('blueprint_graph_batch', path=T, graph_name='EventGraph', ops=ops)
    step = node('FadeInStep', 'Make Literal Float')
    lit = [n for n in step]
    d = hc.call('blueprint_inspect_graph', {'path': T, 'graph_name': 'FadeInStep'})['data']
    s = next(n['node_id'] for n in d['nodes'] if n['node_id'] in lit and
             any(p.get('default_value') == '0.0185' for p in n['pins']))
    c('blueprint_graph_batch', path=T, graph_name='FadeInStep',
      ops=[{'op': 'set_pin', 'node_id': s, 'pin_name': 'Value', 'value': '0.06'}])
    d = hc.call('blueprint_inspect_graph', {'path': T, 'graph_name': 'PromptStep'})['data']
    s = next(n['node_id'] for n in d['nodes'] if any(p.get('default_value') == '0.042' for p in n['pins']))
    c('blueprint_graph_batch', path=T, graph_name='PromptStep',
      ops=[{'op': 'set_pin', 'node_id': s, 'pin_name': 'Value', 'value': '0.066'}], compile=True, save=True)


{'form': form, 'construct': construct}[sys.argv[1]]()
