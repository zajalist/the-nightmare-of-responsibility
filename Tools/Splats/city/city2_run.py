"""Small asset batches and guarded <=60-second city map switches."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
sys.dont_write_bytecode=True
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import editor_lock
import hayba_call as h
ROOT='/Game/FoA/Level2/City/Expanded'
OUT=Path('P:/FoA/Saved/Codex/city2');OUT.mkdir(parents=True,exist_ok=True)
SRC=Path('P:/FoA-Assets/level2/toronto/processed/queen_1600m')
SCRIPT='Tools/Splats/city/city2_ue.py'
os.environ.update(FOA_AGENT='city2',HAYBA_AGENT_ID='city2',FOA_CALLER='city2',FOA_AREAS=ROOT)


def run(step,**args):
    h.renew_all('city2',70)
    cmd=[sys.executable,'Tools/Unreal/ue_remote.py',SCRIPT,'CITY2_STEP='+step]
    cmd += [f'CITY2_{k.upper()}={v}' for k,v in args.items()]
    p=subprocess.run(cmd,capture_output=True,text=True)
    print(p.stdout[-2400:],flush=True)
    assert p.returncode==0,(p.returncode,p.stderr[-1800:])


def call(command,**args):
    r=h.call(command,args,timeout=20);assert r.get('ok'),r
    return r.get('data',{})


def check_exclusive():
    leases=call('lease_status').get('leases',[])
    assert any(l.get('mine') and any(r.get('resource')=='global' for r in l.get('resources',[]))
               and (l.get('expires_in_s') or 0)>3 for l in leases),'city2 exclusive lease lost'


def assets(mode):
    if mode=='import_meshes':
        m=json.loads((SRC/'manifest.json').read_text());total=len(m['meshes'])+len(m['overview']);batch=4
        progress=OUT/'import_progress.json';start=json.loads(progress.read_text())['through'] if progress.exists() else 0
    else:total,batch,start=(13,4,0) if mode=='textures' else (1,1,0)
    for i in range(start,total,batch):
        editor_lock.acquire('city2',areas=[ROOT],ttl=70,wait_s=45)
        try:run(mode,**{'from':i,'n':batch})
        finally:editor_lock.release('city2')
        time.sleep(1)


def switch(mode,sector=None,group=None):
    editor_lock.acquire('city2',wait_s=900,ttl=70)
    switched=False;t0=time.monotonic()
    try:
        state=call('editor_get_state');assert not state['pie_running'],'User PIE active'
        dirty=[p for p in state['dirty_packages'] if '/Maps/' in p or '/ExternalActors/' in p]
        (OUT/'switch_state.json').write_text(json.dumps(state,indent=2))
        assert not dirty,('Dirty packages: coordinator must resolve before map switch',dirty)
        run('before');switched=True
        for item in group or [sector]:
            path='/Game/FoA/Level2/Maps/L_L2_CityTest2' if mode=='master' else f'/Game/FoA/Level2/Maps/City2/L_City2_S{item[0]}_{item[1]}'
            exists=Path('P:/FoA/Content'+path[5:]+'.umap').exists()
            if exists:call('level_load',path=path)
            else:call('level_create',path=path,name=path.rsplit('/',1)[1])
            if mode=='master' and not exists:
                call('actor_spawn',class_path='/Script/Engine.ExponentialHeightFog',label='City2_HeightFog',location=[0,0,-2000])
                call('actor_spawn',class_path='/Script/Engine.DirectionalLight',label='City2_ShadowDirection',location=[0,0,20000],rotation=[-45,-45,0])
            run(mode,sector=','.join(map(str,item or [])))
            if mode=='sector':(OUT/f'sector_{item[0]}_{item[1]}.json').write_text(json.dumps({'complete':True}))
            if time.monotonic()-t0>30:break
    finally:
        try:
            if switched:run('back')
        finally:editor_lock.release('city2');print('CITY2 hold seconds',time.monotonic()-t0,flush=True)


def proof(view,old=False):
    editor_lock.acquire('city2',wait_s=900,ttl=70)
    switched=pie=False;t0=time.monotonic()
    def script(path,*args):
        h.renew_all('city2',70)
        check_exclusive()
        p=subprocess.run([sys.executable,'Tools/Unreal/integration/run_read.py',path,*args],capture_output=True,text=True)
        print(p.stdout[-1800:],flush=True);assert p.returncode==0,p.stderr[-1800:]
    try:
        state=call('editor_get_state');assert not state['pie_running']
        assert not [p for p in state['dirty_packages'] if '/Maps/' in p or '/ExternalActors/' in p],state['dirty_packages']
        compiled=call('blueprint_compile',path=ROOT+'/BP_City2Sector');assert not compiled.get('error_count'),compiled
        run('before');switched=True;call('level_load',path='/Game/FoA/Level2/Maps/L_L2_CityTest'+('' if old else '2'))
        pie=True;script('Tools/Unreal/ui/pie_call.py','FOA_CALL=BEGIN')
        time.sleep(1)
        done=OUT/'proof_done.json';done.unlink(missing_ok=True)
        script('Tools/Splats/city/city2_proof.py','CITY2_VIEW='+view,'CITY2_OLD='+str(int(old)))
        renew=time.monotonic()
        while not done.exists() and time.monotonic()-t0<42:
            time.sleep(.2)
            if time.monotonic()-renew>15:h.renew_all('city2',70);renew=time.monotonic()
        script('Tools/Splats/city/city2_proof.py','CITY2_PROOF=STOP')
        script('Tools/Unreal/ui/pie_call.py','FOA_CALL=END');pie=False
        result=json.loads(done.read_text());assert result['reason']=='passed',result
    finally:
        try:
            if pie:
                script('Tools/Splats/city/city2_proof.py','CITY2_PROOF=STOP')
                script('Tools/Unreal/ui/pie_call.py','FOA_CALL=END')
            if switched:run('back')
        finally:editor_lock.release('city2');print('CITY2 proof hold seconds',time.monotonic()-t0,flush=True)


if __name__=='__main__':
    (OUT/'runner_pid.txt').write_text(str(os.getpid()))
    mode=sys.argv[1]
    if mode in ['import_meshes','textures','capture_graphs','cleanup_variables']:assets(mode)
    elif mode=='sector':switch(mode,tuple(map(int,sys.argv[2].split(','))))
    elif mode=='master':switch(mode)
    elif mode=='proof':proof(sys.argv[2],len(sys.argv)>3 and sys.argv[3]=='before')
    elif mode=='sectors':
        while True:
            pending=[s for s in json.loads((SRC/'manifest.json').read_text())['sectors'] if not (OUT/f'sector_{s[0]}_{s[1]}.json').exists()]
            if not pending:break
            switch('sector',group=pending[:3]);time.sleep(1)
    else:raise ValueError(mode)
