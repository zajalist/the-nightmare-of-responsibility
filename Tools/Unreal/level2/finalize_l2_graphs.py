"""Coordinator-granted final steps, one lease per invocation; never runs PIE.

python -B Tools/Unreal/level2/finalize_l2_graphs.py TARGET
Targets include threshold, merge, stopset, journey, phone_widget, phone_actor,
frontend_phone, drive_hud, battle_hud, journey_hud, player_camera, interactor,
scan_materials, delete_materials.
Layout is position/comment-only via the house planner; runtime wires are untouched.
Material deletion is separate, exact-list-only, backed up and registry-gated twice.
"""
import json
import os
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0,'P:/FoA/Tools/Unreal')
import bp_layout
import editor_lock
import hayba_call as h
from final_l2_graph_targets import TARGETS

ROOT=Path('P:/FoA')
OUT=ROOT/'Saved/Integration/l2_final_graphs'
MATERIALS=tuple('/Game/FoA/Level2/Drive/SM_L2Sedan/SM_L2Sedan/Materials/'+n for n in ('MI_L2Dark','M_L2Flat'))
WORKER='P:/FoA/Tools/Unreal/level2/final_l2_assets.py'


def call(command,**args):
    result=h.call(command,args,timeout=45)
    assert result.get('ok'),result
    data=result.get('data',{})
    assert data.get('ok',True),data
    return data


def checked_compile(path):
    result=call('blueprint_compile',path=path)
    assert result.get('error_count')==0 and result.get('warning_count')==0,result
    call('asset_save',asset_paths=[path])
    return result


def run(step):
    assert step in (*TARGETS,'scan_materials','delete_materials'),step
    owner=os.environ.get('FOA_AGENT','main-level2-final')
    os.environ['FOA_AGENT']=os.environ['HAYBA_AGENT_ID']=owner
    OUT.mkdir(parents=True,exist_ok=True)
    path=TARGETS.get(step)
    if not path:
        imported=json.loads((ROOT/'Saved/Integration/sedan_import.json').read_text())['imported']
        actual={r['path'].split('.')[0] for r in imported if r['kind']=='MaterialInstanceConstant'}
        assert actual==set(MATERIALS),('Unexpected import material list',actual)
        if step=='delete_materials':
            preflight=json.loads((OUT/'scan_materials.json').read_text())
            assert {r['path'] for r in preflight}==set(MATERIALS)
            for material in MATERIALS:
                source=ROOT/('Content'+material[5:]+'.uasset')
                backup=ROOT/'Saved/Backups/level-integration-20261111/SedanImportMaterials'/source.name
                if source.exists() and not backup.exists():
                    backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
    # A deletion is exclusive; read/close preflight and each BP layout are scoped.
    editor_lock.acquire(owner,wait_s=5,ttl=180 if path else 45,
                        areas=[path] if path else (list(MATERIALS) if step=='scan_materials' else None))
    try:
        assert not call('editor_get_state')['pie_running'],'No PIE allowed'
        if path:
            checked_compile(path)
            # Resolve all selected names locally, before any layout. Native
            # blueprint_get_info can itself have a truncated function list.
            call('python_exec_file',path=WORKER,env={'FOA_FINAL_STEP':'capture','FOA_FINAL_BP':path},resources=['asset:'+path])
            manifest=json.loads((OUT/path.rsplit('/',1)[-1]/'capture.json').read_text())
            names=[row['graph'] for row in manifest['graphs']]
            assert names and len(names)==len(set(names)),manifest
            try:
                result=bp_layout.drive(path,graph_names=names)
                assert not result.get('error') and not result.get('failed'),result
            finally:
                checked_compile(path)
            # Parallel asynchronous graph captures can paint blank grids. Finish
            # each renderer before opening the next graph on this editor.
            for row in manifest['graphs']:
                h.renew_all(owner,180)
                stamp=time.time()
                call('python_exec_file',path='P:/FoA/Tools/Unreal/ui/capture_graph.py',
                     env={'FOA_ASSET':path,'FOA_GRAPH':row['graph'],'FOA_PNG':row['png']},resources=['asset:'+path])
                deadline=time.monotonic()+20
                while not (Path(row['png']).exists() and Path(row['png']).stat().st_mtime>=stamp):
                    assert time.monotonic()<deadline,('Graph PNG write deadline',row['graph'])
                    time.sleep(.1)
            # Capturing can dirty the Blueprint; leave it clean after every PNG lands.
            checked_compile(path)
            call('python_exec_file',path=WORKER,env={'FOA_FINAL_STEP':'close_capture','FOA_FINAL_BP':path},resources=['asset:'+path])
            print(json.dumps(dict(asset=path,graphs=len(manifest['graphs']),layout_applied=result.get('applied'),capture_complete=True)))
        else:
            call('python_exec_file',path=WORKER,env={'FOA_FINAL_STEP':step},
                 resources=['global'] if step=='delete_materials' else ['asset:'+p for p in MATERIALS])
    finally:
        editor_lock.release(owner)


if __name__=='__main__':run(sys.argv[1])
