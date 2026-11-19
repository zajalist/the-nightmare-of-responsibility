"""atmosphere lane: push Tools/Unreal/hlsl/mf_dream_monotone.hlsl into MF_Dream_MonoTone's Custom node, safely.
  python Tools/Unreal/pp_monotone_code.py
Editor-rules 9: M_PP_DreamMono leaves PP_DreamMono first and goes back in its slot afterwards. The live code is read
before the change; if M_PP_DreamMono does not compile clean it is put back and recompiled. Hayba material tools only
for the change (editor Python only reads the old code). One lease, released on every path; level saved after."""
import os
import subprocess
import sys

ROOT = 'P:/FoA'
sys.path.insert(0, ROOT + '/Tools/Unreal')
os.environ.update(HAYBA_AGENT_ID='atmosphere', FOA_AGENT='atmosphere', MSYS_NO_PATHCONV='1')
import pp_quality_paths as q  # noqa: E402  (blends, compiled, mf_code, sh, call)

HERE = os.path.dirname(os.path.abspath(__file__))
NEW = open(os.path.join(HERE, 'hlsl', 'mf_dream_monotone.hlsl'), encoding='utf-8').read()
READ = os.path.join(HERE, 'hlsl', '_read_monotone.py')
SAVED = 'P:/FoA/Saved/QA/atmosphere/mf_dream_monotone_live_before.hlsl'


def main():
    got = q.sh(ROOT + '/Tools/Unreal/editor_lock.py', 'acquire', 'atmosphere', '--areas', 'PostProcess', '--assets', q.MF, q.MONO,
               '--actors', 'PP_DreamMono', '--ttl', '300')
    print(got)
    assert 'acquired' in got, 'no lease'
    ok = False
    try:
        print(q.sh(ROOT + '/Tools/Unreal/integration/run_read.py', READ, 'OUT=' + SAVED).splitlines()[-1:])
        old = open(SAVED, encoding='utf-8').read()
        assert 'MT_VS' in old, 'could not read the live code'
        q.blends('M_PP_DreamLens,FaceBlur/M_PP_FaceBlur')
        q.mf_code(NEW)
        ok = q.compiled(q.MONO)
        if not ok:
            q.mf_code(old)
            q.compiled(q.MONO)
            print('ROLLED BACK')
        print([ln for ln in q.sh(ROOT + '/Tools/Unreal/ue_remote.py', ROOT + '/Tools/Unreal/save_assets.py', f'FOA_ASSETS={q.MF},{q.MONO}',
                                 env=dict(FOA_AREAS='PostProcess')).splitlines() if 'FOA_SAVE' in ln])
    finally:
        q.blends('M_PP_DreamMono,M_PP_DreamLens,FaceBlur/M_PP_FaceBlur')
        print(q.sh(ROOT + '/Tools/Unreal/editor_lock.py', 'release', 'atmosphere'))
        print(q.sh(ROOT + '/Tools/Unreal/editor_lock.py', 'save_level', 'atmosphere'))
    assert ok, 'compile failed: rolled back'


if __name__ == '__main__':
    main()
