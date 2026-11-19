"""Coordinator-granted one-step city apply. Never execute while the user plays.

Order: setup, update, release, events, readiness; import dense meshes in the
data lane; plan; sector0..143, master, validate; visual/runtime checks; activate.
Each map invocation returns to Bedroom under the same exclusive lease.
"""
import json
import os
from pathlib import Path
import sys
import time
import city_streaming as c
import build_threshold as t
from finalize_l2_graphs import call,checked_compile
import editor_lock

WORKER='P:/FoA/Tools/Unreal/level2/city_streaming_ue.py'
BEDROOM='/Game/FoA/Maps/L_Tutorial_Bedroom'
OUT=Path('P:/FoA/Saved/Integration/city_streaming')


def cook_config(source,paths):
    lines=source.splitlines();header='[/Script/UnrealEd.ProjectPackagingSettings]'
    assert lines.count(header)==1,'Expected one packaging settings section'
    start=lines.index(header)+1
    end=next((i for i in range(start,len(lines)) if lines[i].lstrip().startswith('[')),len(lines))
    section=[line for line in lines[start:end] if line!='+MapsToCook=(FilePath="/Game/FoA/Level2/Maps/L_L2_CityTest")']
    for path in paths:
        line='+MapsToCook=(FilePath="'+path+'")'
        if line not in section:section.append(line)
    return '\n'.join(lines[:start]+section+lines[end:])+'\n'


def run(step,index=0,count=1):
    if step=='plan':c.write_plan();return
    assert step in ('setup','update','release','events','readiness','sector','master','validate','activate','hide_collision')
    owner='main-city-streaming';os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner,FOA_CALLER=owner)
    mapping=step in ('sector','master')
    assert 1<=count<=12 and (step=='sector' or count==1)
    target=t.BP if step in ('readiness','activate') else '/Game/FoA/Level2/Drive/BP_L2RoadNetwork' if step=='hide_collision' else c.BP
    token=editor_lock.acquire(owner,wait_s=5,ttl=120,areas=None if mapping else [target,c.MASTER,c.MAP_ROOT,c.ASSET_ROOT])
    os.environ['FOA_LEASE']=token or next(iter(t.h.leases_of(owner)))[0]
    switched=False
    try:
        state=call('editor_get_state');assert not state['pie_running'],'User still playing'
        if mapping:
            assert state['map'].split('.')[0]==BEDROOM,state
            assert not state['dirty_packages'],('Save owned work before switching maps',state['dirty_packages'])
            call('python_exec_file',path=WORKER,env={'CITY_STREAM_STEP':'inventory','CITY_STREAM_INVENTORY':'before'},resources=['global'])
            plan=json.loads((OUT/'plan.json').read_text())
            started=time.monotonic()
            indices=range(index,min(index+count,len(plan['sectors']))) if step=='sector' else (index,)
            for current in indices:
                if switched and time.monotonic()-started>32:break
                path=plan['master'] if step=='master' else plan['sectors'][current]['package']
                switched=True
                file=Path('P:/FoA/Content'+path[5:]+'.umap')
                if file.exists():call('level_load',path=path)
                else:call('level_create',path=path,name=path.rsplit('/',1)[1])
                call('python_exec_file',path=WORKER,env={'CITY_STREAM_STEP':step,'CITY_STREAM_INDEX':str(current)},resources=['global'])
                assert file.is_file()
                (OUT/(step+'_'+str(current)+'.json')).write_text(json.dumps(dict(step=step,index=current,saved=True),indent=2))
                print('Saved',path,flush=True)
        elif step in ('validate','hide_collision'):
            call('python_exec_file',path=WORKER,env={'CITY_STREAM_STEP':step},resources=['asset:'+target,'asset:'+c.MAP_ROOT,'asset:'+c.ASSET_ROOT])
            if step=='hide_collision':checked_compile(target)
        else:
            call('python_exec_file',path='P:/FoA/Tools/Unreal/ui/close_ui_editors.py',env={'FOA_ASSETS':target},resources=['asset:'+target])
            if step=='readiness':
                info=call('blueprint_get_info',path=t.BP)
                if 'CitySectorCount' not in {v['name'] for v in info['variables']}:
                    call('blueprint_add_variable',path=t.BP,variable_name='CitySectorCount',variable_type='int',default_value='0')
                if 'CheckCitySectors' not in info['functions']:call('blueprint_add_function',path=t.BP,function_name='CheckCitySectors')
                c.threshold_ready()
            elif step=='activate':
                call('python_exec_file',path=WORKER,env={'CITY_STREAM_STEP':'validate'},resources=['asset:'+c.MAP_ROOT,'asset:'+c.ASSET_ROOT])
                assert json.loads((OUT/'validation.json').read_text())['ok']
                previous=t.D.CITY_MAP
                try:
                    t.D.CITY_MAP=c.MASTER
                    for name in ('StartPath','BeginFall','Land'):t.STEPS[name]();checked_compile(t.BP)
                except BaseException:
                    t.D.CITY_MAP=previous
                    for name in ('StartPath','BeginFall','Land'):t.STEPS[name]();checked_compile(t.BP)
                    raise
                # Persist the canonical rebuild and cook roots only after all new
                # maps/meshes validated and all transition graphs compiled.
                data=Path(t.D.__file__);source=data.read_text()
                old="CITY_MAP = '/Game/FoA/Level2/Maps/L_L2_CityTest'"
                new="CITY_MAP = '"+c.MASTER+"'"
                assert old in source or new in source
                data.write_text(source.replace(old,new))
                config=Path('P:/FoA/Config/DefaultGame.ini')
                plan=json.loads((OUT/'plan.json').read_text())
                config.write_text(cook_config(config.read_text(),[c.MASTER]+[s['package'] for s in plan['sectors']]))
            else:getattr(c,step)()
            checked_compile(target)
        OUT.mkdir(parents=True,exist_ok=True)
        if not mapping:(OUT/(step+'.json')).write_text(json.dumps(dict(step=step,index=index,saved=True),indent=2))
    finally:
        try:
            if switched:
                call('level_load',path=BEDROOM)
                state=call('editor_get_state');assert not state['pie_running'] and state['map'].split('.')[0]==BEDROOM,state
                call('python_exec_file',path=WORKER,env={'CITY_STREAM_STEP':'inventory','CITY_STREAM_INVENTORY':'after'},resources=['global'])
        finally:
            editor_lock.release(owner)
            os.environ.pop('FOA_LEASE',None)


if __name__=='__main__':run(sys.argv[1],*(int(x) for x in sys.argv[2:]))
