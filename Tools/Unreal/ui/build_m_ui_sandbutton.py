# RETIRED for graph edits: rebuilding through Python is banned (editor-rules.md). Kept as the record of how the graph was laid out.
"""M_UI_SandButton (User Interface domain) + MPC_UI + the three variant instances. Run via ue_remote.py.
Parameters are packed into vectors so WBP_SandButton updates its state with ONE SetVectorParameterValue per tick:
  State  = (Hover, PressPhase 0-1, Disabled, FlowPhase)   driven by WBP_SandButton
  Shape  = (SlabTopV, SlabBottomV, EdgeSoftV, RimWidthV)  UV rows of the slab; image extends below for drips
  Look   = (SlabOpacity, GrainAmount, RimIntensity, Seed)
  Tiling = (WidthPx / 256, HeightPx / 256)                 1 noise texel per screen px"""
exec(open('P:/FoA/Tools/Unreal/ui/mat_graph.py').read())
AT = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
V = unreal.MaterialExpressionVectorParameter
MP = unreal.MaterialProperty

# ---- MPC_UI: one global accessibility switch every UI material reads
MPC_PATH = '/Game/FoA/UI/Style/MPC_UI'
mpc = unreal.load_asset(MPC_PATH) or AT.create_asset('MPC_UI', '/Game/FoA/UI/Style', unreal.MaterialParameterCollection,
                                                    unreal.MaterialParameterCollectionFactoryNew())
sp = unreal.CollectionScalarParameter()
sp.set_editor_property('parameter_name', 'ReduceMotion')
sp.set_editor_property('default_value', 0.0)
mpc.set_editor_property('scalar_parameters', [sp])
vps = []
for vname, col in (('Ink', (0.86, 0.86, 0.86, 1)), ('Soot', (0.004, 0.004, 0.004, 1)), ('Panel', (0.012, 0.012, 0.012, 1))):
    vp = unreal.CollectionVectorParameter()  # palette shared by every UI material (matches F_FoA_Typography INK)
    vp.set_editor_property('parameter_name', vname)
    vp.set_editor_property('default_value', unreal.LinearColor(*col))
    vps.append(vp)
mpc.set_editor_property('vector_parameters', vps)
EAL.save_loaded_asset(mpc, False)

# ---- Master material
PATH = '/Game/FoA/UI/Materials/M_UI_SandButton'
m = unreal.load_asset(PATH) or AT.create_asset('M_UI_SandButton', '/Game/FoA/UI/Materials', unreal.Material,
                                                unreal.MaterialFactoryNew())
m.set_editor_property('material_domain', unreal.MaterialDomain.MD_UI)
m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
g = MatGraph(PATH).clear()

# Inputs (x -1900)
state = g.param(V, 'State', -1888, -96, 'State (WBP_SandButton)', unreal.LinearColor(0, 0, 0, 0), 0,
                'R Hover, G PressPhase, B Disabled, A FlowPhase')
shape = g.param(V, 'Shape', -1888, 160, 'Shape', unreal.LinearColor(0.0, 0.7, 0.0125, 0.025), 1,
                'R SlabTopV, G SlabBottomV, B EdgeSoftV, A RimWidthV')
look = g.param(V, 'Look', -1888, 416, 'Look', unreal.LinearColor(0.88, 0.25, 0.35, 0.0), 2,
               'R SlabOpacity, G GrainAmount, B RimIntensity, A Seed')
surface = g.param(V, 'Surface', -1888, 672, 'Shape', unreal.LinearColor(1.406, 0.3125, 0, 0), 3,
                  'RG = widget px / 256 (incl. drip area), B = slab ink (0 panel, 1 ink line)')
tiling = g.add('MaterialExpressionComponentMask', -1664, 672, r=True, g=True, b=False, a=False)
ink = g.add('MaterialExpressionCollectionParameter', -1888, 928, collection=mpc, parameter_name='Ink')
panel = g.add('MaterialExpressionCollectionParameter', -1888, 1056, collection=mpc, parameter_name='Panel')
slab_col = g.add('MaterialExpressionLinearInterpolate', -1664, 992)
g.link(surface, '', tiling, ''); g.link(panel, '', slab_col, 'A'); g.link(ink, '', slab_col, 'B')
g.link(surface, 'B', slab_col, 'Alpha')
sand_col = ink
uv = g.add('MaterialExpressionTextureCoordinate', -1888, -288)
rm = g.add('MaterialExpressionCollectionParameter', -1888, -416, collection=mpc, parameter_name='ReduceMotion')

# Accessibility gate (x -1600): ReduceMotion freezes flow, drips and the press dissolve
calm = g.add('MaterialExpressionOneMinus', -1600, -416)
phase = g.add('MaterialExpressionMultiply', -1600, -288)          # FlowPhase x calm
g.link(rm, '', calm, ''); g.link(state, 'A', phase, 'A'); g.link(calm, '', phase, 'B')

