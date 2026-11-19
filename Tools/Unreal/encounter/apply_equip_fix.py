"""Story lane: apply the equip-flight fix in order (no PIE). fix_equip_flight.py steps through ue_remote, a Hayba
compile (+ save) of both Blueprints after each, then fix_equip_rewire.py. Stops at the first failure.
  python Tools/Unreal/encounter/apply_equip_fix.py [declare garment encounter rewire]"""
import os
import subprocess
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h  # noqa: E402

ROOT = 'P:/FoA'
GB = '/Game/FoA/Gameplay/Encounter/BP_Garment'
EB = '/Game/FoA/Gameplay/Encounter/BP_Encounter'
os.environ.update(HAYBA_AGENT_ID='story', FOA_AGENT='story', FOA_CALLER='story', MSYS_NO_PATHCONV='1',
                  FOA_AREAS='/Game/FoA/Gameplay/Encounter')


def compile_save(*paths):
    for p in paths:
        c = h.call('blueprint_compile', dict(path=p), owner='story', timeout=120)
        d = c.get('data') or {}
        print('compile', p.rsplit('/', 1)[1], c.get('ok'), d.get('error_count'), [str(e)[:200] for e in (d.get('errors') or [])][:5],
              flush=True)
        assert c.get('ok') and not d.get('error_count'), c
        s = h.call('asset_save', dict(asset_paths=[p]), owner='story', timeout=60)
        assert s.get('ok'), s


def remote(step):
    r = subprocess.run([sys.executable, ROOT + '/Tools/Unreal/ue_remote.py', ROOT + '/Tools/Unreal/encounter/fix_equip_flight.py',
                        'FOA_STEP=' + step], cwd=ROOT, capture_output=True, text=True, timeout=600)
    out = (r.stdout + r.stderr).strip()
    print(step, out[-3000:], flush=True)
    assert r.returncode == 0 and step + ' ok' in out, step


assert not h.call('editor_get_state', {}, owner='story')['data']['pie_running'], 'PIE running'
steps = sys.argv[1:] or ['declare', 'garment', 'encounter', 'rewire']
for step in steps:
    if step == 'rewire':
        r = subprocess.run([sys.executable, ROOT + '/Tools/Unreal/encounter/fix_equip_rewire.py'], cwd=ROOT,
                           capture_output=True, text=True, timeout=300)
        print('rewire', (r.stdout + r.stderr)[-2000:], flush=True)
        assert r.returncode == 0, 'rewire'
        compile_save(GB, EB)
        continue
    remote(step)
    compile_save(*{'declare': (GB, EB), 'garment': (GB,), 'encounter': (EB,)}[step])
print('applied', steps)
