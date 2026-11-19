"""Music and Dialogue volume sliders (main, 2026-11-09), in place. They drive SC_Music and SC_Dialogue through horror's
SCM_Settings exactly like the four existing volumes: SetSoundMixClassOverride adds a class adjuster to the mix at
runtime when the mix lacks it, so SCM_Settings itself needs no edit.
  data   SG_FoASettings MusicVolume, DialogueVolume (1.0); BPFL ApplySettings: two class overrides before the push
  tree   WBP_Settings Page_Audio: Size_Row_Music / Row_Music and Size_Row_Dialogue / Row_Dialogue (64 px rows)
  graph  OnMusicChanged(Value) / OnDialogueChanged(Value): store, then ApplySaved (apply and save), like
         OnInterfaceChanged; LoadSavedRows sets both rows from the save
  bind   (editor Python, Hayba cannot make Create Event nodes yet) Row_X.OnRowValueChanged -> OnXChanged, chained
         before the first ShowPage in the EventGraph
  python Tools/Unreal/ui/aaa_audio_rows.py data|tree|graph       ue_remote ... aaa_audio_rows.py FOA_STEP=bind"""
import os
import sys

ROWS = (('Music', 'MusicVolume', 'SC_Music', 'Music volume'), ('Dialogue', 'DialogueVolume', 'SC_Dialogue', 'Dialogue volume'))
SG = '/Game/FoA/UI/Framework/SG_FoASettings'
SG_C = SG + '.SG_FoASettings_C'
LIB = '/Game/FoA/UI/Framework/BPFL_FoASettings'
P = '/Game/FoA/UI/Widgets/Menus/WBP_Settings'
MIX = '/Game/FoA/Audio/Mix'

if os.environ.get('FOA_STEP') == 'bind':  # editor Python
    SETTINGS = P  # bp_graph defines its own P(x, y); keep the path under another name
    exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
    g = Graph(SETTINGS)
    titles = {n: str(BEL.get_node_title(n)).replace('\n', ' ') for n in g.ed.list_all_nodes()}
    if sum(1 for t in titles.values() if t.startswith('Get Row_Music') or t.startswith('Get Row_Dialogue')) >= 2 and \
            any('OnMusicChanged' in t for t in titles.values()):
        print('binds exist')
    else:
        def feeder(node):
            src = PIN.list_connected_pins(BEL.find_execute_pin(node))
            return src[0] if len(src) == 1 else None
        # the ShowPage right after the bind chain (the tab handlers call ShowPage too: never insert there)
        show = next(n for n, t in titles.items() if (t.startswith('Show Page') or t.startswith('ShowPage')) and feeder(n) is not None
                    and str(BEL.get_node_title(PIN.get_owning_node(feeder(n)))).startswith('Bind Event to'))
        prev_pin = feeder(show)
        PIN.break_pin_links(BEL.find_execute_pin(show))
        x, y = 6000, 0
        last = None
        for name, var, _, _ in ROWS:
            src = g.get(f'Row_{name}', x - 64, 192)
            b, mk = bind_function(g, src, f'Row_{name}', 'OnRowValueChanged', f'On{name}Changed', x, y)
            if last is None:
                PIN.try_create_connection(prev_pin, BEL.find_execute_pin(b))
            else:
                g.link(last, 'then', b, 'execute')
            last = b
            x += 384
        g.link(last, 'then', show, 'execute')
        unreal.EditorAssetLibrary.save_loaded_asset(g.bp, False)
        print('binds added; compile with Hayba')
else:
    pass

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402


def c(cmd, **p):
    r = hc.call(cmd, p)
    d = r.get('data') or {}
    print(cmd, p.get('graph_name') or p.get('variable_name') or p.get('function_name') or '', r.get('ok'),
          d.get('applied', d.get('created', '')), d.get('failed_index', ''), d.get('error') or r.get('error') or '')
    return d


def nodes_edges(bp, g):
    d = hc.call('blueprint_inspect_graph', {'path': bp, 'graph_name': g})['data']
    assert d['page']['nodes']['next_offset'] is None and d['page']['edges']['next_offset'] is None, (bp, g)
    return d['nodes'], d['edges']


