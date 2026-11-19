"""WBP_IntroStory v4 (intro lane): edited in place through Hayba, idempotent. Inside a lease on /Game/FoA/UI/Intro:
  python Tools/LookDev/intro_v4/widget_v4.py tree     Line_Sub (WBP_SandLine) in the old line's slot; the v4 variables
                                                      (BackPanels, LineAt, LineOut, Moods) and PlayLine/DismissLine
  python Tools/LookDev/intro_v4/widget_v4.py graphs   NextPanel feeds the Back plate and times the line; PlayLine and
                                                      DismissLine drive the sand text kit; Finish and Destruct clear
                                                      them; UpdateFrame loses the old retainer line and the 0.2 s fades
                                                      (the shader owns every transition); Construct styles the line
  python Tools/LookDev/intro_v4/widget_v4.py defaults the arrays from story.py
  python Tools/LookDev/intro_v4/widget_v4.py prune    Ret_Sub and Txt_Sub go once nothing reads them
  python Tools/LookDev/intro_v4/widget_v4.py tidy     the v3 leftovers go: the four collapsed layer images and the
                                                      ticks that drove them, Img_Foot, and the unused NearInk
                                                      material (NearInk and NearPanels stay as unread variables:
                                                      Hayba has no variable remover)
  python Tools/LookDev/intro_v4/widget_v4.py lineguard  NextPanel sets the PlayLine timer only when LineAt > 0, else
                                                      clears it (a panel without a line: the wordless hook)
  python Tools/LookDev/intro_v4/widget_v4.py clock    PanelTime = world time - PanelStart (the clock the panel and line
                                                      timers run on; summed Slate deltas ran 17 % ahead under hitches)
Every step compiles clean and saves. Lifecycle (Host, OnStoryFinished, Skip, FocusSkip) is untouched, and Index still
steps 0..4, which BP_RoomAudio.UpdateIntro keys its whoosh, buzz and stinger on."""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/ui', 'P:/FoA/Tools/LookDev/intro_v4']
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, graph, ok, save  # noqa: E402
from story import PANELS  # noqa: E402

W = '/Game/FoA/UI/Intro/WBP_IntroStory'
WC = W + '.WBP_IntroStory_C'
SL = '/Game/FoA/UI/Widgets/Common/WBP_SandLine.WBP_SandLine_C'
FONT = '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
TEX = '/Game/FoA/UI/Intro/Textures/T_IntroPlate_'
KML, KSL, KTL = '/Script/Engine.KismetMathLibrary', '/Script/Engine.KismetSystemLibrary', '/Script/Engine.KismetTextLibrary'
MID, TB = '/Script/Engine.MaterialInstanceDynamic', '/Script/UMG.TextBlock'
GS = '/Script/Engine.GameplayStatics'
VARS = [('BackPanels', 'object:/Script/Engine.Texture2D', 'array'), ('LineAt', 'real', 'array'),
        ('LineOut', 'real', 'array'), ('Moods', 'int', 'array')]


def by_title(nodes, title):
    return [n for n in nodes if n['title'] == title]


def pin(n, name):
    return next((p.get('default_value') or p.get('default_object') for p in n['pins'] if p['name'] == name), None)


