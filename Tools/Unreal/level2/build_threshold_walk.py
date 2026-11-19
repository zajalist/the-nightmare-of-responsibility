"""Coordinator-granted bounded authoring: one named step per clean asset lease.

Run ORDER sequentially after explicit editor grant; no PIE/map/sequence edits.
Existing threshold/public phases remain intact. No implicit all-steps command.
"""
import json
import os
from pathlib import Path
import shutil
import sys
import build_threshold as b

ORDER=('skeleton','dream_skeleton','walk_widget','walk_components',*b.walk.GRAPHS,
       'StartPath','Step','BeginFall','RestartFromRoad','RestoreRoom')


def run(*steps):
    """Several steps may share one lease (dreamroom: a short batch keeps the Blueprint whole between other lanes' bursts)."""
    for step in steps:assert step in (*ORDER,'walk_padding'),step
    owner=os.environ.get('FOA_AGENT','main-threshold-walk')
    os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner)
    paths=[b.BP,b.HUD]
    b.editor_lock.acquire(owner,wait_s=900,ttl=90+60*len(steps),areas=paths)
    try:
        assert not b.call('editor_get_state')['pie_running'],'No authoring during user play'
        for path in paths:
            source=Path('P:/FoA/Content'+path[5:]+'.uasset')
            dest=Path('P:/FoA/Saved/Backups/level-integration-20261112/DreamWalk')/source.name
            if source.exists() and not dest.exists():
                dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
        for step in steps:b.STEPS[step]()
        rows=[]
        for path in paths:
            result=b.call('blueprint_compile',path=path)
            assert result.get('error_count')==0 and result.get('warning_count')==0,result
            b.call('asset_save',asset_paths=[path]);rows.append(dict(asset=path,compile=result))
        print(json.dumps(dict(steps=steps,verified=rows)))
    finally:b.editor_lock.release(owner)


if __name__=='__main__':run(*sys.argv[1:])
