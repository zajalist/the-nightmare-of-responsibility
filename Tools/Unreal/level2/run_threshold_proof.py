"""One owned PIE window, strict timeout, save-hash verification and guaranteed PIE stop."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
from threshold_data import proof_budget
owner='main-threshold-proof'
os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner,FOA_CALLER=owner)
case=os.environ.get('FOA_JOURNEY_CASE','transition')
assert case in ('transition','cinematic','cinematic_reduced','animation_probe','early_cleanup','stops','cleanup','reset','drive','job','job_campaign','job_gamepad','job_shift_visual','job_ending','cv','ending','debug','phone','paper','shockwave','streaming'),case
realtime=os.environ.get('FOA_PROOF_REALTIME','0')
root=Path('P:/FoA/Saved/Codex/dream_transition')
out=root/('proof.json' if case=='transition' else 'proof_'+case+'.json')
inputs=root/('input_'+case+'.json')
prefs=Path('P:/FoA/Saved/SaveGames/Settings.sav')
save=Path('P:/FoA/Saved/SaveGames/FoA.sav')
log=Path(os.environ.get('FOA_PROOF_EDITOR_LOG','P:/FoA/Saved/Logs/FoA.log'))
log_start=log.stat().st_size
def digest():return hashlib.sha256(save.read_bytes()).hexdigest() if save.exists() else None
before=digest();original=prefs.read_bytes() if prefs.exists() else None
def call(cmd,**args):
    timeout=45 if cmd in ('editor_start_pie','editor_get_state','editor_stop_pie','python_exec_file') else 15
    r=h.call(cmd,args,owner=owner,timeout=timeout);assert r.get('ok'),r
    return r.get('data',{})

def focus_owned_editor():
    """Real pointer routing requires the owned PIE host to be foreground."""
    import ctypes
    from ctypes import wintypes
    user=ctypes.windll.user32
    user.GetForegroundWindow.restype=wintypes.HWND
    user.SetForegroundWindow.argtypes=[wintypes.HWND]
    user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user.SetWindowPos.argtypes=[wintypes.HWND,wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.UINT]
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    preview=[];editor=[]
    def visit(hwnd,_):
        title=ctypes.create_unicode_buffer(512);user.GetWindowTextW(hwnd,title,len(title))
        if user.IsWindowVisible(hwnd):
            if title.value.startswith('FoA Preview [NetMode: Standalone'):preview.append(hwnd)
            elif title.value=='FoA - Unreal Editor':editor.append(hwnd)
        return True
    user.EnumWindows(callback_type(visit),0)
    found=preview or editor
    assert len(found)==1,('Expected one owned PIE host',len(found))
    pid=wintypes.DWORD();target_thread=user.GetWindowThreadProcessId(found[0],ctypes.byref(pid))
    import psutil
    assert psutil.Process(pid.value).name().lower()=='unrealeditor.exe','Unexpected PIE host process'
    current_thread=ctypes.windll.kernel32.GetCurrentThreadId()
    foreground_thread=user.GetWindowThreadProcessId(user.GetForegroundWindow(),None)
    attached=[]
    try:
        # Windows may reject a background process's SetForegroundWindow.
        # Share its current foreground input queue only for this activation.
        for thread in set((foreground_thread,target_thread))-{0,current_thread}:
            if user.AttachThreadInput(current_thread,thread,True):attached.append(thread)
        # HWND_TOP, not TOPMOST: no persistent window-style change.
        assert user.SetWindowPos(found[0],None,0,0,0,0,0x43)
        user.SetForegroundWindow(found[0])
    finally:
        for thread in attached:user.AttachThreadInput(current_thread,thread,False)
    assert user.GetForegroundWindow()==found[0],'PIE host could not receive mouse focus'
    return found[0]


def preview_click_point(hwnd,target,root_widget):
    import ctypes
    from ctypes import wintypes
    user=ctypes.windll.user32
    user.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
    user.WindowFromPoint.argtypes=[wintypes.POINT]
    user.WindowFromPoint.restype=wintypes.HWND
    user.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT]
    user.GetAncestor.restype=wintypes.HWND
    rect=wintypes.RECT()
    assert user.GetWindowRect(hwnd,ctypes.byref(rect))
    x,y=target['center_x'],target['center_y']
    def preview_at(px,py):
        hit=user.WindowFromPoint(wintypes.POINT(round(px),round(py)))
        return hit==hwnd or user.GetAncestor(hit,2)==hwnd
    if not preview_at(x,y):
        x=rect.left+(x-root_widget['x'])*(rect.right-rect.left)/root_widget['width']
        y=rect.top+(y-root_widget['y'])*(rect.bottom-rect.top)/root_widget['height']
    assert preview_at(x,y),('Click target is outside the PIE preview',x,y,root_widget)
    return x,y

def dispatch_input(request):
    args=dict(request);kind=args.pop('kind','key')
    assert kind in ('key','click'),kind
    if kind=='click':
        assert args.get('match') and args.get('prefer_type')=='SButton',args
        hwnd=focus_owned_editor()
        tree=call('editor_pie_widget_tree',filter=args['match'],max_depth=60)
        matches=[row for row in tree['widgets'] if row.get('type')=='SButton'
            and row.get('text')==args['match'] and row.get('enabled') and row.get('interactive')]
        assert len(matches)==1,('Expected one exact enabled answer button',matches)
        root_widget=call('editor_pie_widget_tree',filter='SWindow',max_depth=1)['widgets'][0]
        x,y=preview_click_point(hwnd,matches[0],root_widget)
        point=dict(x=x,y=y,coordinate_space='absolute',button='left')
        reply=call('editor_pie_mouse',action='click',**point)
        assert reply.get('dispatched'),reply
        reply.update(clicked_type='SButton',clicked_text=args['match'],target_enabled=True)

    else:
        reply=call('editor_pie_press_key',**args)
        assert reply.get('dispatched'),reply
    return reply


def wait_for_play_modifier():
    import ctypes
    # Unreal starts a spectator PIE when Ctrl is down at the start request.
    deadline=time.monotonic()+8
    while ctypes.windll.user32.GetAsyncKeyState(0x11)&0x8000:
        assert time.monotonic()<deadline,'Ctrl stayed held; PIE did not start'
        time.sleep(.05)

def cleanup(started,case,original,token,before,preview=None):
    # One failed input or END call must not bypass the remaining safeguards.
    try:
        if started and call('editor_get_state').get('pie')=='agent:'+owner:
            try:
                # Every transition now uses real W/E, including cases which fail
                # before reaching their specialised proof. Attempt both releases.
                input_error=None
                extra=('Enter','Up','Down','Gamepad_DPad_Up','Gamepad_DPad_Down','Gamepad_FaceButton_Bottom') if case=='cv' else ()
                if case=='drive':extra=('S','Enter','SpaceBar','A','D')
                elif case in ('job','job_campaign'):extra=('S','Enter','SpaceBar','A','D','Up','Down','C')
                elif case in ('job_gamepad','job_shift_visual'):extra=('Gamepad_FaceButton_Bottom','Gamepad_FaceButton_Right','Gamepad_FaceButton_Top','Gamepad_DPad_Left','Gamepad_DPad_Up','Gamepad_DPad_Down')
                elif case=='stops':extra=('Enter','Up','Down')
                elif case=='phone':extra=('P',)
                elif case=='paper':extra=('Enter',)
                for key in ('W','E')+(('F6','F9') if case=='debug' else ())+extra:
                    try:call('editor_pie_press_key',key=key,event='released')
                    except Exception as exc:
                        input_error=input_error or exc
                        print('cleanup input release failed',key,repr(exc),flush=True)
                if input_error:raise input_error
            finally:
                call('editor_stop_pie')
                for _ in range(20):
                    if not call('editor_get_state')['pie_running']:break
                    time.sleep(.2)
                assert not call('editor_get_state')['pie_running']
    finally:
        try:
            try:
                if preview is not None and not call('editor_get_state')['pie_running']:
                    call('object_set_property',path='/Script/UnrealEd.Default__LevelEditorPlaySettings',properties=preview)
            finally:
                if original is not None:prefs.write_bytes(original)
                elif prefs.exists():prefs.unlink()
        finally:
            try:h.release(owner,token)
            finally:assert digest()==before,'Player save changed during proof'
token=h.lease_acquire(owner,['global'],ttl_s=60,wait_s=5)
os.environ['FOA_LEASE']=token
started=False
preview=None
launch=root/('launch_'+uuid.uuid4().hex+'.txt')
try:
    assert not call('editor_get_state')['pie_running']
    preflight=Path('P:/FoA/Saved/QA/preflight.json')
    preflight.unlink(missing_ok=True)
    call('python_exec_file',path='P:/FoA/Tools/QA/preflight_blueprints.py',resources=['global'],
         env={'FOA_PREFLIGHT_SKIP_CONTACTS':os.environ.get('FOA_PROOF_LOW_MEMORY','0')})
    pre=json.loads(preflight.read_text())
    assert pre['ok'],('Blueprint preflight failed; PIE not started',pre['failures'])
    play_settings='/Script/UnrealEd.Default__LevelEditorPlaySettings'
    preview=call('object_get_property',path=play_settings,names=['NewWindowWidth','NewWindowHeight'])['properties']
    call('object_set_property',path=play_settings,properties={'NewWindowWidth':1280,'NewWindowHeight':720})
    stamp=time.time()
    nonce=launch.stem.removeprefix('launch_')
    call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/launch_threshold_proof.py',env={
        'FOA_PROOF_NONCE':nonce,'FOA_JOURNEY_CASE':case,'FOA_PROOF_REALTIME':realtime,
        'FOA_CV_FAILURE_RUNS':os.environ.get('FOA_CV_FAILURE_RUNS','2'),
        'FOA_CV_MOUSE':os.environ.get('FOA_CV_MOUSE','1'),
        'FOA_PROOF_HEADLESS':os.environ.get('FOA_PROOF_HEADLESS','0')},resources=['global'])
    # The start request can succeed before its transport returns.
    wait_for_play_modifier()
    started=True
    reply=call('editor_start_pie')
    assert reply.get('pie_owner')=='agent:'+owner,reply
    for _ in range(20):
        state=call('editor_get_state')
        if state['pie_running'] and state['pie_phase']=='running':break
        time.sleep(.2)
    assert state['pie_phase']=='running' and state['pie']=='agent:'+owner,state
    inputs.unlink(missing_ok=True)
    pending=launch.with_suffix('.pending');pending.write_text(nonce);pending.replace(launch)
    renewed=time.monotonic()
    sent=0;debug_sent=0
    # Earned walking and downstream stages share one measured case budget.
    # The global lease still expires in60s and renews every20s below.
    budget=proof_budget(case,realtime=='1')+4
    running_since=time.monotonic()
    while time.monotonic()-running_since<budget:
        error=launch.with_suffix('.error')
        if error.exists():raise RuntimeError(error.read_text(encoding='utf-8'))
        if time.monotonic()-renewed>20:h.renew_all(owner,60);renewed=time.monotonic()
        if out.exists() and out.stat().st_mtime>=stamp:
            result=json.loads(out.read_text())
            print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
            last=result.get('rows',[])[-1:]
            if last and 'result' in last[0]:
                detail=last[0]['result']
                last=[dict(kind=last[0]['kind'],passed=detail.get('passed'),reason=detail.get('reason'),
                           turns=detail.get('actual_actions',{}).get('turns'),events=len(detail.get('trace',[])))]
            print('last',json.dumps(last),flush=True);break
        if inputs.exists():
            request=json.loads(inputs.read_text())
            if request['id']>sent:
                sent=request.pop('id');reply=dispatch_input(request)
                if request.get('kind')=='click':
                    (root/'mouse_click_reply.json').write_text(json.dumps(reply,indent=2))
                    print('mouse reply',json.dumps(reply),flush=True)
                if request.get('key') in ('F6','F9'):debug_sent+=1
                print('input',sent,request.get('key',request.get('kind')),'dispatched',flush=True)
        time.sleep(.3)
    else:raise TimeoutError('Threshold proof exceeded its PIE budget')
    assert result['reason'] in ('arrived','animation_probe','early_cleanup_passed','stops_passed','cleanup_passed','road_reset_passed','drive_passed','job_passed','job_campaign_passed','job_gamepad_passed','job_shift_visual_passed','job_ending_passed','cv_passed','ending_passed','debug_passed','phone_passed','paper_passed','shockwave_passed','streaming_passed'),result['reason']
    if case=='debug':assert debug_sent==5,('Debug input not delivered',debug_sent)
finally:
    try:cleanup(started,case,original,token,before,preview)
    finally:
        segment=log.read_bytes()[log_start:].decode('utf-8',errors='replace')
        (root/(case+'_pie.log')).write_text(segment,encoding='utf-8')
        launch.unlink(missing_ok=True)
    print('PIE stopped; player save unchanged; settings restored',flush=True)
    assert 'Blueprint Runtime Error' not in segment and 'Accessed None' not in segment,'Blueprint runtime error in '+case+'_pie.log'