def data():
    for _, var, _, _ in ROWS:
        c('blueprint_add_variable', path=SG, variable_name=var, variable_type='real', default_value='1.0',
          category='Audio', update_existing=True)
    c('blueprint_compile', path=SG)
    nodes, edges = nodes_edges(LIB, 'ApplySettings')
    if any(any(MIX + '/SC_Music' in str(p.get('default_value') or '') for p in n['pins']) for n in nodes):
        print('ApplySettings already has Music')
        return
    entry = next(n for n in nodes if n['title'] == 'ApplySettings')
    push = next(n['node_id'] for n in nodes if n['title'].startswith('PushSoundMixModifier'))
    into = [e for e in edges if e['to_node'] == push and e['to_pin'] == 'execute']
    ops = [{'op': 'disconnect', 'node_id': e['from_node'], 'pin_name': e['from_pin'], 'to_node': push, 'to_pin': 'execute'} for e in into]
    prev = None
    for i, (name, var, cls, _) in enumerate(ROWS):
        ops += [{'op': 'add_node', 'ref': f'g{i}', 'node_type': 'variable_get', 'variable_name': var, 'class_path': SG_C, 'x': 1400 + i * 320, 'y': 360},
                {'op': 'connect', 'from_node': entry['node_id'], 'from_pin': 'Settings', 'to_node': f'g{i}', 'to_pin': 'self'},
                {'op': 'add_node', 'ref': f'o{i}', 'node_type': 'call_function', 'function_name': '/Script/Engine.GameplayStatics:SetSoundMixClassOverride', 'x': 1400 + i * 320, 'y': 0},
                {'op': 'set_pin', 'node_id': f'o{i}', 'pin_name': 'InSoundMixModifier', 'value': f'{MIX}/SCM_Settings.SCM_Settings'},
                {'op': 'set_pin', 'node_id': f'o{i}', 'pin_name': 'InSoundClass', 'value': f'{MIX}/{cls}.{cls}'},
                {'op': 'set_pin', 'node_id': f'o{i}', 'pin_name': 'FadeInTime', 'value': '0.1'},
                {'op': 'set_pin', 'node_id': f'o{i}', 'pin_name': 'bApplyToChildren', 'value': 'true'},
                {'op': 'connect', 'from_node': f'g{i}', 'from_pin': var, 'to_node': f'o{i}', 'to_pin': 'Volume'}]
        if prev is None:
            ops += [{'op': 'connect', 'from_node': e['from_node'], 'from_pin': e['from_pin'], 'to_node': f'o{i}', 'to_pin': 'execute'} for e in into]
        else:
            ops += [{'op': 'connect', 'from_node': prev, 'from_pin': 'then', 'to_node': f'o{i}', 'to_pin': 'execute'}]
        prev = f'o{i}'
    ops += [{'op': 'connect', 'from_node': prev, 'from_pin': 'then', 'to_node': push, 'to_pin': 'execute'},
            {'op': 'fit_comments'}]
    c('blueprint_graph_batch', path=LIB, graph_name='ApplySettings', ops=ops, compile=True, save=True)


def tree():
    have = {w['name'] for w in hc.call('ui_query', {'path': P, 'flatten': True})['data']['matches']}
    for name, _, _, label in ROWS:
        if f'Row_{name}' in have:
            continue
        c('ui_build_tree', widget_blueprint_path=P, parent_widget_name='Page_Audio', tree={
            'class': 'SizeBox', 'name': f'Size_Row_{name}',
            'properties': {'HeightOverride': 64, 'bOverride_HeightOverride': True},
            'children': [{'class': '/Game/FoA/UI/Widgets/Common/WBP_SettingRow_Slider.WBP_SettingRow_Slider_C', 'name': f'Row_{name}',
                          'properties': {'Label': label, 'MinValue': 0.0, 'MaxValue': 1.0, 'StepSize': 0.05, 'Value': 1.0,
                                         'DisplayScale': 100.0}}]})
        c('ui_set_variable', widget_blueprint_path=P, widget_name=f'Row_{name}', is_variable=True)
    c('ui_compile_widget', widget_blueprint_path=P)
    c('ui_save_widget', widget_blueprint_path=P)


