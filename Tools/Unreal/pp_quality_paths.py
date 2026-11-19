"""atmosphere lane: cheaper Low/Medium paths for the dream post-process (perf lane request, 2026-11-18), same look.
  python Tools/Unreal/pp_quality_paths.py            (Git Bash or PowerShell, from P:/FoA; takes and releases its lease)
1. MF_Dream_MonoTone's focus rim read three textures per tap at 8 taps (24 reads per pixel, every frame, though the
   rim only shows where a tap lands on stencil 3). Now each tap reads the stencil first and the two depths only on a
   stencil-3 hit: 8 reads per pixel almost everywhere, identical output.
2. The tap budgets' Quality Switches had no Medium input, so Medium paid the Epic count. Medium now takes the old Low
   count (echo 3, lens disc 8) and Low drops further (echo 2, lens disc 6). High and Epic keep 6 and 16.
Hayba C++ material tools only. Editor-rules 9: both dream materials leave PP_DreamMono before anything recompiles and
go back afterwards in the same order (M_PP_FaceBlur stays on). Saved only on clean compiles; otherwise the old
MonoTone code and wiring are restored. Level saved after."""
import json
import os
import subprocess
import sys

ROOT = 'P:/FoA'
sys.path.insert(0, ROOT + '/Tools/Unreal')
os.environ.update(HAYBA_AGENT_ID='atmosphere', FOA_AGENT='atmosphere', MSYS_NO_PATHCONV='1')
import hayba_call as h  # noqa: E402

PP = '/Game/FoA/PostProcess/'
MF = PP + 'Functions/MF_Dream_MonoTone'
MONO, LENS = PP + 'M_PP_DreamMono', PP + 'M_PP_DreamLens'
HERE = os.path.dirname(os.path.abspath(__file__))
NEW = open(os.path.join(HERE, 'hlsl', 'mf_dream_monotone.hlsl'), encoding='utf-8').read()
OLD = open(os.path.join(HERE, 'hlsl', 'mf_dream_monotone_before.hlsl'), encoding='utf-8').read()
# material, quality switch, the old Low constant (now Medium), new Low value, node position
TAPS = [(MONO, 'MaterialExpressionQualitySwitch_2', 'MaterialExpressionConstant_5', 2.0, [-1910, 590]),
        (LENS, 'MaterialExpressionQualitySwitch_2', 'MaterialExpressionConstant_5', 6.0, [-1610, 560])]


def call(cmd, **p):
    r = h.call(cmd, p, timeout=180)
    assert r.get('ok'), (cmd, r.get('error'))
    return r.get('data', {})


def sh(*args, env=None):
    r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True, env=dict(os.environ, **(env or {})))
    return (r.stdout + r.stderr).strip()


def blends(names):
    out = sh(ROOT + '/Tools/Unreal/ue_remote.py', ROOT + '/Tools/Unreal/pp_blendables.py', 'BLENDS=' + names,
             env=dict(FOA_AREAS='PostProcess', FOA_ACTORS='PP_DreamMono'))
    print([ln for ln in out.splitlines() if 'blendables' in ln][-1:])


def mf_code(code):
    """Set the MonoTone Custom node's code and finalize the function (material_compile on a function also saves it)."""
    call('material_set_node', function_path=MF, node_id='MaterialExpressionCustom_2', properties={'Code': code})
    v = call('material_validate', function_path=MF)
    assert v.get('ok', True) and not v.get('problems'), v
    call('material_compile', function_path=MF)


def compiled(path):
    v = call('material_validate', material_path=path)
    if v.get('problems') or not v.get('ok', True):
        print(path, 'validate', v)
        return False
    c = call('material_compile', material_path=path)
    print(path.rsplit('/', 1)[-1], 'compile', 'clean' if not c.get('has_errors') else 'ERRORS', c.get('stats', {}).get('shaders'),
          'samples', c.get('stats', {}).get('texture_samples'))
    return not c.get('has_errors')


def main():
    got = sh(ROOT + '/Tools/Unreal/editor_lock.py', 'acquire', 'atmosphere', '--areas', 'PostProcess', '--assets', MF, MONO, LENS,
             '--actors', 'PP_DreamMono', '--ttl', '400')
    print(got)
    assert 'acquired' in got, 'no lease'
    made, ok = [], False
    try:
        blends('FaceBlur/M_PP_FaceBlur')
        print('before:')
        compiled(MONO), compiled(LENS)
        print('after:')
        mf_code(NEW)
        ok = compiled(MONO)  # the function's code compiles inside its material
        for mat, sw, low, value, pos in TAPS:
            if not ok:
                break
            node = call('material_add_node', material_path=mat, expression_class='MaterialExpressionConstant', node_pos=pos,
                        properties={'R': value})['node_id']
            made.append((mat, node, sw, low))
            call('material_connect_nodes', material_path=mat, from_node=low, from_output_index=0, to_node=sw, to_input='Medium')
            call('material_connect_nodes', material_path=mat, from_node=node, from_output_index=0, to_node=sw, to_input='Low')
            ok = compiled(mat)
        if not ok:  # put the old code and wiring back, recompile, save nothing new
            mf_code(OLD)
            for mat, node, sw, low in made:
                call('material_connect_nodes', material_path=mat, from_node=low, from_output_index=0, to_node=sw, to_input='Low')
                call('material_delete_node', material_path=mat, node_id=node)
                call('material_disconnect', material_path=mat, to_node=sw, to_input='Medium')
            for mat in (MONO, LENS):
                compiled(mat)
            print('ROLLED BACK')
        print([ln for ln in sh(ROOT + '/Tools/Unreal/ue_remote.py', ROOT + '/Tools/Unreal/save_assets.py', f'FOA_ASSETS={MF},{MONO},{LENS}',
                                 env=dict(FOA_AREAS='PostProcess')).splitlines() if 'FOA_SAVE' in ln])
    finally:
        blends('M_PP_DreamMono,M_PP_DreamLens,FaceBlur/M_PP_FaceBlur')
        print(sh(ROOT + '/Tools/Unreal/editor_lock.py', 'release', 'atmosphere'))
        print(sh(ROOT + '/Tools/Unreal/editor_lock.py', 'save_level', 'atmosphere'))
    assert ok, 'compile failed: rolled back'


if __name__ == '__main__':
    main()
