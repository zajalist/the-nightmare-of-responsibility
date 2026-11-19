"""A believable, unbranded phone OS on WBP_Phone (540 x 1201 design px on a 6.68 cm screen, read at 30-35 cm), in place:
  tree   status bar (time, signal bars, battery: rounded boxes, no textures), a lock screen over the apps (big clock,
         the day count, two notification banners) that slides away, Reminders-style rows (a circle per task), a Messages
         thread (contact header over a rounded bubble), the app tabs as a bottom bar
  style  type for phone scale (body 28-30 px, large titles 48-52 px, lock clock 150 px), neutral greys only
  graph  OpenMessage: body-only texts (script.md section 3) with the contact in Txt_ThreadName; Tick: the lock shows for
         1 s whenever the phone appears (a real-time gap over 0.5 s since the last tick) and slides up over 0.35 s
  python Tools/Unreal/ui/aaa_phone.py tree|style|graph"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

P = '/Game/FoA/UI/Game/WBP_Phone'
UIF = '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
DISP = '/Game/FoA/UI/Fonts/F_FoA_Display.F_FoA_Display'
KML = '/Script/Engine.KismetMathLibrary'
INK, SUB, DIM = 0.86, 0.42, 0.22      # linear greys: primary text, secondary text, fills


def c(cmd, **p):
    r = hc.call(cmd, p)
    d = r.get('data') or {}
    bad = d.get('failed_properties') or d.get('error') or r.get('error') or ''
    print(cmd, p.get('widget_name') or p.get('graph_name') or p.get('operation') or '', r.get('ok'),
          d.get('succeeded', d.get('applied', d.get('created', ''))), bad if bad else '')
    return d


def names():
    return {w['name'] for w in hc.call('ui_query', {'path': P, 'flatten': True})['data']['matches']}


def col(v, a=1.0):
    return {'SpecifiedColor': {'R': v, 'G': v, 'B': v, 'A': a}, 'ColorUseRule': 'UseColor_Specified'}


def rbox(fill, a=1.0, radius=8, outline=0.0, outline_v=0.6):
    return {'DrawAs': 'RoundedBox', 'TintColor': col(fill, a),
            'OutlineSettings': {'Width': outline, 'Color': col(outline_v), 'RoundingType': 'FixedRadius',
                                'CornerRadii': {'X': radius, 'Y': radius, 'Z': radius, 'W': radius}}}


def txt(value, size, face='Medium', v=INK, a=1.0, font=UIF, wrap=False, just='Left'):
    return {'Text': value, 'Font': {'FontObject': font, 'TypefaceFontName': face, 'Size': size},
            'ColorAndOpacity': col(v, a), 'AutoWrapText': wrap, 'Justification': just}


def move(name, parent=None, index=None):
    if parent:
        c('ui_mutate_tree', operation='reparent', widget_blueprint_path=P, widget_name=name, new_parent_name=parent)
    if index is not None:
        c('ui_mutate_tree', operation='move', widget_blueprint_path=P, widget_name=name, index=index)


def build(parent, tree):
    c('ui_build_tree', widget_blueprint_path=P, parent_widget_name=parent, tree=tree)


def tree():
    have = names()
    if 'HB_Status' not in have:
        bars = [{'class': 'SizeBox', 'name': f'Sz_Sig{i}', 'properties': {'WidthOverride': 5, 'HeightOverride': 6 + 3 * i},
                 'slot_props': {'vertical_alignment': 'VAlign_Bottom', 'padding': '(Left=0,Top=0,Right=3,Bottom=0)'},
                 'children': [{'class': 'Image', 'name': f'Img_Sig{i}', 'properties': {'Brush': rbox(INK, 1.0 if i < 3 else 0.35, 1.5)}}]}
                for i in range(4)]
        build('VB_Phone', {'class': 'HorizontalBox', 'name': 'HB_Status', 'slot_props': {'padding': '(Left=14,Top=6,Right=10,Bottom=10)'},
                           'children': [
                               {'class': 'TextBlock', 'name': 'Txt_StatusTime', 'properties': txt('6:40', 24, 'SemiBold'),
                                'slot_props': {'vertical_alignment': 'VAlign_Center'}},
                               {'class': 'Spacer', 'name': 'Spc_Status', 'slot_props': {'size': {'SizeRule': 'Fill', 'Value': 1.0}}},
                               {'class': 'HorizontalBox', 'name': 'HB_Signal', 'slot_props': {'vertical_alignment': 'VAlign_Center'},
                                'children': bars},
                               {'class': 'SizeBox', 'name': 'Sz_Batt', 'properties': {'WidthOverride': 34, 'HeightOverride': 17},
                                'slot_props': {'vertical_alignment': 'VAlign_Center', 'padding': '(Left=10,Top=0,Right=0,Bottom=0)'},
                                'children': [{'class': 'Border', 'name': 'Brd_Batt',
                                              'properties': {'Background': rbox(0, 0.0, 4.5, 1.6, 0.55), 'Padding': '(Left=3,Top=3,Right=9,Bottom=3)'},
                                              'children': [{'class': 'Image', 'name': 'Img_BattFill', 'properties': {'Brush': rbox(INK, 1.0, 2)}}]}]},
                               {'class': 'SizeBox', 'name': 'Sz_BattNub', 'properties': {'WidthOverride': 3, 'HeightOverride': 7},
                                'slot_props': {'vertical_alignment': 'VAlign_Center', 'padding': '(Left=2,Top=0,Right=0,Bottom=0)'},
                                'children': [{'class': 'Image', 'name': 'Img_BattNub', 'properties': {'Brush': rbox(0.55, 1.0, 1.5)}}]},
                           ]})
        move('HB_Status', index=0)
    if 'Ovl_Lock' not in have:
        def banner(i, head, body):
            return {'class': 'Border', 'name': f'Brd_Notif{i}',
                    'properties': {'Background': rbox(0.11, 0.92, 26), 'Padding': '(Left=26,Top=20,Right=26,Bottom=22)'},
                    'slot_props': {'padding': '(Left=0,Top=0,Right=0,Bottom=14)'},
                    'children': [{'class': 'VerticalBox', 'name': f'VB_Notif{i}', 'children': [
                        {'class': 'TextBlock', 'name': f'Txt_Notif{i}Head', 'properties': txt(head, 26, 'SemiBold')},
                        {'class': 'TextBlock', 'name': f'Txt_Notif{i}Body', 'properties': txt(body, 26, 'Medium', SUB + 0.2, wrap=True)}]}]}
        build('RootCanvas', {'class': 'Overlay', 'name': 'Ovl_Lock', 'properties': {'Visibility': 'HitTestInvisible'}, 'children': [
            {'class': 'Image', 'name': 'Img_LockBg', 'properties': {'Brush': rbox(0.004, 1.0, 0)},
             'slot_props': {'horizontal_alignment': 'HAlign_Fill', 'vertical_alignment': 'VAlign_Fill'}},
            {'class': 'VerticalBox', 'name': 'VB_Lock',
             'slot_props': {'horizontal_alignment': 'HAlign_Fill', 'vertical_alignment': 'VAlign_Fill',
                            'padding': '(Left=34,Top=120,Right=34,Bottom=60)'},
             'children': [
                 {'class': 'Spacer', 'name': 'Spc_LockGap', 'properties': {'Size': {'X': 1, 'Y': 70}}},
                 banner(0, 'Mom', "Your shirt's in the wardrobe"),
                 banner(1, 'Career Center', 'Reminder: today')]}]})
        print('canvas slot for Ovl_Lock: set via ui_set_slot_layout (MCP) anchors [0,0,1,1], offsets 0,62,0,0')
        for w, i in (('Txt_Clock', 0), ('HB_Day', 1), ('HB_Crossed', 2)):
            move(w, 'VB_Lock', i)
    for i in range(4):
        if f'HB_Task{i}' not in have:
            build('VB_Tasks', {'class': 'HorizontalBox', 'name': f'HB_Task{i}', 'slot_props': {'padding': '(Left=0,Top=10,Right=0,Bottom=10)'},
                               'children': [{'class': 'SizeBox', 'name': f'Sz_Check{i}', 'properties': {'WidthOverride': 30, 'HeightOverride': 30},
                                             'slot_props': {'vertical_alignment': 'VAlign_Center', 'padding': '(Left=4,Top=0,Right=20,Bottom=0)'},
                                             'children': [{'class': 'Image', 'name': f'Img_Check{i}', 'properties': {'Brush': rbox(0, 0.0, 15, 2.5, 0.5)}}]}]})
            move(f'Txt_Task{i}', f'HB_Task{i}')
            move(f'HB_Task{i}', index=i)
    if 'Brd_Bubble' not in have:
        build('ReadMessage', [{'class': 'TextBlock', 'name': 'Txt_ThreadName', 'properties': txt('Mom', 30, 'SemiBold', just='Center'),
                               'slot_props': {'padding': '(Left=0,Top=4,Right=0,Bottom=22)', 'horizontal_alignment': 'HAlign_Center'}},
                              {'class': 'Border', 'name': 'Brd_Bubble', 'properties': {'Background': rbox(0.13, 1.0, 28),
                                                                                       'Padding': '(Left=24,Top=18,Right=24,Bottom=20)'},
                               'slot_props': {'horizontal_alignment': 'HAlign_Left', 'padding': '(Left=0,Top=0,Right=60,Bottom=0)'}}])
        move('Txt_ThreadName', index=0)
        move('Txt_Message', 'Brd_Bubble')
    if 'Brd_TabBar' not in have:
        build('VB_Phone', {'class': 'Border', 'name': 'Brd_TabBar', 'properties': {'Background': rbox(0.07, 1.0, 30), 'Padding': '(Left=8,Top=6,Right=8,Bottom=6)'},
                           'slot_props': {'padding': '(Left=0,Top=14,Right=0,Bottom=8)'}})
        move('HB_Pages', 'Brd_TabBar')
    order = ['HB_Status', 'Pages', 'Spc_Push', 'Btn_Action', 'Brd_TabBar', 'Txt_Controls']
    for i, w in enumerate(order):
        move(w, index=i)
    c('ui_compile_widget', widget_blueprint_path=P)
    c('ui_save_widget', widget_blueprint_path=P)


def style():
    def prop(name, properties=None, slot=None):
        c('ui_set_widget_properties', widget_blueprint_path=P, widget_name=name, properties=properties or {}, slot_props=slot or {})
    prop('Brd_Screen', {'Padding': '(Left=30,Top=18,Right=30,Bottom=26)',
                        'Background': {'DrawAs': 'Image', 'ResourceObject': '/Game/FoA/UI/Textures/T_UI_FadeV.T_UI_FadeV',
                                       'TintColor': col(0.035)}, 'BrushColor': '(R=1,G=1,B=1,A=1)'})
    prop('Txt_Clock', txt('6:40', 150, 'ExtraBold', INK, font=DISP, just='Center'), {'horizontal_alignment': 'HAlign_Center'})
    for w in ('HB_Day', 'HB_Crossed'):
        prop(w, {}, {'horizontal_alignment': 'HAlign_Center'})
    prop('Txt_DayLabel', {'Font': {'FontObject': UIF, 'TypefaceFontName': 'SemiBold', 'Size': 30}, 'ColorAndOpacity': col(INK)})
    prop('Txt_DayNum', {'Font': {'FontObject': UIF, 'TypefaceFontName': 'SemiBold', 'Size': 30}, 'ColorAndOpacity': col(INK)})
    for w in ('Txt_Crossed', 'Txt_CrossedLabel'):
        prop(w, {'Font': {'FontObject': UIF, 'TypefaceFontName': 'Medium', 'Size': 24}, 'ColorAndOpacity': col(SUB + 0.1)})
    for w, t in (('Heading_Tasks', 'Today'), ('Heading_Messages', 'Messages'), ('Heading_Notes', 'What I know')):
        prop(w, txt(t, 50, 'ExtraBold', font=DISP), {'padding': '(Left=4,Top=18,Right=0,Bottom=18)'})
    for i in range(4):
        prop(f'Txt_Task{i}', {'Font': {'FontObject': UIF, 'TypefaceFontName': 'Medium', 'Size': 30}, 'ColorAndOpacity': col(INK)},
             {'vertical_alignment': 'VAlign_Center'})
    for i in range(3):
        st = {}
        for state, shade, a in (('Normal', 0.0, 0.0), ('Hovered', 0.07, 1.0), ('Pressed', 0.12, 1.0), ('Disabled', 0.0, 0.0)):
            st[state] = rbox(shade, a, 20)
        prop(f'Btn_Message{i}', {'WidgetStyle': st, 'BackgroundColor': '(R=1,G=1,B=1,A=1)'}, {'padding': '(Left=0,Top=0,Right=0,Bottom=6)'})
        prop(f'Txt_Sender{i}', {'Font': {'FontObject': UIF, 'TypefaceFontName': 'SemiBold', 'Size': 28}, 'ColorAndOpacity': col(INK),
                                'LineHeightPercentage': 1.05})
    prop('Txt_Message', {'Font': {'FontObject': UIF, 'TypefaceFontName': 'Medium', 'Size': 28}, 'ColorAndOpacity': col(INK), 'AutoWrapText': True})
    prop('Txt_Notebook', {'Font': {'FontObject': UIF, 'TypefaceFontName': 'Medium', 'Size': 28}, 'ColorAndOpacity': col(INK),
                          'AutoWrapText': True, 'LineHeightPercentage': 1.15})
    for t in ('Tasks', 'Messages', 'Notes'):
        st = {s: rbox(0.0, 0.0, 22) for s in ('Normal', 'Hovered', 'Pressed', 'Disabled')}
        prop(f'Btn_{t}', {'WidgetStyle': st, 'BackgroundColor': '(R=1,G=1,B=1,A=1)'})
        prop(f'Tab_{t}', {'Font': {'FontObject': UIF, 'TypefaceFontName': 'SemiBold', 'Size': 24}, 'ColorAndOpacity': col(INK),
                          'Justification': 'Center'})
    prop('Txt_Controls', {'Font': {'FontObject': UIF, 'TypefaceFontName': 'Medium', 'Size': 18}, 'ColorAndOpacity': col(INK, 0.38),
                          'Justification': 'Center'}, {'horizontal_alignment': 'HAlign_Center'})
    prop('Pages', {}, {'size': {'SizeRule': 'Fill', 'Value': 1.0}})
    prop('Spc_Push', {'Size': {'X': 1, 'Y': 6}}, {'size': {'SizeRule': 'Auto', 'Value': 1.0}})
    c('ui_compile_widget', widget_blueprint_path=P)
    c('ui_save_widget', widget_blueprint_path=P)


BODY = {'Mom': ("Morning! Your shirt's in the wardrobe, I ironed it.\n\nEat something before you go. Love you",
                "Proud of you. Call me when you're out. Love you"),
        'Career Center': ('Reminder: your drop-in appointment is today at 10:30. Reply C to cancel.',
                          'We missed you on Tuesday. Drop in any weekday, 9 to 4. No appointment needed.'),
        'Draft': ('im up', "sorry about yesterday. and the day before. today's different i promise")}


def nodes_edges(g):
    nodes, edges, off = [], [], 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': P, 'graph_name': g, 'offset': off})['data']
        nodes += d['nodes']
        off = d['page']['nodes']['next_offset']
    off = 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': P, 'graph_name': g, 'edge_offset': off})['data']
        edges += d['edges']
        off = d['page']['edges']['next_offset']
    return nodes, edges


def graph():
    nodes, edges = nodes_edges('OpenMessage')
    pin = lambda n, k: next((p.get('default_value') or '') for p in n['pins'] if p['name'] == k)  # noqa: E731
    title = {n['node_id']: n['title'].replace('\n', ' ') for n in nodes}
    ops = []
    if not any(t.startswith('Get Txt_ThreadName') for t in title.values()) or '--force' in sys.argv:
        for n in nodes:
            if n['title'].replace(' ', '') != 'SelectString':
                continue
            who = next((k for k in BODY if pin(n, 'B').startswith(k + '\n') or pin(n, 'B') == BODY[k][0]), None)
            assert who, pin(n, 'B')[:30]
            ops += [{'op': 'set_pin', 'node_id': n['node_id'], 'pin_name': 'B', 'value': BODY[who][0]},
                    {'op': 'set_pin', 'node_id': n['node_id'], 'pin_name': 'A', 'value': BODY[who][1]}]
            # the SetText this selector feeds (through Conv_StringToText): add a SetText(Txt_ThreadName, who) after it
            conv = next(e['to_node'] for e in edges if e['from_node'] == n['node_id'])
            st = next(e['to_node'] for e in edges if e['from_node'] == conv)
            ref = 'tn' + str(len(ops))
            ops += [{'op': 'add_node', 'ref': ref + 'g', 'node_type': 'variable_get', 'variable_name': 'Txt_ThreadName', 'x': 0, 'y': 0},
                    {'op': 'add_node', 'ref': ref, 'node_type': 'call_function', 'function_name': '/Script/UMG.TextBlock:SetText', 'x': 0, 'y': 0},
                    {'op': 'add_node', 'ref': ref + 'c', 'node_type': 'call_function', 'function_name': '/Script/Engine.KismetTextLibrary:Conv_StringToText', 'x': 0, 'y': 0},
                    {'op': 'set_pin', 'node_id': ref + 'c', 'pin_name': 'InString', 'value': who},
                    {'op': 'connect', 'from_node': ref + 'c', 'from_pin': 'ReturnValue', 'to_node': ref, 'to_pin': 'InText'},
                    {'op': 'connect', 'from_node': ref + 'g', 'from_pin': 'Txt_ThreadName', 'to_node': ref, 'to_pin': 'self'}]
            nxt = [e for e in edges if e['from_node'] == st and e['from_pin'] == 'then']
            ops += [{'op': 'disconnect', 'node_id': st, 'pin_name': 'then', 'to_node': e['to_node'], 'to_pin': e['to_pin']} for e in nxt]
            ops += [{'op': 'connect', 'from_node': st, 'from_pin': 'then', 'to_node': ref, 'to_pin': 'execute'}]
            ops += [{'op': 'connect', 'from_node': ref, 'from_pin': 'then', 'to_node': e['to_node'], 'to_pin': e['to_pin']} for e in nxt]
        c('blueprint_graph_batch', path=P, graph_name='OpenMessage', ops=ops)
    # Lock screen: Tick with a real-time gap detector (the phone screen only ticks while it draws)
    for v in ('LockT', 'LockLast'):
        c('blueprint_add_variable', path=P, variable_name=v, variable_type='real', default_value='0.0', category='Phone|Lock',
          update_existing=True)
    eg = hc.call('blueprint_inspect_graph', {'path': P, 'graph_name': 'EventGraph'})['data']
    if not any(n['title'].startswith('Event Tick') for n in eg['nodes']):
        ops = [
            {'op': 'add_event', 'ref': 'tick', 'event_name': 'Tick', 'x': 0, 'y': 3000},
            {'op': 'add_node', 'ref': 'now', 'node_type': 'call_function', 'function_name': '/Script/Engine.GameplayStatics:GetRealTimeSeconds', 'x': 200, 'y': 3200},
            {'op': 'add_node', 'ref': 'last', 'node_type': 'variable_get', 'variable_name': 'LockLast', 'x': 200, 'y': 3280},
            {'op': 'add_node', 'ref': 'gap', 'node_type': 'call_function', 'function_name': f'{KML}:Subtract_DoubleDouble', 'x': 400, 'y': 3200},
            {'op': 'add_node', 'ref': 'fresh', 'node_type': 'call_function', 'function_name': f'{KML}:Greater_DoubleDouble', 'x': 600, 'y': 3200},
            {'op': 'set_pin', 'node_id': 'fresh', 'pin_name': 'B', 'value': '0.5'},
            {'op': 'add_node', 'ref': 'lt', 'node_type': 'variable_get', 'variable_name': 'LockT', 'x': 400, 'y': 3360},
            {'op': 'add_node', 'ref': 'adv', 'node_type': 'call_function', 'function_name': f'{KML}:Add_DoubleDouble', 'x': 600, 'y': 3360},
            {'op': 'add_node', 'ref': 'sel', 'node_type': 'call_function', 'function_name': f'{KML}:SelectFloat', 'x': 800, 'y': 3280},
            {'op': 'set_pin', 'node_id': 'sel', 'pin_name': 'A', 'value': '0.0'},
            {'op': 'add_node', 'ref': 'setl', 'node_type': 'variable_set', 'variable_name': 'LockT', 'x': 1000, 'y': 3000},
            {'op': 'add_node', 'ref': 'setn', 'node_type': 'variable_set', 'variable_name': 'LockLast', 'x': 1200, 'y': 3000},
            {'op': 'add_node', 'ref': 'live', 'node_type': 'call_function', 'function_name': f'{KML}:LessEqual_DoubleDouble', 'x': 1200, 'y': 3200},
            {'op': 'set_pin', 'node_id': 'live', 'pin_name': 'B', 'value': '1.5'},
            {'op': 'add_node', 'ref': 'br', 'node_type': 'branch', 'x': 1400, 'y': 3000},
            {'op': 'connect', 'from_node': 'now', 'from_pin': 'ReturnValue', 'to_node': 'gap', 'to_pin': 'A'},
            {'op': 'connect', 'from_node': 'last', 'from_pin': 'LockLast', 'to_node': 'gap', 'to_pin': 'B'},
            {'op': 'connect', 'from_node': 'gap', 'from_pin': 'ReturnValue', 'to_node': 'fresh', 'to_pin': 'A'},
            {'op': 'connect', 'from_node': 'lt', 'from_pin': 'LockT', 'to_node': 'adv', 'to_pin': 'A'},
            {'op': 'connect', 'from_node': 'tick', 'from_pin': 'InDeltaTime', 'to_node': 'adv', 'to_pin': 'B'},
            {'op': 'connect', 'from_node': 'adv', 'from_pin': 'ReturnValue', 'to_node': 'sel', 'to_pin': 'B'},
            {'op': 'connect', 'from_node': 'fresh', 'from_pin': 'ReturnValue', 'to_node': 'sel', 'to_pin': 'bPickA'},
            {'op': 'connect', 'from_node': 'sel', 'from_pin': 'ReturnValue', 'to_node': 'setl', 'to_pin': 'LockT'},
            {'op': 'connect', 'from_node': 'tick', 'from_pin': 'then', 'to_node': 'setl', 'to_pin': 'execute'},
            {'op': 'connect', 'from_node': 'now', 'from_pin': 'ReturnValue', 'to_node': 'setn', 'to_pin': 'LockLast'},
            {'op': 'connect', 'from_node': 'setl', 'from_pin': 'then', 'to_node': 'setn', 'to_pin': 'execute'},
            {'op': 'connect', 'from_node': 'setl', 'from_pin': 'Output_Get', 'to_node': 'live', 'to_pin': 'A'},
            {'op': 'connect', 'from_node': 'live', 'from_pin': 'ReturnValue', 'to_node': 'br', 'to_pin': 'Condition'},
            {'op': 'connect', 'from_node': 'setn', 'from_pin': 'then', 'to_node': 'br', 'to_pin': 'execute'},
            # u = easeIn3(clamp((LockT - 1.0) / 0.35)): the lock slides up the screen height and fades
            {'op': 'add_node', 'ref': 's', 'node_type': 'call_function', 'function_name': f'{KML}:Subtract_DoubleDouble', 'x': 1600, 'y': 3200},
            {'op': 'set_pin', 'node_id': 's', 'pin_name': 'B', 'value': '1.0'},
            {'op': 'connect', 'from_node': 'setl', 'from_pin': 'Output_Get', 'to_node': 's', 'to_pin': 'A'},
            {'op': 'add_node', 'ref': 'd', 'node_type': 'call_function', 'function_name': f'{KML}:Divide_DoubleDouble', 'x': 1780, 'y': 3200},
            {'op': 'set_pin', 'node_id': 'd', 'pin_name': 'B', 'value': '0.35'},
            {'op': 'connect', 'from_node': 's', 'from_pin': 'ReturnValue', 'to_node': 'd', 'to_pin': 'A'},
            {'op': 'add_node', 'ref': 'cl', 'node_type': 'call_function', 'function_name': f'{KML}:FClamp', 'x': 1960, 'y': 3200},
            {'op': 'set_pin', 'node_id': 'cl', 'pin_name': 'Min', 'value': '0.0'},
            {'op': 'set_pin', 'node_id': 'cl', 'pin_name': 'Max', 'value': '1.0'},
            {'op': 'connect', 'from_node': 'd', 'from_pin': 'ReturnValue', 'to_node': 'cl', 'to_pin': 'Value'},
            {'op': 'add_node', 'ref': 'ea', 'node_type': 'call_function', 'function_name': f'{KML}:Ease', 'x': 2140, 'y': 3200},
            {'op': 'set_pin', 'node_id': 'ea', 'pin_name': 'A', 'value': '0.0'},
            {'op': 'set_pin', 'node_id': 'ea', 'pin_name': 'B', 'value': '1.0'},
            {'op': 'set_pin', 'node_id': 'ea', 'pin_name': 'EasingFunc', 'value': 'EaseIn'},
            {'op': 'set_pin', 'node_id': 'ea', 'pin_name': 'BlendExp', 'value': '3.0'},
            {'op': 'connect', 'from_node': 'cl', 'from_pin': 'ReturnValue', 'to_node': 'ea', 'to_pin': 'Alpha'},
            {'op': 'add_node', 'ref': 'lk', 'node_type': 'variable_get', 'variable_name': 'Ovl_Lock', 'x': 2140, 'y': 3100},
            {'op': 'add_node', 'ref': 'up', 'node_type': 'call_function', 'function_name': f'{KML}:Lerp', 'x': 2320, 'y': 3280},
            {'op': 'set_pin', 'node_id': 'up', 'pin_name': 'A', 'value': '0.0'},
            {'op': 'set_pin', 'node_id': 'up', 'pin_name': 'B', 'value': '-1201.0'},
            {'op': 'connect', 'from_node': 'ea', 'from_pin': 'ReturnValue', 'to_node': 'up', 'to_pin': 'Alpha'},
            {'op': 'add_node', 'ref': 'v2', 'node_type': 'call_function', 'function_name': f'{KML}:MakeVector2D', 'x': 2480, 'y': 3280},
            {'op': 'connect', 'from_node': 'up', 'from_pin': 'ReturnValue', 'to_node': 'v2', 'to_pin': 'Y'},
            {'op': 'add_node', 'ref': 'tr', 'node_type': 'call_function', 'function_name': '/Script/UMG.Widget:SetRenderTranslation', 'x': 2600, 'y': 3000},
            {'op': 'connect', 'from_node': 'lk', 'from_pin': 'Ovl_Lock', 'to_node': 'tr', 'to_pin': 'self'},
            {'op': 'connect', 'from_node': 'v2', 'from_pin': 'ReturnValue', 'to_node': 'tr', 'to_pin': 'Translation'},
            {'op': 'connect', 'from_node': 'br', 'from_pin': 'then', 'to_node': 'tr', 'to_pin': 'execute'},
            {'op': 'add_node', 'ref': 'fa', 'node_type': 'call_function', 'function_name': f'{KML}:Subtract_DoubleDouble', 'x': 2480, 'y': 3400},
            {'op': 'set_pin', 'node_id': 'fa', 'pin_name': 'A', 'value': '1.0'},
            {'op': 'connect', 'from_node': 'ea', 'from_pin': 'ReturnValue', 'to_node': 'fa', 'to_pin': 'B'},
            {'op': 'add_node', 'ref': 'op', 'node_type': 'call_function', 'function_name': '/Script/UMG.Widget:SetRenderOpacity', 'x': 2860, 'y': 3000},
            {'op': 'connect', 'from_node': 'lk', 'from_pin': 'Ovl_Lock', 'to_node': 'op', 'to_pin': 'self'},
            {'op': 'connect', 'from_node': 'fa', 'from_pin': 'ReturnValue', 'to_node': 'op', 'to_pin': 'InOpacity'},
            {'op': 'connect', 'from_node': 'tr', 'from_pin': 'then', 'to_node': 'op', 'to_pin': 'execute'},
            {'op': 'comment', 'title': 'Lock clock', 'node_ids': ['tick', 'now', 'last', 'gap', 'fresh', 'lt', 'adv', 'sel', 'setl', 'setn', 'live', 'br'],
             'color': [0.10, 0.20, 0.35]},
            {'op': 'comment', 'title': 'Unlock slides up', 'node_ids': ['s', 'd', 'cl', 'ea', 'lk', 'up', 'v2', 'tr', 'fa', 'op'],
             'color': [0.30, 0.22, 0.10]},
            {'op': 'fit_comments'},
        ]
        c('blueprint_graph_batch', path=P, graph_name='EventGraph', ops=ops)
    c('ui_compile_widget', widget_blueprint_path=P)
    c('ui_save_widget', widget_blueprint_path=P)


{'tree': tree, 'style': style, 'graph': graph}[sys.argv[1]]()
