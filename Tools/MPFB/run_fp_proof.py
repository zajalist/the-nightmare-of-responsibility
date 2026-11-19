"""Coordinator-owned real input/viewport proof; never adopts another PIE session."""
import json,os,sys,time,re
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h
owner=os.environ.get('FOA_AGENT','character');os.environ['HAYBA_AGENT_ID']=owner
assert not h.call('editor_get_state')['data']['pie_running'],'Existing PIE is not ours'
out=Path('P:/FoA/Saved/CharacterShots/fp_final');out.mkdir(parents=True,exist_ok=True)
for name in ('ready.txt','done.txt','stop.txt','input_phase.txt'): (out/name).unlink(missing_ok=True)
prefs=Path('P:/FoA/Saved/SaveGames/Settings.sav');original=prefs.read_bytes() if prefs.exists() else None
log=Path('P:/FoA/Saved/Logs/FoA.log');log_start=log.stat().st_size
lease=h.lease_acquire(owner,['global'],ttl_s=45,wait_s=2);started=False
def call(cmd,**args):
    r=h.call(cmd,args,owner=owner,lease=lease,timeout=10);assert r.get('ok'),r
    return r.get('data',{})
def shot(name):
    path=out/(name+'.png');path.unlink(missing_ok=True)
    call('editor_pie_screenshot',filename=str(path),show_ui=True)
    end=time.monotonic()+2
    while not path.exists() and time.monotonic()<end:time.sleep(.05)
    assert path.exists(),name
    shot_poses[name]=rotation();(out/'shots.json').write_text(json.dumps(shot_poses,indent=1))
def axis(key,value,count):
    for _ in range(count):call('editor_pie_axis',key=key,value=value);time.sleep(.035)
def rotation():
    props=call('object_get_property',path='/Game/FoA/Maps/UEDPIE_0_L_Tutorial_Bedroom.L_Tutorial_Bedroom:PersistentLevel.BP_ThirdPersonPlayerController_C_0',names=['ControlRotation'])['properties']
    return {name:(float(re.search(name+'=([-0-9.]+)',props['ControlRotation'])[1])+180)%360-180 for name in ('Pitch','Yaw','Roll')}
