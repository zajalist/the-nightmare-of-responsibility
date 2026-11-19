"""One <=60s battle proof burst, followed by offline crop/MP4. Use a coordinator-assigned non-QA window.

python Tools/Unreal/ui/battle_torn_record.py <unique output directory> [1280 720]
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0,'P:/FoA/Tools/Unreal')
import editor_lock
import hayba_call as h

OWNER=os.environ.get('FOA_AGENT','battle-ui')
os.environ['HAYBA_AGENT_ID']=os.environ['FOA_AGENT']=OWNER
OUT=Path(sys.argv[1]).resolve()
WIDTH,HEIGHT=map(int,sys.argv[2:4] or ('1280','720'))
PLAY='/Script/UnrealEd.Default__LevelEditorPlaySettings'


def call(cmd,**p):
    r=h.call(cmd,p,timeout=15)
    assert r.get('ok'),(cmd,r)
    return r.get('data',{})


def owns():
    return any('global' in [r.lower() for r in resources] for _,resources in h.leases_of(OWNER))


def python_file(path,env=None):
    assert owns(),'EXCLUSIVE lost'
    return call('python_exec_file',path=path,env=env or {},resources=['global'])


def main():
    assert not (OUT/'result.json').exists(),'Use a fresh proof output directory'
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'runner.pid').write_text(str(os.getpid()))
    editor_lock.acquire(OWNER,ttl=60,wait_s=900)
    start=time.monotonic();started=False;old=None
    prefs=Path('P:/FoA/Saved/SaveGames/Settings.sav')
    original=prefs.read_bytes() if prefs.exists() else None
    try:
        assert owns() and not call('editor_get_state')['pie_running'],'PIE belongs to someone else'
        for path in ('Gameplay/Encounter/WBP_Encounter','Gameplay/Encounter/BP_Encounter',
                     'Gameplay/Encounter/BP_Garment','Gameplay/BP_BeatDirector','UI/Framework/BP_FoAFrontEnd'):
            report=call('blueprint_compile',path='/Game/FoA/'+path)
            assert report.get('error_count')==0,(path,report)
        settings=call('object_get_property',path=PLAY)['properties']
        old={k:settings[k] for k in ('NewWindowWidth','NewWindowHeight')}
        call('object_set_property',path=PLAY,properties={'NewWindowWidth':WIDTH,'NewWindowHeight':HEIGHT,
                                                     })
        python_file('P:/FoA/Tools/Unreal/ui/pie_call.py',{'FOA_CALL':'BEGIN','FOA_CALLER':OWNER})
        started=True
        while not call('editor_get_state')['pie_running']:
            assert time.monotonic()-start<8,'PIE start timeout'
            time.sleep(.15)
        python_file('P:/FoA/Tools/Unreal/ui/battle_torn_proof.py',{'FOA_TORN_OUT':OUT.as_posix(),'FOA_TORN_PLAN':os.environ.get('FOA_TORN_PLAN','Act0,Act1')})
        renewed=time.monotonic();sent=0
        while time.monotonic()-start<52:
            assert owns(),'EXCLUSIVE lost; no further inputs'
            if time.monotonic()-renewed>20:
                h.renew_all(OWNER,60);renewed=time.monotonic()
            if (OUT/'result.json').exists():break
            request=OUT/'input.json'
            if request.exists():
                try:r=json.loads(request.read_text())
                except (ValueError,PermissionError):r={}
                if r.get('id',0)>sent:
                    if r['kind']=='mouse':
                        result=call('editor_pie_mouse',action=r['action'],x=r['x'],y=r['y'],coordinate_space='viewport')
                    else:result=call('editor_pie_press_key',key=r['key'],held_ms=70)
                    sent=r['id'];(OUT/'ack.json').write_text(json.dumps(dict(id=sent,key=r['key'],result=result)))
            time.sleep(.08)
    finally:
        if owns():
            if started:python_file('P:/FoA/Tools/Unreal/ui/pie_call.py',{'FOA_CALL':'END','FOA_CALLER':OWNER})
            if old:call('object_set_property',path=PLAY,properties=old)
            if original is not None:prefs.write_bytes(original)
            editor_lock.release(OWNER)
        print('battle proof hold seconds',round(time.monotonic()-start,2),flush=True)
    post()


def post():
    from PIL import Image
    result=json.loads((OUT/'result.json').read_text())
    dest=OUT/'frames';dest.mkdir(exist_ok=True)
    retained=[]; actual_size=None
    for row in result['frames']:
        p=OUT/'raw'/f'f{row["frame"]:04d}.png'
        if not p.exists():continue
        with Image.open(p) as im:
            if im.size==(WIDTH+6,HEIGHT+40):im=im.crop((3,36,WIDTH+3,HEIGHT+36))
            if actual_size is None:actual_size=im.size
            assert im.size==actual_size,'Capture dimensions changed during proof'
            im.convert('RGB').save(dest/f'f{len(retained):04d}.png')
        retained.append(row)
    assert len(retained)>2,'No valid battle-camera frames'
    fps=(len(retained)-1)/(retained[-1]['t']-retained[0]['t'])
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(fps),'-i',str(dest/'f%04d.png'),
                    '-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(OUT/'battle_ui.mp4')],check=True)
    (OUT/'video.json').write_text(json.dumps(dict(frames=len(retained),fps=fps,size=actual_size),indent=2))
    print('MP4',OUT/'battle_ui.mp4',len(retained),round(fps,2))


if __name__=='__main__':main()