def graph():
    funcs = hc.call('blueprint_get_info', {'path': P})['data']['functions']
    for name, var, _, _ in ROWS:
        fn = f'On{name}Changed'
        if fn not in funcs:
            c('blueprint_add_function', path=P, function_name=fn, inputs=[{'name': 'Value', 'type': 'real'}])
        nodes, edges = nodes_edges(P, fn)
        if len(nodes) > 1:
            print(fn, 'built')
            continue
        entry = nodes[0]['node_id']
        c('blueprint_graph_batch', path=P, graph_name=fn, ops=[
            {'op': 'add_node', 'ref': 'st', 'node_type': 'variable_get', 'variable_name': 'Settings', 'x': 224, 'y': 192},
            {'op': 'add_node', 'ref': 'set', 'node_type': 'variable_set', 'variable_name': var, 'class_path': SG_C, 'x': 288, 'y': 0},
            {'op': 'connect', 'from_node': 'st', 'from_pin': 'Settings', 'to_node': 'set', 'to_pin': 'self'},
            {'op': 'connect', 'from_node': entry, 'from_pin': 'Value', 'to_node': 'set', 'to_pin': var},
            {'op': 'connect', 'from_node': entry, 'from_pin': 'then', 'to_node': 'set', 'to_pin': 'execute'},
            {'op': 'add_node', 'ref': 'ap', 'node_type': 'call_function', 'function_name': f'{P}.WBP_Settings_C:ApplySaved', 'x': 608, 'y': 0},
            {'op': 'connect', 'from_node': 'set', 'from_pin': 'then', 'to_node': 'ap', 'to_pin': 'execute'},
            {'op': 'comment', 'title': f'Store {name.lower()} volume', 'node_ids': [entry, 'st', 'set', 'ap'], 'color': [0.12, 0.26, 0.16]},
            {'op': 'fit_comments'}])
    nodes, edges = nodes_edges(P, 'LoadSavedRows')
    if not any(n['title'].startswith('Get Row_Music') for n in nodes):
        execs = {n['node_id'] for n in nodes if any(p['name'] == 'then' for p in n['pins'])}
        linked = {e['from_node'] for e in edges if e['from_pin'] == 'then'}
        fed = {e['to_node'] for e in edges if e['to_pin'] == 'execute'}
        tail = [n for n in execs - linked if n in fed]
        assert len(tail) == 1, tail
        st = next(n['node_id'] for n in nodes if n['title'] == 'Get Settings')
        ops, prev = [], tail[0]
        for i, (name, var, _, _) in enumerate(ROWS):
            ops += [{'op': 'add_node', 'ref': f'r{i}', 'node_type': 'variable_get', 'variable_name': f'Row_{name}', 'x': 3000 + i * 320, 'y': 192},
                    {'op': 'add_node', 'ref': f'v{i}', 'node_type': 'variable_get', 'variable_name': var, 'class_path': SG_C, 'x': 3000 + i * 320, 'y': 272},
                    {'op': 'connect', 'from_node': st, 'from_pin': 'Settings', 'to_node': f'v{i}', 'to_pin': 'self'},
                    {'op': 'add_node', 'ref': f's{i}', 'node_type': 'call_function',
                     'function_name': '/Game/FoA/UI/Widgets/Common/WBP_SettingRow_Slider.WBP_SettingRow_Slider_C:SetRowValue', 'x': 3064 + i * 320, 'y': 0},
                    {'op': 'connect', 'from_node': f'r{i}', 'from_pin': f'Row_{name}', 'to_node': f's{i}', 'to_pin': 'self'},
                    {'op': 'connect', 'from_node': f'v{i}', 'from_pin': var, 'to_node': f's{i}', 'to_pin': 'NewValue'},
                    {'op': 'connect', 'from_node': prev, 'from_pin': 'then', 'to_node': f's{i}', 'to_pin': 'execute'}]
            prev = f's{i}'
        c('blueprint_graph_batch', path=P, graph_name='LoadSavedRows', ops=ops)
    c('ui_compile_widget', widget_blueprint_path=P)
    c('ui_save_widget', widget_blueprint_path=P)


if os.environ.get('FOA_STEP') != 'bind':
    {'data': data, 'tree': tree, 'graph': graph}[sys.argv[1]]()
