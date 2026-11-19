"""Bounded PIE proof of real wardrobe Notify, collision and interrupted new-day reset.
Run only inside the coordinator's EXCLUSIVE PIE window via integration/run_read.py.
Writes Saved/Integration/wardrobe_transition.json and normal Shot screenshots; does not start or stop PIE.
"""
import json
import os
import time

import unreal

OUT = 'P:/FoA/Saved/Integration/wardrobe_transition.json'
G = '/Game/FoA/Gameplay/'
FROM_ROAM = os.environ.get('FOA_FROM_ROAM') == '1'
S = dict(start=time.monotonic(), phase=0, log=[], shots=0, shot_at=0, handle=None, done=False, atomic_wall_samples=0)
PARTS=('Body','Face','StartOutfit','Shirt','Trousers','Socks','Tie','Suit','BootsWornMesh')


def material_slots(p):
    return {name:[c.get_material(i).get_path_name() if c.get_material(i) else None
                  for i in range(c.get_num_materials())]
            for name in PARTS for c in [p.get_editor_property(name)]}


def actor(w, label):
    return next(a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)
                if a.get_actor_label() == label)


def vec(v):
    return [round(v.x, 3), round(v.y, 3), round(v.z, 3)]


def record(w, label):
    d, p = actor(w, 'BeatDirector'), unreal.GameplayStatics.get_player_character(w, 0)
    ia = p.get_component_by_class(unreal.load_class(None, G + 'BPC_Interactor.BPC_Interactor_C'))
    camera = d.get_editor_property('TopDownCamera')
    hud = actor(w, 'BP_FoAFrontEnd').get_editor_property('HUD')
    dream = actor(w, 'DreamDirector')
    mpc = unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream')
    beat = d.get_editor_property('Beat')
    mid=p.get_editor_property('SandTransitionMID')
    row = dict(label=label, wall=round(time.monotonic() - S['start'], 2), game=unreal.GameplayStatics.get_time_seconds(w),
               beat=str(beat.get_editor_property('Id')) if beat else None,
               transition=d.get_editor_property('bWardrobeTransition'), cinematic=p.get_editor_property('bCinematic'),
               hidden=p.hidden, collision=p.get_actor_enable_collision(), player=vec(p.get_actor_location()),
               move_ignored=unreal.GameplayStatics.get_player_controller(w, 0).is_move_input_ignored(),
               movement=str(p.character_movement.movement_mode), suspended=unreal.SystemLibrary.is_timer_paused(ia, 'Scan'),
               focus=ia.get_editor_property('Target').get_actor_label() if ia.get_editor_property('Target') else None,
               wardrobe=str(actor(w, 'Wardrobe').get_editor_property('State')),
               door_hidden=actor(w, 'Door_Bedroom').hidden, frame_hidden=actor(w, 'DoorFrame_Bedroom').hidden,
               frame=vec(actor(w, 'DoorFrame_Bedroom').get_actor_location()),
               shirt_hidden=actor(w, 'Shirt_T7').hidden,
               camera=vec(camera.get_relative_transform().translation), camera_fov=camera.field_of_view,
               light_visible=d.get_editor_property('WardrobeKeyLight').is_visible(),
               wall_visible=d.get_editor_property('OldDoorWall').is_visible(),
               wall_collision=str(d.get_editor_property('OldDoorWall').get_collision_enabled()),
               sand_transition=p.get_editor_property('bSandTransition'),
               saved_materials=len(p.get_editor_property('SandOriginalMaterials')),
               coverage=mid.get_scalar_parameter_value('Amount') if mid else None,
               transition_mode=mid.get_scalar_parameter_value('Transition') if mid else None,
               echo_base=dream.get_editor_property('BaseEcho'),
               echo=unreal.MaterialLibrary.get_scalar_parameter_value(w, mpc, 'EchoStrength'),
               face_slip=unreal.MaterialLibrary.get_scalar_parameter_value(w, mpc, 'FaceSlip'),
               hud_visibility=str(hud.get_visibility()) if hud else None,
               blockers={c.get_name(): str(c.get_collision_enabled())
                         for c in d.get_components_by_class(unreal.BoxComponent)
                         if c.get_name() in ('FallenWardrobeBlocker', 'OldDoorBlocker')})
    S['log'].append(row)
    print('WARDROBE', label, row)
    return row