def tree():
    if 'Line_Sub' not in str(hc.call('ui_query', {'path': W}).get('data')):
        ok(hc.call('ui_build_tree', {'widget_blueprint_path': W, 'parent_widget_name': 'Cvs_Root', 'tree': {
            'class': SL, 'name': 'Line_Sub',
            'slot_props': {'anchors_min': [0.08, 1], 'anchors_max': [0.92, 1], 'alignment': [0, 0], 'position': [0, -188],
                           'size': [0, 110], 'z_order': 7}}}), 'Line_Sub')
        ok(hc.call('ui_set_variable', {'widget_blueprint_path': W, 'widget_name': 'Line_Sub', 'is_variable': True}), 'var')
    ok(hc.call('ui_set_widget_properties', {'widget_blueprint_path': W, 'widget_name': 'Line_Sub', 'properties': {
        'Scale': 3.1, 'bLineFont': True, 'LineFont': {'FontObject': FONT, 'TypefaceFontName': 'Medium', 'Size': 34},
        'Visibility': 'Collapsed'}}), 'Line_Sub props')  # Play shows it; until then its design text must not
    if 'Ret_Sub' in str(hc.call('ui_query', {'path': W}).get('data')):  # until prune removes it
        ok(hc.call('ui_set_widget_properties', {'widget_blueprint_path': W, 'widget_name': 'Ret_Sub',
                                                'properties': {'Visibility': 'Collapsed'}}), 'old line off')
    info = hc.call('blueprint_get_info', {'path': W})['data']
    have = {v['name'] for v in info['variables']}
    for name, typ, container in VARS:
        if name not in have:
            ok(hc.call('blueprint_add_variable', {'path': W, 'variable_name': name, 'variable_type': typ,
                                                   'container': container, 'category': 'Intro', 'instance_editable': True}), name)
    for name in ('PlayLine', 'DismissLine'):
        if name not in info['functions']:
            ok(hc.call('blueprint_add_function', {'path': W, 'function_name': name}), name)
    compile_bp(W, widget=True)
    print('tree', save(W))


def arr(b, var, idx):
    n = b.node('get_array_item')
    b.link(*b.get(var), n, 'Array')
    b.link(*idx, n, 'Dimension 1')
    return (n, 'Output')


def guarded(b, entry):
    br = b.node('branch', {'Condition': b.get('bDone')})
    b.chain(entry, br)
    return (br, 'else')


def line_fns():
    for fn, body in (('PlayLine', lambda b, idx: b.fn(f'{SL}:Play', self=b.get('Line_Sub'), Line=b.fn(
            f'{KTL}:Conv_StringToText', InString=arr(b, 'Lines', idx)), Mood=arr(b, 'Moods', idx), Hold=0.0)),
                     ('DismissLine', lambda b, idx: b.fn(f'{SL}:Dismiss', self=b.get('Line_Sub')))):
        nodes, _ = graph(W, fn)
        if len(nodes) > 1:
            print(fn, 'already built')
            continue
        b = B(W, fn)
        entry = next(n['node_id'] for n in nodes if n['title'].replace(' ', '') == fn)
        call = body(b, b.get('Index') if fn == 'PlayLine' else None)  # Dismiss needs no index
        b.chain(guarded(b, entry), call)
        b.ops.append(dict(op='comment', title='Sand line', node_ids=sorted(b.refs) + [entry], color=[0.12, 0.16, 0.19]))
        b.run()


def next_panel():
    nodes, edges = graph(W, 'NextPanel')
    if by_title(nodes, 'Set Timer by Function Name') and any(pin(n, 'FunctionName') == 'PlayLine' for n in nodes):
        print('NextPanel already timed')
        return
    st = by_title(nodes, 'SetText (Text)')[0]['node_id']
    prev = next(e['from_node'] for e in edges if e['to_node'] == st and e['to_pin'] == 'execute')
    nxt = next(e['to_node'] for e in edges if e['from_node'] == st and e['from_pin'] == 'then')
    feed = {(e['to_node'], e['to_pin']): e['from_node'] for e in edges}
    totext = feed[(st, 'InText')]
    aref = feed[(totext, 'InString')]
    dead = [st, totext, aref, feed[(aref, 'Array')], feed[(st, 'self')]]
    idx = next(n['node_id'] for n in by_title(nodes, 'Get Index') if any(e['from_node'] == n['node_id'] and e['to_node'] == aref for e in edges))
    b = B(W, 'NextPanel')
    b.ops.append(dict(op='remove', node_ids=dead))
    index = (idx, 'Index')
    back = b.fn(f'{MID}:SetTextureParameterValue', self=b.get('FarInk'), ParameterName='Back', Value=arr(b, 'BackPanels', index))
    play = b.fn(f'{KSL}:K2_SetTimer', FunctionName='PlayLine', Time=arr(b, 'LineAt', index), bLooping=False)
    out = arr(b, 'LineOut', index)
    br = b.node('branch', {'Condition': b.fn(f'{KML}:Greater_DoubleDouble', A=out, B=0.0)})
    dis = b.fn(f'{KSL}:K2_SetTimer', FunctionName='DismissLine', Time=out, bLooping=False)
    keep = b.fn(f'{KSL}:K2_ClearTimer', FunctionName='DismissLine')
    b.chain(prev, back, play, br, dis, nxt)
    b.chain((br, 'else'), keep, nxt)
    b.ops.append(dict(op='comment', title='Back plate and line', node_ids=sorted(b.refs), color=[0.12, 0.16, 0.19]))
    b.run()


