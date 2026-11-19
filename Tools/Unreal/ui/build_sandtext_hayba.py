"""M_UI_SandText + its three material functions, built ONLY with Hayba's C++ material commands over hayba_call.py
(editor-rules: material graphs never through Python). Runs OUTSIDE the editor; hold the editor lock as FOA_AGENT=ui.
  python Tools/Unreal/ui/build_sandtext_hayba.py            # build (assets must not exist yet), compile, instances
  python Tools/Unreal/ui/build_sandtext_hayba.py --probe    # one throwaway node on a TMP_ui_ function: response format
Design and HLSL: Tools/Unreal/ui/_spec_m_ui_sandtext.txt (ported from the approved direction page v3.1).
Comment boxes carry only a 2-5 word title (the user's rule)."""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
from hayba_call import connect, send  # noqa: E402

FN = '/Game/FoA/UI/Materials/Functions'
MAT = '/Game/FoA/UI/Materials'
NOISE = '/Game/FoA/UI/Textures/T_UI_SandNoise.T_UI_SandNoise'
MPC = '/Game/FoA/UI/Style/MPC_UI.MPC_UI'
WHITE = '/Engine/EngineResources/WhiteSquareTexture.WhiteSquareTexture'
C_IN, C_WORK, C_OUT = [0.10, 0.20, 0.35], [0.30, 0.22, 0.10], [0.12, 0.26, 0.16]

SOCK = connect()
MPC_ON = '--mpc' in sys.argv


def hb(cmd, **params):
    r = send(SOCK, cmd, params)
    if not (r.get('ok') or r.get('success')):
        raise RuntimeError(f'{cmd} failed: {json.dumps(r)[:600]}')
    return r


def find_id(r):
    """The new node's id from a material_add_node response, whatever nesting the plugin uses."""
    stack = [r]
    while stack:
        x = stack.pop(0)
        if isinstance(x, dict):
            for k in ('node_id', 'expression_id', 'id', 'name', 'node_name'):
                if isinstance(x.get(k), str) and x[k].startswith(('MaterialExpression', 'Material')) or \
                        (k in ('node_id', 'expression_id') and isinstance(x.get(k), (str, int))):
                    return str(x[k])
            stack += list(x.values())
        elif isinstance(x, list):
            stack += x
    raise RuntimeError(f'no node id in {json.dumps(r)[:400]}')


class G:
    def __init__(self, path, function):
        self.key, self.path = ('function_path' if function else 'material_path'), path

    def node(self, cls, x, y, **props):
        return find_id(hb('material_add_node', **{self.key: self.path}, expression_class=cls, node_pos=[x, y],
                          properties=props))

    def link(self, a, b=None, inp=None, out=None, prop=None):
        p = {self.key: self.path, 'from_node': a}
        if isinstance(out, int):
            p['from_output_index'] = out
        elif out:
            p['from_output'] = out
        if prop:
            p['to_property'] = prop
        else:
            p['to_node'] = b
            if isinstance(inp, int):
                p['to_input_index'] = inp
            elif inp:
                p['to_input'] = inp
            else:
                p['to_input_index'] = 0
        hb('material_connect_nodes', **p)

    def box(self, title, x, y, w, h, color):
        assert 2 <= len(title.split()) <= 5, title
        hb('material_add_comment', **{self.key: self.path}, text=title, node_pos=[x, y], size=[w, h], color=color)

    def fin(self, name, kind, x, y, prio):
        return self.node('MaterialExpressionFunctionInput', x, y, InputName=name, InputType=f'FunctionInput_{kind}',
                         SortPriority=prio)

    def fout(self, name, x, y, prio):
        return self.node('MaterialExpressionFunctionOutput', x, y, OutputName=name, SortPriority=prio)

    def custom(self, x, y, desc, out_type, inputs, code):
        n = self.node('MaterialExpressionCustom', x, y, Description=desc, OutputType=out_type, Code=code,
                      Inputs=[{'InputName': i} for i in inputs])
        return n

    def mask(self, x, y, ch):
        return self.node('MaterialExpressionComponentMask', x, y, **{c: c in ch for c in 'RGBA'})


