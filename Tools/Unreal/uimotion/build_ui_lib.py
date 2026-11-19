"""UI material-function library (UI Material Lab style) + three lean master materials that use it, built ONLY with
Hayba's C++ material commands over hayba_call.py (editor-rules: material graphs never through Python).
Runs OUTSIDE the editor. Per step, under a lease (owner uimotion):
  python Tools/Unreal/uimotion/build_ui_lib.py mf MF_UI_SDFRoundRect      # one function (or: mf all)
  python Tools/Unreal/uimotion/build_ui_lib.py mat M_UI_Meter             # one master + its instance
Every function measures the widget in pixels from ddx/ddy of its UV, so no Size parameter: shapes stay crisp and
resolution-correct in an Image brush or a RetainerBox. Comment boxes carry a 2-5 word title only (the user's rule)."""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
from build_sandtext_hayba import G, hb, fresh, send, SOCK  # noqa: E402  (shared Hayba graph helpers of the UI lane)

LIB = '/Game/FoA/UI/Materials/Lib'
MAT = '/Game/FoA/UI/Materials'
OLD = '/Game/FoA/UI/Materials/Functions'
NOISE = '/Game/FoA/UI/Textures/T_UI_SandNoise.T_UI_SandNoise'
WHITE = '/Engine/EngineResources/WhiteSquareTexture.WhiteSquareTexture'
C_IN, C_WORK, C_OUT = [0.10, 0.20, 0.35], [0.30, 0.22, 0.10], [0.12, 0.26, 0.16]
PX = 'float2 tx = max(abs(float2(ddx(UV.x), ddy(UV.y))), 1e-6);\n'  # UV per screen pixel
HASH = 'p = frac({c} * float2(0.1031, 0.1030)); p += dot(p, p.yx + 33.33); float {h} = frac((p.x + p.y) * p.x);\n'

