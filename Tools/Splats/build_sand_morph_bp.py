"""BP_SandMorph: a station where sand keeps materializing one object after another (make_sand_morph.py, MF_SplatMorph).
No Tick and no dynamic material: each step writes SandEvent = (from row, to row, now, MorphSeconds) to the splat
component's custom primitive data and M_SplatMesh's morph does the rest. Stations advance on a looping timer, staggered
by StartDelay, and skip a step while off-screen (WasRecentlyRendered), so nothing animates unseen.
  python Tools/Unreal/ue_remote.py Tools/Splats/build_sand_morph_bp.py FOA_MORPH_BP=assets   -> Hayba blueprint_compile
  python Tools/Unreal/ue_remote.py Tools/Splats/build_sand_morph_bp.py FOA_MORPH_BP=graphs   -> Hayba compile + asset_save
API: BP_SandMorph.MorphTo(ObjectId)  (row 0 = the sand, 1.. = the station's objects; BPL_SandFX.MorphTo wraps it)."""
import os

exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py').read())  # noqa: S102  house graph helpers
import unreal  # noqa: E402

D = '/Game/FoA/VFX/Sand'
MORPH = f'{D}/BP_SandMorph'
PRIM = '/Script/Engine.PrimitiveComponent'
ACTOR = '/Script/Engine.Actor'
COL.update({'sand': unreal.LinearColor(0.30, 0.22, 0.10, 1), 'pool': unreal.LinearColor(0.12, 0.26, 0.16, 1)})
phase = os.environ.get('FOA_MORPH_BP', 'assets')


def box(g, title, nodes, kind):  # the user's rule: comment boxes carry a short title only
    c = g.ed.add_comment_to_nodes(title, list(nodes), 40)
    BEL.set_comment_color(c, COL[kind])
    for prop, v in (("font_size", 18), ("comment_bubble_visible_in_details_panel", True), ("color_comment_bubble", True)):
        c.set_editor_property(prop, v)
    return c


def assets():
    T = ptype
    bp = unreal.load_asset(MORPH)
    if not bp:
        fac = unreal.BlueprintFactory()
        fac.set_editor_property('parent_class', unreal.Actor)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_SandMorph', D, unreal.Blueprint, fac)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    by = {str(lib.get_variable_name(lib.get_data(h))): h for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
    if 'Splats' not in by:
        root = by.get('DefaultSceneRoot') or sds.k2_gather_subobject_data_for_blueprint(bp)[0]
        h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.StaticMeshComponent,
                                                                     blueprint_context=bp))
        assert not str(fail), fail
        sds.rename_subobject(h, 'Splats')
        by['Splats'] = h
    t = lib.get_object(lib.get_data(by['Splats']))
    for prop, v in (('cast_shadow', False), ('render_custom_depth', True), ('custom_depth_stencil_value', 5)):
        t.set_editor_property(prop, v)
    t.set_collision_profile_name('NoCollision')
    lc = t.get_editor_property('lighting_channels')
    lc.set_editor_property('channel0', True)
    lc.set_editor_property('channel2', True)
    t.set_editor_property('lighting_channels', lc)
    ed = GE.get_graph_editor_by_name(bp, 'EventGraph')
    have = [str(n) for n in BEL.list_member_variable_names(bp)]
    for name, typ, val, editable in (('Rows', T('int'), '6', True), ('Current', T('int'), '0', False),
                                     ('Hold', T('real'), '6.0', True), ('MorphSeconds', T('real'), '4.0', True),
                                     ('StartDelay', T('real'), '0.0', True)):
        if name not in have:
            assert ed.add_member_variable(name, typ, val), name
        BEL.set_blueprint_variable_category(bp, name, 'Sand')
        BEL.set_blueprint_variable_instance_editable(bp, name, editable)
    for f, ins in (('MorphTo', [('ObjectId', T('int'))]), ('Step', [])):
        drop_function(MORPH, f)
        Graph.function(MORPH, f, inputs=ins)
    print('assets ok: Hayba blueprint_compile', MORPH)


