"""BP_Phone onto anim's RE7-style hold (main's contract, 2026-11-09), in place (Hayba). Apply ONLY after anim's phone4 PIE
proof passes and main says go: BP_Phone must not be edited by two lanes at once.
The view target STAYS on the player camera (main, after story's T0 trace: SetViewTargetWithBlend to the phone whipped
the camera into a motion-blur smear, and PhoneCam's aspect constraint letterboxed the whole time the phone was up).
  hold   OpenPhone: drop the hand_r attach, the relative transform, the view-target swap and its saved return target,
         SetCinematic(true), the hold montage and its next section; after StopJumping call
         BP_FoAPlayer.BeginPhoneHold(Phone = self) (anim's UpdatePhoneHold carries the phone in camera space).
         ClosePhone: drop the view restore, SetCinematic(previous), StopAnimMontage and the hide; after the cast call
         EndPhoneHold() (it lowers over 0.35 s, then hides the phone itself).
  taps   PhoneNext/Previous/Up/Down/Confirm/Back: after the tap sound, BP_FoAPlayer.PhoneTap() (a no-op until the grip
         clip lands)
  nocam  (editor Python: ue_remote ... aaa_phone_hold.py FOA_STEP=nocam) delete PhoneCam (no phone camera, so no
         aspect constraint) and the now-unused view variables
  verify no SetViewTarget node in any BP_Phone graph, no camera component, compiles clean
  glass  the Screen widget draws through M_UI_PhoneScreen (OverrideMaterials[0]); ScreenLight, a soft neutral rect light
         in front of the glass (it hides with the actor, so no on/off logic)
  python Tools/Unreal/ui/aaa_phone_hold.py hold|taps|glass, then nocam, then verify
Proof: bash Tools/Unreal/ui/aaa_phone_proof.sh (30 fps 'phone' sweep + qa_phone_raise.py: no letterbox, no smear,
readable at rest)."""
import json
import os
import sys

if os.environ.get('FOA_STEP') == 'nocam':  # editor Python: Hayba has no component or variable removal yet
    import unreal
    bp = unreal.load_asset('/Game/FoA/UI/Game/BP_Phone')
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    hs = sds.k2_gather_subobject_data_for_blueprint(bp)
    by = {str(lib.get_variable_name(lib.get_data(h))): h for h in hs}
    if 'PhoneCam' in by:
        print('PhoneCam deleted', sds.delete_subobject(hs[0], by['PhoneCam'], bp))
    else:
        print('PhoneCam already gone')
    BEL = unreal.BlueprintEditorLibrary
    BEL.remove_unused_variables(bp)  # ReturnViewTarget, BlendSeconds, bPreviousCinematic: dead after 'hold'
    unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
    print('nocam done; then aaa_phone_hold.py verify')

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

P = '/Game/FoA/UI/Game/BP_Phone'
PL = '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'


def c(cmd, **p):
    r = hc.call(cmd, p)
    d = r.get('data') or {}
    print(cmd, p.get('graph_name', ''), r.get('ok'), d.get('applied', d.get('removed', '')), d.get('failed_index', ''),
          d.get('error') or r.get('error') or '', json.dumps(d.get('compile') or '')[:160])
    return d


def graph(g):
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


def one(nodes, prefix):
    hits = [n['node_id'] for n in nodes if n['title'].replace('\n', ' ').startswith(prefix)]
    assert len(hits) == 1, (prefix, len(hits))
    return hits[0]


def nxt(edges, node):
    return [e for e in edges if e['from_node'] == node and e['from_pin'] == 'then']


