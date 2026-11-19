"""M_UI_SandVortex: the page's selection effect for a sand word (index.html drawFx): crisp 1-2 px grains orbit a small
flat ellipse left of the selected word (the vortex) and grains fall off the word's lower edge with gravity, drifting
right. One quad over the button (Img_Vortex in WBP_SandButton, 56 px wider on the left, 40 px taller below); its
render opacity is the hover/focus state, so nothing draws at rest. Built ONLY with Hayba's C++ material commands.
  python Tools/Unreal/editor_lock.py acquire ui --assets /Game/FoA/UI/Materials/M_UI_SandVortex
  python Tools/Unreal/ui/build_m_ui_sandvortex_hayba.py
Params: Word (x0 = vortex centre in px from the quad's left, y = word centre px from top, z = word width px, w = word
height px), Ink (grain colour)."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
from build_sandtext_hayba import G, hb, fresh  # noqa: E402

FOLDER, NAME = '/Game/FoA/UI/Materials', 'M_UI_SandVortex'
PATH = f'{FOLDER}/{NAME}'
C_IN, C_WORK, C_OUT = [0.10, 0.20, 0.35], [0.30, 0.22, 0.10], [0.12, 0.26, 0.16]
CODE = r"""
float2 tx = float2(ddx(UV).x, ddy(UV).y);
float2 px = UV / max(abs(tx), 1e-6);
float2 c0 = Word.xy;
float a = 0.0;
[loop] for (int i = 0; i < 48; i++)
{
    float h1 = frac(sin(i * 12.9898) * 43758.5453);
    float h2 = frac(sin(i * 78.233) * 24634.6345);
    float h3 = frac(sin(i * 39.425) * 12345.6789);
    float ang = h1 * 6.283 + T * (0.6 + 1.4 * h2) * 1.6;
    float r = 0.4 + 0.7 * h3;
    float2 p = c0 + float2(cos(ang) * 15.0 * r, sin(ang) * 7.0 * r - (r - 0.7) * 5.0);
    float front = sin(ang) * 0.5 + 0.5;
    float s = 1.0 + step(0.6, h2);
    float2 d = abs(px - floor(p) - s * 0.5);
    a = max(a, step(d.x, s * 0.5) * step(d.y, s * 0.5) * (0.3 + 0.6 * front) * (0.5 + 0.5 * h3));
}
[loop] for (int k = 0; k < 40; k++)
{
    float g1 = frac(sin(k * 91.345) * 47453.5453);
    float g2 = frac(sin(k * 17.17) * 13758.937);
    float g3 = frac(sin(k * 5.71) * 93751.13);
    float life = 1.1 + 1.1 * g2;
    float ph = frac(T / life + g1);
    float tt = ph * life;
    float2 p0 = float2(c0.x + 20.0 + g3 * Word.z, c0.y + Word.w * 0.5);
    float2 p = p0 + float2((6.0 + 18.0 * g1) * tt, (8.0 * g2) * tt + 45.0 * tt * tt);
    float2 d = abs(px - floor(p) - 0.5);
    a = max(a, step(d.x, 0.5) * step(d.y, 0.5) * sin(3.1416 * ph) * 0.6);
}
return float4(Ink.rgb, a * VA);
""".strip()


def build():
    fresh('material_create', 'material_path', FOLDER, NAME)
    hb('material_set_property', material_path=PATH, properties={'domain': 'EMaterialDomain::MD_UI', 'blend_mode': 'BLEND_Translucent'})
    hb('material_compile', material_path=PATH)  # domain and blend settle on the empty material first
    g = G(PATH, False)
    uv = g.node('MaterialExpressionTextureCoordinate', -900, -60)
    time = g.node('MaterialExpressionTime', -900, 40)
    word = g.node('MaterialExpressionVectorParameter', -900, 140, ParameterName='Word', DefaultValue='(R=28,G=52,B=150,A=36)')
    ink = g.node('MaterialExpressionVectorParameter', -900, 340, ParameterName='Ink', DefaultValue='(R=0.93,G=0.89,B=0.82,A=1.0)')
    vc = g.node('MaterialExpressionVertexColor', -900, 540)
    g.box('Grain inputs', -940, -120, 300, 760, C_IN)
    c = g.custom(-520, 40, 'Vortex and fall', 'CMOT_Float4', ['UV', 'T', 'Word', 'Ink', 'VA'], CODE)
    g.box('Vortex and fall', -560, -20, 280, 200, C_WORK)
    outs = {e['id']: [o.get('name') for o in e.get('outputs', [])] for e in hb('material_get_info', path=PATH)['data']['expressions']}
    for i, src in enumerate((uv, time, word, ink)):
        g.link(src, c, inp=i, out='RGBA' if 'RGBA' in (outs.get(src) or []) else 0)
    g.link(vc, c, inp=4, out='A' if 'A' in (outs.get(vc) or []) else 4)
    rgb, al = g.mask(-200, 0, 'RGB'), g.mask(-200, 120, 'A')
    g.link(c, rgb)
    g.link(c, al)
    g.link(rgb, prop='emissive')
    g.link(al, prop='opacity')
    g.box('Grain output', -240, -60, 260, 280, C_OUT)
    print(hb('material_validate', material_path=PATH).get('data'))
    r = hb('material_compile', material_path=PATH)['data']
    print({k: r.get(k) for k in ('compiled_clean', 'errors', 'saved')})


if __name__ == '__main__':
    assert not any(ch in CODE for ch in "'\"`") and '//' not in CODE, 'no prose or quotes in Custom HLSL'
    build()
