"""atmosphere lane: MPC_Dream Letterbox draws its bars again (level1 lane, 2026-11-18). BP_DreamDirector.SetLetterbox eases
MPC Letterbox 0..1 for story shots (T9's suit hero shot and others), but the shift-streak function that drew the bars was
removed in the content cleanup, so nothing read it. One small Custom node at the end of M_PP_DreamLens (after its film
finish, before the face blur and the UI) blacks out 2.39:1 bars, their height scaled by Letterbox so they slide in.
  python Tools/Unreal/pp_letterbox.py        (takes and releases its own lease; Hayba material tools only)
Editor-rules 9: M_PP_DreamLens leaves PP_DreamMono first and goes back in its slot. Idempotent: does nothing if the node
is there; on a failed compile its two nodes are removed and the old wire restored."""
import os
import sys

ROOT = 'P:/FoA'
sys.path.insert(0, ROOT + '/Tools/Unreal')
os.environ.update(HAYBA_AGENT_ID='atmosphere', FOA_AGENT='atmosphere', MSYS_NO_PATHCONV='1')
import pp_quality_paths as q  # noqa: E402  (blends, compiled, sh, call)

LENS = q.LENS
FINISH, UVNODE = 'MaterialExpressionMaterialFunctionCall_8', 'MaterialExpressionScreenPosition_8'
CODE = """// 2.39:1 bars for story shots: MPC Letterbox 0..1 slides them in (BP_DreamDirector.SetLetterbox)
float aspect = View.ViewSizeAndInvSize.x * View.ViewSizeAndInvSize.w;
float bar = 0.5 * saturate(1.0 - aspect / 2.39) * saturate(Letterbox);
return (UV.y < bar || UV.y > 1.0 - bar) ? float3(0.0, 0.0, 0.0) : Color;"""


def main():
    got = q.sh(ROOT + '/Tools/Unreal/editor_lock.py', 'acquire', 'atmosphere', '--areas', 'PostProcess', '--assets', LENS,
               '--actors', 'PP_DreamMono', '--ttl', '300')
    print(got)
    assert 'acquired' in got, 'no lease'
    made, ok = [], False
    try:
        info = q.call('material_get_info', path=LENS)
        if any(e['class'] == 'MaterialExpressionCustom' for e in info['expressions']):
            print('letterbox node already there')
            ok = True
            return
        q.blends('M_PP_DreamMono,FaceBlur/M_PP_FaceBlur')
        mpc = q.call('material_add_node', material_path=LENS, expression_class='MaterialExpressionCollectionParameter',
                     node_pos=[-400, 380], properties={'Collection': '/Game/FoA/PostProcess/MPC_Dream.MPC_Dream',
                                                       'ParameterName': 'Letterbox'})['node_id']
        made.append(mpc)
        box = q.call('material_add_node', material_path=LENS, expression_class='MaterialExpressionCustom', node_pos=[-150, 0],
                     properties={'Inputs': [{'InputName': 'Color'}, {'InputName': 'UV'}, {'InputName': 'Letterbox'}], 'Code': CODE,
                                 'OutputType': 'CMOT_Float3', 'Description': 'Letterbox bars'})['node_id']
        made.append(box)
        q.call('material_connect_nodes', material_path=LENS, from_node=FINISH, from_output='Color', to_node=box, to_input='Color')
        q.call('material_connect_nodes', material_path=LENS, from_node=UVNODE, from_output='ViewportUV', to_node=box, to_input='UV')
        q.call('material_connect_nodes', material_path=LENS, from_node=mpc, from_output_index=0, to_node=box, to_input='Letterbox')
        q.call('material_connect_nodes', material_path=LENS, from_node=box, from_output_index=0, to_property='EmissiveColor')
        ok = q.compiled(LENS)
        if not ok:
            q.call('material_connect_nodes', material_path=LENS, from_node=FINISH, from_output='Color', to_property='EmissiveColor')
            for n in made:
                q.call('material_delete_node', material_path=LENS, node_id=n)
            q.compiled(LENS)
            print('ROLLED BACK')
        print([ln for ln in q.sh(ROOT + '/Tools/Unreal/ue_remote.py', ROOT + '/Tools/Unreal/save_assets.py', f'FOA_ASSETS={LENS}',
                                 env=dict(FOA_AREAS='PostProcess')).splitlines() if 'FOA_SAVE' in ln])
    finally:
        q.blends('M_PP_DreamMono,M_PP_DreamLens,FaceBlur/M_PP_FaceBlur')
        print(q.sh(ROOT + '/Tools/Unreal/editor_lock.py', 'release', 'atmosphere'))
        print(q.sh(ROOT + '/Tools/Unreal/editor_lock.py', 'save_level', 'atmosphere'))
    assert ok, 'compile failed: rolled back'


if __name__ == '__main__':
    main()