def hold():
    assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    nodes, edges = graph('OpenPhone')
    if any(n['title'].startswith('Begin Phone Hold') or n['title'].startswith('BeginPhoneHold') for n in nodes):
        print('OpenPhone already swapped')
    else:
        jump, cast = one(nodes, 'StopJumping'), one(nodes, 'Cast To BP_FoAPlayer')
        hide, enable = one(nodes, 'Set Actor Hidden In Game'), one(nodes, 'EnableInput')
        cast_out = next(p['name'] for p in next(n for n in nodes if n['node_id'] == cast)['pins']
                        if p['direction'] == 'output' and p['type'] == 'object')
        setb, prevc = one(nodes, 'Set bOpen'), one(nodes, 'Set bPreviousCursor')
        drop = [one(nodes, t) for t in ('Attach Actor To Component', 'Set Actor Relative Location', 'MakeRotator',
                                        'Set Actor Relative Rotation', 'SetViewTargetWithBlend', 'Self-Reference', 'SetCinematic',
                                        'PlayAnimMontage', 'Montage_SetNextSection', 'GetAnimInstance', 'Get Mesh', 'Get Body',
                                        'GetViewTarget', 'Set ReturnViewTarget')]
        c('blueprint_remove_nodes', path=P, graph_name='OpenPhone', node_ids=drop)
        ops = [{'op': 'connect', 'from_node': setb, 'from_pin': 'then', 'to_node': prevc, 'to_pin': 'execute'},
               {'op': 'add_node', 'ref': 'begin', 'node_type': 'call_function', 'function_name': f'{PL}:BeginPhoneHold', 'x': 1400, 'y': 0},
               {'op': 'add_node', 'ref': 'me', 'node_type': 'self', 'x': 1300, 'y': 160},
               {'op': 'connect', 'from_node': cast, 'from_pin': cast_out, 'to_node': 'begin', 'to_pin': 'self'},
               {'op': 'connect', 'from_node': 'me', 'from_pin': 'self', 'to_node': 'begin', 'to_pin': 'Phone'},
               {'op': 'connect', 'from_node': jump, 'from_pin': 'then', 'to_node': 'begin', 'to_pin': 'execute'},
               {'op': 'connect', 'from_node': 'begin', 'from_pin': 'then', 'to_node': hide, 'to_pin': 'execute'},
               {'op': 'connect', 'from_node': hide, 'from_pin': 'then', 'to_node': enable, 'to_pin': 'execute'},
               {'op': 'comment', 'title': 'Hold the phone', 'node_ids': ['begin', 'me'], 'color': [0.10, 0.20, 0.35]},
               {'op': 'fit_comments'}]
        c('blueprint_graph_batch', path=P, graph_name='OpenPhone', ops=ops)
    nodes, edges = graph('ClosePhone')
    if any(n['title'].startswith('End Phone Hold') or n['title'].startswith('EndPhoneHold') for n in nodes):
        print('ClosePhone already swapped')
    else:
        cast = one(nodes, 'Cast To BP_FoAPlayer')
        cast_out = next(p['name'] for p in next(n for n in nodes if n['node_id'] == cast)['pins']
                        if p['direction'] == 'output' and p['type'] == 'object')
        setb, disable = one(nodes, 'Set bOpen'), one(nodes, 'DisableInput')
        drop = [one(nodes, t) for t in ('SetViewTargetWithBlend', 'Get ReturnViewTarget', 'SetCinematic', 'Get bPreviousCinematic',
                                        'StopAnimMontage', 'Set Actor Hidden In Game')]
        c('blueprint_remove_nodes', path=P, graph_name='ClosePhone', node_ids=drop)
        ops = [{'op': 'connect', 'from_node': setb, 'from_pin': 'then', 'to_node': disable, 'to_pin': 'execute'},
               {'op': 'add_node', 'ref': 'end', 'node_type': 'call_function', 'function_name': f'{PL}:EndPhoneHold', 'x': 2000, 'y': 0},
               {'op': 'connect', 'from_node': cast, 'from_pin': cast_out, 'to_node': 'end', 'to_pin': 'self'},
               {'op': 'connect', 'from_node': cast, 'from_pin': 'then', 'to_node': 'end', 'to_pin': 'execute'},
               {'op': 'comment', 'title': 'Lower the phone', 'node_ids': ['end'], 'color': [0.10, 0.20, 0.35]},
               {'op': 'fit_comments'}]
        c('blueprint_graph_batch', path=P, graph_name='ClosePhone', ops=ops)
    c('blueprint_compile', path=P)