# Shape (x -1600 .. -800): slab rows, rim at the top edge, drip zone below
vrow = g.add('MaterialExpressionComponentMask', -1600, -96, r=False, g=True, b=False, a=False)
d_top = g.add('MaterialExpressionSubtract', -1408, -96)           # V - Top
d_bot = g.add('MaterialExpressionSubtract', -1408, 32)            # Bottom - V
in_top = g.add('MaterialExpressionDivide', -1232, -96)
in_bot = g.add('MaterialExpressionDivide', -1232, 32)
s_top = g.add('MaterialExpressionSaturate', -1088, -96)
s_bot = g.add('MaterialExpressionSaturate', -1088, 32)
slab = g.add('MaterialExpressionMultiply', -944, -32)
rim_abs = g.add('MaterialExpressionAbs', -1232, 160)
rim_div = g.add('MaterialExpressionDivide', -1088, 160)
rim = g.add('MaterialExpressionOneMinus', -944, 160)
rim_sat = g.add('MaterialExpressionSaturate', -816, 160)
below = g.add('MaterialExpressionOneMinus', -944, 288)            # 1 under the slab
v_inv = g.add('MaterialExpressionOneMinus', -1232, 384)           # fades to 0 at the image bottom
drip_zone = g.add('MaterialExpressionMultiply', -816, 320)
g.link(uv, '', vrow, '')
g.link(vrow, '', d_top, 'A'); g.link(shape, 'R', d_top, 'B')
g.link(shape, 'G', d_bot, 'A'); g.link(vrow, '', d_bot, 'B')
g.link(d_top, '', in_top, 'A'); g.link(shape, 'B', in_top, 'B')
g.link(d_bot, '', in_bot, 'A'); g.link(shape, 'B', in_bot, 'B')
g.link(in_top, '', s_top, ''); g.link(in_bot, '', s_bot, '')
g.link(s_top, '', slab, 'A'); g.link(s_bot, '', slab, 'B')
g.link(d_top, '', rim_abs, ''); g.link(rim_abs, '', rim_div, 'A'); g.link(shape, 'A', rim_div, 'B')
g.link(rim_div, '', rim, ''); g.link(rim, '', rim_sat, '')
g.link(s_bot, '', below, ''); g.link(vrow, '', v_inv, '')
g.link(below, '', drip_zone, 'A'); g.link(v_inv, '', drip_zone, 'B')

# Sand (x -1600, y 640+): noise + flow in MF_UI_SandFlow, press dissolve in MF_UI_SandDissolve
flow = g.call('/Game/FoA/UI/Materials/Functions/MF_UI_SandFlow', -1408, 640)
press_inv = g.add('MaterialExpressionOneMinus', -1600, 896)
press_bell = g.add('MaterialExpressionMultiply', -1408, 896)      # p(1-p): 0 -> peak -> 0 over the press
press_amt = g.add('MaterialExpressionMultiply', -1232, 896, const_b=2.8)
press_calm = g.add('MaterialExpressionMultiply', -1088, 896)
edge_w = g.add('MaterialExpressionConstant', -1088, 1024, r=0.12)
diss = g.call('/Game/FoA/UI/Materials/Functions/MF_UI_SandDissolve', -944, 896)
g.link(uv, '', flow, 'UV'); g.link(tiling, '', flow, 'Tiling'); g.link(look, 'A', flow, 'Seed')
g.link(phase, '', flow, 'Phase')
g.link(state, 'G', press_inv, ''); g.link(state, 'G', press_bell, 'A'); g.link(press_inv, '', press_bell, 'B')
g.link(press_bell, '', press_amt, 'A'); g.link(press_amt, '', press_calm, 'A'); g.link(calm, '', press_calm, 'B')
g.link(flow, 'Dissolve', diss, 'Noise'); g.link(press_calm, '', diss, 'Amount'); g.link(edge_w, '', diss, 'Edge')

