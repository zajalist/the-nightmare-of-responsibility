"""M_UI_SplatLogo + MI_UI_SplatLogo_Hayba: the Hayba mark forming from sharp 2 px sand grains and blowing back into
them (boot card 3). Spec: _spec_m_ui_splatlogo.txt. Built ONLY with Hayba's C++ material commands; hold
  python Tools/Unreal/editor_lock.py acquire ui --assets /Game/FoA/UI/Materials/M_UI_SplatLogo,/Game/FoA/UI/Materials/MI_UI_SplatLogo_Hayba
Transition 0 = scattered, 1 = assembled (exactly the unaltered mark). Every 2 px screen cell has its own direction and
delay; opacity also takes the widget's own fade (VertexColor.a)."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
from build_sandtext_hayba import G, hb, fresh, send, SOCK  # noqa: E402

FOLDER, NAME, MI = '/Game/FoA/UI/Materials', 'M_UI_SplatLogo', 'MI_UI_SplatLogo_Hayba'
PATH = f'{FOLDER}/{NAME}'
LOGO = '/Game/FoA/UI/Textures/T_UI_Logo_Hayba.T_UI_Logo_Hayba'
C_IN, C_WORK, C_OUT = [0.10, 0.20, 0.35], [0.30, 0.22, 0.10], [0.12, 0.26, 0.16]
CODE = r"""
float2 t = float2(ddx(UV).x, ddy(UV).y);
uint2 q = uint2(int2(floor(Pos / 2.0)) + 65536);
uint h1 = (q.x * 1597334677u) ^ (q.y * 3812015801u);
h1 = (h1 ^ (h1 >> 16)) * 2246822519u;
uint h2 = h1 * 3266489917u + 374761393u;
h2 = (h2 ^ (h2 >> 13)) * 668265263u;
float3 r = float3(h1 & 1023u, (h1 >> 10) & 1023u, h2 & 1023u) / 1023.0;
float k = saturate((T - r.z * 0.35) / 0.65);
float sc = (1.0 - k) * (1.0 - k);
float2 off = (r.xy * 2.0 - 1.0) * 48.0 * sc + float2(0.0, -18.0) * sc;
float4 c = Texture2DSample(Logo, LogoSampler, UV + off * t);
float keep = step(0.22, frac(r.x * 7.31 + r.y * 3.17));
float tone = 0.72 + 0.28 * r.y;
return float4(c.rgb * tone, c.a * step(r.z * 0.6, k) * keep * VA);
""".strip()


def build():
    fresh('material_create', 'material_path', FOLDER, NAME)
    hb('material_set_property', material_path=PATH, properties={'domain': 'EMaterialDomain::MD_UI', 'blend_mode': 'BLEND_Translucent'})
    hb('material_compile', material_path=PATH)  # domain and blend settle on the empty material first
    g = G(PATH, False)
    logo = g.node('MaterialExpressionTextureObjectParameter', -900, -120, ParameterName='Logo', Texture=LOGO)
    uv = g.node('MaterialExpressionTextureCoordinate', -900, 0)
    pos = g.node('MaterialExpressionScreenPosition', -900, 100)
    tr = g.node('MaterialExpressionScalarParameter', -900, 220, ParameterName='Transition', DefaultValue=1.0)
    vc = g.node('MaterialExpressionVertexColor', -900, 320)
    g.box('Logo and grains', -940, -180, 300, 620, C_IN)
    c = g.custom(-520, 40, 'Splat assemble', 'CMOT_Float4', ['Logo', 'UV', 'Pos', 'T', 'VA'], CODE)
    g.box('Splat assemble', -560, -20, 280, 200, C_WORK)
    names = {e['id']: [o.get('name') for o in e.get('outputs', [])] for e in hb('material_get_info', path=PATH)['data']['expressions']}
    g.link(logo, c, inp=0)
    g.link(uv, c, inp=1)
    g.link(pos, c, inp=2, out='PixelPosition' if 'PixelPosition' in (names.get(pos) or []) else 1)
    g.link(tr, c, inp=3)
    g.link(vc, c, inp=4, out='A' if 'A' in (names.get(vc) or []) else 4)
    rgb, al = g.mask(-200, 0, 'RGB'), g.mask(-200, 120, 'A')
    g.link(c, rgb)
    g.link(c, al)
    g.link(rgb, prop='emissive')
    g.link(al, prop='opacity')
    g.box('Mark output', -240, -60, 260, 280, C_OUT)
    print(hb('material_validate', material_path=PATH).get('data'))
    r = hb('material_compile', material_path=PATH)['data']
    print({k: r.get(k) for k in ('compiled_clean', 'errors', 'saved')})
    r = send(SOCK, 'material_create_instance', {'parent_material_path': PATH, 'package_path': FOLDER, 'name': MI})
    print('instance', MI, r.get('ok'), (r.get('error') or '')[:160])


if __name__ == '__main__':
    assert not any(ch in CODE for ch in "'\"`") and '//' not in CODE, 'no prose or quotes in Custom HLSL'
    build()
