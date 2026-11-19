"""M_UI_SandWipe: full-screen black-sand wipe for the day rollover (WBP_DayRollover). Built ONLY with Hayba's C++
material commands over hayba_call.py (editor-rules). Hold: python Tools/Unreal/editor_lock.py acquire ui --assets
/Game/FoA/UI/Materials/M_UI_SandWipe, then run this outside the editor. UI domain, translucent; Cover 0 = clear,
1 = the screen buried in opaque black sand (exactly 1 at Cover 1, so OnRolloverCovered can trust it).
Sand pours from the top: the edge is the row biased by two noise octaves, with sparse grain glints along it."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
from build_sandtext_hayba import G, hb, fresh, NOISE  # noqa: E402

FOLDER, NAME = '/Game/FoA/UI/Materials', 'M_UI_SandWipe'
PATH = f'{FOLDER}/{NAME}'
C_IN, C_WORK, C_OUT = [0.10, 0.20, 0.35], [0.30, 0.22, 0.10], [0.12, 0.26, 0.16]
CODE = r"""
float2 tx = float2(ddx(UV).x, ddy(UV).y);
float2 px = UV / max(abs(tx), 1e-6);
float n1 = Texture2DSample(Noise, NoiseSampler, px / 640.0 + float2(0.0, -T * 0.04)).b;
float n2 = Texture2DSample(Noise, NoiseSampler, px / 120.0 + float2(T * 0.03, -T * 0.35)).b;
float front = Cover * 1.7 - 0.35;
float h = UV.y + (n1 - 0.5) * 0.4 + (n2 - 0.5) * 0.1;
float a = smoothstep(front + 0.015, front - 0.015, h);
a = max(a, step(0.999, Cover));
float2 cell = floor(px / 1.5) + floor(T * 9.0) * 17.0;
float g = frac(sin(dot(cell, float2(12.9898, 78.233))) * 43758.5453);
float rim = saturate(1.0 - abs(h - front) / 0.03) * (1.0 - step(0.999, Cover));
float3 c = step(0.97, g) * rim * 0.45;
return float4(c, a);
""".strip()


def build():
    fresh('material_create', 'material_path', FOLDER, NAME)
    hb('material_set_property', material_path=PATH, properties={'domain': 'EMaterialDomain::MD_UI', 'blend_mode': 'BLEND_Translucent'})
    hb('material_compile', material_path=PATH)  # domain and blend settle on the empty material first
    g = G(PATH, False)
    uv = g.node('MaterialExpressionTextureCoordinate', -900, -60)
    noise = g.node('MaterialExpressionTextureObject', -900, 40, Texture=NOISE)
    time = g.node('MaterialExpressionTime', -900, 160)
    cover = g.node('MaterialExpressionScalarParameter', -900, 260, ParameterName='Cover', DefaultValue=0.0)
    g.box('Wipe inputs', -940, -120, 300, 500, C_IN)
    c = g.custom(-520, 40, 'Sand wipe', 'CMOT_Float4', ['UV', 'Noise', 'T', 'Cover'], CODE)
    g.box('Sand wipe', -560, -20, 280, 200, C_WORK)
    for i, src in enumerate((uv, noise, time, cover)):
        g.link(src, c, inp=i)
    rgb = g.mask(-200, 0, 'RGB')
    al = g.mask(-200, 120, 'A')
    g.link(c, rgb)
    g.link(c, al)
    g.link(rgb, prop='emissive')
    g.link(al, prop='opacity')
    g.box('Colour and coverage', -240, -60, 260, 280, C_OUT)
    print(hb('material_validate', material_path=PATH).get('data'))
    r = hb('material_compile', material_path=PATH)['data']
    print({k: r.get(k) for k in ('compiled_clean', 'errors', 'saved')})


if __name__ == '__main__':
    assert not any(ch in CODE for ch in "'\"`") and '//' not in CODE, 'no prose or quotes in Custom HLSL'
    build()
