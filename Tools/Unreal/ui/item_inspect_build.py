"""Item inspect (user ask 2026-11-10, main's approved plan): taking an item opens it in 3D, centred, rotatable, then closes.
Steps, in order (each idempotent; build only when main releases the editor):
  ue_remote ... item_inspect_build.py FOA_AREAS=<LIB> FOA_STEP=lib   BPFL_ItemInspect through the function-library factory
  python Tools/Unreal/ui/item_inspect_build.py assets       BP_ItemInspect (actor), WBP_ItemInspect, the BPFL's functions
  python Tools/Unreal/ui/item_inspect_build.py graphs       the function bodies (Hayba, typed nodes only)
  ue_remote ... item_inspect_build.py FOA_AREAS=<BP> FOA_STEP=input   InputKey/Axis events, execute when paused, consumed
  python Tools/Unreal/ui/item_inspect_build.py hook         BP_Interactable.ApplyRow: RequestInspect(Row.Give) after
                                                            Inventory.Add (main's grant; anim owns the asset: own lease)
  python Tools/Unreal/ui/item_inspect_build.py finish       compile everything, asset_save force
Design (main 2026-11-10):
  Request(Item)   first take of an item per morning (Seen string; a new morning = BeatIndex went backwards), not in
                  SkipItems (default "|Shirt|KeyStub|", story's to edit), after OpenDelay (0.55 s, a variable for anim's new grabs)
  Open(Item)      DT_Items row: Mesh (soft) / DisplayName / LookLine; the mesh 35 cm in front of the camera, its bounds
                  40% of the visible height, 3/4 angle (yaw 35, pitch -15); pause; widget; UI open cue
  TickStep        runs while paused (real-time dt): ease in 0.3 s / out 0.25 s, inertia (e^-6t), pitch +-70, follows
                  the camera, the PP weight (darker, vignette, DOF at 35 cm)
  input           mouse drag (LMB + MouseX/Y), right stick, arrows/D-pad; E, Esc, B, right click close; P and Tab are
                  bound and consumed; every binding executes when paused and consumes its key
  look            ItemMesh on lighting channel 1 with stencil 200 only (no collision, so no focus rim), KeyLight/RimLight
                  on channel 1 only"""
import json
import os
import sys

UI = '/Game/FoA/UI/Game'
BP = f'{UI}/BP_ItemInspect'
BPC = f'{BP}.BP_ItemInspect_C'
LIB = f'{UI}/BPFL_ItemInspect'
WBP = f'{UI}/WBP_ItemInspect'
WBPC = f'{WBP}.WBP_ItemInspect_C'
DT = '/Game/FoA/Gameplay/DT_Items.DT_Items'
S_ITEM = '/Game/FoA/Gameplay/S_Item.S_Item'
S_ROW = '/Game/FoA/Gameplay/S_Interaction.S_Interaction'
DIR_C = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
SND = '/Game/FoA/Audio/SFX/UI/'
KML, KSL, GS = '/Script/Engine.KismetMathLibrary', '/Script/Engine.KismetSystemLibrary', '/Script/Engine.GameplayStatics'
KSTR, KTXT = '/Script/Engine.KismetStringLibrary', '/Script/Engine.KismetTextLibrary'
PRIM, SCENE, ACTOR = '/Script/Engine.PrimitiveComponent', '/Script/Engine.SceneComponent', '/Script/Engine.Actor'
CH1 = '(bChannel0=False,bChannel1=True,bChannel2=False)'

STEP = os.environ.get('FOA_STEP') or (sys.argv[1] if len(sys.argv) > 1 else '')

if STEP == 'input':  # editor Python ---------------------------------------------------------------------
    exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
    if True:
        g = Graph(BP)
        pal = [str(n) for n in g.ed.list_available_nodes([])]
        norm = lambda t: str(t).split('\n')[0].replace(' ', '').replace('-', '').lower()  # noqa: E731
        have = {norm(BEL.get_node_title(n)) for n in g.ed.list_all_nodes()}  # exact titles: 'E' must not match 'Event Tick'
        bound = lambda key: norm(key.split('|')[-1]) in have  # noqa: E731

        def key_node(key_path, x, y):
            hits = [n for n in pal if n.replace(' ', '').endswith(key_path.replace(' ', ''))]
            assert hits, ('no palette entry', key_path)
            n = g.node(hits[0], x, y)
            for prop, v in (('b_execute_when_paused', True), ('b_consume_input', True), ('b_override_parent_binding', True)):
                try:
                    n.set_editor_property(prop, v)
                except Exception as ex:  # a node type without that flag (axis events name some differently)
                    print('flag', prop, 'not on', key_path, repr(ex)[:80])
            return n

        y = 1200
        # close: E, Escape, B, right click
        for key in ('Input|KeyboardEvents|E', 'Input|KeyboardEvents|Escape', 'Input|GamepadEvents|GamepadFaceButtonRight', 'Input|MouseEvents|RightMouseButton'):
            if bound(key):
                continue
            n = key_node(key, 0, y)
            c = g.call(f'{BPC}:Close', 300, y)
            g.link(n, 'Pressed', c, 'execute')
            y += 200
        # consumed and ignored: P, Tab
        for key in ('Input|KeyboardEvents|P', 'Input|KeyboardEvents|Tab'):
            if not bound(key):
                key_node(key, 0, y)
                y += 160
        # drag: left mouse sets bDragging; mouse axes rotate while dragging (TickStep reads them)
        if not bound('LeftMouseButton'):
            n = key_node('Input|MouseEvents|LeftMouseButton', 0, y)
            s1 = g.set('bDragging', 300, y)
            g.default(s1, 'bDragging', 'true')
            s0 = g.set('bDragging', 300, y + 120)
            g.link(n, 'Pressed', s1, 'execute')
            g.link(n, 'Released', s0, 'execute')
            y += 280
        for axis, var in (('MouseX', 'AxisMouseX'), ('MouseY', 'AxisMouseY'), ('GamepadRightThumbstickX-Axis', 'AxisStickX'),
                          ('GamepadRightThumbstickY-Axis', 'AxisStickY')):
            if bound(axis):
                continue  # shortcut: a node left by a failed run is not re-linked here; item_inspect_axis_fix.py wires it
            n = key_node(('Input|MouseEvents|' if 'Mouse' in axis else 'Input|GamepadEvents|') + axis, 0, y)
            s = g.set(var, 300, y)
            g.link(n, 'AxisValue', s, var)
            g.link(n, 'then', s, 'execute')
            y += 200
        # arrows and D-pad: an impulse per press into the e^-6t inertia; total turn = impulse / 6 = 45 degrees
        # signs match a drag: Right turns the facing side right (yaw down), Up lifts it (pitch down)
        for key, dx, dy in (('Input|KeyboardEvents|Left', 270, 0), ('Input|KeyboardEvents|Right', -270, 0), ('Input|KeyboardEvents|Up', 0, -270), ('Input|KeyboardEvents|Down', 0, 270),
                            ('Input|GamepadEvents|GamepadD-padLeft', 270, 0), ('Input|GamepadEvents|GamepadD-padRight', -270, 0),
                            ('Input|GamepadEvents|GamepadD-padUp', 0, -270), ('Input|GamepadEvents|GamepadD-padDown', 0, 270)):
            if bound(key):
                continue
            n = key_node(key, 0, y)
            r = g.call(f'{BPC}:Rotate', 300, y, DX=dx, DY=dy)
            g.link(n, 'Pressed', r, 'execute')
            y += 180
        unreal.EditorAssetLibrary.save_loaded_asset(g.bp, False)
        # bExecuteWhenPaused / bConsumeInput are not Python-visible: Hayba object_set_property sets them on these
        for n in g.ed.list_all_nodes():
            if n.get_class().get_name() in ('K2Node_InputKey', 'K2Node_InputAxisKeyEvent'):
                print('KEYNODE', n.get_path_name())
        print('input events done; compile with Hayba')