def code(name):
    """HLSL block `name` from the spec (between its Custom header line and the next blank-indented section)."""
    spec = open('P:/FoA/Tools/Unreal/ui/_spec_m_ui_sandtext.txt', encoding='utf-8').read().split('\n')
    i = next(k for k, l in enumerate(spec) if f'Custom "{name}"' in l)
    body = []
    for line in spec[i + 1:]:
        if not line.startswith('    ') or line.lstrip().startswith('->'):
            break
        body.append(line[4:])
    return '\n'.join(body)


def fresh(create_cmd, key, folder, name):
    """Create the asset, or empty an existing one (a rerun after a failed build) node by node; never deletes assets."""
    path = f'{folder}/{name}'
    r = send(SOCK, create_cmd, {'package_path': folder, 'name': name})
    if r.get('ok') or r.get('success'):
        return path
    info = hb('material_get_info', path=path)['data']
    for ex in info.get('expressions', []) + info.get('dead_nodes', []):
        nid = ex.get('id') if isinstance(ex, dict) else ex
        if nid:
            send(SOCK, 'material_delete_node', {key: path, 'node_id': nid})
    for cm in info.get('comments', []):
        send(SOCK, 'material_delete_comment', {key: path, 'comment_id': cm.get('id')})
    print('emptied existing', path)
    return path


IN = {}  # function name -> its input names in pin order


def build_function(name, inputs, custom, outputs):
    """inputs: [(name, kind)]; custom: (title, out_type, hlsl); outputs: [(name, channels or None)]."""
    IN[name] = [n for n, _ in inputs]
    fresh('material_function_create', 'function_path', FN, name)
    g = G(f'{FN}/{name}', True)
    ins = {n: g.fin(n, k, -900, i * 120, i) for i, (n, k) in enumerate(inputs)}
    c = g.custom(-480, 0, custom[0], custom[1], [n for n, _ in inputs], custom[2])
    for i, (n, _) in enumerate(inputs):
        g.link(ins[n], c, inp=n)
    for i, (n, ch) in enumerate(outputs):
        o = g.fout(n, 0, i * 160, i)
        if ch:
            m = g.mask(-200, i * 160, ch)
            g.link(c, m)
            g.link(m, o)
        else:
            g.link(c, o)
    g.box('Function inputs', -940, -60, 300, len(inputs) * 120 + 60, C_IN)
    g.box(custom[0], -520, -60, 300, 200, C_WORK)
    g.box('Function outputs', -240, -60, 340, len(outputs) * 160 + 60, C_OUT)
    hb('material_compile', function_path=f'{FN}/{name}')
    print('function ok', name)


def build():
    if '--material-only' in sys.argv:  # the functions built and saved already; record their pin order only
        IN.update({'MF_UI_SandShape': ['Glyphs', 'Noise', 'UV', 'T', 'M', 'Scale', 'E', 'Rev', 'Out'],
                   'MF_UI_SandGrain': ['Noise', 'UV', 'T', 'M', 'Scale', 'E', 'Edge', 'Glint'],
                   'MF_UI_TimeEcho': ['Glyphs', 'UV', 'T', 'Scale', 'Echo']})
        return build_material()
    build_function('MF_UI_SandShape',
                   [('Glyphs', 'Texture2D'), ('Noise', 'Texture2D'), ('UV', 'Vector2'), ('T', 'Scalar'), ('M', 'Scalar'),
                    ('Scale', 'Scalar'), ('E', 'Scalar'), ('Rev', 'Scalar'), ('Out', 'Scalar')],
                   ('Sand shape', 'CMOT_Float4', code('Sand shape')), [('Alpha', 'R'), ('Edge', 'G')])
    build_function('MF_UI_SandGrain',
                   [('Noise', 'Texture2D'), ('UV', 'Vector2'), ('T', 'Scalar'), ('M', 'Scalar'), ('Scale', 'Scalar'),
                    ('E', 'Scalar'), ('Edge', 'Scalar'), ('Glint', 'Scalar')],
                   ('Grain and glint', 'CMOT_Float2', code('Grain and glint')), [('Tone', 'R'), ('Highlight', 'G')])
    build_function('MF_UI_TimeEcho',
                   [('Glyphs', 'Texture2D'), ('UV', 'Vector2'), ('T', 'Scalar'), ('Scale', 'Scalar'), ('Echo', 'Scalar')],
                   ('Echo taps', 'CMOT_Float1', code('Echo taps')), [('Echo', None)])
    build_material()


