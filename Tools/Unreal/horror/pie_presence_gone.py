"""Audio lane: PIE proof for BP_RoomAudio.UpdatePresence when the Nightmare is gone (the "Accessed None ...
CallFunc_GetActorOfClass_ReturnValue" spam). Inside one PIE burst:
  t=3 s   show BP_Nightmare (the presence drone should fade in),
  t=10 s  destroy it (UpdatePresence now finds None 4 times a second: the drone should fade out, with no errors),
  t=30 s  end. Logs whether GetActorOfClass still finds it after the destroy.
Pair with record_audio.sh (FOA_DRIVER=Tools/Unreal/horror/pie_presence_gone.py) for the mix, the active sounds and
bp_errors.csv. Writes Saved/HorrorShots/<FOA_RUN>_timeline.json. Changes the PIE world only."""
import json
import os
import time

import unreal

RUN = os.environ.get('FOA_RUN', 'presence')
OUT = f'P:/FoA/Saved/HorrorShots/{RUN}_timeline.json'
NM = '/Game/FoA/Characters/Player/BP_Nightmare.BP_Nightmare_C'
S = {'t0': time.time(), 'log': [], 'h': None, 'done': False, 'shown': False, 'gone': False, 'checked': False}


def log(kind, **kw):
    S['log'].append(dict(t=round(time.time() - S['t0'], 2), epoch=round(time.time(), 2), kind=kind, **kw))


def finish():
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(S['log'], fh, indent=1)


def tick(_dt):
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not w:
        log('pie_gone')
        return finish()
    el = time.time() - S['t0']
    cls = unreal.load_class(None, NM)
    if el >= 3 and not S['shown']:
        S['shown'] = True
        m = unreal.GameplayStatics.get_actor_of_class(w, cls)
        if m:
            m.set_actor_hidden_in_game(False)
        log('show', found=bool(m))
    if el >= 10 and not S['gone']:
        S['gone'] = True
        m = unreal.GameplayStatics.get_actor_of_class(w, cls)
        if m:
            m.destroy_actor()
        log('destroy', found=bool(m))
    if el >= 11 and not S['checked']:
        S['checked'] = True
        log('after_destroy', still_found=bool(unreal.GameplayStatics.get_actor_of_class(w, cls)))
    if el >= 30:
        log('end')
        finish()


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('presence-gone test scheduled ->', OUT)