def shot(w):
    folder='P:/FoA/Saved/Integration/WardrobeShots'
    os.makedirs(folder,exist_ok=True)
    pc=unreal.GameplayStatics.get_player_controller(w,0)
    # No showui: this cinematic hides its HUD, and the global Slate UI path can capture an editor window.
    unreal.SystemLibrary.execute_console_command(w,f'Shot filename={folder}/frame_{S["shots"]:03d}.png -nosuffix',pc)
    S['shots'] += 1


def phone_action(w):
    widget = actor(w, 'Phone_Nightstand').get_component_by_class(unreal.WidgetComponent).get_widget()
    assert widget, 'T0 phone widget missing'
    widget.call_method('DoAction')


def finish(result, error=None):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['handle'])
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(dict(result=result, error=error, shots=S['shots'], atomic_wall_samples=S['atomic_wall_samples'], log=S['log']), f, indent=2)
    print('WARDROBE PROOF', result, error or '', OUT)


def topple(w):
    d, p = actor(w, 'BeatDirector'), unreal.GameplayStatics.get_player_character(w, 0)
    d.call_method('EnterBeat', (6,))
    assert p.teleport(unreal.Vector(310, 75, 94), unreal.Rotator(pitch=0,yaw=180,roll=0)), 'fixture cannot stand by old door'
    wardrobe = actor(w, 'Wardrobe')
    assert str(wardrobe.get_editor_property('State')) == 'Standing'
    # The real BPI row and its WardrobeFalling event, rather than a fabricated beat completion.
    wardrobe.call_method('Interact', ('Notify', 'HandleOff'))
    S['fall_at'] = unreal.GameplayStatics.get_time_seconds(w)
    record(w, 'fall_starts')