def clears(g, exec_from):
    """Clear the line timers right after `exec_from` (a node id, or 'entry') in graph g."""
    nodes, edges = graph(W, g)
    if any(pin(n, 'FunctionName') == 'PlayLine' for n in nodes):
        print(g, 'already clears the line')
        return
    src = (next(n['node_id'] for n in nodes if n['title'].replace(' ', '') == g) if exec_from == 'entry'
           else exec_from(nodes, edges))
    nxt = next((e['to_node'] for e in edges if e['from_node'] == src and e['from_pin'] == 'then'), None)
    b = B(W, g)
    a = b.fn(f'{KSL}:K2_ClearTimer', FunctionName='PlayLine')
    d = b.fn(f'{KSL}:K2_ClearTimer', FunctionName='DismissLine')
    if nxt:
        b.ops.append(dict(op='disconnect', node_id=src, pin_name='then'))
        b.chain(src, a, d, nxt)
    else:
        b.chain(src, a, d)
    b.run()


def update_frame():
    nodes, edges = graph(W, 'UpdateFrame')
    sop = [n for n in by_title(nodes, 'SetRenderOpacity')]
    reveal = [n for n in nodes if n['title'] == 'SetScalarParameterValue' and pin(n, 'ParameterName') == 'Reveal']
    quick = [n for n in nodes if n['title'] in ('float * float', 'double * double') and pin(n, 'B') == '5']
    b = B(W, 'UpdateFrame')
    if quick:  # the shader owns every transition: the widget no longer fades the plate (the hook is a hard cut)
        b.ops.append(dict(op='set_pin', node_id=quick[0]['node_id'], pin_name='B', value='1000'))
    if sop or reveal:
        feed = {(e['to_node'], e['to_pin']): e['from_node'] for e in edges}
        dead = []
        for n in sop:
            dead += [n['node_id'], feed[(n['node_id'], 'self')]]
            prev = feed[(n['node_id'], 'execute')]
        upd = by_title(nodes, 'UpdateInkReveal')[0]['node_id']
        for n in reveal:  # the ui lane's retainer hook: SetScalar <- GetEffectMaterial <- Ret_Sub; Value <- Ease <- Clamp <- / <- PanelTime
            rid = n['node_id']
            mat = feed[(rid, 'self')]
            ease = feed[(rid, 'Value')]
            clamp = feed[(ease, 'Alpha')]
            div = feed[(clamp, 'Value')]
            dead += [rid, mat, feed[(mat, 'self')], ease, clamp, div, feed[(div, 'A')]]
        b.ops.append(dict(op='remove', node_ids=sorted(set(dead))))
        b.link(prev, 'then', upd, 'execute')
    if b.ops:
        b.run()
    else:
        print('UpdateFrame already v4')


