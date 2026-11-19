"""atmosphere lane: a cheaper Low path for the dream post-process (coordinator 11-18 15:10; the GTX 1060 Low fight).
  python Tools/Unreal/pp_low_branch.py            (takes and releases its own lease; Hayba material tools only)
  python Tools/Unreal/pp_low_branch.py revert     (puts the old wiring back)
Material quality Low (r.MaterialQualityLevel 0, which the Low preset sets through sg.EffectsQuality 0) takes:
  M_PP_DreamMono  SandFXAmount 0 into MF_Dream_SandWarp: its heat-haze UV warp around the black sand returns at once
                  (it reads 25 textures a pixel: 8 taps x stencil, custom depth and depth, plus the centre depth);
                  EchoStrength 0 into MF_Dream_TimeEcho: the time-shift ghosts return the plain pixel (10 reads to 1).
                  The mono grade, the stencil-1 colour keep, the focus rim and the face blur are untouched.
  M_PP_DreamLens  the halation and edge-haze disc at 4 taps (the function's minimum; Low was 6, Medium 8, High 16).
Both are Quality Switches whose Default input is the old wire, so Medium, High and Epic compile the same code as before.
Editor-rules 9: both materials leave PP_DreamMono first and go back in the same order. On a failed compile the old
wiring is put back. The level is saved after."""
import os
import sys

ROOT = 'P:/FoA'
sys.path.insert(0, ROOT + '/Tools/Unreal')
os.environ.update(HAYBA_AGENT_ID='atmosphere', FOA_AGENT='atmosphere', MSYS_NO_PATHCONV='1')
import pp_quality_paths as q  # noqa: E402  (blends, compiled, sh, call)

MONO, LENS = q.MONO, q.LENS
ECHO_CALL, SAND_CALL = 'MaterialExpressionMaterialFunctionCall_12', 'MaterialExpressionMaterialFunctionCall_0'
ECHO_MPC, SAND_MPC = 'MaterialExpressionCollectionParameter_36', 'MaterialExpressionCollectionParameter_1'
LENS_LOW = 'MaterialExpressionConstant_0'  # the lens disc's Low tap count (pp_quality_paths made it 6)


def mono_low():
    """Two Quality Switches (Default = the old MPC wire, Low = one shared 0) and a title-only comment. Returns the new ids."""
    made = []
    zero = q.call('material_add_node', material_path=MONO, expression_class='MaterialExpressionConstant',
                  node_pos=[-2160, -60], properties={'R': 0.0})['node_id']
    made.append(zero)
    for name, mpc, fn, pos in (('sand', SAND_MPC, SAND_CALL, [-2160, -200]), ('echo', ECHO_MPC, ECHO_CALL, [-1600, 200])):
        sw = q.call('material_add_node', material_path=MONO, expression_class='MaterialExpressionQualitySwitch', node_pos=pos)['node_id']
        made.append(sw)
        q.call('material_connect_nodes', material_path=MONO, from_node=mpc, from_output_index=0, to_node=sw, to_input='Default')
        q.call('material_connect_nodes', material_path=MONO, from_node=zero, from_output_index=0, to_node=sw, to_input='Low')
        q.call('material_connect_nodes', material_path=MONO, from_node=sw, from_output_index=0, to_node=fn, to_input_index=1)
    return made


def revert_mono(made):
    q.call('material_connect_nodes', material_path=MONO, from_node=SAND_MPC, from_output_index=0, to_node=SAND_CALL, to_input_index=1)
    q.call('material_connect_nodes', material_path=MONO, from_node=ECHO_MPC, from_output_index=0, to_node=ECHO_CALL, to_input_index=1)
    for n in made:
        q.call('material_delete_node', material_path=MONO, node_id=n)


def main(revert=False):
    got = q.sh(ROOT + '/Tools/Unreal/editor_lock.py', 'acquire', 'atmosphere', '--areas', 'PostProcess', '--assets', MONO, LENS,
               '--actors', 'PP_DreamMono', '--ttl', '300')
    print(got)
    assert 'acquired' in got, 'no lease'
    ok = False
    try:
        q.blends('FaceBlur/M_PP_FaceBlur')
        if revert:
            info = q.call('material_get_info', path=MONO)
            made = [e['id'] for e in info['expressions'] if e['class'] == 'MaterialExpressionQualitySwitch'
                    and e['id'] != 'MaterialExpressionQualitySwitch_2']
            made += [e['id'] for e in info['expressions'] if e['class'] == 'MaterialExpressionConstant' and e.get('x') == -2160]
            revert_mono(made)
            q.call('material_set_node', material_path=LENS, node_id=LENS_LOW, properties={'R': 6.0})
            ok = q.compiled(MONO) and q.compiled(LENS)
        else:
            made = mono_low()
            q.call('material_set_node', material_path=LENS, node_id=LENS_LOW, properties={'R': 4.0})
            ok = q.compiled(MONO) and q.compiled(LENS)
            if not ok:
                revert_mono(made)
                q.call('material_set_node', material_path=LENS, node_id=LENS_LOW, properties={'R': 6.0})
                q.compiled(MONO), q.compiled(LENS)
                print('ROLLED BACK')
        print([ln for ln in q.sh(ROOT + '/Tools/Unreal/ue_remote.py', ROOT + '/Tools/Unreal/save_assets.py', f'FOA_ASSETS={MONO},{LENS}',
                                 env=dict(FOA_AREAS='PostProcess')).splitlines() if 'FOA_SAVE' in ln])
    finally:
        q.blends('M_PP_DreamMono,M_PP_DreamLens,FaceBlur/M_PP_FaceBlur')
        print(q.sh(ROOT + '/Tools/Unreal/editor_lock.py', 'release', 'atmosphere'))
        print(q.sh(ROOT + '/Tools/Unreal/editor_lock.py', 'save_level', 'atmosphere'))
    assert ok, 'compile failed: rolled back'


if __name__ == '__main__':
    main(revert=sys.argv[1:] == ['revert'])