# name: (inputs [(name, kind)], (custom title, out type, hlsl), outputs [(name, mask)])
MF = {
    'MF_UI_SDFRoundRect': (
        [('UV', 'Vector2'), ('Inset', 'Scalar'), ('Radius', 'Scalar')],
        ('Rounded rect SDF', 'CMOT_Float2', PX +
         'float2 size = 1.0 / tx;\n'
         'float2 p = (UV - 0.5) * size;\n'
         'float2 b = max(size * 0.5 - Inset, 0.0);\n'
         'float r = min(Radius, min(b.x, b.y));\n'
         'float2 q = abs(p) - b + r;\n'
         'float d = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;\n'
         'return float2(d, saturate(0.5 - d));'),
        [('Dist', 'R'), ('Mask', 'G')]),
    'MF_UI_SDFRing': (
        [('UV', 'Vector2'), ('Radius', 'Scalar'), ('Width', 'Scalar')],
        ('Ring SDF', 'CMOT_Float3', PX +
         'float2 size = 1.0 / tx;\n'
         'float2 p = (UV - 0.5) * size;\n'
         'float R = Radius > 0.0 ? Radius : 0.5 * min(size.x, size.y) - Width * 0.5 - 1.0;\n'
         'float d = abs(length(p) - R) - Width * 0.5;\n'
         'float a = frac(atan2(p.x, -p.y) / 6.2831853 + 1.0);\n'
         'return float3(d, saturate(0.5 - d), a);'),
        [('Dist', 'R'), ('Mask', 'G'), ('Angle', 'B')]),
    'MF_UI_RadialTimer': (
        [('UV', 'Vector2'), ('Progress', 'Scalar'), ('Head', 'Scalar')],
        ('Radial sweep', 'CMOT_Float2', PX +
         'float2 p = (UV - 0.5) / tx;\n'
         'float r = max(length(p), 1.0);\n'
         'float a = frac(atan2(p.x, -p.y) / 6.2831853 + 1.0);\n'
         'float arc = (Progress - a) * 6.2831853 * r;\n'
         'float fill = Progress >= 1.0 ? 1.0 : saturate(arc + 0.5) * saturate(a * 6.2831853 * r + 0.5) * step(0.0005, Progress);\n'
         'return float2(fill, fill * exp(-max(arc, 0.0) / max(Head, 1.0)) * step(Progress, 0.999));'),
        [('Fill', 'R'), ('Head', 'G')]),
    'MF_UI_TrailFill': (
        [('Noise', 'Texture2D'), ('UV', 'Vector2'), ('Value', 'Scalar'), ('TrailFrom', 'Scalar'), ('ChipT', 'Scalar'),
         ('Jitter', 'Scalar')],
        ('Fill and trail', 'CMOT_Float3', PX +
         'float w = 1.0 / tx.x;\n'
         'float x = UV.x * w;\n'
         'float n = Texture2DSample(Noise, NoiseSampler, UV / tx / 96.0).b - 0.5;\n'
         'float v = Value * w + n * Jitter;\n'
         'float t = max(lerp(TrailFrom, Value, ChipT), Value) * w + n * Jitter * 1.5;\n'
         'float fill = saturate(v - x + 0.5) * step(0.0005, Value);\n'
         'float trail = saturate(t - x + 0.5) * (1.0 - fill);\n'
         'return float3(fill, trail, fill * exp(-abs(v - x) / 2.5));'),
        [('Fill', 'R'), ('Trail', 'G'), ('Head', 'B')]),
    'MF_UI_EdgeGlow': (
        [('Dist', 'Scalar'), ('Line', 'Scalar'), ('Glow', 'Scalar'), ('Halation', 'Scalar'), ('UV', 'Vector2')],
        ('Line and halo', 'CMOT_Float2', PX +
         'float o = max(Dist, 0.0);\n'
         'float g = max(Glow, 0.5);\n'
         'float line = saturate(Line * 0.5 + 0.5 - abs(Dist));\n'
         'float halo = Dist > 0.0 ? 0.65 * exp(-o / g) + Halation * 0.35 * exp(-o / (g * 4.0)) : 0.25 * exp(Dist / g);\n'
         'float2 e = min(UV, 1.0 - UV) / tx;\n'
         'float fade = saturate(min(e.x, e.y) / g);\n'  # the halo reaches 0 at the quad border, never a lit box
         'return float2(line, halo * (1.0 - line) * fade * fade);'),
        [('Line', 'R'), ('Glow', 'G')]),
    'MF_UI_TimeSlice': (
        [('UV', 'Vector2'), ('T', 'Scalar'), ('Amount', 'Scalar'), ('Bands', 'Scalar'), ('Shift', 'Scalar')],
        ('Slice and scan', 'CMOT_Float4', PX +
         'float2 c = float2(floor(UV.y * Bands), floor(T * 15.0));\n'
         'float2 ' + HASH.format(c='c', h='h1') + HASH.format(c='(c + 17.0)', h='h2') +
         'float on = step(1.0 - 0.7 * Amount, h1) * step(0.001, Amount);\n'
         'float dx = (h2 - 0.5) * 2.0 * Shift * Amount * tx.x * on;\n'
         'float scan = 1.0 - 0.2 * Amount * (0.5 + 0.5 * cos(UV.y / tx.y * 3.14159265));\n'
         'return float4(UV.x + dx, UV.y, scan, on);'),
        [('UV', 'RG'), ('Scan', 'B'), ('Slice', 'A')]),
}
REVEAL_IN = [('Noise', 'Texture2D'), ('UV', 'Vector2'), ('T', 'Scalar'), ('Reveal', 'Scalar'), ('Dir', 'Vector2'),
             ('Width', 'Scalar'), ('Scale', 'Scalar')]
REVEAL_FIELD = (PX +
                'float2 d = Dir / max(length(Dir), 1e-4);\n'
                'float g = dot(UV - 0.5, d) / max(abs(d.x) + abs(d.y), 1e-4) + 0.5;\n'
                'float n = Texture2DSample(Noise, NoiseSampler, UV / tx / 160.0).b;\n'
                'return saturate(lerp(1.0 - g, n, 0.4));')