def construct():
    nodes, edges = graph(W, 'EventGraph')
    if any(n['title'].startswith('SetJustification') for n in nodes):
        print('Construct already styles the line')
        return
    bind = by_title(nodes, 'Bind Event to On Clicked')[0]['node_id']
    nxt = next(e['to_node'] for e in edges if e['from_node'] == bind and e['from_pin'] == 'then')
    b = B(W, 'EventGraph')
    txt = lambda: b.get('Txt_Line', cls=SL, target=b.get('Line_Sub'))  # noqa: E731
    j = b.fn('/Script/UMG.TextLayoutWidget:SetJustification', self=txt(), InJustification='Center')
    so = b.fn(f'{TB}:SetShadowOffset', self=txt(), InShadowOffset='(X=0.000000,Y=2.000000)')
    sc = b.fn(f'{TB}:SetShadowColorAndOpacity', self=txt(), InShadowColorAndOpacity='(R=0.000000,G=0.000000,B=0.000000,A=0.850000)')
    b.ops.append(dict(op='disconnect', node_id=bind, pin_name='then'))
    b.chain(bind, j, so, sc, nxt)
    b.ops.append(dict(op='comment', title='Line style', node_ids=sorted(b.refs), color=[0.12, 0.16, 0.19]))
    b.run()


def graphs():
    line_fns()
    next_panel()
    clears('Finish', 'entry')
    clears('EventGraph', lambda ns, es: next(n['node_id'] for n in ns if n['title'] == 'Clear Timer by Function Name'
                                              and pin(n, 'FunctionName') == 'FocusSkip'
                                              and any(e['to_node'] == n['node_id'] and e['from_pin'] == 'then' for e in es)))
    update_frame()
    construct()
    compile_bp(W, widget=True)
    print('graphs', save(W))


def defaults():
    plates = [f'{TEX}{p[0]}.T_IntroPlate_{p[0]}' for p in PANELS]
    ok(hc.call('blueprint_set_defaults', {'path': W, 'properties': {
        'Panels': plates, 'BackPanels': [f'{TEX}{p[0]}_Back.T_IntroPlate_{p[0]}_Back' for p in PANELS],
        'Lines': [p[1] for p in PANELS], 'Seconds': [p[2] for p in PANELS], 'LineAt': [p[5] for p in PANELS],
        'LineOut': [p[6] for p in PANELS], 'Moods': [p[7] for p in PANELS]}}), 'defaults')
    nodes, _ = graph(W, 'NextPanel')
    less = by_title(nodes, 'integer < integer')[0]
    assert pin(less, 'B') == str(len(PANELS)), pin(less, 'B')
    compile_bp(W, widget=True)
    d = hc.call('object_get_property', {'path': W + '.Default__WBP_IntroStory_C',
                                        'names': ['Seconds', 'LineAt', 'LineOut', 'Moods', 'BackPanels']})['data']
    print('defaults', save(W), d.get('properties'))


def prune():
    for g in ('NextPanel', 'UpdateFrame', 'EventGraph', 'Finish', 'FocusSkip', 'ApplyLayer', 'EnsureInkMaterials', 'UpdateInkReveal'):
        nodes, _ = graph(W, g)
        bad = [n['title'] for n in nodes if 'Txt_Sub' in n['title'] or 'Ret_Sub' in n['title']]
        assert not bad, (g, bad)
    if 'Ret_Sub' in str(hc.call('ui_query', {'path': W}).get('data')):
        ok(hc.call('ui_remove_element', {'widget_blueprint_path': W, 'widget_name': 'Ret_Sub'}), 'remove Ret_Sub')
    compile_bp(W, widget=True)
    print('prune', save(W))


def lineguard():
    nodes, edges = graph(W, 'NextPanel')
    if any(n['title'] == 'Clear Timer by Function Name' and pin(n, 'FunctionName') == 'PlayLine' for n in nodes):
        print('NextPanel already guards PlayLine')
        return
    play = next(n['node_id'] for n in nodes if n['title'] == 'Set Timer by Function Name' and pin(n, 'FunctionName') == 'PlayLine')
    prev = next(e['from_node'] for e in edges if e['to_node'] == play and e['to_pin'] == 'execute')
    nxt = next(e['to_node'] for e in edges if e['from_node'] == play and e['from_pin'] == 'then')
    at = next((e['from_node'], e['from_pin']) for e in edges if e['to_node'] == play and e['to_pin'] == 'Time')
    b = B(W, 'NextPanel')
    br = b.node('branch', {'Condition': b.fn(f'{KML}:Greater_DoubleDouble', A=at, B=0.0)})
    none = b.fn(f'{KSL}:K2_ClearTimer', FunctionName='PlayLine')
    b.ops.append(dict(op='disconnect', node_id=prev, pin_name='then'))
    b.chain(prev, br, play)
    b.chain((br, 'else'), none, nxt)
    b.run()
    compile_bp(W, widget=True)
    print('lineguard', save(W))


