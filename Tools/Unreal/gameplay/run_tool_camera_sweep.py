"""One coordinated <=43s PIE session at the assigned local time."""
import ast,datetime,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path('P:/FoA');sys.path.insert(0,str(ROOT/'Tools/Unreal'))
import hayba_call as hc
OWNER='tool-camera';os.environ.update(FOA_AGENT=OWNER,HAYBA_AGENT_ID=OWNER)
OUT=ROOT/'Saved/QA'/('tool_camera_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));OUT.mkdir(parents=True)
CASE_CAP=43;case_start=0;case_name='camera'
source=ast.parse((ROOT/'Tools/Unreal/integration/level1_qa_bursts.py').read_text())
needed={'command','result','roam','focus_pie_window'}
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in needed],type_ignores=[]),'<existing QA helpers>','exec'))
def inject(script,**env):
    run=subprocess.run([sys.executable,str(ROOT/'Tools/Unreal/integration/run_read.py'),str(ROOT/script)]+[f'{k}={v}' for k,v in env.items()],capture_output=True,text=True,timeout=12,cwd=ROOT)
    with (OUT/'inject.log').open('a') as f:f.write(run.stdout+run.stderr)
    assert run.returncode==0,run.stdout[-1000:]+run.stderr[-1000:]
at=datetime.datetime.fromisoformat(os.environ['FOA_CAMERA_START'])
while datetime.datetime.now()<at:time.sleep(.2)
assert datetime.datetime.now()<at+datetime.timedelta(seconds=15),'Missed assigned window'
acq=subprocess.run([sys.executable,str(ROOT/'Tools/Unreal/editor_lock.py'),'acquire',OWNER,'--ttl','55','--wait','5'],capture_output=True,text=True,cwd=ROOT)
assert acq.returncode==0,acq.stdout+acq.stderr
started=False;settings=None;payload={};case_start=time.time()
settings_path='/Script/UnrealEd.Default__LevelEditorPlaySettings'
try:
    assert not command('editor_get_state').get('pie_running'),'Existing PIE belongs to someone else'
    settings=command('object_get_property',path=settings_path,names=['NewWindowWidth','NewWindowHeight','LastExecutedPlayModeType'])['properties']
    command('object_set_property',path=settings_path,properties={'NewWindowWidth':1280,'NewWindowHeight':720,'LastExecutedPlayModeType':'PlayMode_InEditorFloating'})
    command('editor_start_pie');started=True
    for _ in range(20):
        if command('editor_get_state').get('pie_running'):break
        time.sleep(.1)
    focus_pie_window();roam();stamp=time.time()
    inject('Tools/Unreal/gameplay/pie_tool_camera_sweep.py',FOA_TOOL_NATIVE=0)
    payload=result('Saved/Integration/tool_camera_sweep.json',stamp,18)
except Exception as exc:payload={'error':repr(exc)}
finally:
    try:
        if started:command('editor_stop_pie')
        if settings:command('object_set_property',path=settings_path,properties=settings)
    finally:subprocess.run([sys.executable,str(ROOT/'Tools/Unreal/editor_lock.py'),'release',OWNER],cwd=ROOT)
payload['elapsed']=time.time()-case_start
(OUT/'result.json').write_text(json.dumps(payload,indent=1));print(OUT,payload,flush=True)
