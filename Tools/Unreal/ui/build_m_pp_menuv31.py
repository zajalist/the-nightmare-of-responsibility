"""M_PP_MenuV31: the v3.1 direction page's full-screen look as one menu-only post-process pass (menulook lane).
Built ONLY with Hayba's C++ material commands over hayba_call.py (editor-rules). Runs OUTSIDE the editor while holding
  python Tools/Unreal/editor_lock.py acquire ui --assets /Game/FoA/UI/Menu
  python Tools/Unreal/ui/build_m_pp_menuv31.py            # create (or empty and rebuild in place), compile, save
  python Tools/Unreal/ui/build_m_pp_menuv31.py --code     # only replace the Custom node's HLSL, then compile
It sits on BP_MenuCamera's camera blendables (never on PP_DreamMono), after tonemapping at priority -1, so it runs
before the dream stack: M_PP_DreamMono moshes it (the pp lane owns the datamosh) and M_PP_DreamLens finishes it.
Ported from the page's bg and present shaders (rays, dust, shadow band, dark field, highlight streak, halation)
plus its pts dust grains and the 10% overlay grain. Comment boxes carry only a 2-5 word title (the user's rule)."""
import json
import os
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
from build_sandtext_hayba import G, hb, fresh, send, SOCK  # noqa: E402  (importing builds nothing)

FOLDER, NAME = '/Game/FoA/UI/Menu', 'M_PP_MenuV31'
PATH = f'{FOLDER}/{NAME}'
MPC = '/Game/FoA/PostProcess/MPC_Dream.MPC_Dream'
C_IN, C_PAR, C_WORK = [0.10, 0.20, 0.35], [0.12, 0.26, 0.16], [0.30, 0.22, 0.10]
DEFAULTS = {  # tuned against the page at matched moments (Saved/MenuLook)
    'Light': (0.39, 0.05, 0.8, 1.0),   # the bay window in the 02:37 moonbeam framing (pose_F3); rays 0.8: less haze   # xy light in viewport UV (the window, as BP_MenuCamera frames it), z rays, w dust
    'Field': (0.15, 0.6, 0.45, 0.85),   # x left floor, y left ramp end, z bottom floor, w vignette (the window sits behind the title)
    'Look': (3.0, 1.0, 1.0, 1.0),      # x streak px per tap at 1080p, y streak gain, z halation, w film grain
}
INPUTS = ['UV', 'Scene', 'T', 'RM', 'Mosh', 'Light', 'Field', 'Look']

CODE = r"""
#define MV31_S(p) SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(p, PPI_PostProcessInput0), PPI_PostProcessInput0), PPI_PostProcessInput0, false).rgb
#define MV31_Hq(a) frac(((a).x + (a).y + 2.0 * dot(a, (a).yx + 33.33)) * ((a).x + dot(a, (a).yx + 33.33)))
#define MV31_H(p) MV31_Hq(frac((p) * float2(0.1031, 0.1030)))
const float3 lw = float3(0.299, 0.587, 0.114);
float2 res = View.ViewSizeAndInvSize.xy;
float k1080 = res.y / 1080.0;
float t = lerp(T, 4.0, saturate(RM));
float3 c = Scene.rgb;
float2 sp = UV, dir = (UV - Light.xy) * (0.9 / 24.0);
float rays = 0.0;
[loop] for (int i = 0; i < 24; i++) { sp -= dir; rays += smoothstep(0.5, 0.95, dot(MV31_S(sp), lw)) * (1.0 - i / 24.0); }
rays /= 24.0;
float bx = (UV.x - lerp(1.25, -0.25, saturate(frac(t / 21.0) * 21.0 / 3.2))) / 0.07;
float band = exp(-bx * bx);
rays *= (0.82 + 0.18 * sin(t * 1.7 + 3.0 * sin(t * 0.37))) * (1.0 - 0.6 * band);
c *= 1.0 - 0.3 * band * smoothstep(0.25, 0.7, dot(c, lw));
float2 g0 = float2(UV.x * res.x / res.y, 1.0 - UV.y);
float dust = 0.0;
[unroll] for (int k = 0; k < 3; k++)
{
    float sc = 90.0 + 60.0 * k;
    float2 g = g0 * sc + float2(t * (0.6 + 0.3 * k), -t * (0.9 + 0.4 * k));
    float2 id = floor(g), off = float2(MV31_H(id), MV31_H(id + 7.3)) - 0.5;
    dust += step(0.9, MV31_H(id + 3.1)) * smoothstep(1.4, 0.5, length(frac(g) - 0.5 - off * 0.6) * res.y / sc / k1080);
}
c += float3(1.0, 0.93, 0.8) * (rays * 0.4 * Light.z + dust * rays * 3.0 * Light.w);
float2 q = float2(UV.x, 1.0 - UV.y);
float2 v = (q - float2(0.7, 0.55)) * float2(1.0, 0.9);
float field = lerp(Field.z, 1.0, smoothstep(0.0, 0.3, q.y)) * lerp(Field.x, 1.0, smoothstep(0.02, Field.y, q.x))
            * lerp(1.0, 1.0 - Field.w, smoothstep(0.45, 1.1, length(v)));
c *= field;
float st = Look.x * k1080 * lerp((1.0 + 0.4 * sin(t * 0.5)) * (1.0 + 1.6 * saturate(Mosh / 0.6)), 0.5, saturate(RM));
float3 acc = 0.0;
[loop] for (int j = 1; j <= 12; j++)
{
    float3 s = MV31_S(UV - float2(0.0, j * st / res.y));
    acc = max(acc, s * smoothstep(0.42, 0.9, dot(s, lw)) * pow(1.0 - j / 13.0, 1.4));
}
float3 glow = 0.0;
[unroll] for (int a = 0; a < 8; a++)
{
    float3 s = MV31_S(UV + float2(cos(a * 0.785), sin(a * 0.785)) * 7.0 * k1080 / res);
    glow += s * smoothstep(0.5, 0.95, dot(s, lw));
}
c += glow * (field * 0.35 / 8.0 * Look.z) * float3(1.0, 0.8, 0.55);
c += max(acc * field - c, 0.0) * 0.5 * Look.y;
float n = MV31_H(floor(UV * res) + floor(t * 9.5) * 13.7);
c = lerp(c, lerp(2.0 * c * n, 1.0 - 2.0 * (1.0 - c) * (1.0 - n), step(0.5, c)), 0.1 * Look.w);
float2 gg = g0 * 45.0 - float2(t * 2.0, 0.0);
float2 gid = floor(gg), go = float2(MV31_H(gid + 1.7), MV31_H(gid + 9.2)) - 0.5;
go.y += 0.2 * sin(t * 0.7 + 6.283 * MV31_H(gid));
float gd = length(frac(gg) - 0.5 - go * 0.6) * res.y / 45.0 / k1080;
float ga = step(0.75, MV31_H(gid + 5.5)) * smoothstep(1.2, 0.4, gd) * (0.6 + 0.4 * sin(t * (1.0 + 3.0 * MV31_H(gid + 4.4)) + 30.0 * MV31_H(gid + 2.2)));
c = lerp(c, float3(0.93, 0.89, 0.82) * (0.82 + 0.24 * MV31_H(gid + 6.6)), saturate(ga * 0.24 * Light.w));
#undef MV31_S
#undef MV31_H
#undef MV31_Hq
return c;
""".strip()