DEAD = ('Img_Mid', 'Img_Figure', 'Img_Fx', 'Img_Near', 'Img_Foot')


def tidy():
    # UpdateFrame: keep ApplyLayer(Img_Panel); the other four drove collapsed images every tick
    nodes, edges = graph(W, 'UpdateFrame')
    feed = {(e['to_node'], e['to_pin']): e['from_node'] for e in edges}
    title = {n['node_id']: n['title'] for n in nodes}
    layers = [n['node_id'] for n in by_title(nodes, 'ApplyLayer')]
    dead_calls = [c for c in layers if title.get(feed.get((c, 'Image'))) != 'Get Img_Panel']
    if dead_calls:
        keep = next(c for c in layers if c not in dead_calls)
        last = next(c for c in dead_calls if not any(e['from_node'] == c and e['from_pin'] == 'then' and e['to_node'] in dead_calls for e in edges))
        after = next(e['to_node'] for e in edges if e['from_node'] == last and e['from_pin'] == 'then')
        dead = set(dead_calls) | {feed[(c, 'Image')] for c in dead_calls}
        # their Alpha feeds (Index > 0, Index == -1, the 0.25 x): nothing else in UpdateFrame uses these titles
        dead |= {n['node_id'] for n in nodes if n['title'] in ('integer > integer', 'Equal (Integer)', 'To Float (Boolean)')
                 or (n['title'] in ('float * float', 'double * double') and pin(n, 'B') == '0.25')}
        assert all(e['to_node'] in dead for e in edges if e['from_node'] in dead and e['from_pin'] != 'then'), 'a removed node feeds a kept one'
        b = B(W, 'UpdateFrame')
        b.ops.append(dict(op='remove', node_ids=sorted(dead)))
        b.link(keep, 'then', after, 'execute')
        b.run()
    # EnsureInkMaterials: only the plate's material (Img_Panel) is made
    nodes, edges = graph(W, 'EnsureInkMaterials')
    feed = {(e['to_node'], e['to_pin']): e['from_node'] for e in edges}
    near_get = [n['node_id'] for n in by_title(nodes, 'Get Img_Near')]
    if near_get:
        title = {n['node_id']: n['title'] for n in nodes}
        brush = next(e['to_node'] for e in edges if e['from_node'] == near_get[0] and title[e['to_node']] == 'SetBrushFromMaterial')
        dyn = next(e['to_node'] for e in edges if e['from_node'] == near_get[0] and title[e['to_node']] == 'GetDynamicMaterial')
        setn = by_title(nodes, 'Set NearInk')[0]['node_id']
        andn = by_title(nodes, 'AND Boolean')[0]['node_id']
        far_valid = feed[(andn, 'A')] if title[feed[(feed[(andn, 'A')], 'Object')]] == 'Get FarInk' else feed[(andn, 'B')]
        near_valid = feed[(andn, 'B')] if far_valid == feed[(andn, 'A')] else feed[(andn, 'A')]
        branch = next(e['to_node'] for e in edges if e['from_node'] == andn)
        b = B(W, 'EnsureInkMaterials')
        b.ops.append(dict(op='remove', node_ids=[near_get[0], brush, dyn, setn, andn, near_valid, feed[(near_valid, 'Object')]]))
        b.link(far_valid, 'ReturnValue', branch, 'Condition')
        b.run()
    # NextPanel: no NearInk texture
    nodes, edges = graph(W, 'NextPanel')
    feed = {(e['to_node'], e['to_pin']): e['from_node'] for e in edges}
    title = {n['node_id']: n['title'] for n in nodes}
    sets = [n['node_id'] for n in nodes if n['title'] == 'SetTextureParameterValue' and title.get(feed.get((n['node_id'], 'self'))) == 'Get NearInk']
    if sets:
        st = sets[0]
        prev = feed[(st, 'execute')]
        nxt = next(e['to_node'] for e in edges if e['from_node'] == st and e['from_pin'] == 'then')
        val = feed[(st, 'Value')]
        b = B(W, 'NextPanel')
        b.ops.append(dict(op='remove', node_ids=[st, feed[(st, 'self')], val, feed[(val, 'Array')]]))
        b.link(prev, 'then', nxt, 'execute')
        b.run()
    compile_bp(W, widget=True)
    save(W)
    for g in ('UpdateFrame', 'EnsureInkMaterials', 'NextPanel', 'ApplyLayer', 'EventGraph', 'Finish', 'FocusSkip', 'UpdateInkReveal'):
        nodes, _ = graph(W, g)
        bad = [n['title'] for n in nodes if any(d in n['title'] for d in DEAD) or n['title'] in ('Get NearInk', 'Set NearInk')]
        assert not bad, (g, bad)
    q = str(hc.call('ui_query', {'path': W}).get('data'))
    for w in DEAD:
        if w in q:
            ok(hc.call('ui_remove_element', {'widget_blueprint_path': W, 'widget_name': w}), 'remove ' + w)
    compile_bp(W, widget=True)
    print('tidy', save(W))