def tick(_dt):
    try:
        w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not w:
            return finish('FAIL', 'PIE ended before proof finished')
        wall = time.monotonic() - S['start']
        if wall > 40:
            return finish('FAIL', '40 second cap')
        d, p = actor(w, 'BeatDirector'), unreal.GameplayStatics.get_player_character(w, 0)
        game = unreal.GameplayStatics.get_time_seconds(w)
        if S['phase'] in (5, 6, 7, 9) and actor(w, 'Door_Bedroom').hidden:
            fill = d.get_editor_property('OldDoorWall')
            assert fill.is_visible() and not fill.hidden_in_game, 'Door vanished before wall became visible'
            assert fill.get_collision_enabled() == unreal.CollisionEnabled.QUERY_AND_PHYSICS, 'Vanished doorway has no collision'
            S['atomic_wall_samples'] += 1
        if wall - S['shot_at'] > 0.3:
            S['shot_at'] = wall
            shot(w)
        if S['phase'] == 0 and wall > 0.3:
            unreal.SystemLibrary.execute_console_command(w, 'ke * OnSplashFinished')
            S['phase'] = 1
        elif S['phase'] == 1 and wall > 1.0:
            unreal.SystemLibrary.execute_console_command(w, 'ke * OnTitleConfirmed')
            S['phase'] = 2
        elif S['phase'] == 2 and wall > 1.8:
            unreal.SystemLibrary.execute_console_command(w, 'ke * WakeUp')
            S['phase'] = 3
        elif S['phase'] == 3 and actor(w, 'BP_FoAFrontEnd').get_editor_property('bInGameplay') \
                and d.get_editor_property('SeqPlayer') and not d.get_editor_property('bWakeDone') \
                and p.get_editor_property('bCinematic'):
            d.call_method('SkipWakeUp')
            S['ready_at'] = game + 1.0
            S['phase'] = 4
        elif S['phase'] == 4 and game > S['ready_at']:
            if not FROM_ROAM:
                phone_action(w)
            S['ready_at'] = game + 0.75
            S['phase'] = 4.5
        elif S['phase'] == 4.5 and game > S['ready_at']:
            camera = d.get_editor_property('TopDownCamera')
            S['camera_home'] = camera.get_relative_transform().export_text()
            S['camera_fov'] = camera.field_of_view
            S['hud_visibility'] = str(actor(w, 'BP_FoAFrontEnd').get_editor_property('HUD').get_visibility())
            S['echo_home'] = actor(w, 'DreamDirector').get_editor_property('BaseEcho')
            S['face_home'] = unreal.MaterialLibrary.get_scalar_parameter_value(w,unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream'),'FaceSlip')
            S['materials_home'] = material_slots(p)
            S['home'] = actor(w, 'DoorFrame_Bedroom').get_actor_location()
            S['knowledge'] = set(str(k) for k in unreal.GameplayStatics.get_game_instance(w).get_editor_property('Knowledge'))
            topple(w)
            S['phase'] = 5
        elif S['phase'] == 5 and game - S['fall_at'] > 0.25:
            r = record(w, 'locked')
            assert r['transition'] and r['cinematic'] and r['suspended'] and r['move_ignored']
            assert r['focus'] is None
            assert not r['collision']
            assert abs(r['camera_fov'] - 60.0) < 0.01 and abs(r['camera'][2] - 255.0) < 0.1
            assert 'HIDDEN' in r['hud_visibility']
            assert r['light_visible']
            assert abs(r['echo_base'] - 0.03) < 0.0001 and r['echo'] <= 0.04
            assert abs(r['face_slip'] - S['face_home']) < .0001
            S['phase'] = 6
        elif S['phase'] == 6 and game - S['fall_at'] > 4.4:
            r = record(w, 'disintegrated')
            assert r['hidden'] and r['door_hidden'] and r['frame_hidden']
            assert r['wall_visible'] and 'QUERY_AND_PHYSICS' in r['wall_collision']
            assert S['atomic_wall_samples'] > 0, 'No vanished-door samples observed'
            assert r['sand_transition'] and r['saved_materials'] > 0
            assert r['coverage'] <= .01 and abs(r['transition_mode']-1.)<.0001
            S['phase'] = 7
        elif S['phase'] == 7 and game - S['fall_at'] > 5.85:
            r = record(w, 'reformed')
            assert not r['hidden'] and r['collision'] and r['transition']
            assert r['beat'] == 'T7' and r['frame'][0] < 0 and not r['frame_hidden'] and not r['door_hidden']
            assert r['shirt_hidden'] and all('QUERY_ONLY' in mode for mode in r['blockers'].values())
            assert d.get_editor_property('ClothingSearchStage') == 1
            assert r['wall_visible'] and 'QUERY_AND_PHYSICS' in r['wall_collision']
            wardrobe = actor(w, 'Wardrobe')
            center, extent = wardrobe.get_actor_bounds(False)
            radius = p.capsule_component.get_scaled_capsule_radius()
            assert p.get_actor_location().x < center.x - extent.x - radius, 'reformed inside fallen footprint'
            safe = p.get_actor_location()
            p.set_actor_location(unreal.Vector(center.x, center.y, safe.z), True, False)
            assert p.get_actor_location().x <= center.x - extent.x - 8 - radius + 2, 'sweep entered fallen blocker'
            assert p.teleport(safe, p.get_actor_rotation())
            record(w, 'collision_sweep_blocked')
            S['phase'] = 8
        elif S['phase'] == 8 and game - S['fall_at'] > 7.5:
            r = record(w, 'control_restored')
            assert not r['transition'] and not r['cinematic'] and not r['suspended'] and not r['move_ignored']
            camera = d.get_editor_property('TopDownCamera')
            assert camera.get_relative_transform().export_text() == S['camera_home']
            assert abs(camera.field_of_view - S['camera_fov']) < 0.01
            assert r['hud_visibility'] == S['hud_visibility']
            assert not r['light_visible']
            assert abs(r['echo_base'] - S['echo_home']) < 0.0001
            assert not r['sand_transition'] and r['saved_materials'] == 0
            assert material_slots(p) == S['materials_home'], 'Base material slots were not restored exactly'
            d.call_method('ResetHouse')
            topple(w)
            S['phase'] = 9
        elif S['phase'] == 9 and game - S['fall_at'] > 4.4:
            r = record(w, 'interrupt_during_vanish')
            assert r['hidden'] and r['transition']
            assert r['wall_visible'] and 'QUERY_AND_PHYSICS' in r['wall_collision']
            d.call_method('RestartDay')
            S['restart_at'] = game
            S['phase'] = 10
        elif S['phase'] == 10 and game - S['restart_at'] > 4.5:
            d.call_method('SkipWakeUp')
            S['phase'] = 11
        elif S['phase'] == 11 and game - S['restart_at'] > 6.0:
            phone_action(w)
            S['phase'] = 12
        elif S['phase'] == 12 and game - S['restart_at'] > 7.0:
            r = record(w, 'new_day_no_stale_timers')
            assert not r['transition'] and not r['hidden'] and r['collision'] and not r['cinematic']
            assert not r['suspended'] and not r['move_ignored'] and r['wardrobe'] == 'Standing'
            assert not r['door_hidden'] and not r['frame_hidden']
            assert all('NO_COLLISION' in mode for mode in r['blockers'].values())
            camera = d.get_editor_property('TopDownCamera')
            assert camera.get_relative_transform().export_text() == S['camera_home']
            assert abs(camera.field_of_view - S['camera_fov']) < 0.01
            assert not r['light_visible']
            assert not r['wall_visible'] and 'NO_COLLISION' in r['wall_collision']
            assert not r['sand_transition'] and r['saved_materials'] == 0
            assert abs(r['echo_base'] - S['echo_home']) < 0.0001
            assert (actor(w, 'DoorFrame_Bedroom').get_actor_location() - S['home']).length() < 0.1
            for name in ('WardrobeSandTick', 'WardrobeVanish', 'WardrobeReappear', 'FinishWardrobeTransition', 'StageWrongWall', 'ExitTopDown'):
                assert not unreal.SystemLibrary.is_timer_active(d, name), 'stale timer ' + name
            assert S['knowledge'] <= set(str(k) for k in unreal.GameplayStatics.get_game_instance(w).get_editor_property('Knowledge'))
            shot(w)
            topple(w)
            S['phase'] = 13
        elif S['phase'] == 13 and game-S['fall_at'] > .6:
            record(w,'interrupt_during_rattle')
            d.call_method('RestartDay');S['rattle_restart']=game;S['phase']=14
        elif S['phase'] == 14 and game-S['rattle_restart'] > 4.5:
            d.call_method('SkipWakeUp');S['phase']=15
        elif S['phase'] == 15 and game-S['rattle_restart'] > 6.:
            phone_action(w);S['phase']=16
        elif S['phase'] == 16 and game-S['rattle_restart'] > 7.:
            r=record(w,'rattle_timer_cancelled')
            assert r['wardrobe']=='Standing' and not r['transition'] and not r['cinematic']
            assert not r['sand_transition'] and not r['wall_visible']
            assert not unreal.SystemLibrary.is_timer_active(actor(w,'Wardrobe'),'WardrobeBeginFall')
            finish('PASS')
    except Exception as exc:
        finish('FAIL', repr(exc))


if FROM_ROAM:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    assert world, 'FOA_FROM_ROAM requires active PIE gameplay'
    player = unreal.GameplayStatics.get_player_character(world, 0)
    controller = unreal.GameplayStatics.get_player_controller(world, 0)
    assert not player.get_editor_property('bCinematic') and not controller.is_move_input_ignored()
    assert player.character_movement.movement_mode == unreal.MovementMode.MOVE_WALKING
    S['phase'] = 4
    S['ready_at'] = unreal.GameplayStatics.get_time_seconds(world) + 0.2
S['handle'] = unreal.register_slate_post_tick_callback(tick)
print('WARDROBE proof scheduled, 40 second cap; coordinator owns PIE lifecycle')
