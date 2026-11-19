"""Story lane, in PIE (run_chase_final.py pie_battle_view, one EXCLUSIVE window): the user's live battle, 2026-11-10:
"in the battle mode now I don't see any of the clothes". Read-only diagnosis, then suspect toggles, each with a frame.
Fixture: front end, SkipWakeUp, EnterBeat(8); the battle intro plays (FOA_SKIP=1 skips it through BattleIntroDone).
Once BP_Encounter is active (+1.5 s):
  base     frame + per garment: Rig/Body visibility, skinned asset, anim, materials, bounds, the bounds centre projected
           to the screen (on screen or not), distance to the camera; the view target, camera location/rotation/FOV,
           the camera manager's fade amount
  t_anim   every Rig stops its animation and goes to its ref pose (rig's clips)          -> frame
  t_mat    every Rig's materials -> WorldGridMaterial (face's MI_Garment_*)             -> frame
  t_scale  every Rig's world scale reported (and set to 1 if below 0.05)                -> frame
Result: Saved/StoryShots/battle_view.json; frames Saved/StoryShots/battle_view/<step>.png."""
import importlib
import json
import os
import sys
import time
from pathlib import Path

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402
importlib.reload(proof_save)

OUT = Path('P:/FoA/Saved/StoryShots/battle_view.json')
SHOTS = 'P:/FoA/Saved/StoryShots/battle_view/'
Path(SHOTS).mkdir(parents=True, exist_ok=True)
ROOT = '/Game/FoA/'
SKIP = os.environ.get('FOA_SKIP', '0') == '1'
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
S = dict(t0=time.time(), phase=0, rows=[], done=False, h=None, at=0.0, steps=['base', 't_anim', 't_mat', 't_scale'], i=0)


def actor(path):
    return unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, ROOT + path))


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def r1(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def log(kind, **kw):
    S['rows'].append(dict(kind=kind, t=round(time.time() - S['t0'], 2), **kw))


def shown(c):
    return c.is_visible() and not c.get_editor_property('hidden_in_game') and not c.get_owner().get_editor_property('hidden')


def snapshot(enc, step):
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    cam = pc.player_camera_manager
    cl, cr = cam.get_camera_location(), cam.get_camera_rotation()
    gs = []
    for g in enc.get_editor_property('Garments') or []:
        comps = []
        for c in g.get_components_by_class(unreal.PrimitiveComponent):
            o, e, _ = unreal.SystemLibrary.get_component_bounds(c)
            res = unreal.GameplayStatics.project_world_to_screen(pc, o, False)
            ok, scr = (res if isinstance(res, tuple) else (res is not None, res))
            info = dict(name=c.get_name(), cls=c.get_class().get_name(), shown=shown(c), visible=c.is_visible(),
                        hig=c.get_editor_property('hidden_in_game'), centre=r1(o), extent=r1(e), scale=r1(c.get_world_scale()),
                        on_screen=bool(ok), screen=[round(scr.x), round(scr.y)] if ok else None,
                        cam_dist=round((o - cl).length()), attach=c.get_attach_parent().get_name() if c.get_attach_parent() else None,
                        mats=[m.get_name() if m else None for m in c.get_materials()] if hasattr(c, 'get_materials') else None)
            if isinstance(c, unreal.SkeletalMeshComponent):
                sa = c.get_skinned_asset()
                info.update(asset=sa.get_name() if sa else None, anim=str(c.get_editor_property('animation_mode')),
                            single=c.get_editor_property('animation_data').get_editor_property('anim_to_play').get_name()
                            if c.get_editor_property('animation_data').get_editor_property('anim_to_play') else None,
                            playing=c.is_playing() if hasattr(c, 'is_playing') else None)
            comps.append(info)
        d = prop(g, 'Data')
        gs.append(dict(id=d.get_name() if d else None, state=str(prop(g, 'State')), actor=r1(g.get_actor_location()),
                       hidden=g.get_editor_property('hidden'), body=prop(g, 'Body').get_name() if prop(g, 'Body') else None,
                       comps=comps))
    vt = pc.get_view_target()
    log('snapshot', step=step, view=vt.get_name() if vt else None, cam=r1(cl), rot=[round(cr.pitch, 1), round(cr.yaw, 1)],
        fov=round(cam.get_fov_angle(), 1), fade=prop(cam, 'fade_amount'), state=str(prop(enc, 'BattleState')), garments=gs)
    unreal.SystemLibrary.execute_console_command(w, 'Shot showui filename=%s%s.png -nosuffix' % (SHOTS, step), pc)


def toggle(enc, step):
    for g in enc.get_editor_property('Garments') or []:
        for c in g.get_components_by_class(unreal.SkeletalMeshComponent):
            if step == 't_anim':
                c.stop()
                c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
                c.set_animation(None)
            elif step == 't_mat':
                grid = unreal.load_asset('/Engine/EngineMaterials/WorldGridMaterial')
                for i in range(c.get_num_materials()):
                    c.set_material(i, grid)
            elif step == 't_scale' and c.get_world_scale().x < 0.05:
                c.set_world_scale3d(unreal.Vector(1, 1, 1))


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    if S['h'] is not None:
        unreal.unregister_slate_post_tick_callback(S['h'])
    try:
        proof_save.restore(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), PROOF)
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning('[proof_save] restore failed: %r' % exc)
    OUT.write_text(json.dumps(dict(reason=reason, rows=S['rows']), indent=1, default=str))
    unreal.log('[battle_view] finished ' + reason)


def tick(dt):
    try:
        if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() != w:  # ended or replaced: touch nothing cached
            return finish('pie_gone')
        t = time.time() - S['t0']
        if t > 46:
            log('cap_state', missing=S.get('missing'), phase=S['phase'])
            return finish('cap')
        d = actor('Gameplay/BP_BeatDirector.BP_BeatDirector_C')
        fe = actor('UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
        enc = actor('Gameplay/Encounter/BP_Encounter.BP_Encounter_C')
        pc = unreal.GameplayStatics.get_player_controller(w, 0)
        p = unreal.GameplayStatics.get_player_character(w, 0)
        if not (d and fe and enc):  # the world is still loading (or another map is open: logged once at the cap)
            S['missing'] = dict(map=w.get_name(), d=bool(d), fe=bool(fe), enc=bool(enc))
            return
        ph = S['phase']
        if ph == 0 and t > 0.1:
            fe.call_method('OnSplashFinished', ()); S['phase'] = 1
        elif ph == 1 and t > 0.4:
            fe.call_method('OnTitleConfirmed', ()); S['phase'] = 2
        elif ph == 2 and t > 0.7:
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
            d.call_method('EnterBeat', (8,))
            S['intro_at'] = t; S['phase'] = 5
            log('enter_t8')
        elif ph == 5:
            if enc.get_editor_property('bActive') and str(enc.get_editor_property('BattleState')) == 'PlayerCommand':
                S['at'] = t + 1.0; S['phase'] = 6
                log('battle_active')
            elif SKIP and t > S['intro_at'] + 1.0 and not S.get('skipped'):
                S['skipped'] = True
                d.call_method('BattleIntroDone', ())
        elif ph == 6 and t >= S['at']:
            step = S['steps'][S['i']]
            if step != 'base':
                toggle(enc, step)
            snapshot(enc, step)
            S['i'] += 1
            S['at'] = t + 0.6
            if S['i'] >= len(S['steps']):
                S['phase'] = 7
        elif ph == 7 and t >= S['at']:
            finish('done')
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started', skip=SKIP)