def clock():
    info = hc.call('blueprint_get_info', {'path': W})['data']
    if 'PanelStart' not in {v['name'] for v in info['variables']}:
        ok(hc.call('blueprint_add_variable', {'path': W, 'variable_name': 'PanelStart', 'variable_type': 'real',
                                               'category': 'Intro'}), 'PanelStart')
        compile_bp(W, widget=True)
    nodes, edges = graph(W, 'NextPanel')
    if not any(n['title'] == 'Set PanelStart' for n in nodes):
        st = next(n['node_id'] for n in by_title(nodes, 'Set PanelTime'))
        nxt = next(e['to_node'] for e in edges if e['from_node'] == st and e['from_pin'] == 'then')
        b = B(W, 'NextPanel')
        start = b.set('PanelStart', b.fn(f'{GS}:GetTimeSeconds'))
        b.ops.append(dict(op='disconnect', node_id=st, pin_name='then'))
        b.chain(st, start, nxt)
        b.run()
    nodes, edges = graph(W, 'UpdateFrame')
    if any(n['title'] == 'GetTimeSeconds' for n in nodes):
        print('UpdateFrame already on the world clock')
    else:
        add = next(n['node_id'] for n in by_title(nodes, 'float + float')
                   if any(e['to_node'] == n['node_id'] and e['to_pin'] == 'B' and e['from_pin'] == 'Delta' for e in edges))
        feed_a = next(e['from_node'] for e in edges if e['to_node'] == add and e['to_pin'] == 'A')
        outs = [(e['to_node'], e['to_pin']) for e in edges if e['from_node'] == add]
        b = B(W, 'UpdateFrame')
        now = b.fn(f'{KML}:Subtract_DoubleDouble', A=b.fn(f'{GS}:GetTimeSeconds'), B=b.get('PanelStart'))
        b.ops.append(dict(op='remove', node_ids=[add, feed_a]))
        for node, p in outs:
            b.link(now, 'ReturnValue', node, p)
        b.run()
    compile_bp(W, widget=True)
    print('clock', save(W))


if __name__ == '__main__':
    assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    {'tree': tree, 'graphs': graphs, 'defaults': defaults, 'prune': prune, 'clock': clock, 'tidy': tidy, 'lineguard': lineguard}[sys.argv[1]]()