elif STEP == 'lib':  # editor Python: Hayba's blueprint_create makes a plain Blueprint, whose function entries get no __WorldContext
    import unreal
    if unreal.EditorAssetLibrary.does_asset_exist(LIB):
        old = unreal.load_asset(LIB)
        assert not [str(r) for r in unreal.EditorAssetLibrary.find_package_referencers_for_asset(LIB, False)], 'BPFL referenced'
        unreal.EditorAssetLibrary.delete_asset(LIB)
    lib = unreal.AssetToolsHelpers.get_asset_tools().create_asset('BPFL_ItemInspect', UI, unreal.Blueprint, unreal.BlueprintFunctionLibraryFactory())
    print('created', lib.get_path_name(), unreal.EditorAssetLibrary.save_loaded_asset(lib, False))

else:  # Hayba ---------------------------------------------------------------------------------------------------------
    sys.path.insert(0, 'P:/FoA/Tools/Unreal')
    import editor_lock  # noqa: E402
    import hayba_call as hc  # noqa: E402

    def ok(r, what):
        assert r.get('ok'), (what, r.get('error'), (r.get('data') or {}).get('error'))
        return r.get('data') or {}

    def graph(path, g):
        nodes, edges, off = [], [], 0
        while off is not None:
            d = hc.call('blueprint_inspect_graph', {'path': path, 'graph_name': g, 'offset': off})['data']
            nodes += d['nodes']
            off = d['page']['nodes']['next_offset']
        off = 0
        while off is not None:
            d = hc.call('blueprint_inspect_graph', {'path': path, 'graph_name': g, 'edge_offset': off})['data']
            edges += d['edges']
            off = d['page']['edges']['next_offset']
        return nodes, edges

    def batch(path, g, ops):
        have = {v.get('name') for v in hc.call('blueprint_get_info', {'path': path})['data'].get('variables', [])}
        missing = sorted({o['variable_name'] for o in ops if o.get('node_type') in ('variable_get', 'variable_set')
                          and not o.get('class_path')} - have - WIDGET_VARS.get(path, set()))
        assert not missing, (g, 'missing variables', missing)  # blueprint_graph_batch is not atomic
        r = hc.call('blueprint_graph_batch', {'path': path, 'graph_name': g, 'ops': ops})
        d = r.get('data') or {}
        print(g, r.get('ok'), d.get('applied'), d.get('failed_index', ''), d.get('error') or r.get('error') or '')
        assert r.get('ok'), g
        return d

    def compile_bp(path):
        if path == WBP:
            d = hc.call('ui_compile_widget', {'widget_blueprint_path': path})['data']
            assert d.get('compiled_clean'), (path, d.get('errors'))
        else:
            d = hc.call('blueprint_compile', {'path': path}).get('data') or {}
            assert d.get('compiled') and not d.get('error_count'), (path, d)

    def empty(path, g):
        nodes, edges = graph(path, g)
        real = [n for n in nodes if n['title'] not in (g,) and not n['title'].startswith('Return') and n['title'] != 'Comment']
        return nodes, edges, not real

    WIDGET_VARS = {WBP: {'Txt_ItemName', 'Txt_ItemLine', 'Txt_Hint'}, BP: {'ItemMesh', 'PP', 'KeyLight', 'RimLight'}, LIB: {'Result'}}

    def assets():
        info = hc.call('blueprint_get_info', {'path': BP})
        if not info.get('ok'):
            ok(hc.call('blueprint_create', {'name': 'BP_ItemInspect', 'package_path': BP, 'parent_class_path': '/Script/Engine.Actor'}), 'create BP')
        comps = {c.get('name') for c in hc.call('blueprint_get_info', {'path': BP})['data'].get('components', [])}
        for name, cls in (('ItemMesh', 'StaticMeshComponent'), ('KeyLight', 'RectLightComponent'), ('RimLight', 'RectLightComponent'),
                          ('PP', 'PostProcessComponent')):
            if name not in comps:
                ok(hc.call('blueprint_add_component', {'path': BP, 'component_class_path': f'/Script/Engine.{cls}', 'component_name': name}), name)
        props = {
            'ItemMesh': {'LightingChannels': CH1, 'bRenderCustomDepth': True, 'CustomDepthStencilValue': 200, 'CastShadow': False,
                         'RelativeLocation': '(X=35,Y=0,Z=0)'},
            # item at (35,0,0) in camera space; key above-left in front, rim behind-right, both aimed at it
            'KeyLight': {'RelativeLocation': '(X=15,Y=-20,Z=18)', 'RelativeRotation': '(Pitch=-32.5,Yaw=45,Roll=0)', 'IntensityUnits': 'Candelas',
                         'Intensity': 6.0, 'AttenuationRadius': 120.0, 'SourceWidth': 20.0, 'SourceHeight': 20.0, 'BarnDoorAngle': 60.0,
                         'LightingChannels': CH1, 'CastShadows': False, 'LightColor': '(R=255,G=250,B=240,A=255)'},
            'RimLight': {'RelativeLocation': '(X=60,Y=18,Z=14)', 'RelativeRotation': '(Pitch=-24.4,Yaw=-144.2,Roll=0)', 'IntensityUnits': 'Candelas',
                         'Intensity': 10.0, 'AttenuationRadius': 120.0, 'SourceWidth': 10.0, 'SourceHeight': 30.0, 'BarnDoorAngle': 60.0,
                         'LightingChannels': CH1, 'CastShadows': False, 'LightColor': '(R=255,G=255,B=255,A=255)'},
            'PP': {'bUnbound': True, 'BlendWeight': 0.0, 'Priority': 10.0,
                   'Settings': '(bOverride_AutoExposureBias=True,AutoExposureBias=-0.7,bOverride_VignetteIntensity=True,VignetteIntensity=0.6,'
                               'bOverride_DepthOfFieldFocalDistance=True,DepthOfFieldFocalDistance=35.0,bOverride_DepthOfFieldFstop=True,DepthOfFieldFstop=1.4)'}}
        for comp, p in props.items():
            r = hc.call('object_set_property', {'path': f'{BPC}:{comp}_GEN_VARIABLE', 'properties': p})
            print(comp, (r.get('data') or {}).get('applied'), r.get('error') or '')
        for name, typ, dv, edit in (('OpenDelay', 'real', '0.55', True), ('SkipItems', 'string', '|Shirt|KeyStub|', True), ('Seen', 'string', '', False),
                                    ('LastBeat', 'int', '0', False), ('PendingItem', 'name', 'None', False), ('bOpen', 'bool', 'false', False),
                                    ('bClosing', 'bool', 'false', False), ('bDragging', 'bool', 'false', False), ('T', 'real', '0.0', False),
                                    ('CloseT', 'real', '0.0', False), ('LastReal', 'real', '0.0', False), ('Yaw', 'real', '35.0', False),
                                    ('Pitch', 'real', '-15.0', False), ('VelYaw', 'real', '0.0', False), ('VelPitch', 'real', '0.0', False),
                                    ('Scale', 'real', '1.0', False), ('Center', 'vector', '', False), ('AxisMouseX', 'real', '0.0', False),
                                    ('AxisMouseY', 'real', '0.0', False), ('AxisStickX', 'real', '0.0', False), ('AxisStickY', 'real', '0.0', False),
                                    ('Widget', f'object:{WBPC}', '', False)):
            if name == 'Widget' and not hc.call('blueprint_get_info', {'path': WBP}).get('ok'):
                continue  # added after the widget exists
            ok(hc.call('blueprint_add_variable', {'path': BP, 'variable_name': name, 'variable_type': typ, 'default_value': dv,
                                                   'instance_editable': edit, 'category': 'Inspect', 'update_existing': True}), name)
        ok(hc.call('blueprint_set_defaults', {'path': BP, 'properties': {
            'PrimaryActorTick': '(bCanEverTick=True,bStartWithTickEnabled=True,bTickEvenWhenPaused=True)', 'InputPriority': 100}}), 'defaults')
        funcs = hc.call('blueprint_get_info', {'path': BP})['data']['functions']
        for name, spec in (('Request', dict(inputs=[{'name': 'Item', 'type': 'name'}])), ('OpenPending', {}),
                           ('Open', dict(inputs=[{'name': 'Item', 'type': 'name'}])), ('TickStep', {}),
                           ('Rotate', dict(inputs=[{'name': 'DX', 'type': 'real'}, {'name': 'DY', 'type': 'real'}])),
                           ('Close', {}), ('Finish', {}), ('IsInspecting', dict(outputs=[{'name': 'bInspecting', 'type': 'bool'}], pure=True))):
            if name not in funcs:
                ok(hc.call('blueprint_add_function', {'path': BP, 'function_name': name, **spec}), name)
        compile_bp(BP)
        # the widget: name and line bottom-centre, the hint under them, in the HUD's type style
        if not hc.call('blueprint_get_info', {'path': WBP}).get('ok'):
            ok(hc.call('ui_create_widget', {'path': UI, 'name': 'WBP_ItemInspect'}), 'create widget')  # comes with RootCanvas
        if 'Txt_ItemName' not in json.dumps(hc.call('ui_query', {'path': WBP}).get('data') or {}):
            font = lambda size, face: {'FontObject': '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI', 'TypefaceFontName': face, 'Size': size}  # noqa: E731
            ok(hc.call('ui_build_tree', {'widget_blueprint_path': WBP, 'tree': {
                    'class': 'VerticalBox', 'name': 'VB_Text', 'slot_props': {'anchors_min': [0.5, 1], 'anchors_max': [0.5, 1], 'alignment': [0.5, 1],
                                                                              'position': [0, -96], 'auto_size': True},
                     'children': [
                         {'class': 'TextBlock', 'name': 'Txt_ItemName', 'properties': {'Text': 'Item', 'Justification': 'Center', 'Font': font(34, 'SemiBold')}},
                         {'class': 'TextBlock', 'name': 'Txt_ItemLine', 'properties': {'Text': '', 'Justification': 'Center', 'Font': font(26, 'Medium')}},
                         {'class': 'Spacer', 'name': 'Spc_Hint', 'properties': {'Size': {'X': 1, 'Y': 22}}},
                         {'class': 'TextBlock', 'name': 'Txt_Hint', 'properties': {'Text': 'Drag  Rotate      E  Put away', 'Justification': 'Center',
                                                                                    'Font': font(18, 'Medium'),
                                                                                    'ColorAndOpacity': {'SpecifiedColor': {'R': 0.45, 'G': 0.45, 'B': 0.45, 'A': 1}}}}]}}),
               'tree')
            for w in WIDGET_VARS[WBP]:
                ok(hc.call('ui_set_variable', {'widget_blueprint_path': WBP, 'widget_name': w, 'is_variable': True}), w)
            compile_bp(WBP)
        ok(hc.call('blueprint_add_variable', {'path': BP, 'variable_name': 'Widget', 'variable_type': f'object:{WBPC}', 'category': 'Inspect',
                                              'update_existing': True}), 'Widget var')
        # the library: the one call in BP_Interactable.ApplyRow (main's grant)
        assert hc.call('blueprint_get_info', {'path': LIB}).get('ok'), 'run the lib step first (ue_remote ... FOA_STEP=lib)'
        if 'RequestInspect' not in hc.call('blueprint_get_info', {'path': LIB})['data']['functions']:
            ok(hc.call('blueprint_add_function', {'path': LIB, 'function_name': 'RequestInspect', 'inputs': [{'name': 'Item', 'type': 'name'}]}), 'RequestInspect')
        compile_bp(BP)
        compile_bp(LIB)
        print('assets done')

    def graphs():
        # ---- IsInspecting ----
        nodes, edges, e0 = empty(BP, 'IsInspecting')
        if e0:
            entry = next(n['node_id'] for n in nodes if n['title'] == 'IsInspecting')
            ret = next(n['node_id'] for n in nodes if n['title'].startswith('Return'))
            ops = [] if [x for x in edges if x['from_node'] == entry and x['to_node'] == ret] else \
                [{'op': 'connect', 'from_node': entry, 'from_pin': 'then', 'to_node': ret, 'to_pin': 'execute'}]
            batch(BP, 'IsInspecting', ops + [{'op': 'add_node', 'ref': 'o', 'node_type': 'variable_get', 'variable_name': 'bOpen', 'x': 200, 'y': 120},
                                             {'op': 'connect', 'from_node': 'o', 'from_pin': 'bOpen', 'to_node': ret, 'to_pin': 'bInspecting'}])
        # ---- Rotate(DX, DY): an impulse into the inertia ----
        nodes, edges, e0 = empty(BP, 'Rotate')
        if e0:
            e = nodes[0]['node_id']
            ops = []
            prev = e
            for k, (pin, var) in enumerate((('DX', 'VelYaw'), ('DY', 'VelPitch'))):
                ops += [{'op': 'add_node', 'ref': f'g{k}', 'node_type': 'variable_get', 'variable_name': var, 'x': 200, 'y': 200 + k * 120},
                        {'op': 'add_node', 'ref': f'a{k}', 'node_type': 'call_function', 'function_name': f'{KML}:Add_DoubleDouble', 'x': 400, 'y': 200 + k * 120},
                        {'op': 'connect', 'from_node': f'g{k}', 'from_pin': var, 'to_node': f'a{k}', 'to_pin': 'A'},
                        {'op': 'connect', 'from_node': e, 'from_pin': pin, 'to_node': f'a{k}', 'to_pin': 'B'},
                        {'op': 'add_node', 'ref': f's{k}', 'node_type': 'variable_set', 'variable_name': var, 'x': 600 + k * 240, 'y': 0},
                        {'op': 'connect', 'from_node': f'a{k}', 'from_pin': 'ReturnValue', 'to_node': f's{k}', 'to_pin': var},
                        {'op': 'connect', 'from_node': prev, 'from_pin': 'then', 'to_node': f's{k}', 'to_pin': 'execute'}]
                prev = f's{k}'
            batch(BP, 'Rotate', ops)
        # ---- Close: start the ease-out, the close cue (input stays ours until Finish) ----
        nodes, edges, e0 = empty(BP, 'Close')
        if e0:
            e = nodes[0]['node_id']
            batch(BP, 'Close', [
                {'op': 'add_node', 'ref': 'o', 'node_type': 'variable_get', 'variable_name': 'bOpen', 'x': 160, 'y': 200},
                {'op': 'add_node', 'ref': 'c', 'node_type': 'variable_get', 'variable_name': 'bClosing', 'x': 160, 'y': 280},
                {'op': 'add_node', 'ref': 'nc', 'node_type': 'call_function', 'function_name': f'{KML}:Not_PreBool', 'x': 320, 'y': 280},
                {'op': 'connect', 'from_node': 'c', 'from_pin': 'bClosing', 'to_node': 'nc', 'to_pin': 'A'},
                {'op': 'add_node', 'ref': 'and', 'node_type': 'call_function', 'function_name': f'{KML}:BooleanAND', 'x': 480, 'y': 220},
                {'op': 'connect', 'from_node': 'o', 'from_pin': 'bOpen', 'to_node': 'and', 'to_pin': 'A'},
                {'op': 'connect', 'from_node': 'nc', 'from_pin': 'ReturnValue', 'to_node': 'and', 'to_pin': 'B'},
                {'op': 'add_node', 'ref': 'br', 'node_type': 'branch', 'x': 640, 'y': 0},
                {'op': 'connect', 'from_node': 'and', 'from_pin': 'ReturnValue', 'to_node': 'br', 'to_pin': 'Condition'},
                {'op': 'connect', 'from_node': e, 'from_pin': 'then', 'to_node': 'br', 'to_pin': 'execute'},
                {'op': 'add_node', 'ref': 'sc', 'node_type': 'variable_set', 'variable_name': 'bClosing', 'x': 860, 'y': 0},
                {'op': 'set_pin', 'node_id': 'sc', 'pin_name': 'bClosing', 'value': 'true'},
                {'op': 'connect', 'from_node': 'br', 'from_pin': 'then', 'to_node': 'sc', 'to_pin': 'execute'},
                {'op': 'add_node', 'ref': 'ct', 'node_type': 'variable_set', 'variable_name': 'CloseT', 'x': 1080, 'y': 0},
                {'op': 'set_pin', 'node_id': 'ct', 'pin_name': 'CloseT', 'value': '0.0'},
                {'op': 'connect', 'from_node': 'sc', 'from_pin': 'then', 'to_node': 'ct', 'to_pin': 'execute'},
                {'op': 'add_node', 'ref': 'snd', 'node_type': 'call_function', 'function_name': f'{GS}:PlaySound2D', 'x': 1300, 'y': 0},
                {'op': 'set_pin', 'node_id': 'snd', 'pin_name': 'Sound', 'value': f'{SND}SFX_UI_Close_A.SFX_UI_Close_A'},
                {'op': 'set_pin', 'node_id': 'snd', 'pin_name': 'bIsUISound', 'value': 'true'},
                {'op': 'connect', 'from_node': 'ct', 'from_pin': 'then', 'to_node': 'snd', 'to_pin': 'execute'}])
        print('graphs: IsInspecting, Rotate, Close built; Request, OpenPending, Open, TickStep, Finish, the widget hint and '
              'RequestInspect follow in graphs2 (written once the first half compiles in the editor)')

    class B:
        """blueprint_graph_batch ops. Pin kwargs take a literal, a node ref (its ReturnValue) or (ref, pin)."""

        def __init__(s, path, g):
            s.path, s.g, s.ops, s.k, s.refs, s.execs = path, g, [], 0, set(), set()

        def _add(s, spec, pins):
            s.k += 1
            ref = f'n{s.k}'
            s.refs.add(ref)
            s.ops.append(dict(op='add_node', ref=ref, x=0, y=0, **spec))
            s._pins(ref, pins)
            return ref

        def _pins(s, ref, pins):
            for k, v in pins.items():
                if isinstance(v, tuple):
                    s.link(v[0], v[1], ref, k)
                elif isinstance(v, str) and v in s.refs:
                    s.link(v, 'ReturnValue', ref, k)
                elif v != '':  # an empty string is the pin's default already (set_pin refuses '')
                    s.ops.append(dict(op='set_pin', node_id=ref, pin_name=k, value=str(v).lower() if isinstance(v, bool) else str(v)))

        def fn(s, func, **pins):
            return s._add(dict(node_type='call_function', function_name=func), pins)

        def node(s, kind, pins=None, **spec):
            return s._add(dict(node_type=kind, **spec), pins or {})

        def get(s, var, cls=None, target=None):
            ref = s._add(dict(node_type='variable_get', variable_name=var, **({'class_path': cls} if cls else {})),
                         {'self': target} if target else {})
            return (ref, var)

        def set(s, var, value=None, cls=None, target=None):
            pins = {} if value is None else {var: value}
            return s._add(dict(node_type='variable_set', variable_name=var, **({'class_path': cls} if cls else {})),
                          {**pins, **({'self': target} if target else {})})

        def link(s, a, ap, b, bp):
            s.ops.append(dict(op='connect', from_node=a, from_pin=ap, to_node=b, to_pin=bp))

        def chain(s, *refs):
            for a, b in zip(refs, refs[1:]):
                a, ap = a if isinstance(a, tuple) else (a, 'then')
                s.execs.update({a, b})
                s.link(a, ap, b, 'execute')

        def run(s):
            # exec nodes on one row in chain order, data nodes below in creation order
            row = [o['ref'] for o in s.ops if o['op'] == 'add_node' and o['ref'] in s.execs]
            data = [o['ref'] for o in s.ops if o['op'] == 'add_node' and o['ref'] not in s.execs]
            for o in s.ops:
                if o['op'] == 'add_node':
                    r = o['ref']
                    o['x'], o['y'] = ((row.index(r) + 1) * 320, 0) if r in row else ((data.index(r) // 4 + 1) * 300, 260 + (data.index(r) % 4) * 140)
            return batch(s.path, s.g, s.ops)

    PCM, PC_, SMC, TB, W = ('/Script/Engine.PlayerCameraManager', '/Script/Engine.PlayerController', '/Script/Engine.StaticMeshComponent',
                            '/Script/UMG.TextBlock', '/Script/UMG.Widget')

    def entry_of(path, g):
        nodes, edges = graph(path, g)
        e = next(n for n in nodes if n['title'].replace(' ', '') == g)
        return e['node_id'], nodes, edges

    def pin_of(nodes, node_id, pred, what):
        n = next(n for n in nodes if n['node_id'] == node_id)
        hits = [p['name'] for p in n['pins'] if pred(p)]
        assert hits, (what, [(p['name'], p.get('direction'), p.get('type') or p.get('category')) for p in n['pins']])
        return hits[0]

    def is_exec(p):
        return 'exec' in json.dumps({k: v for k, v in p.items() if k != 'name'}).lower()

    def graphs2():
        ok(hc.call('blueprint_add_variable', {'path': BP, 'variable_name': 'bPad', 'variable_type': 'bool', 'default_value': 'false',
                                              'category': 'Inspect', 'update_existing': True}), 'bPad')
        compile_bp(BP)
        # ---- OpenPending: Open(PendingItem) ----
        if empty(BP, 'OpenPending')[2]:
            e, _, _ = entry_of(BP, 'OpenPending')
            b = B(BP, 'OpenPending')
            b.chain(e, b.fn(f'{BPC}:Open', Item=b.get('PendingItem')))
            b.run()
        # ---- Request(Item): first take per morning, not skipped, not while open; Open after OpenDelay ----
        if empty(BP, 'Request')[2]:
            e, _, _ = entry_of(BP, 'Request')
            b = B(BP, 'Request')
            d = b.fn(f'{GS}:GetActorOfClass', ActorClass=DIR_C)
            br0 = b.node('branch', {'Condition': b.fn(f'{KSL}:IsValid', Object=d)})
            bi = b.get('BeatIndex', cls=DIR_C, target=d)
            later = b.fn(f'{KML}:Less_IntInt', A=bi, B=b.get('LastBeat'))  # BeatIndex went back: a new morning
            s_seen0 = b.set('Seen', b.fn(f'{KML}:SelectString', A='', B=b.get('Seen'), bPickA=later))
            s_lb = b.set('LastBeat', bi)
            key = b.fn(f'{KSTR}:Concat_StrStr', A=b.fn(f'{KSTR}:Concat_StrStr', A='|', B=b.fn(f'{KSTR}:Conv_NameToString', InName=(e, 'Item'))), B='|')
            skip = b.fn(f'{KML}:BooleanOR', A=b.fn(f'{KML}:BooleanOR', A=b.fn(f'{KSTR}:Contains', SearchIn=b.get('SkipItems'), Substring=key),
                                                   B=b.fn(f'{KSTR}:Contains', SearchIn=b.get('Seen'), Substring=key)), B=b.get('bOpen'))
            br1 = b.node('branch', {'Condition': skip})
            s_seen = b.set('Seen', b.fn(f'{KSTR}:Concat_StrStr', A=b.get('Seen'), B=key))
            s_p = b.set('PendingItem', (e, 'Item'))
            tm = b.fn(f'{KSL}:K2_SetTimer', FunctionName='OpenPending', Time=b.get('OpenDelay'), bLooping=False)
            b.chain(e, d, br0, s_seen0, s_lb, br1)  # GetActorOfClass is an exec node
            b.chain((br0, 'else'), br1)
            b.chain((br1, 'else'), s_seen, s_p, tm)
            b.run()
        # ---- Open(Item): two passes, the row/struct/cast pins are only known once those nodes exist ----
        if empty(BP, 'Open')[2]:
            a = B(BP, 'Open')
            row = a.node('get_data_table_row', {'DataTable': DT})
            brk = a.node('break_struct', struct_path=S_ITEM)
            cast = a.node('cast', class_path='/Script/Engine.StaticMesh')
            cw = a.node('create_widget', {'Class': WBPC})
            refs = a.run().get('refs') or {}
            row, brk, cast, cw = (refs[r] for r in (row, brk, cast, cw))
            e, nodes, _ = entry_of(BP, 'Open')
            out = lambda p: str(p.get('direction')).lower().startswith(('out', 'egpd_out')) and not is_exec(p)  # noqa: E731
            inn = lambda p: str(p.get('direction')).lower().startswith(('in', 'egpd_in')) and not is_exec(p)  # noqa: E731
            row_out = pin_of(nodes, row, out, 'row out')
            brk_in = pin_of(nodes, brk, inn, 'brk in')
            mesh_p = pin_of(nodes, brk, lambda p: out(p) and p['name'].startswith('Mesh'), 'Mesh')
            name_p = pin_of(nodes, brk, lambda p: out(p) and p['name'].startswith('DisplayName'), 'DisplayName')
            line_p = pin_of(nodes, brk, lambda p: out(p) and p['name'].startswith('LookLine'), 'LookLine')
            cast_out = pin_of(nodes, cast, lambda p: out(p) and p['name'].startswith('As'), 'cast out')
            b = B(BP, 'Open')
            b.refs |= {row, brk, cast, cw}
            b.link(e, 'Item', row, 'RowName')
            b.link(row, row_out, brk, brk_in)
            load = b.fn(f'{KSL}:LoadAsset_Blocking', Asset=(brk, mesh_p))
            b.link(load, 'ReturnValue', cast, 'Object')
            mesh = b.get('ItemMesh')
            sm = b.fn(f'{SMC}:SetStaticMesh', self=mesh, NewMesh=(cast, cast_out))
            # BoxSphereBounds has no generic break: the KML function
            bnd = b.fn(f'{KML}:BreakBoxSphereBounds', InBoxSphereBounds=b.fn('/Script/Engine.StaticMesh:GetBounds', self=(cast, cast_out)))
            s_c = b.set('Center', (bnd, 'Origin'))
            cam = b.fn(f'{GS}:GetPlayerCameraManager', PlayerIndex=0)
            pc = b.fn(f'{GS}:GetPlayerController', PlayerIndex=0)
            vs = b.fn(f'{PC_}:GetViewportSize', self=pc)
            tan = b.fn(f'{KML}:DegTan', A=b.fn(f'{KML}:Multiply_DoubleDouble', A=b.fn(f'{PCM}:GetFOVAngle', self=cam), B=0.5))
            # bounds sphere 40% of the visible height at 35 cm: 0.4 * (70 tan(hFOV/2) SizeY/SizeX) / (2 R)
            num = b.fn(f'{KML}:Multiply_DoubleDouble', A=b.fn(f'{KML}:Multiply_DoubleDouble', A=tan, B=b.fn(f'{KML}:Conv_IntToDouble', InInt=(vs, 'SizeY'))), B=14.0)
            den = b.fn(f'{KML}:FMax', A=b.fn(f'{KML}:Multiply_DoubleDouble', A=b.fn(f'{KML}:Conv_IntToDouble', InInt=(vs, 'SizeX')), B=(bnd, 'SphereRadius')), B=1.0)
            s_s = b.set('Scale', b.fn(f'{KML}:Divide_DoubleDouble', A=num, B=den))
            sets = [b.set(v, x) for v, x in (('bOpen', True), ('bClosing', False), ('bDragging', False), ('T', 0.0), ('CloseT', 0.0),
                                             ('Yaw', 35.0), ('Pitch', -15.0), ('VelYaw', 0.0), ('VelPitch', 0.0))]
            s_lr = b.set('LastReal', b.fn(f'{GS}:GetRealTimeSeconds'))
            coll = b.fn(f'{PRIM}:SetCollisionEnabled', self=mesh, NewType='NoCollision')
            hid = b.fn(f'{ACTOR}:SetActorHiddenInGame', bNewHidden=False)
            b.link(pc, 'ReturnValue', cw, 'OwningPlayer')
            s_w = b.set('Widget', (cw, 'ReturnValue'))
            wv = b.get('Widget')
            t1 = b.fn(f'{TB}:SetText', self=b.get('Txt_ItemName', cls=WBPC, target=wv), InText=(brk, name_p))
            t2 = b.fn(f'{TB}:SetText', self=b.get('Txt_ItemLine', cls=WBPC, target=wv), InText=(brk, line_p))
            op0 = b.fn(f'{W}:SetRenderOpacity', self=wv, InOpacity=0.0)
            add = b.fn('/Script/UMG.UserWidget:AddToViewport', self=wv, ZOrder=30)
            pause = b.fn(f'{GS}:SetGamePaused', bPaused=True)
            ein = b.fn(f'{ACTOR}:EnableInput', PlayerController=pc)
            snd = b.fn(f'{GS}:PlaySound2D', Sound=f'{SND}SFX_UI_Open_A.SFX_UI_Open_A', bIsUISound=True)
            first = b.fn(f'{BPC}:TickStep')
            b.chain(e, row)
            b.chain(row, load, cast)
            b.chain(cast, sm, s_c, s_s, *sets, s_lr, coll, hid, cw, s_w, t1, t2, op0, add, pause, ein, snd, first)
            b.run()
        # ---- TickStep: real-time dt, inertia, ease, follow the camera, device hint ----
        if empty(BP, 'TickStep')[2]:
            e, _, _ = entry_of(BP, 'TickStep')
            b = B(BP, 'TickStep')
            br = b.node('branch', {'Condition': b.get('bOpen')})
            now = b.fn(f'{GS}:GetRealTimeSeconds')
            dt = b.fn(f'{KML}:FClamp', Value=b.fn(f'{KML}:Subtract_DoubleDouble', A=now, B=b.get('LastReal')), Min=0.0, Max=0.1)

            def mul(x, y):
                return b.fn(f'{KML}:Multiply_DoubleDouble', A=x, B=y)

            def addf(x, y):
                return b.fn(f'{KML}:Add_DoubleDouble', A=x, B=y)

            def absf(v):
                return b.fn(f'{KML}:Abs', A=v)

            drag = b.fn(f'{KML}:SelectFloat', A=1.0, B=0.0, bPickA=b.get('bDragging'))
            decay = b.fn(f'{KML}:Exp', A=mul(dt, -6.0))
            # a drag moves the facing side with the cursor (0.4 deg per count once the e^-6t tail settles);
            # the stick turns at up to 150 deg/s
            vy = mul(addf(addf(b.get('VelYaw'), mul(mul(b.get('AxisMouseX'), -2.4), drag)), mul(mul(b.get('AxisStickX'), -900.0), dt)), decay)
            vp = mul(addf(addf(b.get('VelPitch'), mul(mul(b.get('AxisMouseY'), -2.4), drag)), mul(mul(b.get('AxisStickY'), -900.0), dt)), decay)
            s_vy, s_vp = b.set('VelYaw', vy), b.set('VelPitch', vp)
            s_yaw = b.set('Yaw', addf(b.get('Yaw'), mul(b.get('VelYaw'), dt)))
            s_pit = b.set('Pitch', b.fn(f'{KML}:FClamp', Value=addf(b.get('Pitch'), mul(b.get('VelPitch'), dt)), Min=-70.0, Max=70.0))
            s_t, s_ct = b.set('T', addf(b.get('T'), dt)), b.set('CloseT', addf(b.get('CloseT'), dt))
            a_in = b.fn(f'{KML}:Ease', A=0.0, B=1.0, Alpha=b.fn(f'{KML}:FClamp', Value=b.fn(f'{KML}:Divide_DoubleDouble', A=b.get('T'), B=0.3), Min=0.0, Max=1.0),
                        EasingFunc='EaseOut', BlendExp=3.0)
            e_out = b.fn(f'{KML}:Ease', A=1.0, B=0.0, Alpha=b.fn(f'{KML}:FClamp', Value=b.fn(f'{KML}:Divide_DoubleDouble', A=b.get('CloseT'), B=0.25), Min=0.0, Max=1.0),
                         EasingFunc='EaseIn', BlendExp=3.0)
            a = b.fn(f'{KML}:FMin', A=a_in, B=b.fn(f'{KML}:SelectFloat', A=e_out, B=1.0, bPickA=b.get('bClosing')))
            cam = b.fn(f'{GS}:GetPlayerCameraManager', PlayerIndex=0)
            mv = b.fn(f'{ACTOR}:K2_SetActorLocationAndRotation', NewLocation=b.fn(f'{PCM}:GetCameraLocation', self=cam),
                      NewRotation=b.fn(f'{PCM}:GetCameraRotation', self=cam), bTeleport=True)
            sc = mul(b.get('Scale'), b.fn(f'{KML}:Lerp', A=0.85, B=1.0, Alpha=a))
            # turntable: yaw about the screen's vertical, then pitch about the screen's horizontal
            rot = b.fn(f'{KML}:ComposeRotators', A=b.fn(f'{KML}:MakeRotator', Roll=0.0, Pitch=0.0, Yaw=b.get('Yaw')),
                       B=b.fn(f'{KML}:MakeRotator', Roll=0.0, Pitch=b.get('Pitch'), Yaw=0.0))
            mesh = b.get('ItemMesh')
            s3 = b.fn(f'{SCENE}:SetRelativeScale3D', self=mesh, NewScale3D=b.fn(f'{KML}:Conv_DoubleToVector', InDouble=sc))
            rr = b.fn(f'{SCENE}:K2_SetRelativeRotation', self=mesh, NewRotation=rot, bTeleport=True)
            # keep the bounds centre (not the pivot) on the 35 cm point
            off = b.fn(f'{KML}:GreaterGreater_VectorRotator', A=b.fn(f'{KML}:Multiply_VectorFloat', A=b.get('Center'), B=sc), B=rot)
            rl = b.fn(f'{SCENE}:K2_SetRelativeLocation', self=mesh,
                      NewLocation=b.fn(f'{KML}:Subtract_VectorVector', A=b.fn(f'{KML}:MakeVector', X=35.0, Y=0.0, Z=0.0), B=off), bTeleport=True)
            pp = b.set('BlendWeight', a, cls='/Script/Engine.PostProcessComponent', target=b.get('PP'))
            wv = b.get('Widget')
            op = b.fn(f'{W}:SetRenderOpacity', self=wv, InOpacity=a)
            pad_now = b.fn(f'{KML}:Greater_DoubleDouble', A=addf(absf(b.get('AxisStickX')), absf(b.get('AxisStickY'))), B=0.15)
            kb_now = b.fn(f'{KML}:BooleanOR', A=b.get('bDragging'),
                          B=b.fn(f'{KML}:Greater_DoubleDouble', A=addf(absf(b.get('AxisMouseX')), absf(b.get('AxisMouseY'))), B=0.5))
            s_pad = b.set('bPad', b.fn(f'{KML}:BooleanAND', A=b.fn(f'{KML}:BooleanOR', A=b.get('bPad'), B=pad_now), B=b.fn(f'{KML}:Not_PreBool', A=kb_now)))
            hint = b.fn(f'{KML}:SelectString', A='Right stick  Rotate      B  Put away', B='Drag  Rotate      E  Put away', bPickA=b.get('bPad'))
            ht = b.fn(f'{TB}:SetText', self=b.get('Txt_Hint', cls=WBPC, target=wv), InText=b.fn(f'{KTXT}:Conv_StringToText', InString=hint))
            s_lr = b.set('LastReal', now)  # last: every dt above reads the old LastReal
            done = b.node('branch', {'Condition': b.fn(f'{KML}:BooleanAND', A=b.get('bClosing'),
                                                       B=b.fn(f'{KML}:GreaterEqual_DoubleDouble', A=b.get('CloseT'), B=0.25))})
            fin = b.fn(f'{BPC}:Finish')
            b.chain(e, br, s_vy, s_vp, s_yaw, s_pit, s_t, s_ct, mv, s3, rr, rl, pp, op, s_pad, ht, s_lr, done, fin)
            b.run()
        # ---- Finish: hand everything back ----
        if empty(BP, 'Finish')[2]:
            e, _, _ = entry_of(BP, 'Finish')
            b = B(BP, 'Finish')
            pc = b.fn(f'{GS}:GetPlayerController', PlayerIndex=0)
            steps = [b.set(v, False) for v in ('bOpen', 'bClosing', 'bDragging')]
            steps += [b.fn(f'{GS}:SetGamePaused', bPaused=False), b.fn(f'{ACTOR}:DisableInput', PlayerController=pc),
                      b.fn(f'{W}:RemoveFromParent', self=b.get('Widget')), b.fn(f'{ACTOR}:SetActorHiddenInGame', bNewHidden=True),
                      b.set('BlendWeight', 0.0, cls='/Script/Engine.PostProcessComponent', target=b.get('PP')),
                      b.fn(f'{SMC}:SetStaticMesh', self=b.get('ItemMesh'))]
            b.chain(e, *steps)
            b.run()
        # ---- Event Tick -> TickStep ----
        nodes, edges = graph(BP, 'EventGraph')
        if not any(n['title'].replace(' ', '').startswith('TickStep') for n in nodes):
            b = B(BP, 'EventGraph')
            b.ops.append(dict(op='add_event', ref='tick', event_name='ReceiveTick'))
            b.refs.add('tick')
            ts = b.fn(f'{BPC}:TickStep')
            b.chain('tick', ts)
            b.execs.discard('tick')
            b.run()
        compile_bp(BP)
        # ---- BPFL: RequestInspect (find or spawn) and IsItemInspecting (for the guards) ----
        if empty(LIB, 'RequestInspect')[2]:
            e, _, _ = entry_of(LIB, 'RequestInspect')
            b = B(LIB, 'RequestInspect')
            act = b.fn(f'{GS}:GetActorOfClass', ActorClass=BPC)
            br = b.node('branch', {'Condition': b.fn(f'{KSL}:IsValid', Object=act)})
            r1 = b.fn(f'{BPC}:Request', self=act, Item=(e, 'Item'))
            sp = b.node('spawn_actor_from_class', {'Class': BPC, 'SpawnTransform': b.fn(f'{KML}:MakeTransform')})
            r2 = b.fn(f'{BPC}:Request', self=sp, Item=(e, 'Item'))
            for n in (act, sp):  # a function library has no self: the caller's world
                b.link(e, '__WorldContext', n, 'WorldContextObject')
            give = b.node('branch', {'Condition': b.fn(f'{KML}:NotEqual_NameName', A=(e, 'Item'), B='None')})
            b.chain(e, give, act, br, r1)
            b.chain((br, 'else'), sp, r2)
            b.run()
        if 'IsItemInspecting' not in hc.call('blueprint_get_info', {'path': LIB})['data']['functions']:
            ok(hc.call('blueprint_add_function', {'path': LIB, 'function_name': 'IsItemInspecting', 'locals': [{'name': 'Result', 'type': 'bool'}],
                                                   'outputs': [{'name': 'bInspecting', 'type': 'bool'}]}), 'IsItemInspecting')
        nodes, edges, e0 = empty(LIB, 'IsItemInspecting')
        if e0:
            e = next(n['node_id'] for n in nodes if n['title'].replace(' ', '') == 'IsItemInspecting')
            ret = next(n['node_id'] for n in nodes if n['title'].startswith('Return'))
            b = B(LIB, 'IsItemInspecting')
            b.refs.add(ret)
            if any(x['from_node'] == e and x['to_node'] == ret for x in edges):
                b.ops.append(dict(op='disconnect', node_id=e, pin_name='then', to_node=ret, to_pin='execute'))
            act = b.fn(f'{GS}:GetActorOfClass', ActorClass=BPC)
            b.link(e, '__WorldContext', act, 'WorldContextObject')
            br = b.node('branch', {'Condition': b.fn(f'{KSL}:IsValid', Object=act)})
            # one Return (Hayba hands back the existing result node); IsInspecting only runs on a live actor (no Accessed None)
            keep = b.set('Result', (b.fn(f'{BPC}:IsInspecting', self=act), 'bInspecting'))
            b.link(*b.get('Result'), ret, 'bInspecting')
            b.chain(e, act, br, keep, ret)
            b.chain((br, 'else'), ret)
            b.run()
        compile_bp(LIB)
        print('graphs2 done')

    def guards():
        """FE.TogglePause, FE.ToggleDebugPanel, FE.OpenPhone: do nothing while an item is up (its keys are consumed too)."""
        FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
        tok = editor_lock.acquire('ui', wait_s=120, ttl=120, areas=[FE])
        try:
            for fn in ('TogglePause', 'ToggleDebugPanel', 'OpenPhone'):
                e, nodes, edges = entry_of(FE, fn)
                if any(n['title'].replace(' ', '').startswith('IsItemInspecting') for n in nodes):
                    print(fn, 'guarded already')
                    continue
                nxt = [x for x in edges if x['from_node'] == e and x['from_pin'] == 'then']
                assert len(nxt) == 1, (fn, nxt)
                b = B(FE, fn)
                b.ops.append(dict(op='disconnect', node_id=e, pin_name='then', to_node=nxt[0]['to_node'], to_pin=nxt[0]['to_pin']))
                gi = b.fn(f'{LIB}.BPFL_ItemInspect_C:IsItemInspecting')
                br = b.node('branch', {'Condition': (gi, 'bInspecting')})
                b.chain(e, gi, br)
                b.link(br, 'else', nxt[0]['to_node'], nxt[0]['to_pin'])
                for o in b.ops:  # park the guard left of the old body
                    if o['op'] == 'add_node':
                        o['x'], o['y'] = -700 + 320 * (o['ref'] == br), -260
                batch(FE, fn, b.ops)
            compile_bp(FE)
            print('FE save', (hc.call('asset_save', {'asset_paths': [FE], 'force': True}).get('data') or {}).get('saved_count'))
        finally:
            if tok:
                hc.release('ui', tok)
                editor_lock.forget('ui', tok)

    def flags():
        """Every key/axis binding runs while paused (Open pauses the game); the input step cannot set it from Python."""
        base = f'{BP}.BP_ItemInspect:EventGraph.'
        n = 0
        for cls in ('K2Node_InputKey', 'K2Node_InputAxisKeyEvent'):
            for i in range(64):
                path = f'{base}{cls}_{i}'
                if not hc.call('object_get_property', {'path': path}).get('ok'):
                    continue
                ok(hc.call('object_set_property', {'path': path, 'properties': {'bExecuteWhenPaused': True, 'bConsumeInput': True,
                                                                                  'bOverrideParentBinding': True}}), path)
                n += 1
        compile_bp(BP)
        print('flags on', n, 'bindings; save', (hc.call('asset_save', {'asset_paths': [BP], 'force': True}).get('data') or {}).get('saved_count'))

    def hook():
        """BP_Interactable.ApplyRow: Inventory.Add(Row.Give) -> BPFL_ItemInspect.RequestInspect(Row.Give) -> the old next."""
        IA = '/Game/FoA/Gameplay/BP_Interactable'
        tok = editor_lock.acquire('ui', wait_s=120, ttl=120, areas=[IA])
        try:
            G = 'CommitInteractionRow'  # Inventory.Add moved here from ApplyRow (story 2026-11-10)
            nodes, edges = graph(IA, G)
            T = {n['node_id']: n['title'] for n in nodes}
            if any(t.replace(' ', '').startswith('RequestInspect') for t in T.values()):
                print('hook already in', G)
                return
            add = [n for n in nodes if n['title'] == 'Add' and any(p['name'] == 'bAdded' for p in n['pins'])]
            assert len(add) == 1, [n['title'] for n in nodes]
            add = add[0]['node_id']
            give = next(e for e in edges if e['to_node'] == add and e['to_pin'] == 'Item')  # Break Row.Give -> Add.Item
            nxt = [e for e in edges if e['from_node'] == add and e['from_pin'] == 'then']
            assert len(nxt) == 1, nxt
            r = hc.call('blueprint_graph_batch', {'path': IA, 'graph_name': G, 'ops': [
                {'op': 'disconnect', 'node_id': add, 'pin_name': 'then', 'to_node': nxt[0]['to_node'], 'to_pin': 'execute'},
                {'op': 'add_node', 'ref': 'ri', 'node_type': 'call_function', 'function_name': f'{LIB}.BPFL_ItemInspect_C:RequestInspect', 'x': 1060, 'y': -200},
                {'op': 'connect', 'from_node': give['from_node'], 'from_pin': give['from_pin'], 'to_node': 'ri', 'to_pin': 'Item'},
                {'op': 'connect', 'from_node': add, 'from_pin': 'then', 'to_node': 'ri', 'to_pin': 'execute'},
                {'op': 'connect', 'from_node': 'ri', 'from_pin': 'then', 'to_node': nxt[0]['to_node'], 'to_pin': 'execute'}]})
            d = r.get('data') or {}
            print('hook', r.get('ok'), d.get('applied'), d.get('failed_index', ''), d.get('error') or r.get('error') or '')
            assert r.get('ok')
            c = hc.call('blueprint_compile', {'path': IA}).get('data') or {}
            assert c.get('compiled') and not c.get('error_count'), c
            print('BP_Interactable compiled', c.get('error_count'), c.get('warning_count'), 'save',
                  (hc.call('asset_save', {'asset_paths': [IA], 'force': True}).get('data') or {}).get('saved_count'))
            nodes, edges = graph(IA, G)
            T = {n['node_id']: n['title'] for n in nodes}
            ri = next(n for n in nodes if n['title'].replace(' ', '').startswith('RequestInspect'))
            print('added node', ri['node_id'], ri['title'], '| exec', [(T[e['from_node']], T[e['to_node']]) for e in edges
                                                                     if ri['node_id'] in (e['from_node'], e['to_node']) and e['to_pin'] == 'execute'])
        finally:
            if tok:
                hc.release('ui', tok)
                editor_lock.forget('ui', tok)

    def finish():
        for path in (BP, LIB, WBP, '/Game/FoA/UI/Framework/BP_FoAFrontEnd', '/Game/FoA/UI/Game/BP_Phone'):
            if hc.call('blueprint_get_info', {'path': path}).get('ok'):
                compile_bp(path)
                print(path.split('/')[-1], 'save', (hc.call('asset_save', {'asset_paths': [path], 'force': True}).get('data') or {}).get('saved_count'))

    assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    token = editor_lock.acquire('ui', wait_s=120, ttl=120, areas=[BP, LIB, WBP])
    try:
        {'assets': assets, 'graphs': graphs, 'graphs2': graphs2, 'flags': flags, 'guards': guards, 'hook': hook, 'finish': finish}[STEP]()
    finally:
        if token:
            hc.release('ui', token)
            editor_lock.forget('ui', token)