def taps():
    assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    for f in ('PhoneNext', 'PhonePrevious', 'PhoneUp', 'PhoneDown', 'PhoneConfirm', 'PhoneBack'):
        nodes, edges = graph(f)
        if any('Phone Tap' in n['title'] or 'PhoneTap' in n['title'] for n in nodes):
            print(f, 'already taps')
            continue
        snd = one(nodes, 'PlaySound2D')
        after = nxt(edges, snd)
        ops = [{'op': 'disconnect', 'node_id': snd, 'pin_name': 'then', 'to_node': e['to_node'], 'to_pin': e['to_pin']} for e in after]
        ops += [{'op': 'add_node', 'ref': 'pawn', 'node_type': 'call_function', 'function_name': '/Script/Engine.GameplayStatics:GetPlayerPawn', 'x': 200, 'y': -120},
                {'op': 'add_node', 'ref': 'cast', 'node_type': 'cast', 'class_path': PL, 'x': 420, 'y': -260},
                {'op': 'connect', 'from_node': 'pawn', 'from_pin': 'ReturnValue', 'to_node': 'cast', 'to_pin': 'Object'},
                {'op': 'connect', 'from_node': snd, 'from_pin': 'then', 'to_node': 'cast', 'to_pin': 'execute'},
                {'op': 'add_node', 'ref': 'tap', 'node_type': 'call_function', 'function_name': f'{PL}:PhoneTap', 'x': 700, 'y': -260}]
        c('blueprint_graph_batch', path=P, graph_name=f, ops=ops)
        nodes, edges = graph(f)
        cast = next(n for n in nodes if n['title'].startswith('Cast To BP_FoAPlayer'))
        tap = one(nodes, 'Phone Tap') if any(n['title'].startswith('Phone Tap') for n in nodes) else one(nodes, 'PhoneTap')
        cast_out = next(p['name'] for p in cast['pins'] if p['direction'] == 'output' and p['type'] == 'object')
        fail = next(p['name'] for p in cast['pins'] if p['direction'] == 'output' and p['type'] == 'exec' and p['name'] != 'then')
        ops = [{'op': 'connect', 'from_node': cast['node_id'], 'from_pin': cast_out, 'to_node': tap, 'to_pin': 'self'},
               {'op': 'connect', 'from_node': cast['node_id'], 'from_pin': 'then', 'to_node': tap, 'to_pin': 'execute'}]
        for e in after:
            ops += [{'op': 'connect', 'from_node': tap, 'from_pin': 'then', 'to_node': e['to_node'], 'to_pin': e['to_pin']},
                    {'op': 'connect', 'from_node': cast['node_id'], 'from_pin': fail, 'to_node': e['to_node'], 'to_pin': e['to_pin']}]
        c('blueprint_graph_batch', path=P, graph_name=f, ops=ops)
    c('blueprint_compile', path=P)