def vec(v):
    return '(R={},G={},B={},A={})'.format(*v)


def custom_id():
    info = hb('material_get_info', path=PATH)['data']
    return next(e['id'] for e in info['expressions'] if e.get('class') == 'MaterialExpressionCustom')


def build():
    fresh('material_create', 'material_path', FOLDER, NAME)
    # domain before any node (editor-rules); priority -1 runs it ahead of the dream stack's priority 0 and 1
    hb('material_set_property', material_path=PATH, properties={'domain': 'EMaterialDomain::MD_PostProcess'})
    hb('material_compile', material_path=PATH)  # the domain settles on the empty material (sand-text builder pattern)
    hb('object_set_property', path=PATH, properties={'BlendablePriority': -1})
    g = G(PATH, False)
    uv = g.node('MaterialExpressionScreenPosition', -1200, -160)
    scene = g.node('MaterialExpressionSceneTexture', -1200, -40, SceneTextureId='PPI_PostProcessInput0')
    time = g.node('MaterialExpressionTime', -1200, 100)
    # shortcut: plain scalars until the restart-2 Hayba DLL resolves CollectionParameter ids; then read MPC_Dream again
    rm = g.node('MaterialExpressionScalarParameter', -1200, 200, ParameterName='ReduceMotion', DefaultValue=0.0)
    mosh = g.node('MaterialExpressionScalarParameter', -1200, 300, ParameterName='MoshAmount', DefaultValue=0.0)
    g.box('Frame and time', -1240, -220, 320, 600, C_IN)
    pars = [g.node('MaterialExpressionVectorParameter', -1200, 460 + 200 * i, ParameterName=k, DefaultValue=vec(v))
            for i, (k, v) in enumerate(DEFAULTS.items())]
    g.box('Look parameters', -1240, 400, 320, 620, C_PAR)
    c = g.custom(-720, 0, 'Menu v3.1 look', 'CMOT_Float3', INPUTS, CODE)
    g.box('Menu look pass', -760, -60, 360, 480, C_WORK)
    outs = {e['id']: [o.get('name') for o in e.get('outputs', [])] for e in hb('material_get_info', path=PATH)['data']['expressions']}
    print('vector outputs', outs.get(pars[0]), 'screen outputs', outs.get(uv))
    for i, src in enumerate([uv, scene, time, rm, mosh] + pars):
        names = outs.get(src) or []
        g.link(src, c, inp=i, out=next((n for n in ('RGBA', 'ViewportUV', 'Color') if n in names), 0))
    g.link(c, prop='emissive')
    finish()


def finish():
    print(json.dumps(hb('material_validate', material_path=PATH), indent=0)[:600])
    r = hb('material_compile', material_path=PATH)
    print(json.dumps(r, indent=0)[:1500])


if __name__ == '__main__':
    if '--code' in sys.argv:
        hb('material_set_node', material_path=PATH, node_id=custom_id(), properties={'Code': CODE})
        finish()
    else:
        build()
