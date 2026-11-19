"""Teen skin v2 on M_FoA_TeenSurface (Hayba C++ material calls only), run inside a lease on Teen/Materials:
  python Tools/Unreal/face/build_teen_skin.py import   # stage + import T_Teen_SkinMicro_N (normal map, 512)
  python Tools/Unreal/face/build_teen_skin.py graph    # Preintegrated Skin, packed response, micro normal
Was: Default Lit, constant roughness 0.65 and specular 0.3, no normal: flat, waxy, the terminator cut hard.
Now: Preintegrated Skin (cheap, no extra pass, fine for low-end), SkinResponse = (roughness, specular, scatter,
micro tiles), ScatterColor, and a tiled micro normal (MicroStrength) so hands in first person stop reading as plastic.
Children (MI_Teen_Skin, MI_Teen_Skin_Groom, MI_Teen_Tongue, MI_Teen_Lashes) inherit; nothing else changes."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

ROOT = '/Game/FoA/Characters/Teen/Materials'
M = ROOT + '/M_FoA_TeenSurface'
MP = {'material_path': M}
TEX = ROOT + '/T_Teen_SkinMicro_N'
SRC = Path('P:/FoA-Assets/character/skin/T_Teen_SkinMicro_N.png')


def call(cmd, **kw):
    r = hc.call(cmd, kw)
    assert r.get('ok'), (cmd, r)
    d = r.get('data', {})
    assert not d.get('errors'), (cmd, d)
    return d


def do_import():
    if not Path('P:/FoA/Content/FoA/Characters/Teen/Materials/T_Teen_SkinMicro_N.uasset').exists():
        stage = Path(tempfile.gettempdir()) / 'hayba-asset-connectors/FoA/teen_skin_micro'
        stage.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SRC, stage / SRC.name)
        call('asset_import', source_file=str(stage / SRC.name), destination_path=ROOT, asset_type='texture')
    print(call('texture_set_settings', path=TEX, properties={'srgb': False, 'compression_settings': 'TC_Normalmap',
                                                             'max_texture_size': 512}))
    print(call('asset_save', asset_paths=[TEX]))


def comments(info):
    """The old 'Character surface' box becomes 'Albedo'; two new boxes. Title only (editor rules)."""
    boxes = [('Albedo', [-760, -70], [700, 470], [0.25, 0.32, 0.35]),
             ('Skin response', [-760, 380], [420, 420], [0.35, 0.25, 0.2]),
             ('Micro normal', [-1160, 800], [1100, 520], [0.2, 0.3, 0.25])]
    old = info.get('comments', [])
    for i, (text, pos, size, col) in enumerate(boxes):
        if i < len(old):
            call('material_set_comment', **MP, comment_id=old[i]['id'], text=text, node_pos=pos, size=size, color=col,
                 show_bubble=True, color_bubble=True)
        else:
            call('material_add_comment', **MP, text=text, node_pos=pos, size=size, color=col)


def finish():
    """Resume after the comment step (first run stopped there)."""
    comments(call('material_get_info', path=M))
    print(call('material_validate', **MP))
    print(json.dumps(call('material_compile', **MP))[:600])


def graph():
    info = call('material_get_info', path=M)
    have = {e.get('parameter_name') for e in info['expressions'] if e.get('parameter_name')}
    assert 'SkinResponse' not in have, 'already built: edit the parameters on the instances instead'
    print(call('material_set_property', **MP, properties={'shading_model': 'MSM_PreintegratedSkin'}))

    def add(cls, pos, props):
        return call('material_add_node', **MP, expression_class='MaterialExpression' + cls, node_pos=pos, properties=props)['node_id']
    resp = add('VectorParameter', [-700, 420], {'ParameterName': 'SkinResponse', 'DefaultValue': {'R': 0.52, 'G': 0.35, 'B': 0.75, 'A': 22.0}})
    scat = add('VectorParameter', [-700, 640], {'ParameterName': 'ScatterColor', 'DefaultValue': {'R': 0.62, 'G': 0.24, 'B': 0.16, 'A': 1.0}})
    uv = add('TextureCoordinate', [-1100, 860], {})
    tiles = add('Multiply', [-900, 860], {})
    micro = add('TextureSampleParameter2D', [-700, 860], {'ParameterName': 'MicroNormal', 'Texture': TEX, 'SamplerType': 'SAMPLERTYPE_Normal'})
    flat = add('Constant3Vector', [-700, 1100], {'Constant': {'R': 0.0, 'G': 0.0, 'B': 1.0, 'A': 0.0}})
    amt = add('ScalarParameter', [-700, 1200], {'ParameterName': 'MicroStrength', 'DefaultValue': 0.55})
    blend = add('LinearInterpolate', [-360, 900], {})
    links = [(uv, 0, tiles, 'A'), (resp, 4, tiles, 'B'), (tiles, 0, micro, 'Coordinates'),
             (flat, 0, blend, 'A'), (micro, 0, blend, 'B'), (amt, 0, blend, 'Alpha')]
    for a, ai, b, pin in links:
        call('material_connect_nodes', **MP, from_node=a, from_output_index=ai, to_node=b, to_input=pin)
    for a, ai, prop in [(resp, 1, 'roughness'), (resp, 2, 'specular'), (resp, 3, 'opacity'), (scat, 0, 'subsurface_color'),
                        (blend, 0, 'normal')]:
        call('material_connect_nodes', **MP, from_node=a, from_output_index=ai, to_property=prop)
    for e in info['expressions']:
        if e['class'] == 'MaterialExpressionConstant':
            call('material_delete_node', **MP, node_id=e['id'])
    comments(info)
    print(call('material_validate', **MP))
    print(json.dumps(call('material_compile', **MP))[:600])


{'import': do_import, 'graph': graph, 'finish': finish}[sys.argv[1]]()
