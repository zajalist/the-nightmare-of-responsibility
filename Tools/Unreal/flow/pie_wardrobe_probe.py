"""Story lane, in PIE (run_chase_final.py pie_wardrobe_probe, one EXCLUSIVE window): the wardrobe fall's real timeline,
read only, before the first-person rework (the user's pick A, 2026-11-10). Fixture as gameplay/pie_wardrobe_transition.py:
EnterBeat(6), he stands at the door (320, 80) facing it, the wardrobe's real Notify HandleOff row. Samples every frame for
7.5 s: the wardrobe's State, its Pivot's world rotation and location, its bounds, his location, the view target, the
camera. Result: Saved/StoryShots/wardrobe_probe.json."""
import importlib
import json
import sys
import time
from pathlib import Path

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402
importlib.reload(proof_save)

OUT = Path('P:/FoA/Saved/StoryShots/wardrobe_probe.json')
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
S = dict(t0=time.time(), phase=0, rows=[], done=False, h=None, fall=None)


def label(lbl):
    return next((a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if a.get_actor_label() == lbl), None)


def r1(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


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
    unreal.log('[wardrobe_probe] ' + reason)


def tick(_dt):
    try:
        t = time.time() - S['t0']
        if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() != w:  # ended or replaced: touch nothing cached
            return finish('pie_gone')
        if t > 44:
            return finish('cap')
        d, fe = label('BeatDirector'), label('BP_FoAFrontEnd')
        wr = label('Wardrobe')
        if not (d and fe and wr):
            return
        pc = unreal.GameplayStatics.get_player_controller(w, 0)
        p = unreal.GameplayStatics.get_player_character(w, 0)
        ph = S['phase']
        if ph == 0 and t > 0.2:
            fe.call_method('OnSplashFinished', ()); S['phase'] = 1
        elif ph == 1 and t > 0.5:
            fe.call_method('OnTitleConfirmed', ()); S['phase'] = 2
        elif ph == 2 and t > 0.8:
            fe.call_method('WakeUp', ()); S['phase'] = 3
        elif ph == 3:
            story = fe.get_editor_property('Story')
            if story and story.is_in_viewport():
                story.call_method('Finish', ())
            elif fe.get_editor_property('bInGameplay') and d.get_editor_property('SeqPlayer') and not d.get_editor_property('bWakeDone'):
                d.call_method('SkipWakeUp', ()); S['phase'] = 4
        elif ph == 4 and d.get_editor_property('bWakeDone') and pc.get_view_target() == p and not p.get_editor_property('bCinematic'):
            unreal.SystemLibrary.pause_timer(d, 'PollStoryMoment')
            unreal.SystemLibrary.clear_timer(d, 'TryStoryMoment')
            d.call_method('EnterBeat', (6,))
            p.teleport(unreal.Vector(320, 80, 94), unreal.Rotator(0, 0, 0))
            pc.set_control_rotation(unreal.Rotator(0, 0, 0))
            S['at'] = t + 0.6; S['phase'] = 5
        elif ph == 5 and t >= S['at']:
            wr.call_method('Interact', ('Notify', 'HandleOff'))
            S['fall'] = unreal.GameplayStatics.get_time_seconds(w); S['phase'] = 6
        elif ph == 6:
            gt = unreal.GameplayStatics.get_time_seconds(w) - S['fall']
            piv = wr.get_editor_property('Pivot')
            o, e = wr.get_actor_bounds(True)
            cam = pc.player_camera_manager
            S['rows'].append(dict(t=round(gt, 3), state=str(wr.get_editor_property('State')),
                                  pivot_rot=[round(x, 1) for x in (piv.get_world_rotation().pitch, piv.get_world_rotation().yaw, piv.get_world_rotation().roll)],
                                  pivot_loc=r1(piv.get_world_location()), bounds=[r1(o), r1(e)], pawn=r1(p.get_actor_location()),
                                  hidden=p.is_hidden() if hasattr(p, 'is_hidden') else p.get_editor_property('hidden'),
                                  view=pc.get_view_target().get_name(), cam=r1(cam.get_camera_location()),
                                  door_hidden=label('Door_Bedroom').get_editor_property('hidden'),
                                  beat=str(d.get_editor_property('Beat').get_editor_property('Id')) if d.get_editor_property('Beat') else None))
            if gt > 7.5:
                finish('done')
    except Exception as exc:  # noqa: BLE001
        S['rows'].append(dict(error=repr(exc)))
        finish('error')


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('wardrobe probe scheduled')