# Compose (x -640 .. 0): sand alpha = slab grain + hover rim + hover drips; colour lerps slab -> sand
grain_slab = g.add('MaterialExpressionMultiply', -640, -32)       # slab x grain
grain_amt = g.add('MaterialExpressionMultiply', -496, -32)        # x GrainAmount
rim_gain = g.add('MaterialExpressionLinearInterpolate', -640, 160, const_a=0.35, const_b=1.0)
rim_i = g.add('MaterialExpressionMultiply', -496, 128)            # rim x RimIntensity
rim_h = g.add('MaterialExpressionMultiply', -352, 160)            # x hover gain
drip = g.add('MaterialExpressionMultiply', -640, 352)             # zone x streaks
drip_h = g.add('MaterialExpressionMultiply', -496, 352)           # x Hover x calm
hover_calm = g.add('MaterialExpressionMultiply', -640, 480, const_b=3.0)
sand_a = g.add('MaterialExpressionAdd', -352, 32)
sand_b = g.add('MaterialExpressionAdd', -224, 128)
slab_a = g.add('MaterialExpressionMultiply', -496, -192)          # slab x SlabOpacity
alpha = g.add('MaterialExpressionAdd', -96, -96)
alpha_sat = g.add('MaterialExpressionSaturate', 32, -96)
alpha_diss = g.add('MaterialExpressionMultiply', 160, -64)
dim = g.add('MaterialExpressionLinearInterpolate', 160, 64, const_a=1.0, const_b=0.4)
opacity = g.add('MaterialExpressionMultiply', 304, -32)
tint_t = g.add('MaterialExpressionAdd', -96, 256)                 # sand + glint
tint_sat = g.add('MaterialExpressionSaturate', 32, 256)
color = g.add('MaterialExpressionLinearInterpolate', 304, 256)
g.link(slab, '', grain_slab, 'A'); g.link(flow, 'Grain', grain_slab, 'B')
g.link(grain_slab, '', grain_amt, 'A'); g.link(look, 'G', grain_amt, 'B')
g.link(state, 'R', rim_gain, 'Alpha')
g.link(rim_sat, '', rim_i, 'A'); g.link(look, 'B', rim_i, 'B')
g.link(rim_i, '', rim_h, 'A'); g.link(rim_gain, '', rim_h, 'B')
g.link(drip_zone, '', drip, 'A'); g.link(flow, 'Drip', drip, 'B')
g.link(state, 'R', hover_calm, 'A')
g.link(drip, '', drip_h, 'A'); g.link(hover_calm, '', drip_h, 'B')
g.link(grain_amt, '', sand_a, 'A'); g.link(rim_h, '', sand_a, 'B')
g.link(sand_a, '', sand_b, 'A'); g.link(drip_h, '', sand_b, 'B')
g.link(slab, '', slab_a, 'A'); g.link(look, 'R', slab_a, 'B')
g.link(slab_a, '', alpha, 'A'); g.link(sand_b, '', alpha, 'B')
g.link(alpha, '', alpha_sat, ''); g.link(alpha_sat, '', alpha_diss, 'A'); g.link(diss, 'Opacity', alpha_diss, 'B')
g.link(state, 'B', dim, 'Alpha')
g.link(alpha_diss, '', opacity, 'A'); g.link(dim, '', opacity, 'B')
g.link(sand_b, '', tint_t, 'A'); g.link(diss, 'Edge', tint_t, 'B'); g.link(tint_t, '', tint_sat, '')
g.link(slab_col, '', color, 'A'); g.link(sand_col, '', color, 'B'); g.link(tint_sat, '', color, 'Alpha')
g.out(color, '', MP.MP_EMISSIVE_COLOR); g.out(opacity, '', MP.MP_OPACITY)

g.comment('Inputs', 'Packed vector params (State set once per tick); colours from MPC_UI', -1920, -480, 448, 1664, 'input')
g.comment('Reduce motion', 'MPC_UI.ReduceMotion freezes flow, drips and dissolve', -1616, -480, 160, 304, 'input')
g.comment('Shape: slab rows, top rim, drip zone',
          'Measured in UV rows from Shape; the image extends below the button so drips have room',
          -1616, -160, 928, 640, 'shape')
g.comment('Sand flow and press dissolve',
          'Noise/flow live in MF_UI_SandFlow; press bell 4p(1-p) dissolves and reforms in 0.6 s',
          -1616, 576, 928, 576, 'noise')
g.comment('Compose alpha and colour',
          'Rest: dark slab + faint grain. Hover: rim + drips. Press: glinting dissolve. Disabled: 40%',
          -656, -256, 1104, 864, 'fx')
g.finish()

# ---- Variants (MIs). Image = 360 x 80 px: 56 px button + 24 px drip room below.
def mi(name, shape_v, look_v, slab_ink, seed):
    p = f'/Game/FoA/UI/Materials/{name}'
    inst = unreal.load_asset(p) or AT.create_asset(name, '/Game/FoA/UI/Materials', unreal.MaterialInstanceConstant,
                                                   unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(inst, m)
    MEL.set_material_instance_vector_parameter_value(inst, 'Shape', unreal.LinearColor(*shape_v))
    MEL.set_material_instance_vector_parameter_value(inst, 'Look', unreal.LinearColor(*look_v[:3], seed))
    MEL.set_material_instance_vector_parameter_value(inst, 'Surface', unreal.LinearColor(1.406, 0.3125, slab_ink, 0))
    MEL.update_material_instance(inst)
    EAL.save_loaded_asset(inst, False)
    print('MI', p)


mi('MI_UI_SandButton_Primary', (0.0, 0.7, 0.0125, 0.025), (0.9, 0.12, 0.35), 0.0, 0.0)
mi('MI_UI_SandButton_Secondary', (0.675, 0.7, 0.0125, 0.025), (0.35, 0.6, 0.6), 1.0, 0.37)
mi('MI_UI_SandButton_Quiet', (0.675, 0.7, 0.0125, 0.025), (0.0, 0.0, 0.5), 1.0, 0.71)
