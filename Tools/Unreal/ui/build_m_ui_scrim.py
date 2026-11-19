# RETIRED for graph edits: rebuilding through Python is banned (editor-rules.md). Kept as the record of how the graph was laid out.
"""M_UI_Scrim: left-to-right legibility gradient over the live menu camera (no backdrop textures). Run via ue_remote.py.
Scrim = (AlphaLeft, AlphaRight, RampStartU, RampEndU); colour = MPC_UI.Soot."""
exec(open('P:/FoA/Tools/Unreal/ui/mat_graph.py').read())
AT = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
PATH = '/Game/FoA/UI/Materials/M_UI_Scrim'
mpc = unreal.load_asset('/Game/FoA/UI/Style/MPC_UI')
m = unreal.load_asset(PATH) or AT.create_asset('M_UI_Scrim', '/Game/FoA/UI/Materials', unreal.Material,
                                                unreal.MaterialFactoryNew())
m.set_editor_property('material_domain', unreal.MaterialDomain.MD_UI)
m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
g = MatGraph(PATH).clear()
uv = g.add('MaterialExpressionTextureCoordinate', -896, 0)
u = g.add('MaterialExpressionComponentMask', -704, 0, r=True, g=False, b=False, a=False)
scrim = g.param(unreal.MaterialExpressionVectorParameter, 'Scrim', -896, 160, 'Scrim',
                unreal.LinearColor(0.88, 0.25, 0.0, 0.62), 0, 'R alpha left, G alpha right, B ramp start U, A ramp end U')
ramp = g.add('MaterialExpressionSmoothStep', -512, 64)
alpha = g.add('MaterialExpressionLinearInterpolate', -288, 128)
soot = g.add('MaterialExpressionCollectionParameter', -288, -64, collection=mpc, parameter_name='Soot')
g.link(uv, '', u, '')
g.link(scrim, 'B', ramp, 'Min'); g.link(scrim, 'A', ramp, 'Max'); g.link(u, '', ramp, 'Value')
g.link(scrim, 'R', alpha, 'A'); g.link(scrim, 'G', alpha, 'B'); g.link(ramp, '', alpha, 'Alpha')
g.out(soot, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR); g.out(alpha, '', unreal.MaterialProperty.MP_OPACITY)
g.comment('Ramp along U', 'SmoothStep between two U stops; one packed vector drives every variant', -928, -32, 608, 352, 'shape')
g.comment('Soot from MPC_UI', 'Same black as every other UI surface', -320, -128, 288, 400, 'out')
g.finish()
for name, v in (('MI_UI_Scrim_Menu', (0.88, 0.0, 0.0, 0.62)), ('MI_UI_Scrim_Pause', (0.92, 0.5, 0.0, 0.85)),
                ('MI_UI_Scrim_Dialog', (0.72, 0.72, 0.0, 1.0))):
    p = f'/Game/FoA/UI/Materials/{name}'
    inst = unreal.load_asset(p) or AT.create_asset(name, '/Game/FoA/UI/Materials', unreal.MaterialInstanceConstant,
                                                   unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(inst, m)
    MEL.set_material_instance_vector_parameter_value(inst, 'Scrim', unreal.LinearColor(*v))
    MEL.update_material_instance(inst)
    print(name, EAL.save_asset(p, only_if_is_dirty=False))