def build_mf(name):
    if name == 'MF_UI_SandReveal':
        return build_reveal()
    inputs, (title, otype, hlsl), outputs = MF[name]
    path = fresh('material_function_create', 'function_path', LIB, name)
    g = G(path, True)
    ins = {n: g.fin(n, k, -900, i * 120, i) for i, (n, k) in enumerate(inputs)}
    c = g.custom(-480, 0, title, otype, [n for n, _ in inputs], hlsl)
    for n, _ in inputs:
        g.link(ins[n], c, inp=n)
    for i, (n, ch) in enumerate(outputs):
        m = g.mask(-200, i * 160, ch)
        g.link(c, m)
        g.link(m, g.fout(n, 0, i * 160, i))
    g.box('Function inputs', -940, -60, 300, len(inputs) * 120 + 60, C_IN)
    g.box(title, -520, -60, 280, 200, C_WORK)
    g.box('Function outputs', -240, -60, 380, len(outputs) * 160 + 60, C_OUT)
    print(json.dumps(hb('material_validate', function_path=path))[:300])
    hb('material_compile', function_path=path)
    print('function ok', name)


def build_reveal():
    """Directional sand reveal: a gradient-plus-noise field into the existing MF_UI_SandDissolve threshold, whose
    break-away edge drives the existing MF_UI_SandGrain glints. Reuses both; adds one Custom."""
    path = fresh('material_function_create', 'function_path', LIB, 'MF_UI_SandReveal')
    g = G(path, True)
    ins = {n: g.fin(n, k, -1400, i * 120, i) for i, (n, k) in enumerate(REVEAL_IN)}
    field = g.custom(-1000, 0, 'Reveal field', 'CMOT_Float1', ['Noise', 'UV', 'Dir'], REVEAL_FIELD)
    for n in ('Noise', 'UV', 'Dir'):
        g.link(ins[n], field, inp=n)
    amt = g.node('MaterialExpressionOneMinus', -1000, 240)
    g.link(ins['Reveal'], amt)
    diss = g.node('MaterialExpressionMaterialFunctionCall', -700, 0, function=f'{OLD}/MF_UI_SandDissolve')
    g.link(field, diss, inp=0); g.link(amt, diss, inp=1); g.link(ins['Width'], diss, inp=2)
    one = g.node('MaterialExpressionConstant', -700, 520, R=1.0)
    grain = g.node('MaterialExpressionMaterialFunctionCall', -420, 200, function=f'{OLD}/MF_UI_SandGrain')
    # SandGrain pins: Noise, UV, T, M, Scale, E, Edge, Glint
    for src, i, out in ((ins['Noise'], 0, None), (ins['UV'], 1, None), (ins['T'], 2, None), (one, 3, None),
                        (ins['Scale'], 4, None), (one, 5, None), (diss, 6, 1), (one, 7, None)):
        g.link(src, grain, inp=i, out=out)
    for i, (n, src, out) in enumerate((('Opacity', diss, 0), ('Edge', diss, 1), ('Tone', grain, 0),
                                       ('Glint', grain, 1))):
        g.link(src, g.fout(n, 0, i * 160, i), out=out)
    g.box('Function inputs', -1440, -60, 300, len(REVEAL_IN) * 120 + 60, C_IN)
    g.box('Reveal field', -1040, -60, 280, 400, C_WORK)
    g.box('Sand threshold and grain', -740, -60, 620, 680, C_WORK)
    g.box('Function outputs', -60, -60, 300, 700, C_OUT)
    print(json.dumps(hb('material_validate', function_path=path))[:300])
    hb('material_compile', function_path=path)
    print('function ok MF_UI_SandReveal')


# ---------------------------------------------------------------- masters

def ui_material(name):
    path = fresh('material_create', 'material_path', MAT, name)
    # Domain and blend FIRST, on the empty material (editor-rules; the 23:37 MaterialShader assert).
    hb('material_set_property', material_path=path,
       properties={'domain': 'EMaterialDomain::MD_UI', 'blend_mode': 'BLEND_Translucent'})
    hb('material_compile', material_path=path)
    return path, G(path, False)


def call(g, fn, x, y, links):
    """MaterialFunctionCall of a Lib function, its pins linked by index: links = [(src, out or None), ...]."""
    n = g.node('MaterialExpressionMaterialFunctionCall', x, y, function=f'{LIB}/{fn}')
    for i, (src, out) in enumerate(links):
        if src is not None:
            g.link(src, n, inp=i, out=out)
    return n


def vparam(g, name, x, y, rgba, group):
    return g.node('MaterialExpressionVectorParameter', x, y, ParameterName=name, Group=group,
                  DefaultValue='(R=%g,G=%g,B=%g,A=%g)' % tuple(rgba))