def glass():
    """One screen drawer (main 2026-11-10): the Screen widget, on SM_Phone's Screen socket (0,0,-0.51, pitch -90) via the
    construction script (no Blueprint socket attach exists in Hayba or Python), 0.02 cm out of the glass, one-sided,
    fitted to the glass; the glass slot stays MI_Phone_Screen (base colour 0.004, roughness 0.05: plain black glass)."""
    assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    # stencil 200: the world lane's dream echo skips it, so phone text is not doubled (main, 2026-11-09)
    print(hc.call('object_set_property', {'path': f'{P}.BP_Phone_C:Screen_GEN_VARIABLE', 'properties': {
        'OverrideMaterials': ["/Script/Engine.Material'/Game/FoA/UI/Materials/M_UI_PhoneScreen.M_UI_PhoneScreen'"],
        'bRenderCustomDepth': True, 'CustomDepthStencilValue': 200, 'bIsTwoSided': False,
        # the SM_Phone glass (slot 1): 13.67 x 6.60 cm. 540 x 1118 keeps its aspect (2.07), 6.60 / 540 = 0.01222 cm per px
        # (the old 540 x 1201 at 0.01237 was 14.9 cm tall and drew over the bezel)
        'DrawSize': '(X=540,Y=1118)', 'RelativeScale3D': '(X=0.01222,Y=0.01222,Z=0.01222)'}}).get('data'))
    nodes, edges = graph('UserConstructionScript')
    if not any('AttachComponentToComponent' in n['title'].replace(' ', '') for n in nodes):
        entry = next(n['node_id'] for n in nodes if n['title'] in ('Construction Script', 'UserConstructionScript'))
        ops = [{'op': 'add_node', 'ref': 'scr', 'node_type': 'variable_get', 'variable_name': 'Screen', 'x': 200, 'y': 200},
               {'op': 'add_node', 'ref': 'mesh', 'node_type': 'variable_get', 'variable_name': 'Mesh', 'x': 200, 'y': 300},
               {'op': 'add_node', 'ref': 'at', 'node_type': 'call_function', 'function_name': '/Script/Engine.SceneComponent:K2_AttachToComponent', 'x': 420, 'y': 0},
               {'op': 'connect', 'from_node': 'scr', 'from_pin': 'Screen', 'to_node': 'at', 'to_pin': 'self'},
               {'op': 'connect', 'from_node': 'mesh', 'from_pin': 'Mesh', 'to_node': 'at', 'to_pin': 'Parent'},
               {'op': 'set_pin', 'node_id': 'at', 'pin_name': 'SocketName', 'value': 'Screen'},
               {'op': 'set_pin', 'node_id': 'at', 'pin_name': 'LocationRule', 'value': 'SnapToTarget'},
               {'op': 'set_pin', 'node_id': 'at', 'pin_name': 'RotationRule', 'value': 'SnapToTarget'},
               {'op': 'set_pin', 'node_id': 'at', 'pin_name': 'ScaleRule', 'value': 'KeepRelative'},
               {'op': 'connect', 'from_node': entry, 'from_pin': 'then', 'to_node': 'at', 'to_pin': 'execute'},
               {'op': 'add_node', 'ref': 'off', 'node_type': 'call_function', 'function_name': '/Script/Engine.SceneComponent:K2_SetRelativeLocation', 'x': 760, 'y': 0},
               {'op': 'connect', 'from_node': 'scr', 'from_pin': 'Screen', 'to_node': 'off', 'to_pin': 'self'},
               {'op': 'set_pin', 'node_id': 'off', 'pin_name': 'NewLocation', 'value': '0.02, 0, 0'},  # out of the glass (socket X)
               {'op': 'connect', 'from_node': 'at', 'from_pin': 'then', 'to_node': 'off', 'to_pin': 'execute'},
               {'op': 'comment', 'title': 'Screen on the glass socket', 'node_ids': ['scr', 'mesh', 'at', 'off'], 'color': [0.10, 0.20, 0.35]}]
        r = hc.call('blueprint_graph_batch', {'path': P, 'graph_name': 'UserConstructionScript', 'ops': ops})
        print('construction script', r.get('ok'), (r.get('data') or {}).get('error') or r.get('error') or '')
        assert r.get('ok')
    info = hc.call('blueprint_get_info', {'path': P})['data']
    if not any(cc.get('name') == 'ScreenLight' for cc in info.get('components', [])):
        print(hc.call('blueprint_add_component', {'path': P, 'component_class_path': '/Script/Engine.RectLightComponent',
                                                  'component_name': 'ScreenLight'}).get('ok'))
    print(hc.call('object_set_property', {'path': f'{P}.BP_Phone_C:ScreenLight_GEN_VARIABLE', 'properties': {
        'RelativeLocation': '(X=0,Y=0,Z=-1.2)', 'RelativeRotation': '(Pitch=-90,Yaw=0,Roll=0)', 'IntensityUnits': 'Candelas',
        'Intensity': 2.5, 'AttenuationRadius': 55.0, 'SourceWidth': 6.7, 'SourceHeight': 14.9, 'BarnDoorAngle': 70.0,
        'LightColor': '(R=255,G=255,B=255,A=255)', 'CastShadows': False}}).get('data'))
    c('blueprint_compile', path=P)


def verify():
    assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    info = hc.call('blueprint_get_info', {'path': P})['data']
    cams = [cc['name'] for cc in info.get('components', []) if 'Camera' in (cc.get('class') or '')]
    views = [(g, n['title']) for g in info['functions'] + ['EventGraph'] for n in graph(g)[0] if 'ViewTarget' in n['title']]
    widgets = [cc['name'] for cc in info.get('components', []) if 'WidgetComponent' in (cc.get('class') or '')]
    setup = 'ApplyScreen' if 'ApplyScreen' in info['functions'] else 'UserConstructionScript'  # phone_apply_screen.py moved it
    attach = [n for n in graph(setup)[0] if 'AttachComponentToComponent' in n['title'].replace(' ', '')]
    sock = [p.get('default_value') for n in attach for p in n['pins'] if p['name'] == 'SocketName']
    scr = (hc.call('object_get_property', {'path': f'{P}.BP_Phone_C:Screen_GEN_VARIABLE', 'properties': ['bIsTwoSided', 'DrawSize']})
           .get('data') or {}).get('properties', {})
    d = c('blueprint_compile', path=P)
    ok = not cams and not views and len(set(widgets)) == 1 and sock == ['Screen'] and scr.get('bIsTwoSided') == 'False'
    assert ok, (cams, views, widgets, sock, scr)
    print('verified: no camera, no view-target node, one screen drawer', widgets, 'on socket', sock, scr, 'errors', d.get('error_count'))


if os.environ.get('FOA_STEP') != 'nocam':
    {'hold': hold, 'taps': taps, 'glass': glass, 'verify': verify}[sys.argv[1]]()
