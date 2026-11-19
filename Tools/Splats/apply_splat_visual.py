"""Native asset-only apply AFTER the parent explicitly grants a stopped-editor window.

python Tools/Splats/apply_splat_visual.py sky|dream|interview
python Tools/Splats/apply_splat_visual.py city --start 0 --count 4
No map switches/saves, actor changes, PIE, or new material assets. Each invocation owns
and releases a scoped 60s lease; import small city batches, verify receipt before continuing.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time
sys.path[:0]=[str(Path(__file__).resolve().parent),'P:/FoA/Tools/Unreal']
import hayba_call as h

ROOT=Path('P:/FoA')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('step',choices=['sky','dream','interview','city'])
    ap.add_argument('--start',type=int,default=0);ap.add_argument('--count',type=int,default=4)
    a=ap.parse_args();owner='main-splat-visual'
    os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner)
    if a.step=='sky':paths=['/Game/FoA/Level2/Dream/M_L2_PanoSky']
    elif a.step in ('dream','interview'):
        name='SM_DreamA' if a.step=='dream' else 'SM_DreamInterview'
        paths=[f'/Game/FoA/Level2/Dream/{name}/StaticMeshes/{name}']
    else:
        assert 1<=a.count<=8 and a.start>=0
        manifest=json.loads(Path('P:/FoA-Assets/level2/toronto/processed/queen_600m_dense/manifest.json').read_text())
        entries=manifest['meshes'][a.start:a.start+a.count];assert entries
        paths=[f"/Game/FoA/Level2/City/Meshes/{e['name']}/StaticMeshes/{e['name']}" for e in entries]
    token=h.lease_acquire(owner,['asset:'+p for p in paths],ttl_s=60,wait_s=3)
    os.environ['FOA_LEASE']=token;renewed=time.monotonic()
    def call(command,**args):
        nonlocal renewed
        if time.monotonic()-renewed>20:
            assert h.call('lease_renew',dict(token=token,ttl_s=60),owner=owner)['ok'];renewed=time.monotonic()
        result=h.call(command,args,owner=owner,timeout=45);assert result.get('ok'),result
        data=result.get('data',{});assert data.get('ok',True) and not data.get('errors') and not data.get('failed') and not data.get('has_errors'),data
        return data
    try:
        assert not call('editor_get_state')['pie_running'],'Stop user PIE first'
        for path in paths:
            source=ROOT/'Content'/((path.removeprefix('/Game/'))+'.uasset')
            backup=ROOT/'Saved/Backups/splat_visual_20261112'/source.relative_to(ROOT/'Content')
            if source.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
        env={'FOA_LEASE':token,'FOA_SPLAT_ASSETS':json.dumps(paths),'FOA_SPLAT_PHASE':'prepare','FOA_SPLAT_LABEL':a.step+'_'+str(a.start)}
        resources=['asset:'+p for p in paths]
        call('python_exec_file',path=str(ROOT/'Tools/Splats/splat_visual_native.py'),env=env,resources=resources)
        if a.step=='sky':
            import build_splat_world_lean as builder
            builder.call=call;builder.sky();call('asset_save',asset_paths=paths)
        else:
            script='import_l2_city.py' if a.step=='city' else 'import_l2_dream.py'
            applyenv={'FOA_CITY':'meshes','FOA_CITY_FROM':str(a.start),'FOA_CITY_N':str(a.count)} if a.step=='city' else {'FOA_L2_STEP':'interview' if a.step=='interview' else 'mesh'}
            call('python_exec_file',path=str(ROOT/'Tools/Splats'/script),env=applyenv,resources=resources)
        env['FOA_SPLAT_PHASE']='receipt'
        call('python_exec_file',path=str(ROOT/'Tools/Splats/splat_visual_native.py'),env=env,resources=resources)
        print('Splat visual assets saved',paths)
    finally:
        h.release(owner,token);os.environ.pop('FOA_LEASE',None)

if __name__=='__main__':main()
