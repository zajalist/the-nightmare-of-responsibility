"""Horror lane PIE proof: drives a running PIE from a Slate tick callback to T4, stands the pawn at the dead door,
reports KeySnapped (T5), walks it out of BP_Jumpscare's zone facing the room, and logs every jumpscare phase change.
The scare window runs at 'slomo 0.25' so the in-engine Shot
recorder gets four times the frames; make_media.py retimes them to game time. Frames come from in-engine 'Shot' requests: every FOA_SHOT_SLOW s, and every FOA_SHOT_FAST s from the false
calm until 1.5 s after the hit. The timeline goes to Saved/HorrorShots/<run>_timeline.json.
  python Tools/Unreal/integration/run_read.py Tools/Unreal/horror/pie_jumpscare.py FOA_RUN=<name>   (inside an EXCLUSIVE burst)
Reads PIE actors; writes only the test pawn's position and control rotation."""
import json
import os
import time

import unreal

RUN = os.environ.get('FOA_RUN', 'jumpscare')
OUT = f'P:/FoA/Saved/HorrorShots/{RUN}_timeline.json'
SLOW, FAST = float(os.environ.get('FOA_SHOT_SLOW', '0.5')), float(os.environ.get('FOA_SHOT_FAST', '0.033'))
DIR_C = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
JS_C = '/Game/FoA/Gameplay/Jumpscare/BP_Jumpscare.BP_Jumpscare_C'
DOOR = unreal.Vector(300, 80, 0)      # inside the zone, at the door
ROOM = unreal.Vector(170, 60, 0)      # out of the zone, towards the room
# (delay after previous step, action)
STEPS = [(0.0, 'cmd:viewmode lit'), (0.5, 'cmd:ke * OnSplashFinished'), (1.0, 'cmd:ke * OnTitleConfirmed'),
         (1.5, 'cmd:ke * WakeUp'), (5.5, 'cmd:ke * OnStoryFinished'), (2.0, 'cmd:ke * SkipWakeUp'),
         (0.0, 'wait:ANY:12'),
         (1.0, 'cmd:ke * ReportEvent PhoneWakeUp'), (0.5, 'cmd:ke * ClosePhone'), (1.0, 'cmd:ke * ReportEvent FirstSteps'), (0.0, 'wait:T2:4'),
         (0.8, 'cmd:ke * ReportEvent Searched'), (0.0, 'wait:T3:3'), (0.8, 'cmd:ke * ReportEvent KeyTaken'), (0.0, 'wait:T4:3'),
         (0.2, 'door'), (2.5, 'cmd:ke * ReportEvent KeySnapped'), (0.0, 'wait:T5:3'), (3.0, 'leave'), (0.0, 'cmd:slomo 0.25'),
         (18.0, 'cmd:slomo 1'), (0.5, 'end')]
S = {'t0': time.time(), 'mark': time.time(), 'shot': 0.0, 'i': 0, 'h': None, 'beat': None, 'phase': None,
     'fast_until': 0.0, 'log': [], 'done': False, 'z': None}


def log(kind, **kw):
    e = dict(t=round(time.time() - S['t0'], 3), epoch=round(time.time(), 3), kind=kind, **kw)
    S['log'].append(e)
    unreal.log('[horror] ' + json.dumps(e))


def finish():
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(S['log'], fh, indent=1)
    unreal.log(f'[horror] timeline -> {OUT}')


def place(w, at, yaw):
    pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
    if S['z'] is None:
        S['z'] = pawn.get_actor_location().z  # keep the capsule's own height
    pawn.set_actor_location(unreal.Vector(at.x, at.y, S['z']), False, True)
    unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.Rotator(roll=0, pitch=-8, yaw=yaw))


def tick(_dt):
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not w:
        log('pie_gone')
        return finish()
    now = time.time()
    d = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, DIR_C))
    b = d.get_editor_property('Beat') if d else None
    beat = str(b.get_editor_property('Id')) if b else None
    if beat != S['beat']:
        S['beat'] = beat
        pc = unreal.GameplayStatics.get_player_controller(w, 0)
        vt = pc.get_view_target() if pc else None
        log('beat', beat=beat, view=vt.get_class().get_name() if vt else None)
    js = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, JS_C))
    if js:
        ph = js.get_editor_property('Phase')
        if ph != S['phase']:
            S['phase'] = ph
            log('phase', phase=ph, fired=js.get_editor_property('bFired'))
            if ph == 2:
                S['fast_until'] = now + 18.0  # at slomo 0.25: calm (<=1.9 s) + riser 0.4 + hold 0.65 + 1.5 s of aftermath
    gap = FAST if now < S['fast_until'] else SLOW
    if now - S['shot'] >= gap:
        S['shot'] = now
        unreal.SystemLibrary.execute_console_command(w, 'Shot')  # game viewport only ('showui' grabs the whole editor)
    if S['i'] >= len(STEPS):
        return finish()
    delay, act = STEPS[S['i']]
    if act.startswith('wait:'):
        _, want, timeout = act.split(':')
        hit = beat is not None if want == 'ANY' else beat == want
        if hit or now - S['mark'] > float(timeout):
            if not hit:
                log('miss', want=want, beat=beat)
            S['i'] += 1
            S['mark'] = now
        return
    if now - S['mark'] < delay:
        return
    S['i'] += 1
    S['mark'] = now
    if act.startswith('cmd:'):
        unreal.SystemLibrary.execute_console_command(w, act[4:])
        log('cmd', cmd=act[4:], beat=beat)
    elif act == 'door':
        place(w, DOOR, 0)
        pc = unreal.GameplayStatics.get_player_controller(w, 0)
        vt = pc.get_view_target()
        log('door', view=vt.get_class().get_name() if vt else None)
    elif act == 'leave':
        place(w, ROOM, 180)
        log('leave')
    elif act == 'end':
        log('end')
        finish()
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('horror jumpscare run scheduled', len(STEPS), 'steps ->', OUT)
