"""One coordinator-owned stopped-editor step; compile and save before releasing."""
import json
import os
from pathlib import Path
import shutil
import sys
import build_drive as b
from finalize_l2_graphs import call,checked_compile

ORDER=('free_setup','road_templates','camera','car_templates','BP_L2Car.PlaceAtCheckpoint',
       'BP_L2Car.CheckDestination','BP_L2Car.Move','BP_L2Car.Schedule','BP_L2Car.StartLeg',
       'BP_L2Car.Continue','BP_L2Car.Deactivate','BP_L2Car.QueueTurn','widget_polish','camera_wire')


def run(step):
    assert step in ORDER,step
    owner='main-free-drive'
    os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner,FOA_CALLER=owner)
    b.D.OWNER=owner
    paths=[b.CAR,b.ROAD,b.HUD]
    token=b.editor_lock.acquire(owner,wait_s=3,ttl=60,areas=[b.D.ROOT])
    try:
        if token is None:
            held=b.h.leases_of(owner)
            assert len(held)==1,('Expected one covering asset lease',held)
            token=held[0][0]
        assert token,'Native lease required'
        os.environ['FOA_LEASE']=token
        assert not call('editor_get_state')['pie_running'],'Stop user play before authoring'
        for path in paths:
            source=Path('P:/FoA/Content'+path[5:]+'.uasset')
            backup=Path('P:/FoA/Saved/Backups/level-integration-20261112/FreeDrive')/source.name
            if source.exists() and not backup.exists():
                backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
        if step.endswith('_templates'):
            call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/free_drive_setup.py',
                 env={'FOA_FREE_SETUP':step.split('_')[0],'FOA_LEASE':token},resources=['asset:'+b.D.ROOT])
        else:b.STEPS[step]()
        rows=[dict(asset=path,compile=checked_compile(path)) for path in paths]
        print(json.dumps(dict(step=step,verified=rows)))
    finally:b.editor_lock.release(owner)


if __name__=='__main__':run(sys.argv[1])
