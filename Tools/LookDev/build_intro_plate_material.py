"""M_IntroPlate (story lane): the intro's one UI material. Hayba material tools only; idempotent (creates the asset once,
then rewrites the Custom node's HLSL from Tools/LookDev/hlsl/intro_plate.hlsl).
  python Tools/LookDev/build_intro_plate_material.py
Parameters: Texture (the packed plate; the name WBP_IntroStory.NextPanel already sets), Age, Motion, Panel."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h  # noqa: E402

ROOT = '/Game/FoA/UI/Intro'
P = ROOT + '/M_IntroPlate'
HLSL = Path('P:/FoA/Tools/LookDev/hlsl/intro_plate.hlsl')
FIRST = '/Game/FoA/UI/Intro/Textures/T_IntroPlate_Room'
OWNER = 'story'


def main():
    os.environ['HAYBA_AGENT_ID'] = OWNER
    token = h.lease_acquire(OWNER, ['asset:' + P], ttl_s=120, wait_s=60)

    def c(cmd, **params):
        r = h.call(cmd, params, owner=OWNER, lease=token, timeout=90)
        assert r.get('ok'), (cmd, r)
        d = r.get('data', {})
        assert d.get('ok', True) and not d.get('failed') and not d.get('has_errors'), (cmd, d)
        return d

    try:
        assert not c('editor_get_state')['pie_running'], 'PIE running'
        if not Path('P:/FoA/Content/FoA/UI/Intro/M_IntroPlate.uasset').exists():
            c('material_create', package_path=ROOT, name='M_IntroPlate')
            c('material_set_property', material_path=P, properties={'domain': 'EMaterialDomain::MD_UI',
                                                                    'blend_mode': 'BLEND_Translucent'})
        info = c('material_get_info', path=P)
        custom = [e for e in info['expressions'] if e['class'] == 'MaterialExpressionCustom']
        if custom:
            c('material_set_node', material_path=P, node_id=custom[0]['id'], properties={'Code': HLSL.read_text()})
        else:
            def node(cls, x, y, **props):
                return c('material_add_node', material_path=P, expression_class=cls, node_pos=[x, y], properties=props)['node_id']
            uv = node('MaterialExpressionTextureCoordinate', -900, -120)
            plate = node('MaterialExpressionTextureObjectParameter', -900, 40, ParameterName='Texture', Texture=FIRST,
                         SamplerType='SAMPLERTYPE_LinearColor')
            age = node('MaterialExpressionScalarParameter', -900, 260, ParameterName='Age', DefaultValue=2.0)
            motion = node('MaterialExpressionScalarParameter', -900, 360, ParameterName='Motion', DefaultValue=0.0)
            panel = node('MaterialExpressionScalarParameter', -900, 460, ParameterName='Panel', DefaultValue=0.0)
            fx = node('MaterialExpressionCustom', -480, 120, Description='Intro plate', OutputType='CMOT_Float4',
                      Code=HLSL.read_text(), Inputs=[{'InputName': n} for n in ('UV', 'Plate', 'Age', 'Motion', 'Panel')])
            for src, name in zip((uv, plate, age, motion, panel), ('UV', 'Plate', 'Age', 'Motion', 'Panel')):
                c('material_connect_nodes', material_path=P, from_node=src, to_node=fx, to_input=name, from_output_index=0)
            rgb = node('MaterialExpressionComponentMask', -160, 60, R=True, G=True, B=True, A=False)
            alpha = node('MaterialExpressionComponentMask', -160, 220, R=False, G=False, B=False, A=True)
            for n in (rgb, alpha):
                c('material_connect_nodes', material_path=P, from_node=fx, to_node=n, to_input='Input')
            c('material_connect_nodes', material_path=P, from_node=rgb, to_property='emissive')
            c('material_connect_nodes', material_path=P, from_node=alpha, to_property='opacity')
            for title, xy, size in [('Plate and clock', [-960, -190], [330, 760]), ('Parallax and sand', [-540, 40], [330, 260]),
                                    ('Out', [-200, 0], [260, 340])]:
                c('material_add_comment', material_path=P, text=title, node_pos=xy, size=size, color=[0.18, 0.18, 0.18])
        c('material_validate', material_path=P)
        result = c('material_compile', material_path=P)
        assert not result.get('errors'), result
        c('asset_save', asset_paths=[P])
        Path('P:/FoA/Saved/StoryShots/intro_material_compile.json').write_text(json.dumps(result, indent=1))
        print('M_IntroPlate compiled', {k: result.get(k) for k in ('ok', 'errors', 'num_instructions', 'instruction_count')})
    finally:
        h.release(OWNER, token)


if __name__ == '__main__':
    main()
