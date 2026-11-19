"""M_IntroPlate v4 (intro lane): Hayba material tools only, edited in place and idempotent.
  $env:HAYBA_AGENT_ID='intro'; python Tools/LookDev/intro_v4/build_material_v4.py [--check]
Adds the Back texture parameter, the shared T_UI_SandNoise and MPC_UI.ReduceMotion (Calm), rewrites the Custom node from
Tools/LookDev/hlsl/intro_plate_v4.hlsl with the timing table from story.py, wires, validates, compiles (which saves).
--check only reads the graph back and asserts the wiring."""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/LookDev/intro_v4']
import hayba_call as h  # noqa: E402
from story import hlsl_table  # noqa: E402

P = '/Game/FoA/UI/Intro/M_IntroPlate'
BACK = '/Game/FoA/UI/Intro/Textures/T_IntroPlate_Room_Back.T_IntroPlate_Room_Back'
MPC = '/Game/FoA/UI/Style/MPC_UI.MPC_UI'
HLSL = Path('P:/FoA/Tools/LookDev/hlsl/intro_plate_v4.hlsl')
INPUTS = ['UV', 'Plate', 'Back', 'Noise', 'Age', 'Motion', 'Panel', 'Calm']
NOISE = '/Game/FoA/UI/Textures/T_UI_SandNoise.T_UI_SandNoise'  # the ui lane's shared noise pack, reused
OWNER = os.environ.setdefault('HAYBA_AGENT_ID', 'intro')


def c(cmd, **params):
    r = h.call(cmd, params, timeout=180)
    assert r.get('ok'), (cmd, r.get('error'), r.get('data'))
    d = r.get('data', {})
    assert d.get('ok', True) and not d.get('failed') and not d.get('has_errors'), (cmd, d)
    return d


def code():
    src = HLSL.read_text(encoding='utf-8')
    assert '// @@TABLE@@' in src
    return src.replace('// @@TABLE@@', hlsl_table())


def nodes():
    info = c('material_get_info', path=P)
    return info, {e['id']: e for e in info['expressions']}


def find(ex, cls, name=None):
    return next((i for i, e in ex.items() if e['class'] == cls and (name is None or name in json.dumps(e))), None)


def build():
    info, ex = nodes()
    custom = find(ex, 'MaterialExpressionCustom')
    uv, plate = find(ex, 'MaterialExpressionTextureCoordinate'), find(ex, 'MaterialExpressionTextureObjectParameter', '"Texture"')
    params = {n: find(ex, 'MaterialExpressionScalarParameter', f'"{n}"') for n in ('Age', 'Motion', 'Panel')}
    back = find(ex, 'MaterialExpressionTextureObjectParameter', '"Back"')
    if not back:
        back = c('material_add_node', material_path=P, expression_class='MaterialExpressionTextureObjectParameter',
                 node_pos=[-900, 150], properties={'ParameterName': 'Back', 'Texture': BACK,
                                                  'SamplerType': 'SAMPLERTYPE_LinearColor'})['node_id']
    noise = find(ex, 'MaterialExpressionTextureObject')  # the graph's only plain texture object (get_info omits its texture)
    if not noise:
        noise = c('material_add_node', material_path=P, expression_class='MaterialExpressionTextureObject',
                  node_pos=[-900, 225], properties={'Texture': NOISE, 'SamplerType': 'SAMPLERTYPE_LinearColor'})['node_id']
    calm = find(ex, 'MaterialExpressionCollectionParameter')
    if not calm:
        calm = c('material_add_node', material_path=P, expression_class='MaterialExpressionCollectionParameter',
                 node_pos=[-900, 560], properties={'Collection': MPC, 'ParameterName': 'ReduceMotion'})['node_id']
    assert all([custom, uv, plate, back, noise, calm, *params.values()]), (custom, uv, plate, back, noise, calm, params)
    c('material_set_node', material_path=P, node_id=custom, node_pos=[-480, 120],
      properties={'Description': 'Intro multiplane', 'OutputType': 'CMOT_Float4', 'Code': code(),
                  'Inputs': [{'InputName': n} for n in INPUTS]})
    src = {'UV': uv, 'Plate': plate, 'Back': back, 'Noise': noise, 'Age': params['Age'], 'Motion': params['Motion'],
           'Panel': params['Panel'], 'Calm': calm}
    for name in INPUTS:
        c('material_connect_nodes', material_path=P, from_node=src[name], to_node=custom, to_input=name, from_output_index=0)
    for i, (n, y) in enumerate([(uv, -120), (plate, 0), (back, 150), (noise, 225), (params['Age'], 300), (params['Motion'], 390),
                                (params['Panel'], 480), (calm, 570)]):
        c('material_set_node', material_path=P, node_id=n, node_pos=[-900, y])
    titles = {'Plate and clock': 'Plates and clock', 'Parallax and sand': 'Multiplane and sand'}
    for cm in info.get('comments', []):
        if cm['text'] in titles:
            c('material_set_comment', material_path=P, comment_id=cm['id'], text=titles[cm['text']])
    c('material_validate', material_path=P)
    r = c('material_compile', material_path=P)
    Path('P:/FoA/Saved/QA/lanes/intro_material_compile.json').write_text(json.dumps(r, indent=1))
    print('compiled', {k: r.get(k) for k in ('has_errors', 'saved', 'stats')})


def check():
    info, ex = nodes()
    custom = find(ex, 'MaterialExpressionCustom')
    print(json.dumps(ex[custom], indent=1)[:1500])


if __name__ == '__main__':
    assert not c('editor_get_state')['pie_running'], 'PIE running'
    (check if '--check' in sys.argv else build)()
