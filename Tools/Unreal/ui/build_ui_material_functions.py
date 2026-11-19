# RETIRED for graph edits: rebuilding through Python is banned (editor-rules.md). Kept as the record of how the graph was laid out.
"""Builds the two UI sand material functions (lean, commented). Run via Tools/Unreal/ue_remote.py.
MF_UI_SandFlow    : noise pack sampled twice (stream right + fall down) -> Grain (R), Dissolve (B), Drip (A)
MF_UI_SandDissolve: threshold dissolve + bright break-away edge; shared by M_UI_SandButton and M_UI_SandWipe"""
exec(open('P:/FoA/Tools/Unreal/ui/mat_graph.py').read())
FIT = unreal.FunctionInputType
NOISE = unreal.load_asset('/Game/FoA/UI/Textures/T_UI_SandNoise')


def fin(g, name, kind, x, y, prio, desc):
    return g.add("MaterialExpressionFunctionInput", x, y, input_name=name, input_type=kind, sort_priority=prio,
                 description=desc)


def fout(g, name, x, y, prio, desc):
    return g.add("MaterialExpressionFunctionOutput", x, y, output_name=name, sort_priority=prio, description=desc)


# ---------------------------------------------------------------- MF_UI_SandFlow
g = MatGraph('/Game/FoA/UI/Materials/Functions/MF_UI_SandFlow', function=True).clear()
uv = fin(g, "UV", FIT.FUNCTION_INPUT_VECTOR2, -1088, 0, 0, "Widget UV (TexCoord 0)")
til = fin(g, "Tiling", FIT.FUNCTION_INPUT_VECTOR2, -1088, 112, 1, "Widget px / 256: one noise texel per screen px")
seed = fin(g, "Seed", FIT.FUNCTION_INPUT_SCALAR, -1088, 224, 2, "Per-instance offset so buttons never share grain")
phase = fin(g, "Phase", FIT.FUNCTION_INPUT_SCALAR, -1088, 336, 3, "Flow phase the widget accumulates (speed x dt)")
mul = g.add("MaterialExpressionMultiply", -848, 48)
add = g.add("MaterialExpressionAdd", -688, 112)
pan_flow = g.add("MaterialExpressionPanner", -512, 16, speed_x=1.0, speed_y=0.0, desc="stream right")
pan_fall = g.add("MaterialExpressionPanner", -512, 256, speed_x=0.0, speed_y=-0.6, desc="fall down")
tex_flow = g.add("MaterialExpressionTextureSample", -320, 0, texture=NOISE,
                 sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR, desc="R grain, G clumps")
tex_fall = g.add("MaterialExpressionTextureSample", -320, 256, texture=NOISE,
                 sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR, desc="B dissolve, A drips")
o_grain = fout(g, "Grain", 128, 64, 0, "Sparse sand specks (clump density baked into R), 0-1")
o_diss = fout(g, "Dissolve", 128, 272, 1, "Dissolve threshold noise, 0-1")
o_drip = fout(g, "Drip", 128, 368, 2, "Falling drip streaks, 0-1")
g.link(uv, "", mul, "A"); g.link(til, "", mul, "B")
g.link(mul, "", add, "A"); g.link(seed, "", add, "B")
for p in (pan_flow, pan_fall):
    g.link(add, "", p, "Coordinate"); g.link(phase, "", p, "Time")
g.link(pan_flow, "", tex_flow, "UVs"); g.link(pan_fall, "", tex_fall, "UVs")
g.link(tex_flow, "R", o_grain, ""); g.link(tex_fall, "B", o_diss, ""); g.link(tex_fall, "A", o_drip, "")
g.comment("Inputs", "UV, px tiling, seed, and the phase the widget owns", -1120, -64, 272, 496, "input")
g.comment("Sample one noise pack twice",
          "Phase is accumulated in BP so hover speed-ups never jump; flow pan = grain (R), fall pan = drips + dissolve",
          -880, -64, 752, 496, "noise")
g.comment("Outputs", "Grain, Dissolve, Drip", 112, 0, 224, 432, "out")
g.finish()

# ---------------------------------------------------------------- MF_UI_SandDissolve
g = MatGraph('/Game/FoA/UI/Materials/Functions/MF_UI_SandDissolve', function=True).clear()
noise = fin(g, "Noise", FIT.FUNCTION_INPUT_SCALAR, -960, 0, 0, "Threshold noise, 0-1 (MF_UI_SandFlow.Dissolve)")
amt = fin(g, "Amount", FIT.FUNCTION_INPUT_SCALAR, -960, 112, 1, "0 = solid, 1 = fully blown away")
edge = fin(g, "Edge", FIT.FUNCTION_INPUT_SCALAR, -960, 224, 2, "Edge width in noise units (0.05-0.15)")
neg = g.add("MaterialExpressionMultiply", -720, 224, const_b=-1.0)
lerp = g.add("MaterialExpressionLinearInterpolate", -560, 112, const_b=1.0)
sub = g.add("MaterialExpressionSubtract", -400, 32)
div = g.add("MaterialExpressionDivide", -256, 64)
sat = g.add("MaterialExpressionSaturate", -112, 64)
inv = g.add("MaterialExpressionOneMinus", 32, 176)
band = g.add("MaterialExpressionMultiply", 176, 160)
gain = g.add("MaterialExpressionMultiply", 320, 160, const_b=4.0)
o_op = fout(g, "Opacity", 496, 48, 0, "Multiply into opacity")
o_edge = fout(g, "Edge", 496, 176, 1, "Bright break-away rim, 0-1")
g.link(edge, "", neg, "A")
g.link(neg, "", lerp, "A"); g.link(amt, "", lerp, "Alpha")
g.link(noise, "", sub, "A"); g.link(lerp, "", sub, "B")
g.link(sub, "", div, "A"); g.link(edge, "", div, "B")
g.link(div, "", sat, "")
g.link(sat, "", inv, ""); g.link(sat, "", band, "A"); g.link(inv, "", band, "B")
g.link(band, "", gain, "A")
g.link(sat, "", o_op, ""); g.link(gain, "", o_edge, "")
g.comment("Inputs", "Noise, Amount, Edge width", -992, -64, 256, 384, "input")
g.comment("Threshold from lerp(-Edge, 1, Amount)",
          "Starting at -Edge means Amount 0 keeps every grain, even noise = 0", -736, -64, 592, 384, "fx")
g.comment("Edge band o(1-o)x4", "Peaks at the break line: the glint where sand lets go", -128, 96, 560, 224,
          "fx")
g.comment("Outputs", "Opacity, Edge", 480, -16, 240, 336, "out")
g.finish()
