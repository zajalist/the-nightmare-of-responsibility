"""Coordinator-approved <=40 s PIE proof; owns start/stop and restores every preference byte."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import argparse
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as hc

LANE='room-takeover-intro'
os.environ['HAYBA_AGENT_ID']=os.environ['FOA_AGENT']=LANE
os.environ['FOA_EXCLUSIVE']='1'
parser=argparse.ArgumentParser()
parser.add_argument('--art',action='store_true')
parser.add_argument('--variant',default='runtime_absorption')
args=parser.parse_args()
art=args.art
OUT=Path('P:/FoA/Saved/LookDev/intro_restored/'+('rice_ink/'+args.variant if art else 'runtime'))
(OUT/'frames').mkdir(parents=True,exist_ok=True)
def c(n,**p):
    r=hc.call(n,p); assert r.get('ok'),r
    return r.get('data',{})
assert not c('editor_get_state').get('pie_running')
prefs=Path('P:/FoA/Saved/SaveGames/Settings.sav')
original=prefs.read_bytes()
if (OUT/'proof.json').exists():(OUT/'proof.json').unlink()
started=False
token=hc.lease_acquire(LANE,['global'],ttl_s=65,wait_s=20)
try:
    assert not c('editor_get_state').get('pie_running'),'PIE started while waiting for the lease'
    for path in ('/Game/FoA/UI/Game/WBP_HUD','/Game/FoA/UI/Intro/WBP_IntroStory'):
        status=c('object_get_property',path=path,names=['Status']).get('properties',{}).get('Status','')
        assert 'Error' not in status, (path,status)
    c('editor_start_pie')
    started=True
    time.sleep(1)
    p=subprocess.run([sys.executable,'Tools/Unreal/integration/run_read.py','Tools/LookDev/intro_runtime_probe.py']+(['FOA_INTRO_ART_REVIEW=1','FOA_INTRO_ART_OUTPUT='+args.variant] if art else []),capture_output=True,text=True,timeout=8)
    print(p.stdout,p.stderr,flush=True); assert p.returncode==0
    start=time.monotonic()
    while time.monotonic()-start<(25 if art else 24):
        time.sleep(.5)
        if (OUT/'proof.json').exists():
            result=json.loads((OUT/'proof.json').read_text())
            assert not result.get('error'),result
    key=c('editor_pie_press_key',key='SpaceBar')
    (OUT/'skip_key.json').write_text(json.dumps(key,indent=2))
    print('Skip input:',key,flush=True)
    time.sleep(max(0,33-(time.monotonic()-start)))
finally:
    if started and c('editor_get_state').get('pie_running'):c('editor_stop_pie')
    if started:
        prefs.write_bytes(original)
        assert prefs.read_bytes()==original,'Could not restore exact saved preferences'
        print('Stopped owned PIE; settings unchanged',flush=True)
    hc.release(LANE,token)
result=json.loads((OUT/'proof.json').read_text())
assert result['error'] is None,result
rows=result['rows']
assert len({r['panel'] for r in rows})>=3,'Panels did not advance'
if art:assert set(r['panel'] for r in rows if not r['done'])==set(range(8)),'Art review did not cover all eight panels'
moving=[r for r in rows if r['panel']==0 and r['reduce']==0]
assert max(r['far']['x'] for r in moving)-min(r['far']['x'] for r in moving)>1,'Far layer did not move'
reduced=[r for r in rows if r['reduce']==1 and 12.5<r['t']<14.9]
assert reduced and all(r['motion']==0 and r['far']['x']==0 for r in reduced),'Reduced motion failed'
layered=[r for r in rows if r['panel']>0 and r['reduce']==0 and r['near']['alpha']>.1]
assert layered and any(abs(r['near']['x']-r['far']['x'])>1 for r in layered),'Separated layers did not move at different depths'
assert any(abs(r['near']['x']-r['far']['x'])>35 for r in layered),'Stronger ink parallax displacement was not observed'
assert all(r['far']['texture'].startswith('T_Intro_Game') and r['near']['texture'].startswith('T_Intro_Game') for r in rows),'Old concept art remains referenced'
assert all(r['far']['reveal'] is not None and r['near']['reveal'] is not None for r in rows),'Ink material instances are not bound'
assert any(0<r['far']['reveal']<1 for r in rows if not r['done'] and r['reduce']==0),'Animated ink reveal was not observed'
assert all(r['far']['reveal']==1 and r['near']['reveal']==1 for r in reduced),'Reduced motion did not bypass the ink reveal'
assert rows[-1]['done'] and not rows[-1]['in_viewport'] and rows[-1]['gameplay'],'Skip failed to hand back to gameplay'
print('PASS: real-game ink material bindings, strong separated depth motion, animated reveal, advance, reduced motion, focused skip and gameplay handoff')