def build_material():
    path = fresh('material_create', 'material_path', MAT, 'M_UI_SandText')
    # Domain and blend FIRST, on the empty material: switching a populated Surface material to UI while its shaders
    # compile asserts in MaterialShader.cpp (editor crash 23:37, missing FLumenTranslucencyRadianceCacheMarkVS).
    hb('material_set_property', material_path=path,
       properties={'domain': 'EMaterialDomain::MD_UI', 'blend_mode': 'BLEND_Translucent'})
    hb('material_compile', material_path=path)
    g = G(path, False)
    # Inputs
    tex = g.node('MaterialExpressionTextureObjectParameter', -2400, -200, ParameterName='Texture', Texture=WHITE)
    noise = g.node('MaterialExpressionTextureObject', -2400, -40, Texture=NOISE, SamplerType='SAMPLERTYPE_LinearColor')
    uv = g.node('MaterialExpressionTextureCoordinate', -2400, 100)
    time = g.node('MaterialExpressionTime', -2400, 200)
    # --mpc once the restart-2 Hayba DLL is live (it resolves CollectionParameter ids, 064cae9a); until then plain
    # parameters with the same defaults (shortcut: ReduceMotion is not linked to MPC_UI without --mpc)
    rm = g.node('MaterialExpressionCollectionParameter', -2400, 300, Collection=MPC, ParameterName='ReduceMotion')         if MPC_ON else g.node('MaterialExpressionScalarParameter', -2400, 300, ParameterName='ReduceMotion', DefaultValue=0.0)
    m = g.node('MaterialExpressionOneMinus', -2160, 300)
    t = g.node('MaterialExpressionMultiply', -1980, 220)
    g.link(rm, m); g.link(time, t, inp='A'); g.link(m, t, inp='B')
    state = g.node('MaterialExpressionVectorParameter', -2400, 440, ParameterName='State', DefaultValue='(R=0,G=0,B=0,A=0)')
    calm = g.node('MaterialExpressionVectorParameter', -2400, 640, ParameterName='Calm',
                  DefaultValue='(R=0.28,G=1.0,B=0.0,A=1.0)')
    scale = g.node('MaterialExpressionScalarParameter', -2400, 840, ParameterName='Scale', DefaultValue=2.2)
    rev = g.node('MaterialExpressionScalarParameter', -2400, 940, ParameterName='Reveal', DefaultValue=1.0)
    glint = g.node('MaterialExpressionScalarParameter', -2400, 1040, ParameterName='Glint', DefaultValue=0.0)
    g.box('Material inputs', -2440, -260, 680, 1400, C_IN)
    # Selection: energy and echo for this word
    e = g.node('MaterialExpressionLinearInterpolate', -1700, 520)
    echo_amt = g.node('MaterialExpressionLinearInterpolate', -1700, 700)
    g.link(calm, e, inp='A', out='R'); g.link(calm, e, inp='B', out='G'); g.link(state, e, inp='Alpha', out='R')
    g.link(calm, echo_amt, inp='A', out='B'); g.link(calm, echo_amt, inp='B', out='A'); g.link(state, echo_amt, inp='Alpha', out='R')
    g.box('Word selection', -1740, 460, 300, 400, C_WORK)
    # Shape, grain, echo
    shape = g.node('MaterialExpressionMaterialFunctionCall', -1300, -200, function=f'{FN}/MF_UI_SandShape')
    for src, inp, out in ((tex, 'Glyphs', None), (noise, 'Noise', None), (uv, 'UV', None), (t, 'T', None), (m, 'M', None),
                          (scale, 'Scale', None), (e, 'E', None), (rev, 'Rev', None), (state, 'Out', 'A')):
        g.link(src, shape, inp=IN['MF_UI_SandShape'].index(inp), out=out)  # call pins read 'UV (V2)': link by index
    grain = g.node('MaterialExpressionMaterialFunctionCall', -1300, 260, function=f'{FN}/MF_UI_SandGrain')
    for src, inp, out in ((noise, 'Noise', None), (uv, 'UV', None), (t, 'T', None), (m, 'M', None), (scale, 'Scale', None),
                          (e, 'E', None), (shape, 'Edge', 'Edge'), (glint, 'Glint', None)):
        g.link(src, grain, inp=IN['MF_UI_SandGrain'].index(inp), out=out)
    echo = g.node('MaterialExpressionMaterialFunctionCall', -1300, 700, function=f'{FN}/MF_UI_TimeEcho')
    for src, inp, out in ((tex, 'Glyphs', None), (uv, 'UV', None), (t, 'T', None), (scale, 'Scale', None),
                          (echo_amt, 'Echo', None)):
        g.link(src, echo, inp=IN['MF_UI_TimeEcho'].index(inp), out=out)
    g.box('Sand letters', -1340, -260, 360, 1180, C_WORK)
    # Compose: premultiplied page output -> Translucent (straight) emissive + opacity
    vc = g.node('MaterialExpressionVertexColor', -900, -300)
    al = g.node('MaterialExpressionMultiply', -700, -200)
    g.link(shape, al, inp='A', out='Alpha'); g.link(vc, al, inp='B', out='A')
    inv = g.node('MaterialExpressionOneMinus', -520, 40)
    g.link(al, inv)
    ae0 = g.node('MaterialExpressionMultiply', -360, 120)
    g.link(echo, ae0, inp='A', out='Echo'); g.link(inv, ae0, inp='B')
    ae = g.node('MaterialExpressionMultiply', -200, 120)
    g.link(ae0, ae, inp='A'); g.link(vc, ae, inp='B', out='A')
    op = g.node('MaterialExpressionAdd', 0, 40)
    g.link(al, op, inp='A'); g.link(ae, op, inp='B')
    tone_al = g.node('MaterialExpressionMultiply', -360, -120)
    g.link(grain, tone_al, inp='A', out='Tone'); g.link(al, tone_al, inp='B')
    num = g.node('MaterialExpressionAdd', -200, -120)
    g.link(tone_al, num, inp='A'); g.link(ae, num, inp='B')
    ink = g.node('MaterialExpressionCollectionParameter', -200, -320, Collection=MPC, ParameterName='Ink') if MPC_ON else         g.node('MaterialExpressionVectorParameter', -200, -320, ParameterName='Ink', DefaultValue='(R=0.86,G=0.86,B=0.86,A=1.0)')
    inked = g.node('MaterialExpressionMultiply', 0, -200)
    g.link(ink, inked, inp='A', out=0); g.link(num, inked, inp='B')
    den = g.node('MaterialExpressionMax', 160, 40, ConstB=0.001)
    g.link(op, den, inp='A')
    col = g.node('MaterialExpressionDivide', 320, -160)
    g.link(inked, col, inp='A'); g.link(den, col, inp='B')
    hi = g.node('MaterialExpressionMultiply', 320, -340)
    g.link(grain, hi, inp='A', out='Highlight'); g.link(al, hi, inp='B')
    emis = g.node('MaterialExpressionAdd', 520, -220)
    g.link(col, emis, inp='A'); g.link(hi, emis, inp='B')
    g.link(emis, prop='emissive'); g.link(op, prop='opacity')
    g.box('Compose the word', -940, -380, 1600, 640, C_OUT)
    print(json.dumps(hb('material_validate', material_path=path))[:400])
    print(json.dumps(hb('material_compile', material_path=path))[:1200])
    for mi, params in (('MI_UI_SandText_Menu', {}),
                       ('MI_UI_SandText_Title', {'Calm': [0.0, 0.0, 0.55, 0.55], 'Scale': 9.0, 'Glint': 1.0})):
        r = send(SOCK, 'material_create_instance', {'parent_material_path': path, 'package_path': MAT, 'name': mi})
        if not r.get('ok') and 'already exists' not in json.dumps(r):
            raise RuntimeError(json.dumps(r)[:400])
        for k, v in params.items():
            hb('material_set_param', instance_path=f'{MAT}/{mi}', param_name=k, value=v)
        print('instance ok', mi)


def probe():
    """Learn the response formats on a throwaway function, then delete it (cleanup rule: TMP_ui_ prefix)."""
    hb('material_function_create', package_path=FN, name='TMP_ui_Probe')
    g = G(f'{FN}/TMP_ui_Probe', True)
    r = hb('material_add_node', function_path=g.path, expression_class='MaterialExpressionCustom', node_pos=[0, 0],
           properties={'Description': 'Probe', 'OutputType': 'CMOT_Float2', 'Code': 'return float2(A, B);',
                       'Inputs': '((InputName="A"),(InputName="B"))'})
    print(json.dumps(r, indent=1)[:1500])
    print(json.dumps(hb('material_get_info', function_path=g.path), indent=1)[:2500])


if __name__ == '__main__':
    probe() if '--probe' in sys.argv else build()