shot_poses={}
try:
    assert not call('editor_get_state')['pie_running']
    call('editor_start_pie');started=True;time.sleep(.4)
    call('python_exec_file',path='P:/FoA/Tools/MPFB/ue_fp_observe.py',env={},resources=['global'])
    deadline=time.monotonic()+13
    while not (out/'ready.txt').exists() and not (out/'done.txt').exists() and time.monotonic()<deadline:time.sleep(.1)
    assert (out/'ready.txt').exists(),(out/'report.json').read_text() if (out/'report.json').exists() else 'setup timeout'
    shot('forward')
    a=rotation()['Yaw'];axis('MouseX',100,1);time.sleep(.1);b=rotation()['Yaw'];sensitivity=((b-a+180)%360-180)/100
    assert .01<abs(sensitivity)<5,sensitivity
    pa=rotation()['Pitch'];axis('MouseY',100,1);time.sleep(.1);pb=rotation()['Pitch'];pitch_sensitivity=((pb-pa+180)%360-180)/100
    assert .01<abs(pitch_sensitivity)<5,pitch_sensitivity
    axis('MouseY',-100,1);time.sleep(.1)
    (out/'input_calibration.json').write_text(json.dumps({'degrees_per_mouse_unit':sensitivity,'pitch_degrees_per_mouse_unit':pitch_sensitivity,'before':a,'after':b}))
    for label,value,count in (('rapid_right_180',90/sensitivity,2),('rapid_left_360',-90/sensitivity,4),('rapid_right_360',90/sensitivity,4)):
        (out/'input_phase.txt').write_text(label);axis('MouseX',value,count);time.sleep(.2);shot(label)
    (out/'input_phase.txt').write_text('gentle_sweep');axis('MouseX',24,4);time.sleep(.3);shot('turn_right')
    axis('MouseY',-30/pitch_sensitivity,4);time.sleep(.3);shot('look_down')
    assert shot_poses['look_down']['Pitch']<=-64.5,shot_poses['look_down']
    call('editor_pie_press_key',key='LeftControl',event='pressed');time.sleep(.8);shot('crouch')
    call('editor_pie_press_key',key='W',event='pressed');time.sleep(.35);call('editor_pie_press_key',key='W',event='released');time.sleep(.3);shot('crouch_walk')
    call('editor_pie_press_key',key='LeftControl',event='released');time.sleep(.8);shot('stand_again')
    (out/'input_phase.txt').write_text('forward_walk');call('editor_pie_press_key',key='W',event='pressed');time.sleep(.7);shot('forward_walk');call('editor_pie_press_key',key='W',event='released');time.sleep(.25)
    (out/'input_phase.txt').write_text('up_left')
    axis('MouseY',30/pitch_sensitivity,6);axis('MouseX',-36,4);time.sleep(.4);shot('look_up_left')
    assert shot_poses['look_up_left']['Pitch']>=64.5,shot_poses['look_up_left']
    (out/'stop.txt').write_text('stop');deadline=time.monotonic()+2
    while not (out/'done.txt').exists() and time.monotonic()<deadline:time.sleep(.1)
    assert (out/'done.txt').exists(),'observer did not clean up'
    report=json.loads((out/'report.json').read_text());rows=[r for r in report['rows'] if r['settled']]
    assert report['error'] is None and report['reason']=='complete',{'error':report['error'],'reason':report['reason'],'samples':len(rows)}
    assert rows and all(r['view']=='BP_FoAPlayer_C_0' for r in rows),'Camera left the player during proof'
    crouched=[r for r in rows if r['crouched']];standing=[r for r in rows if not r['crouched']]
    assert len(crouched)>=2 and standing and not rows[-1]['crouched'],'Real crouch/release input failed'
    height_drop=max(r['capsule_half_height'] for r in standing)-min(r['capsule_half_height'] for r in crouched)
    assert height_drop>=10,height_drop
    assert max(abs(r['neck_yaw']) for r in rows)<=62,'Neck yaw limit failed'
    assert all(-65.5<=r['pitch']<=65.5 and abs(r['roll'])<1 for r in rows),'Pitch/roll limits failed'
    assert min(r['pitch'] for r in rows)<=-64.5 and max(r['pitch'] for r in rows)>=64.5,'Both pitch limits must be exercised'
    assert not any(r['face_visible'] or r['hair_visible'] for r in rows),'Head became visible in first person'
    with log.open('rb') as stream:
        stream.seek(log_start);new_log=stream.read().decode('utf-8',errors='replace')
    turn_errors=[line for line in new_log.splitlines() if 'UpdateTurnInPlace' in line and 'Accessed None' in line]
    assert not turn_errors,turn_errors
    # FadeAmount is not a reflected UE property. Check the actual viewport rather than inventing a fade readback.
    from PIL import Image,ImageStat
    luminance={}
    for name in ('forward','turn_right','look_down','crouch','crouch_walk','stand_again','look_up_left'):
        im=Image.open(out/(name+'.png')).convert('L');width,height=im.size
        luminance[name]=ImageStat.Stat(im.crop((width//4,height//4,3*width//4,3*height//4))).mean[0]
    assert luminance['forward']>8,'Actual forward view is black; inspect fade/exposure before approval'
    print(json.dumps({'error':report['error'],'reason':report['reason'],'samples':len(rows),'crouch_seen':bool(crouched),'capsule_height_drop_cm':height_drop,
        'pitch_range':[min(r['pitch'] for r in rows),max(r['pitch'] for r in rows)],'max_neck_yaw':max(abs(r['neck_yaw']) for r in rows),
        'viewport_luminance':luminance,'head_visible':any(r['face_visible'] or r['hair_visible'] for r in rows)},indent=1))
finally:
    cleanup_errors=[]
    try:
        if started:
            try:
                (out/'stop.txt').write_text('cleanup');end=time.monotonic()+1
                while not (out/'done.txt').exists() and time.monotonic()<end:time.sleep(.05)
            except Exception as ex:cleanup_errors.append(str(ex))
            for key in ('W','LeftControl'):
                try:call('editor_pie_press_key',key=key,event='released')
                except Exception as ex:cleanup_errors.append(str(ex))
            try:call('editor_stop_pie')
            except Exception as ex:cleanup_errors.append(str(ex))
    finally:
        try:
            if original is None:prefs.unlink(missing_ok=True)
            else:prefs.write_bytes(original)
            assert (prefs.read_bytes() if prefs.exists() else None)==original,'Preferences restore failed'
        finally:h.release(owner,lease)
    if cleanup_errors:raise RuntimeError('PIE cleanup: '+'; '.join(cleanup_errors))