def sparam(g, name, x, y, v, group):
    return g.node('MaterialExpressionScalarParameter', x, y, ParameterName=name, Group=group, DefaultValue=v)


def compose(g, x, y, title, ins, hlsl):
    """One Custom compose node (rgb, a) -> Emissive and Opacity."""
    c = g.custom(x, y, title, 'CMOT_Float4', [n for n, _, _ in ins], hlsl)
    for n, src, out in ins:
        g.link(src, c, inp=n, out=out)
    rgb, a = g.mask(x + 300, y, 'RGB'), g.mask(x + 300, y + 140, 'A')
    g.link(c, rgb); g.link(c, a)
    # the widget's Color and Opacity (render opacity, fades) reach a UI material only as VertexColor
    vc = g.node('MaterialExpressionVertexColor', x + 300, y + 260)
    op = g.node('MaterialExpressionMultiply', x + 480, y + 160)
    g.link(a, op, inp='A'); g.link(vc, op, inp='B', out='A')
    g.link(rgb, prop='emissive'); g.link(op, prop='opacity')
    return c


def finish(path, instances):
    print(json.dumps(hb('material_validate', material_path=path))[:400])
    r = hb('material_compile', material_path=path)
    print(json.dumps(r.get('data', r))[:1500])
    for mi, params in instances:
        send(SOCK, 'material_create_instance', {'parent_material_path': path, 'package_path': MAT, 'name': mi})  # kept if it exists
        for k, v in params.items():
            hb('material_set_param', instance_path=f'{MAT}/{mi}', param_name=k, value=v)
        print('instance ok', mi)


def build_meter():
    """Health / posture meter: crumbling sand edge, delayed chip trail driven by one UMG-animated scalar (ChipT)."""
    path, g = ui_material('M_UI_Meter')
    uv = g.node('MaterialExpressionTextureCoordinate', -1700, -200)
    noise = g.node('MaterialExpressionTextureObject', -1700, -80, Texture=NOISE, SamplerType='SAMPLERTYPE_LinearColor')
    value = sparam(g, 'Value', -1700, 60, 0.62, 'Meter')
    trail = sparam(g, 'TrailFrom', -1700, 160, 0.85, 'Meter')
    chip = sparam(g, 'ChipT', -1700, 260, 0.0, 'Meter')
    hit = sparam(g, 'Hit', -1700, 360, 0.0, 'Meter')
    shape = vparam(g, 'Shape', -1700, 460, (6, 3, 2.5, 6), 'Shape')  # R inset px, G radius px, B jitter px, A glow px
    ink = vparam(g, 'Ink', -1700, 660, (0.86, 0.86, 0.86, 1), 'Shape')
    seg = sparam(g, 'Segments', -1700, 860, 0.0, 'Meter')  # 0 = continuous; the Shirt's six buttons = 6
    one = g.node('MaterialExpressionConstant', -1700, 960, R=1.0)
    g.box('Meter inputs', -1740, -260, 300, 1300, C_IN)
    rr = call(g, 'MF_UI_SDFRoundRect', -1200, -200, [(uv, None), (shape, 'R'), (shape, 'G')])
    tf = call(g, 'MF_UI_TrailFill', -1200, 60, [(noise, None), (uv, None), (value, None), (trail, None), (chip, None),
                                                (shape, 'B')])
    eg = call(g, 'MF_UI_EdgeGlow', -1200, 420, [(rr, 0), (one, None), (shape, 'A'), (hit, None), (uv, None)])
    g.box('Shape fill and glow', -1240, -260, 360, 900, C_WORK)
    compose(g, -700, -100, 'Compose meter',
            [('Mask', rr, 1), ('Fill', tf, 0), ('Trail', tf, 1), ('Head', tf, 2), ('Line', eg, 0), ('Halo', eg, 1),
             ('Hit', hit, None), ('Ink', ink, 0), ('UV', uv, None), ('Segments', seg, None)],
            'float gap = abs(frac(UV.x * Segments + 0.5) - 0.5) / max(Segments * abs(ddx(UV.x)), 1e-6);\n'
            'float notch = Segments > 1.0 ? saturate(gap - 0.75) : 1.0;\n'
            'Fill *= notch; Trail *= notch;\n'
            'float body = Mask * (0.14 + 0.70 * Fill + 0.42 * Trail * (1.0 + Hit) + 0.35 * Head);\n'
            'float edge = Line * 0.45 + Halo * Hit * 0.8;\n'
            'float a = saturate(Mask * 0.92 + edge);\n'
            'return float4(Ink * (body + Hit * Mask * Fill * 0.5 + edge) / max(a, 0.001), a);')
    g.box('Compose meter', -740, -160, 820, 560, C_OUT)
    finish(path, [('MI_UI_Meter_Garment', {'Shape': [14, 6, 2.5, 7]})])