def graphs():
    T = ptype
    # MorphTo: SandEvent = (Current, ObjectId, now, MorphSeconds); Current = ObjectId
    g = Graph.function(MORPH, 'MorphTo', inputs=[('ObjectId', T('int'))])
    e = g.at(entry_node(g), 0, 0)
    ev = fcall(g, f'{KML}:MakeVector4', 320, 200,
               X=fcall(g, f'{KML}:Conv_IntToDouble', 100, 160, InInt=mget(g, 'Current', -100, 160)),
               Y=fcall(g, f'{KML}:Conv_IntToDouble', 100, 260, InInt=po(e, 'ObjectId')),
               Z=fcall(g, f'{GS}:GetTimeSeconds', 100, 360), W=mget(g, 'MorphSeconds', 100, 440))
    s = fcall(g, f'{PRIM}:SetVectorParameterForCustomPrimitiveData', 620, 0, self=mget(g, 'Splats', 400, 420),
              ParameterName='SandEvent', Value=ev)
    c = mset(g, 'Current', 940, 0, po(e, 'ObjectId'))
    chain(e, s, c)
    box(g, 'Morph to object', [e, ev, s, c], 'sand')
    # Step: on-screen only, the next row of the chain (after the last object, back to the sand)
    g = Graph.function(MORPH, 'Step')
    e = g.at(entry_node(g), 0, 0)
    seen = fcall(g, f'{ACTOR}:WasRecentlyRendered', 240, 160, Tolerance=0.5)
    br = g.branch(520, 0)
    feed(br, Condition=po(seen, 'ReturnValue'))
    nxt = fcall(g, f'{KML}:Percent_IntInt', 560, 260, A=fcall(g, f'{KML}:Add_IntInt', 380, 260, A=mget(g, 'Current', 200, 260), B=1),
                B=mget(g, 'Rows', 380, 340))
    mt = fcall(g, self_call(MORPH, 'MorphTo'), 820, 0, ObjectId=nxt)
    seq(e, seen, br)
    go(br, mt)
    box(g, 'Next object on screen', [e, seen, br, nxt, mt], 'pool')
    # BeginPlay: rest on the sand row, then a looping Step timer every Hold + MorphSeconds, staggered by StartDelay
    eg = Graph(MORPH, 'EventGraph')
    bp = unreal.load_asset(MORPH)
    old = [n for n in eg.ed.list_all_nodes() if 'ReceiveBeginPlay' in str(n.get_name()) or 'K2_SetTimer' in BEL.get_node_title(n)]
    begin = next((n for n in eg.ed.list_nodes_of_class(unreal.K2Node_Event) if 'BeginPlay' in BEL.get_node_title(n)), None)
    begin = begin or eg.at(BEL.add_event_override(bp, 'ReceiveBeginPlay', unreal.IntPoint(0, 0)), 0, 0)
    rest = fcall(eg, f'{PRIM}:SetVectorParameterForCustomPrimitiveData', 300, 0, self=mget(eg, 'Splats', 80, 200),
                 ParameterName='SandEvent', Value=fcall(eg, f'{KML}:MakeVector4', 80, 300, X=0.0, Y=0.0, Z=0.0, W=0.0))
    tm = fcall(eg, f'{KSL}:K2_SetTimer', 640, 0, FunctionName='Step', bLooping='true',
               Time=fcall(eg, f'{KML}:Add_DoubleDouble', 440, 260, A=mget(eg, 'Hold', 260, 260), B=mget(eg, 'MorphSeconds', 260, 340)),
               InitialStartDelay=mget(eg, 'StartDelay', 440, 380))
    chain(begin, rest, tm)
    box(eg, 'Station cycle', [begin, rest, tm], 'pool')
    print('graphs ok: Hayba blueprint_compile + asset_save', MORPH, '(BeginPlay rebuilt:', len(old), 'old nodes seen)')


assets() if phase == 'assets' else graphs()
