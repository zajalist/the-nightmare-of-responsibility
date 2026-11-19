"""Item inspect fixes for the user's live report (2026-11-10, images/71.png: no 3D key, texts overlapping the prompt
and the narration).

1. root (editor Python, ue_remote FOA_STEP=root): Hayba's blueprint_add_component adds SCS ROOT nodes, so ItemMesh (the
   first one added) became the actor's RootComponent and KeyLight/RimLight hang under it. TickStep then moved the actor to
   the camera and set the ROOT's "relative" transform, which for a root is the world transform: the key went to about
   (35,0,0) in world space (the room's origin), with its lights, and never in front of the camera. Fix: a plain
   SceneComponent 'Root' becomes the scene root; ItemMesh, KeyLight, RimLight and PP hang under it, so the graphs work
   as designed (Root at the camera, ItemMesh 35 cm ahead in camera space, the lights fixed in camera space).
2. hud (Hayba, FOA_STEP=hud): while an item is up the HUD fades out with the panel (HUD render opacity = 1 - a in
   TickStep, back to 1 in Finish), so the interaction prompt and the narration line never sit under the item's name,
   line and hint. Paused timers keep the narration line, which shows again when the panel closes.
  python Tools/Unreal/ue_remote.py Tools/Unreal/ui/item_inspect_fix.py FOA_AREAS=/Game/FoA/UI/Game/BP_ItemInspect FOA_STEP=root
  python Tools/Unreal/ui/item_inspect_fix.py hud
Both idempotent; quiet slot, PIE off."""
import os
import sys

BP = '/Game/FoA/UI/Game/BP_ItemInspect'
BPC = f'{BP}.BP_ItemInspect_C'
FE_C = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
STEP = os.environ.get('FOA_STEP') or (sys.argv[1] if len(sys.argv) > 1 else '')

if STEP == 'root':  # editor Python ------------------------------------------------------------------------------------
    import unreal
    bp = unreal.load_asset(BP)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    data = {str(lib.get_variable_name(lib.get_data(h))): h for h in handles}
    print('components', sorted(data))
    if 'Root' not in data:
        new, why = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=handles[0], new_class=unreal.SceneComponent,
                                                                      blueprint_context=bp))
        assert lib.is_handle_valid(new), why
        sds.rename_subobject(new, unreal.Text('Root'))
        handles = sds.k2_gather_subobject_data_for_blueprint(bp)
        data = {str(lib.get_variable_name(lib.get_data(h))): h for h in handles}
    root = data['Root']
    if not lib.is_root_component(lib.get_data(root)):
        assert sds.make_new_scene_root(handles[0], root, bp), 'make_new_scene_root'
    for name in ('ItemMesh', 'KeyLight', 'RimLight', 'PP'):
        sds.attach_subobject(root, data[name])
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    for h in handles:
        d = lib.get_data(h)
        print('SCS', lib.get_variable_name(d), 'root' if lib.is_root_component(d) else '')
    cdo = unreal.get_default_object(unreal.load_class(None, BPC))
    rc = cdo.get_editor_property('root_component')
    assert rc and rc.get_name().startswith('Root'), rc
    print('root is', rc.get_name(), '| saved', unreal.EditorAssetLibrary.save_loaded_asset(bp, False))

elif STEP == 'hud':  # Hayba ---------------------------------------------------------------------------------------------
    sys.path.insert(0, 'P:/FoA/Tools/Unreal')
    sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
    import editor_lock  # noqa: E402
    import hayba_call as hc  # noqa: E402
    from hayba_batch import B, compile_bp, graph, ok, save  # noqa: E402
    KML, KSL, GS, W = '/Script/Engine.KismetMathLibrary', '/Script/Engine.KismetSystemLibrary', '/Script/Engine.GameplayStatics', '/Script/UMG.Widget'

    def node(ns, title):
        hits = [n['node_id'] for n in ns if n['title'].replace('\n', ' ') == title]
        assert len(hits) == 1, (title, len(hits))
        return hits[0]

    def insert(g, before_title, after_title, build):
        """Cut the exec link before -> after and put build(b) (a list of exec refs) between them."""
        ns, es = graph(BP, g)
        if any(n['title'].replace('\n', ' ') in ('Get HudRef', 'Set HudRef') for n in ns):
            print(g, 'already has the HUD fade')
            return
        a, z = node(ns, before_title), node(ns, after_title)
        assert any(e['from_node'] == a and e['to_node'] == z and e['to_pin'] == 'execute' for e in es), (g, before_title, after_title)
        b = B(BP, g)
        b.ops.append(dict(op='disconnect', node_id=a, pin_name='then', to_node=z, to_pin='execute'))
        b.refs |= {a, z}
        steps, also = build(b, ns)  # also: extra exec outs (a branch's False) that rejoin at `after`
        b.chain(a, *steps, z)
        for ref, pin in also:
            b.link(ref, pin, z, 'execute')
        b.run()

    assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    tok = editor_lock.acquire('ui', wait_s=120, ttl=120, areas=[BP])
    try:
        ok(hc.call('blueprint_add_variable', {'path': BP, 'variable_name': 'HudRef', 'variable_type': 'object:/Script/UMG.UserWidget',
                                              'category': 'Inspect', 'update_existing': True}), 'HudRef')
        compile_bp(BP)

        # GetActorOfClass can be None (no front end): read HUD only through a valid check
        def open_hud_guarded(b, ns):
            fe = b.fn(f'{GS}:GetActorOfClass', ActorClass=FE_C)
            br = b.node('branch', {'Condition': b.fn(f'{KSL}:IsValid', Object=fe)})
            keep = b.set('HudRef', b.get('HUD', cls=FE_C, target=fe))
            return [fe, br, keep], [(br, 'else')]
        insert('Open', 'EnableInput', 'PlaySound2D', open_hud_guarded)

        def tick_hud(b, ns):  # HUD opacity follows the panel: 1 - a (a = the Min (Float) ease value)
            a = node(ns, 'Min (Float)')
            b.refs.add(a)
            br = b.node('branch', {'Condition': b.fn(f'{KSL}:IsValid', Object=b.get('HudRef'))})
            op = b.fn(f'{W}:SetRenderOpacity', self=b.get('HudRef'), InOpacity=b.fn(f'{KML}:Subtract_DoubleDouble', A=1.0, B=(a, 'ReturnValue')))
            return [br, op], [(br, 'else')]
        insert('TickStep', 'SetText (Text)', 'Set LastReal', tick_hud)

        ns, es = graph(BP, 'Finish')
        if not any(n['title'].replace('\n', ' ') == 'Get HudRef' for n in ns):
            tail = node(ns, 'SetStaticMesh')
            b = B(BP, 'Finish')
            b.refs.add(tail)
            br = b.node('branch', {'Condition': b.fn(f'{KSL}:IsValid', Object=b.get('HudRef'))})
            b.chain(tail, br, b.fn(f'{W}:SetRenderOpacity', self=b.get('HudRef'), InOpacity=1.0))
            b.run()
        compile_bp(BP)
        print('BP_ItemInspect save', save(BP))
    finally:
        if tok:
            hc.release('ui', tok)
            editor_lock.forget('ui', tok)
