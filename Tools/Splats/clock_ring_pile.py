"""BP_SandMaterialize: the alarm's ring judder and the persistent crumble pile (user feedback on LS_WakeUp's clock).
  Ring (float 0..1, Expose to Cinematics): every tick the Splats component sits at a ~2 mm high-frequency shake, small
  hops off its base and a few degrees of yaw, all scaled by Ring (0 = still). Sequencer keys it; ticks run in PIE and
  MRQ renders, not while scrubbing in the editor.
  Pile: a black-sand mound on the base (SM_SandMound_A, MI_SandSpill_Mound), hidden at DissolveAmount 0.
  SetDissolveAmount grows it with the crumble (0.25 -> 0.9 maps to 5% -> 100%), so the keyed 0 -> 1 leaves a pile on
  the nightstand that stays into gameplay (Keep State); the next morning's DissolveAmount 0 clears it.
Idempotent: adds only what is missing (markers: the SetRelativeLocationAndRotation / SetRelativeScale3D calls, the Pile component).
  $env:FOA_AREAS='VFX'; python Tools/Unreal/ue_remote.py Tools/Splats/clock_ring_pile.py
  -> Hayba blueprint_compile + save /Game/FoA/VFX/Sand/BP_SandMaterialize"""
exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py').read())  # noqa: S102  house graph helpers
import unreal  # noqa: E402

COL.update({'sand': unreal.LinearColor(0.30, 0.22, 0.10, 1)})

MAT = '/Game/FoA/VFX/Sand/BP_SandMaterialize'
SCENE = '/Script/Engine.SceneComponent'
PILE = (0.375, 0.375, 0.46)   # relative to the actor's 0.36: a ~13.5 cm wide, ~4 cm high mound (SM_SandMound_A is R 50, H 24)


def calls_named(g, name):
    return [n for n in g.ed.list_nodes_of_class(unreal.K2Node_CallFunction) if name in str(BEL.get_node_title(n)).replace(' ', '')]


def pile_component(bp):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    by_name = {str(lib.get_variable_name(lib.get_data(h))): h for h in handles}
    if 'Pile' not in by_name:
        root = by_name.get('DefaultSceneRoot') or handles[0]
        h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.StaticMeshComponent,
                                                                     blueprint_context=bp))
        assert not str(fail), fail
        sds.rename_subobject(h, 'Pile')
        by_name['Pile'] = h
    t = lib.get_object(lib.get_data(by_name['Pile']))
    t.set_editor_property('static_mesh', unreal.load_asset('/Game/FoA/Procedural/SM_SandMound_A/SM_SandMound_A/StaticMeshes/SM_SandMound_A'))
    t.set_editor_property('override_materials', [unreal.load_asset('/Game/FoA/VFX/Sand/MI_SandSpill_Mound')])
    t.set_editor_property('relative_scale3d', unreal.Vector(*PILE))
    t.set_editor_property('visible', False)
    t.set_editor_property('render_custom_depth', True)        # stencil 5: the post's sand passes treat it as sand
    t.set_editor_property('custom_depth_stencil_value', 5)
    t.set_collision_profile_name('NoCollision')


def ring_tick():
    g = Graph(MAT)
    done = calls_named(g, 'SetRelativeLocationAndRotation')
    if done:   # built already (an earlier run may have stopped before its comment)
        if not list(g.ed.list_comment_nodes()):
            box(g, 'Ring judder', '', done, 'sand')
        return
    ev = next((n for n in g.ed.list_nodes_of_class(unreal.K2Node_Event) if 'Tick' in str(BEL.get_node_title(n))), None) \
        or g.event('ReceiveTick', 0, 600)
    g.at(ev, 0, 600)
    t = fcall(g, f'{GS}:GetTimeSeconds', 0, 760)
    r = g.get('Ring', 0, 880)
    def wave(fn, k, x, y):  # noqa: E306  sin/cos(t * k)
        return fcall(g, f'{KML}:{fn}', x + 220, y, A=fcall(g, f'{KML}:Multiply_DoubleDouble', x, y, A=po(t), B=k))
    sx, cy = wave('Sin', 91.0, 260, 740), wave('Cos', 77.0, 260, 860)
    hop = fcall(g, f'{KML}:MultiplyMultiply_FloatFloat', 700, 980, Base=fcall(g, f'{KML}:FMax', 480, 980, A=wave('Sin', 9.3, 40, 980), B=0.0),
                Exp=8.0)                                                   # rare, short lifts off the base
    loc = fcall(g, f'{KML}:Multiply_VectorFloat', 1180, 760, B=po(r),
                A=fcall(g, f'{KML}:MakeVector', 940, 760, X=fcall(g, f'{KML}:Multiply_DoubleDouble', 720, 740, A=po(sx), B=0.6),
                        Y=fcall(g, f'{KML}:Multiply_DoubleDouble', 720, 860, A=po(cy), B=0.6),
                        Z=fcall(g, f'{KML}:Multiply_DoubleDouble', 940, 980, A=po(hop), B=1.5)))
    yaw = fcall(g, f'{KML}:Multiply_DoubleDouble', 1180, 1100, A=wave('Sin', 53.0, 700, 1100),
                B=fcall(g, f'{KML}:Multiply_DoubleDouble', 940, 1180, A=po(r), B=2.5))
    rot = fcall(g, f'{KML}:MakeRotator', 1400, 1060, Yaw=po(yaw))
    s = fcall(g, f'{SCENE}:K2_SetRelativeLocationAndRotation', 1640, 600, self=g.get('Splats', 1400, 680),
              NewLocation=po(loc), NewRotation=po(rot))
    go(ev, s)
    box(g, 'Ring judder', '', [ev, t, r, sx, cy, hop, loc, yaw, rot, s], 'sand')


def crumble_pile():
    g = Graph(MAT, 'SetDissolveAmount')
    if calls_named(g, 'SetRelativeScale3D'):
        return
    last = next(n for n in g.ed.list_nodes_of_class(unreal.K2Node_CallFunction)
                if 'CustomPrimitiveData' in str(BEL.get_node_title(n)).replace(' ', ''))
    e = entry_node(g)
    k = fcall(g, f'{KML}:MapRangeClamped', 860, 260, Value=po(e, 'NewValue'), InRangeA=0.25, InRangeB=0.9, OutRangeA=0.05, OutRangeB=1.0)
    sc = fcall(g, f'{SCENE}:SetRelativeScale3D', 1300, 0, self=g.get('Pile', 1060, 140),
               NewScale3D=fcall(g, f'{KML}:Multiply_VectorFloat', 1100, 300, A=fcall(g, f'{KML}:MakeVector', 860, 420, X=PILE[0], Y=PILE[1], Z=PILE[2]),
                                B=po(k)))
    vis = fcall(g, f'{SCENE}:SetVisibility', 1600, 0, self=g.get('Pile', 1360, 140),
                bNewVisibility=fcall(g, f'{KML}:Greater_DoubleDouble', 1360, 260, A=po(e, 'NewValue'), B=0.2))
    chain(last, sc, vis)
    box(g, 'Crumble pile', '', [k, sc, vis], 'sand')


def run():
    bp = unreal.load_asset(MAT)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    ensure_vars(MAT, [('Ring', ptype('real'), '0.0', 'Sand', True)])
    BEL.set_blueprint_variable_expose_to_cinematics(unreal.load_asset(MAT), 'Ring', True)
    pile_component(unreal.load_asset(MAT))
    ring_tick()
    crumble_pile()
    print('clock ring + pile ok; Hayba compile + save', MAT)


run()