def build_ring():
    """Telegraph / parry / hold ring: SDF annulus, radial sweep with a glowing head, a highlighted window band."""
    path, g = ui_material('M_UI_Ring')
    uv = g.node('MaterialExpressionTextureCoordinate', -1700, -200)
    prog = sparam(g, 'Progress', -1700, -80, 0.7, 'Ring')
    hit = sparam(g, 'Hit', -1700, 20, 0.0, 'Ring')
    ring = vparam(g, 'Ring', -1700, 120, (0, 6, 8, 0.5), 'Shape')  # R radius px (0 fits), G width px, B glow px, A halation
    win = vparam(g, 'Window', -1700, 320, (0.78, 0.9, 1, 0), 'Ring')  # R start, G end (0-1 of the turn), B strength
    ink = vparam(g, 'Ink', -1700, 520, (0.86, 0.86, 0.86, 1), 'Shape')
    head = g.node('MaterialExpressionConstant', -1700, 720, R=40.0)
    one = g.node('MaterialExpressionConstant', -1700, 820, R=1.0)
    g.box('Ring inputs', -1740, -260, 300, 1160, C_IN)
    sd = call(g, 'MF_UI_SDFRing', -1200, -200, [(uv, None), (ring, 'R'), (ring, 'G')])
    rt = call(g, 'MF_UI_RadialTimer', -1200, 80, [(uv, None), (prog, None), (head, None)])
    eg = call(g, 'MF_UI_EdgeGlow', -1200, 340, [(sd, 0), (one, None), (ring, 'B'), (ring, 'A'), (uv, None)])
    g.box('Ring sweep and glow', -1240, -260, 360, 840, C_WORK)
    compose(g, -700, -100, 'Compose ring',
            [('Mask', sd, 1), ('Angle', sd, 2), ('Fill', rt, 0), ('Head', rt, 1), ('Line', eg, 0), ('Halo', eg, 1),
             ('Window', win, 0), ('Hit', hit, None), ('Ink', ink, 0)],
            'float w = max(fwidth(Angle), 1e-4); w = w > 0.25 ? 1e-3 : w;\n'
            'float win = saturate((Angle - Window.x) / w + 0.5) * saturate((Window.y - Angle) / w + 0.5) * Window.z;\n'
            'float body = Mask * (0.10 + 0.50 * Fill + 0.80 * win * (1.0 - Fill) + 0.45 * win * Fill + 0.4 * Head);\n'
            'float edge = Line * 0.35 * (0.4 + win) + Halo * (0.25 + 0.75 * max(Hit, 0.6 * win));\n'
            'float a = saturate(Mask * 0.9 + edge);\n'
            'return float4(Ink * (body + Hit * Mask + edge) / max(a, 0.001), a);')
    g.box('Compose ring', -740, -160, 820, 560, C_OUT)
    finish(path, [('MI_UI_Ring_Parry', {})])


