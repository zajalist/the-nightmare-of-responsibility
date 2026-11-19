"""Text FX kit, material half: M_UI_SandText gains two scalars, both 0 by default (no change to existing instances).
  Shiver  0..1  rows of the word tremble at 20 Hz and a grey split ghost trails right (shock). Scaled by 1 - ReduceMotion.
  Sweep   0..1  a 20 degree light band crosses the word once as Sweep goes 0 to 1 (matters now). Off at exactly 0 and 1.
Built ONLY with Hayba's C++ material tools (editor-rules). Idempotent: does nothing if the Shiver parameter exists.
Hold the lease first:  python Tools/Unreal/editor_lock.py acquire ui --areas UI
  python Tools/Unreal/ui/textfx/sandtext_fx.py [--check]"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
from hayba_call import call  # noqa: E402

M = '/Game/FoA/UI/Materials/M_UI_SandText'
X = 'MaterialExpression'
# Existing nodes (material_get_info 2026-11-17): MF_UI_SandShape call, MF_UI_TimeEcho call, 1 - ReduceMotion, the
# retainer texture, TexCoord, the motion-scaled time, the echo's first multiply, and the final colour add.
SHAPE, ECHO, M1, TEX, UV, T = X + 'MaterialFunctionCall_6', X + 'MaterialFunctionCall_8', X + 'OneMinus_4', \
    X + 'TextureObjectParameter_2', X + 'TextureCoordinate_2', X + 'Multiply_14'
ECHO_MUL, COLOR = X + 'Multiply_16', X + 'Add_8'

HLSL = r"""float2 tx = float2(ddx(UV).x, ddy(UV).y);
float tick = floor(T * 20.0);
float row = floor(UV.y / tx.y / 3.0);
float h = frac(sin(row * 12.9898 + tick * 78.233) * 43758.5453);
float g = frac(sin(tick * 37.719 + 4.1) * 43758.5453);
float k = frac(sin(row * 3.17 + tick * 1.93) * 9631.17);
float2 j = float2((h - 0.5) * 7.0 * step(0.45, k) + (g - 0.5) * 2.5, (g - 0.5) * 1.5) * S;
float2 uv = UV + j * tx;
float fr = Texture2DSample(Glyphs, GlyphsSampler, uv - float2(2.5 + 2.0 * g, 0.0) * S * tx).a * 0.4 * saturate(S * 2.0);
float d = UV.x - (W * 1.6 - 0.3) + 0.36 * (UV.y - 0.5) * tx.x / max(tx.y, 1e-6);
float band = saturate(1.0 - abs(d) / 0.09) * step(0.001, W) * step(W, 0.999);
return float4(uv, fr, 1.0 + 0.55 * band * band);"""


def hb(cmd, **p):
    r = call(cmd, p)
    if not r.get('ok'):
        raise RuntimeError(f'{cmd} failed: {json.dumps(r)[:500]}')
    return r.get('data') or {}


def node(cls, x, y, **props):
    d = hb('material_add_node', material_path=M, expression_class=cls, node_pos=[x, y], properties=props)
    for k in ('node_id', 'expression_id', 'id', 'name'):
        if isinstance(d.get(k), str):
            return d[k]
    raise RuntimeError(json.dumps(d)[:300])


def link(a, b=None, inp=None, out=0, prop=None):
    p = dict(material_path=M, from_node=a)
    p['from_output_index' if isinstance(out, int) else 'from_output'] = out
    if prop:
        p['to_property'] = prop
    else:
        p['to_node'] = b
        p['to_input_index' if isinstance(inp, int) else 'to_input'] = inp
    hb('material_connect_nodes', **p)


def info():
    return hb('material_get_info', path=M)


def check():
    d = info()
    names = {e.get('parameter_name') for e in d['expressions']}
    by = {e['id']: e for e in d['expressions']}
    uv_in = by[SHAPE]['inputs'][2]
    print('params', sorted(n for n in names if n), 'shape UV <-', uv_in.get('from_node'),
          'emissive <-', next(o['from_node'] for o in d['material_outputs'] if o['property'] == 'EmissiveColor'))
    return 'Shiver' in names


def build():
    if check():
        print('already patched')
        return
    shiver = node(X + 'ScalarParameter', -3660, 1260, ParameterName='Shiver', DefaultValue=0.0)
    sweep = node(X + 'ScalarParameter', -3660, 1420, ParameterName='Sweep', DefaultValue=0.0)
    s = node(X + 'Multiply', -3420, 1260)
    link(shiver, s, 'A'); link(M1, s, 'B')
    cu = node(X + 'Custom', -3200, 1280, Description='Shiver and sweep', OutputType='CMOT_Float4', Code=HLSL,
              Inputs=[{'InputName': n} for n in ('Glyphs', 'UV', 'T', 'S', 'W')])
    for i, src in enumerate((TEX, UV, T, s, sweep)):
        link(src, cu, i)
    uv = node(X + 'ComponentMask', -2960, 1220, R=True, G=True, B=False, A=False)
    fr = node(X + 'ComponentMask', -2960, 1360, R=False, G=False, B=True, A=False)
    gain = node(X + 'ComponentMask', -2960, 1500, R=False, G=False, B=False, A=True)
    for m in (uv, fr, gain):
        link(cu, m, 0)
    link(uv, SHAPE, 2)                       # the letters read the trembling UV; grain and echo stay put
    ghost = node(X + 'Add', -2440, 880)
    link(ECHO, ghost, 'A'); link(fr, ghost, 'B')
    link(ghost, ECHO_MUL, 'A')               # the split ghost rides the echo layer (presence-gated, ink coloured)
    lit = node(X + 'Multiply', 96, 144)
    link(COLOR, lit, 'A'); link(gain, lit, 'B')
    link(lit, prop='emissive')
    hb('material_add_comment', material_path=M, text='Shiver and sweep', node_pos=[-3700, 1180], size=[900, 480],
       color=[0.30, 0.22, 0.10])
    print(json.dumps(hb('material_validate', material_path=M))[:600])
    print(json.dumps(hb('material_compile', material_path=M))[:800])
    check()


if __name__ == '__main__':
    check() if '--check' in sys.argv else build()
