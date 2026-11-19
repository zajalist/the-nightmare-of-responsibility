"""Apply the reviewed position/comment-only city graph plan, capture and close it."""
import json
import os
from pathlib import Path
import sys
import time
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import editor_lock
from finalize_l2_graphs import call

ROOT=Path('P:/FoA')
OUT=ROOT/'Saved/Integration/city_billboards'
PATH='/Game/FoA/Level2/M_SplatCity_Lean'


def run():
    plan=json.loads((OUT/'layout_plan.json').read_text())
    assert plan['asset']==PATH and not plan['problems'] and len(plan['calls'])==19
    allowed=dict(material_set_node={'material_path','node_id','node_pos'},
                 material_set_comment={'material_path','comment_id','node_pos','size','text'},
                 material_validate={'material_path'},material_compile={'material_path'})
    for action in plan['calls']:
        assert action['name'] in allowed and set(action['args'])<=allowed[action['name']]
        assert action['args']['material_path']==PATH
    owner='main-level2-final-city'
    os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner,FOA_CALLER=owner)
    editor_lock.acquire(owner,wait_s=5,ttl=90,areas=[PATH])
    try:
        assert not call('editor_get_state')['pie_running']
        rows=[]
        for action in plan['calls']:
            data=call(action['name'],**action['args'])
            if action['name']=='material_compile':assert data.get('compiled_clean') and not data.get('errors'),data
            rows.append(dict(command=action['name'],result=data))
        call('asset_save',asset_paths=[PATH])
        png=OUT/'M_SplatCity_Lean_graph.png';stamp=time.time()
        worker=str(ROOT/'Tools/Devlog/ue_capture.py')
        call('python_exec_file',path=worker,resources=['asset:'+PATH],env=dict(
            FOA_CLOSE='',FOA_ASSET=PATH,FOA_GRAPH='',FOA_PNG=str(png),FOA_META=str(OUT/'graph_meta.json')))
        deadline=time.monotonic()+20
        while not png.is_file() or png.stat().st_mtime<stamp:
            assert time.monotonic()<deadline,'City graph PNG deadline'
            time.sleep(.1)
        # Root confirmed no target editor was open before this finalization pass.
        call('python_exec_file',path=worker,resources=['asset:'+PATH],env=dict(
            FOA_CLOSE=PATH,FOA_ASSET='',FOA_GRAPH='',FOA_PNG='',FOA_META=''))
        call('asset_save',asset_paths=[PATH])
        (OUT/'layout_applied.json').write_text(json.dumps(dict(calls=rows,png=str(png),closed=True),indent=2))
        print(json.dumps(dict(calls=len(rows),compiled_clean=True,png=str(png),closed=True)),flush=True)
    finally:editor_lock.release(owner)


if __name__=='__main__':run()
