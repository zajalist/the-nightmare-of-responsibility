"""The phone screen's glass (Hayba): M_UI_PhoneScreen, the WidgetComponent's masked material.
Surface, Masked, Unlit. One Custom node (hlsl/phone_glass.hlsl): the widget render target ('SlateUI', set by the
WidgetComponent) times Nits, rounded screen corners as the opacity mask, a faint edge falloff, and a glass sheen from
Fresnel and the reflection vector that carries fingerprint smudges (T_UI_SandNoise.B), so smudges show only where the
glass catches light.
  python Tools/Unreal/ui/aaa_phone_glass.py mat"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

M = '/Game/FoA/UI/Materials/M_UI_PhoneScreen'


def c(cmd, **p):
    r = hc.call(cmd, p)
    d = r.get('data') or {}
    print(cmd, p.get('expression_class', p.get('property', '')), r.get('ok'), d.get('node_id', ''), d.get('error') or r.get('error') or '',
          json.dumps(d.get('stats') or '')[:200])
    return d


def mat():
    if hc.call('material_get_info', {'path': M}).get('ok'):
        sys.exit('exists')
    c('material_create', package_path='/Game/FoA/UI/Materials', name='M_UI_PhoneScreen')
    # domain and blend on the EMPTY material (a domain change mid-compile crashed the editor)
    c('material_set_property', material_path=M, properties={'domain': 'EMaterialDomain::MD_Surface', 'blend_mode': 'BLEND_Masked',
                                                            'shading_model': 'MSM_Unlit', 'two_sided': False})
    code = open('P:/FoA/Tools/Unreal/ui/hlsl/phone_glass.hlsl').read()
    assert not any(ch in code for ch in "'\"`") and '//' not in code
    n = {}
    n['uv'] = c('material_add_node', material_path=M, expression_class='MaterialExpressionTextureCoordinate', node_pos=[-1200, -200])['node_id']
    n['ui'] = c('material_add_node', material_path=M, expression_class='MaterialExpressionTextureSampleParameter2D', node_pos=[-1000, -300],
                properties={'ParameterName': 'SlateUI', 'Texture': '/Engine/EngineResources/WhiteSquareTexture.WhiteSquareTexture'})['node_id']
    n['nits'] = c('material_add_node', material_path=M, expression_class='MaterialExpressionScalarParameter', node_pos=[-1000, -120],
                  properties={'ParameterName': 'Nits', 'DefaultValue': 1.35})['node_id']
    n['size'] = c('material_add_node', material_path=M, expression_class='MaterialExpressionConstant2Vector', node_pos=[-1000, -40],
                  properties={'R': 540.0, 'G': 1201.0})['node_id']
    n['rad'] = c('material_add_node', material_path=M, expression_class='MaterialExpressionConstant', node_pos=[-1000, 40],
                 properties={'R': 46.0})['node_id']
    n['noise'] = c('material_add_node', material_path=M, expression_class='MaterialExpressionTextureObject', node_pos=[-1000, 120],
                   properties={'Texture': '/Game/FoA/UI/Textures/T_UI_SandNoise.T_UI_SandNoise'})['node_id']
    n['refl'] = c('material_add_node', material_path=M, expression_class='MaterialExpressionReflectionVectorWS', node_pos=[-1000, 220])['node_id']
    n['fres'] = c('material_add_node', material_path=M, expression_class='MaterialExpressionFresnel', node_pos=[-1000, 300],
                  properties={'Exponent': 4.0, 'BaseReflectFraction': 0.04})['node_id']
    n['glass'] = c('material_add_node', material_path=M, expression_class='MaterialExpressionVectorParameter', node_pos=[-1000, 400],
                   properties={'ParameterName': 'Glass', 'DefaultValue': {'R': 0.05, 'G': 0.05, 'B': 0.05, 'A': 1.4}})['node_id']
    n['cus'] = c('material_add_node', material_path=M, expression_class='MaterialExpressionCustom', node_pos=[-640, 0],
                 properties={'Description': 'Phone glass', 'OutputType': 'CMOT_Float4', 'Code': code,
                             'Inputs': [{'InputName': k} for k in ('UV', 'Ui', 'Nits', 'Size', 'Radius', 'Noise', 'Refl', 'Fres', 'Glass')]})['node_id']
    n['rgb'] = c('material_add_node', material_path=M, expression_class='MaterialExpressionComponentMask', node_pos=[-380, -40],
                 properties={'R': True, 'G': True, 'B': True, 'A': False})['node_id']
    n['a'] = c('material_add_node', material_path=M, expression_class='MaterialExpressionComponentMask', node_pos=[-380, 80],
               properties={'R': False, 'G': False, 'B': False, 'A': True})['node_id']
    for src, out, dst in (('uv', None, 'UV'), ('ui', 'RGB', 'Ui'), ('nits', None, 'Nits'), ('size', None, 'Size'), ('rad', None, 'Radius'),
                          ('noise', None, 'Noise'), ('refl', None, 'Refl'), ('fres', None, 'Fres'), ('glass', None, 'Glass')):
        kw = {'from_output': out} if out else {}
        c('material_connect_nodes', material_path=M, from_node=n[src], to_node=n['cus'], to_input=dst, **kw)
    c('material_connect_nodes', material_path=M, from_node=n['uv'], to_node=n['ui'], to_input='UVs')
    c('material_connect_nodes', material_path=M, from_node=n['cus'], to_node=n['rgb'], to_input='Input')
    c('material_connect_nodes', material_path=M, from_node=n['cus'], to_node=n['a'], to_input='Input')
    c('material_connect_nodes', material_path=M, from_node=n['rgb'], to_property='emissive_color')
    c('material_connect_nodes', material_path=M, from_node=n['a'], to_property='opacity_mask')
    c('material_add_comment', material_path=M, text='Screen inputs', node_pos=[-1488, -704], size=[760, 688])
    c('material_add_comment', material_path=M, text='Glass inputs', node_pos=[-1488, 32], size=[760, 620])
    c('material_add_comment', material_path=M, text='Phone glass', node_pos=[-704, -208], size=[640, 460])
    c('material_validate', material_path=M)
    c('material_compile', material_path=M)


{'mat': mat}[sys.argv[1]]()
