"""Story lane, in PIE, read only probe: does BP_BeatDirector.SetStoryHUDHidden reach the front end's HUD? Called directly
at T1, then read back (the flag, the cached widget, the HUD's visibility) a tick and 0.5 s later, then restored.
-> Saved/StoryShots/hud_probe.json"""
import importlib
import json
import sys
import time
from pathlib import Path

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402
importlib.reload(proof_save)

OUT = Path('P:/FoA/Saved/StoryShots/hud_probe.json')
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
S = dict(t0=time.time(), phase=0, after=0.0, done=False, h=None, rows=[])
D = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
FES = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))


def prop(o, n, default='<no property>'):
    try:
        return o.get_editor_property(n)
    except Exception as exc:  # noqa: BLE001
        return '%s: %r' % (default, exc)


def log(kind):
    huds = [prop(fe, 'HUD') for fe in FES]
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, front_ends=len(FES), flag=prop(D, 'bStoryHUDHidden'),
               cached=str(prop(D, 'StoryHUD')), cached_vis=str(prop(D, 'StoryHUDVisibility')),
               huds=[(str(hd.get_name()) if hasattr(hd, 'get_name') else str(hd), str(hd.get_visibility()) if hasattr(hd, 'get_visibility') else None) for hd in huds])
    S['rows'].append(row)
    unreal.log('[hud_probe] ' + json.dumps(row, default=str))


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    try:
        proof_save.restore(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), PROOF)
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning('[proof_save] restore failed: %r' % exc)
    OUT.write_text(json.dumps(dict(reason=reason, rows=S['rows']), indent=1, default=str))


def cmd(c):
    unreal.SystemLibrary.execute_console_command(w, c, pc)


def tick(dt):
    try:
        if S['done']:
            return
        if time.time() - S['t0'] > 40:
            return finish('timeout_%d' % S['phase'])
        if time.time() < S['after']:
            return
        ph = S['phase']
        steps = {0: ('ke * OnSplashFinished', 0.8), 1: ('ke * OnTitleConfirmed', 1.2), 2: ('ke * WakeUp', 6.2),
                 3: ('ke * OnStoryFinished', 2.6), 4: ('ke * SkipWakeUp', 0.6)}
        if ph in steps:
            cmd(steps[ph][0]); S['after'] = time.time() + steps[ph][1]; S['phase'] += 1
        elif ph == 5:
            if D.get_editor_property('BeatIndex') != 0:
                return
            cmd('ke * ReportEvent PhoneWakeUp'); cmd('ke * ClosePhone'); S['after'] = time.time() + 1.0; S['phase'] += 1
        elif ph == 6:
            log('before'); D.call_method('SetStoryHUDHidden', (True,)); log('after_hide_call'); S['after'] = time.time() + 0.5; S['phase'] += 1
        elif ph == 7:
            log('hide_plus_0.5'); D.call_method('SetStoryHUDHidden', (False,)); log('after_show_call'); S['after'] = time.time() + 0.3; S['phase'] += 1
        elif ph == 8:
            log('show_plus_0.3'); finish('probed')
    except Exception as exc:  # noqa: BLE001
        S['rows'].append(dict(error=repr(exc)))
        finish('error')


OUT.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