def build_panel():
    """Prompt card / phone panel / transition: the RetainerBox effect material. Texture = the retainer's children
    (text), sampled through the time-shift slice; dark sand panel, edge halo, directional sand reveal."""
    path, g = ui_material('M_UI_Panel')
    uv = g.node('MaterialExpressionTextureCoordinate', -2000, -300)
    tex = g.node('MaterialExpressionTextureObjectParameter', -2000, -200, ParameterName='Texture', Texture=WHITE)
    noise = g.node('MaterialExpressionTextureObject', -2000, -40, Texture=NOISE, SamplerType='SAMPLERTYPE_LinearColor')
    time = g.node('MaterialExpressionTime', -2000, 100)
    # shortcut: a plain ReduceMotion scalar like M_UI_SandText, since Hayba CollectionParameter ids still resolve to None
    # (M_UI_Scrim log, 00:39); switch to MPC_UI.ReduceMotion once that is fixed.
    rm = sparam(g, 'ReduceMotion', -2000, 180, 0.0, 'Panel')
    m = g.node('MaterialExpressionOneMinus', -1800, 180)
    t = g.node('MaterialExpressionMultiply', -1640, 120)
    g.link(rm, m); g.link(time, t, inp='A'); g.link(m, t, inp='B')
    reveal = sparam(g, 'Reveal', -2000, 300, 1.0, 'Panel')
    slice_ = sparam(g, 'Slice', -2000, 400, 0.0, 'Panel')
    hit = sparam(g, 'Hit', -2000, 500, 0.0, 'Panel')
    fill = sparam(g, 'Fill', -2000, 600, 0.72, 'Panel')
    panel = vparam(g, 'Panel', -2000, 700, (10, 6, 10, 0.4), 'Shape')  # R inset px, G radius px, B glow px, A halation
    dirv = vparam(g, 'Dir', -2000, 900, (1, 0.3, 0, 0), 'Shape')       # RG reveal direction
    dir2 = g.mask(-1800, 900, 'RG')
    g.link(dirv, dir2)
    ink = vparam(g, 'Ink', -2000, 1100, (0.86, 0.86, 0.86, 1), 'Shape')
    k = {n: g.node('MaterialExpressionConstant', -2000, y, R=v) for n, y, v in
         (('one', 1300, 1.0), ('width', 1380, 0.12), ('scale', 1460, 2.0), ('bands', 1540, 18.0), ('shift', 1620, 28.0))}
    g.box('Panel inputs', -2040, -360, 520, 2060, C_IN)
    rr = call(g, 'MF_UI_SDFRoundRect', -1300, -300, [(uv, None), (panel, 'R'), (panel, 'G')])
    eg = call(g, 'MF_UI_EdgeGlow', -1300, -60, [(rr, 0), (k['one'], None), (panel, 'B'), (panel, 'A'), (uv, None)])
    sr = call(g, 'MF_UI_SandReveal', -1300, 200, [(noise, None), (uv, None), (t, None), (reveal, None), (dir2, None),
                                                  (k['width'], None), (k['scale'], None)])
    ts = call(g, 'MF_UI_TimeSlice', -1300, 620, [(uv, None), (t, None), (slice_, None), (k['bands'], None),
                                                 (k['shift'], None)])
    g.box('Shape reveal and slice', -1340, -360, 380, 1260, C_WORK)
    compose(g, -800, -100, 'Compose panel',
            [('Tex', tex, None), ('SUV', ts, 0), ('UV', uv, None), ('Mask', rr, 1), ('Line', eg, 0), ('Halo', eg, 1),
             ('Op', sr, 0), ('Edge', sr, 1), ('Tone', sr, 2), ('Glint', sr, 3), ('Scan', ts, 1), ('SliceM', ts, 2),
             ('Fill', fill, None), ('Hit', hit, None), ('Ink', ink, 0)],
            'float content = Texture2DSample(Tex, TexSampler, SUV).a;\n'
            'float ghost = Texture2DSample(Tex, TexSampler, UV).a * SliceM * 0.45;\n'
            'float ink = max(content, ghost) * Mask;\n'
            'float body = max(ink, Fill);\n'
            'float edge = Line * 0.5 * Fill + Halo * (0.3 * Fill + 0.7 * Hit);\n'
            'float a = saturate(saturate(max(Mask * Fill, ink) + edge) * Op + Edge * 0.6 * body);\n'
            'float tone = (ink * Tone + edge + Hit * Mask * 0.35 * Fill + Glint * 0.8 * body) * Scan;\n'
            'return float4(Ink * tone / max(a, 0.001), a);')
    g.box('Compose panel', -840, -160, 820, 560, C_OUT)
    finish(path, [('MI_UI_Panel_Prompt', {})])


if __name__ == '__main__':
    what, name = sys.argv[1], sys.argv[2]
    if what == 'mf':
        for n in (list(MF) + ['MF_UI_SandReveal'] if name == 'all' else [name]):
            build_mf(n)
    else:
        {'M_UI_Meter': build_meter, 'M_UI_Ring': build_ring, 'M_UI_Panel': build_panel}[name]()
