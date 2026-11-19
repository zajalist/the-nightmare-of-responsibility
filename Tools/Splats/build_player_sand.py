"""Build the player's skin/sand overlay with Hayba C++ tools; no editor Python.

  python Tools/Splats/build_player_sand.py
Amount: 0 clears, .06 gives sparse body patches, 1 forces full sand for transitions.
Run only after PIE ends. The existing player owns overlay assignment and splat attachment.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools/Unreal'))
import hayba_call as hc

MAT = '/Game/FoA/VFX/Sand/M_SandOverlay'
OWNER = 'codex-sand'


def main():
    state = hc.call('editor_get_state')
    assert state.get('ok') and not state['data']['pie_running'], 'Exit PIE before changing materials'
    token = hc.lease_acquire(OWNER, ['asset:/Game/FoA/VFX'], ttl_s=90, wait_s=20)
    transcript = []

    def call(cmd, **params):
        r = hc.call(cmd, params, owner=OWNER, lease=token, timeout=40)
        transcript.append({'cmd': cmd, 'params': params, 'response': r})
        assert r.get('ok'), f'{cmd}: {r}'
        return r.get('data', {})

    try:
        info = hc.call('material_get_info', {'path': MAT})
        if not info.get('ok'):
            call('material_create', package_path='/Game/FoA/VFX/Sand', name='M_SandOverlay')
        expressions = call('material_get_info', path=MAT).get('expressions', [])
        if not expressions:
            call('material_set_property', material_path=MAT, properties={
                'blend_mode': 'Masked', 'shading_model': 'DefaultLit',
                'opacity_mask_clip_value': 0.35})
            call('material_set_property', material_path=MAT, properties={'used_with_skeletal_meshes': True})

        def node(cls, xy, **props):
            old = next((n for n in expressions if n['class'].endswith(cls)
                        and [n.get('x'), n.get('y')] == xy), None)
            if old:
                if props:
                    call('material_set_node', material_path=MAT, node_id=old['id'], properties=props)
                return old['id']
            return call('material_add_node', material_path=MAT, expression_class=cls,
                        node_pos=xy, properties=props)['node_id']

        pos = node('MaterialExpressionPreSkinnedPosition', [-1050, 0])
        pixel_pos = node('MaterialExpressionVertexInterpolator', [-820, 0])
        call('material_connect_nodes', material_path=MAT, from_node=pos, to_node=pixel_pos, to_input_index=0)
        clock = node('MaterialExpressionTime', [-1050, 180])
        amount = node('MaterialExpressionScalarParameter', [-1050, 340], ParameterName='Amount', DefaultValue=0.06)
        reduce = node('MaterialExpressionCollectionParameter', [-1050, 520],
                      Collection='/Game/FoA/PostProcess/MPC_Dream.MPC_Dream', ParameterName='ReduceMotion')
        transition = node('MaterialExpressionScalarParameter', [-1050, 700], ParameterName='Transition', DefaultValue=0.0)
        inputs = [{'InputName': n} for n in ('P', 'Clock', 'Amount', 'ReduceMotion', 'Transition')]
        shell = node('MaterialExpressionCustom', [-600, 0], Description='Sand coverage', OutputType='CMOT_Float4',
                     Code=(ROOT / 'Tools/Splats/hlsl/skin_sand.hlsl').read_text(), Inputs=inputs)
        slip = node('MaterialExpressionCustom', [-600, 400], Description='Sand slices', OutputType='CMOT_Float3',
                    Code=(ROOT / 'Tools/Splats/hlsl/skin_sand_slip.hlsl').read_text(), Inputs=inputs)
        for target in (shell, slip):
            for src, pin in zip((pixel_pos if target == shell else pos, clock, amount, reduce, transition),
                                ('P', 'Clock', 'Amount', 'ReduceMotion', 'Transition')):
                call('material_connect_nodes', material_path=MAT, from_node=src, to_node=target, to_input=pin)
        rgb = node('MaterialExpressionComponentMask', [-300, 0], R=True, G=True, B=True, A=False)
        alpha = node('MaterialExpressionComponentMask', [-300, 180], R=False, G=False, B=False, A=True)
        rough = node('MaterialExpressionConstant', [-300, 570], R=0.78)
        spec = node('MaterialExpressionConstant', [-300, 730], R=0.22)
        for target in (rgb, alpha):
            call('material_connect_nodes', material_path=MAT, from_node=shell, to_node=target, to_input='Input')
        for src, prop in ((rgb, 'base_color'), (alpha, 'opacity_mask'), (slip, 'world_position_offset'),
                          (rough, 'roughness'), (spec, 'specular')):
            call('material_connect_nodes', material_path=MAT, from_node=src, to_property=prop)
        info = call('material_get_info', path=MAT)
        if not info.get('comments'):
            call('material_add_comment', material_path=MAT, text='Skin into sand',
                 node_pos=[-1110, -80], size=[1080, 960], color=[0.15, 0.18, 0.22])
        valid = call('material_validate', material_path=MAT)
        assert valid.get('ok') and not valid.get('problems'), valid
        result = call('material_compile', material_path=MAT)
        assert not result.get('has_errors') and not result.get('errors') and result.get('saved'), result
        drift = '/Game/FoA/VFX/Splats/Instances/MI_Sand_FaceDrift'
        call('material_set_param', instance_path=drift, param_name='Glitch', value=0.04)
        call('material_set_param', instance_path=drift, param_name='TimeCfg', value=[1.0, 0.0, -1.0, 3.2])
        print(json.dumps({'material': MAT, 'compile': result, 'nodes': len(info['expressions'])}))
    finally:
        out = ROOT / 'Saved/SandShots/player_sand_build.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(transcript, indent=2))
        hc.release(OWNER, token)


if __name__ == '__main__':
    main()
