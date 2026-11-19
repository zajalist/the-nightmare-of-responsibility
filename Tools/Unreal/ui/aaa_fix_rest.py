"""AAA pass, main's review of rec_fast_r1 f0184 (Hayba, in place): the title and menu must be clean at rest.
  mats   MF_UI_TimeEcho never samples past the retainer's top (the wrapped ghost); 5 s breathe period;
         title instance echo 0 at rest; M_PP_MenuV31 Look.y (downward bright streak) 0
  fe     BP_FoAFrontEnd: TitleGlitch no longer fires (datamosh only at time breaks); the dream menu preset (its own
         6 s MenuGlitch and stronger echoes) is never enabled from the front end
  title  FormStep drives the title echo only while the letters gather: Calm.B = 0.55 x (1 - reveal)
  build  Txt_Build dims to a near-black grey
  python Tools/Unreal/ui/aaa_fix_rest.py mats|fe|title|build"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
TITLE = '/Game/FoA/UI/Widgets/Menus/WBP_Title'
KML = '/Script/Engine.KismetMathLibrary'


def c(cmd, **p):
    r = hc.call(cmd, p)
    d = r.get('data') or {}
    print(cmd, r.get('ok'), d.get('applied', d.get('succeeded')), d.get('error') or r.get('error') or '',
          json.dumps(d.get('compile') or d.get('stats') or '')[:200])
    return d


def nodes(bp, graph):
    out, off = [], 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': bp, 'graph_name': graph, 'offset': off})['data']
        out += d['nodes']
        off = d['page']['nodes']['next_offset']
    return out


def edges(bp, graph):
    out, off = [], 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': bp, 'graph_name': graph, 'edge_offset': off})['data']
        out += d['edges']
        off = d['page']['edges']['next_offset']
    return out


def mats():
    mf = '/Game/FoA/UI/Materials/Functions/MF_UI_TimeEcho'
    c('material_set_node', function_path=mf, node_id='MaterialExpressionCustom_0',
      properties={'Code': open('P:/FoA/Tools/Unreal/ui/hlsl/time_echo_v4.hlsl').read()})
    c('material_validate', function_path=mf)
    c('material_compile', function_path=mf)
    c('material_set_param', instance_path='/Game/FoA/UI/Materials/MI_UI_SandText_Title', param_name='Calm',
      value=[0.0, 0.0, 0.0, 0.0])
    pp = '/Game/FoA/UI/Menu/M_PP_MenuV31'
    c('material_set_node', material_path=pp, node_id='MaterialExpressionVectorParameter_8',
      properties={'DefaultValue': {'R': 3.0, 'G': 0.0, 'B': 1.0, 'A': 1.0}})
    c('material_validate', material_path=pp)
    c('material_compile', material_path=pp)


def fe():
    g = nodes(FE, 'TitleGlitch')
    entry = next(n['node_id'] for n in g if n['title'] == 'TitleGlitch')
    out = [e for e in edges(FE, 'TitleGlitch') if e['from_node'] == entry and e['from_pin'] == 'then']
    ops = [{'op': 'disconnect', 'node_id': entry, 'pin_name': 'then', 'to_node': e['to_node'], 'to_pin': e['to_pin']} for e in out]
    if ops:
        ops.append({'op': 'comment', 'title': 'Off: datamosh only at time breaks', 'node_ids': [entry], 'color': [0.18, 0.18, 0.18]})
        c('blueprint_graph_batch', path=FE, graph_name='TitleGlitch', ops=ops)
    g = nodes(FE, 'SetDreamMenuMode')
    entry = next(n['node_id'] for n in g if n['title'] == 'SetDreamMenuMode')
    menu = next(n['node_id'] for n in g if n['title'].startswith('Set Menu Mode') or n['title'].startswith('SetMenuMode'))
    link = [e for e in edges(FE, 'SetDreamMenuMode') if e['from_node'] == entry and e['to_node'] == menu and e['to_pin'] == 'Enabled']
    ops = [{'op': 'disconnect', 'node_id': entry, 'pin_name': e['from_pin'], 'to_node': menu, 'to_pin': 'Enabled'} for e in link]
    ops.append({'op': 'set_pin', 'node_id': menu, 'pin_name': 'Enabled', 'value': 'false'})
    c('blueprint_graph_batch', path=FE, graph_name='SetDreamMenuMode', ops=ops, compile=True, save=True)


def title():
    g = nodes(TITLE, 'FormStep')
    if any(n['title'].startswith('SetVectorParameterValue') for n in g):
        print('title echo already driven')
        return
    ssp = next(n['node_id'] for n in g if n['title'].startswith('SetScalarParameterValue'))
    gem = next(n['node_id'] for n in g if n['title'].startswith('GetEffectMaterial'))
    ease = next(n['node_id'] for n in g if n['title'].startswith('Ease'))
    br = next(n['node_id'] for n in g if n['title'] == 'Branch')
    ops = [
        {'op': 'disconnect', 'node_id': ssp, 'pin_name': 'then', 'to_node': br, 'to_pin': 'execute'},
        {'op': 'add_node', 'ref': 'inv', 'node_type': 'call_function', 'function_name': f'{KML}:Lerp', 'x': 1280, 'y': 520},
        {'op': 'set_pin', 'node_id': 'inv', 'pin_name': 'A', 'value': '0.55'},
        {'op': 'set_pin', 'node_id': 'inv', 'pin_name': 'B', 'value': '0.0'},
        {'op': 'connect', 'from_node': ease, 'from_pin': 'ReturnValue', 'to_node': 'inv', 'to_pin': 'Alpha'},
        {'op': 'add_node', 'ref': 'col', 'node_type': 'call_function', 'function_name': f'{KML}:MakeColor', 'x': 1480, 'y': 520},
        {'op': 'set_pin', 'node_id': 'col', 'pin_name': 'R', 'value': '0.0'},
        {'op': 'set_pin', 'node_id': 'col', 'pin_name': 'G', 'value': '0.0'},
        {'op': 'set_pin', 'node_id': 'col', 'pin_name': 'A', 'value': '0.0'},
        {'op': 'connect', 'from_node': 'inv', 'from_pin': 'ReturnValue', 'to_node': 'col', 'to_pin': 'B'},
        {'op': 'add_node', 'ref': 'svp', 'node_type': 'call_function',
         'function_name': '/Script/Engine.MaterialInstanceDynamic:SetVectorParameterValue', 'x': 1480, 'y': 0},
        {'op': 'set_pin', 'node_id': 'svp', 'pin_name': 'ParameterName', 'value': 'Calm'},
        {'op': 'connect', 'from_node': gem, 'from_pin': 'ReturnValue', 'to_node': 'svp', 'to_pin': 'self'},
        {'op': 'connect', 'from_node': 'col', 'from_pin': 'ReturnValue', 'to_node': 'svp', 'to_pin': 'Value'},
        {'op': 'connect', 'from_node': ssp, 'from_pin': 'then', 'to_node': 'svp', 'to_pin': 'execute'},
        {'op': 'connect', 'from_node': 'svp', 'from_pin': 'then', 'to_node': br, 'to_pin': 'execute'},
        {'op': 'fit_comments'},
    ]
    c('blueprint_graph_batch', path=TITLE, graph_name='FormStep', ops=ops, compile=True, save=True)


def build():
    print(hc.call('ui_set_widget_properties', {'widget_blueprint_path': '/Game/FoA/UI/Widgets/Menus/WBP_MainMenu',
                                                'widget_name': 'Txt_Build',
                                                'properties': {'ColorAndOpacity': {'SpecifiedColor': [0.05, 0.05, 0.05, 1.0]}}}))
    c('ui_compile_widget', widget_blueprint_path='/Game/FoA/UI/Widgets/Menus/WBP_MainMenu')
    c('ui_save_widget', widget_blueprint_path='/Game/FoA/UI/Widgets/Menus/WBP_MainMenu')


{'mats': mats, 'fe': fe, 'title': title, 'build': build}[sys.argv[1]]()
