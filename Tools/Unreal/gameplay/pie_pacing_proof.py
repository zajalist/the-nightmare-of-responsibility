"""25s bounded sequence/contact proof, injected after real front-end/phone free roam atT1.
Uses the real interaction handler for boot reach/grab; explicit FirstSteps is labeled as the fixture precondition.
Never starts/stops PIE and never writes an Actor editor property.
"""
import json
from pathlib import Path
import time
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world
player = unreal.GameplayStatics.get_player_character(world, 0)
controller = unreal.GameplayStatics.get_player_controller(world, 0)
actor_class = unreal.load_class(None, '/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C')
actors = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(world, actor_class)}
boot, bed = actors['Boot_L'], actors['Bed']
director = unreal.GameplayStatics.get_actor_of_class(world, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
gi = unreal.GameplayStatics.get_game_instance(world)
door = next(a for a in actors.values() if str(a.get_editor_property('InteractionKey')) == 'Door')
original_progress = dict(SaveSlot=str(gi.get_editor_property('SaveSlot')),
    Knowledge=set(gi.get_editor_property('Knowledge')), Notebook=list(gi.get_editor_property('Notebook')))
QA_SLOT = 'FoA_QA_Pacing_Isolated'
interactor = player.get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
inventory = player.get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'))
old_speed = unreal.GameplayStatics.get_global_time_dilation(world)
unreal.GameplayStatics.set_global_time_dilation(world, 1.0)
S = dict(start=time.time(), phase=0, ready=0, handle=None, rows=[], done=False, isolated=False)


def snap(label):
    row = dict(label=label, t=round(time.time() - S['start'], 3), stage=gi.get_editor_property('InteractionStage'),
               boot=str(boot.get_editor_property('State')), pending=boot.get_editor_property('bPendingRow'),
               items=[str(n) for n in inventory.get_editor_property('Items')],
               move_ignored=controller.is_move_input_ignored(), look_ignored=controller.is_look_input_ignored())
    row['boots_visible'] = next(c for c in player.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'BootsWornMesh').is_visible()
    row['door_active'] = door.get_editor_property('bToolActive')
    row['knowledge_case'] = 'isolated fresh first-day GI; original progress restored without saving'
    S['rows'].append(row)
    return row


def use_boot():
    v = boot.get_actor_location()
    toward = unreal.Vector(-v.x, -v.y, 0); toward.normalize()
    stand = unreal.Vector(v.x + toward.x * 75, v.y + toward.y * 75, player.get_actor_location().z)
    assert player.teleport(stand, player.get_actor_rotation())
    controller.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(stand + unreal.Vector(0, 0, 60), v))
    interactor.call_method('SetFocus', (boot,)); interactor.call_method('Refresh', (True,))
    assert str(interactor.get_editor_property('Verb')) == 'Use'
    interactor.call_method('Interact', ())


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    if S['handle'] is not None:
        unreal.unregister_slate_post_tick_callback(S['handle'])
    unreal.GameplayStatics.set_global_time_dilation(world, old_speed)
    if S['isolated']:
        gi.call_method('SetProofProgressContext', (original_progress['SaveSlot'], original_progress['Knowledge'], original_progress['Notebook']))
        unreal.GameplayStatics.delete_game_in_slot(QA_SLOT, 0)
    out = Path('P:/FoA/Saved/Integration/pacing_runtime.json')
    out.write_text(json.dumps(dict(reason=reason, rows=S['rows']), indent=1), encoding='utf-8')
    print('PACING_PROOF', reason, str(out))


def tick(_dt):
    try:
        t = time.time() - S['start']
        if not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
            return finish('pie_gone')
        if t > 25:
            return finish('cap')
        if S['phase'] == 0:
            gi.call_method('SetProofProgressContext', (QA_SLOT, set(), [])); S['isolated'] = True
            row = snap('real_phone_complete_T1')
            assert row['stage'] == 1 and row['boot'] == 'Closed' and 'Key' not in row['items'], row
            assert not boot.call_method('CanInteract', ('Use', 'None'))
            boot.call_method('Interact', ('Use', 'None'))
            bed.call_method('Interact', ('Look', 'None'))
            row = snap('early_key_blocked_look_allowed_without_skipping_T1')
            assert row['stage'] == 1 and row['boot'] == 'Closed' and 'Key' not in row['items'], row
            director.call_method('ReportEvent', ('FirstSteps',))
            S['rows'].append(dict(label='explicit_FirstSteps_fixture', native_movement_test='owned separately by coordinator'))
            bed.call_method('Interact', ('Look', 'None'))
            row = snap('real_bed_look_advances_T2_to_T3'); assert row['stage'] == 3, row
            use_boot()
            row = snap('reach_started_no_early_reward'); assert row['pending'] and row['boot'] == 'Closed' and 'Key' not in row['items'], row
            S['ready'] = t + .4; S['phase'] = 1
        elif S['phase'] == 1 and t > S['ready']:
            row = snap('before_Grab_still_untaken'); assert row['boot'] == 'Closed' and 'Key' not in row['items'], row
            boot.call_method('CancelPendingRow', (True,))
            S['ready'] = t + 1.6; S['phase'] = 2
        elif S['phase'] == 2 and t > S['ready']:
            row = snap('cancelled_timer_stayed_cancelled')
            assert not row['pending'] and row['boot'] == 'Closed' and 'Key' not in row['items'] and row['stage'] == 3, row
            use_boot(); S['ready'] = t + 1.5; S['phase'] = 3
        elif S['phase'] == 3 and t > S['ready']:
            row = snap('authored_Grab_committed_once')
            assert not row['pending'] and row['boot'] == 'Searched' and row['items'].count('Key') == 1 and row['stage'] == 4, row
            assert not row['boots_visible'], row
            assert not door.call_method('CanInteract', ('Use', 'Key')), 'First-day bare feet must block first key attempt'
            before = set(gi.get_editor_property('Knowledge'))
            gi.call_method('SetProofProgressContext', (QA_SLOT, before | {unreal.Name('Knows.KeySnaps')}, list(gi.get_editor_property('Notebook'))))
            assert door.call_method('CanInteract', ('Use', 'Key')), 'Known replay shortcut must remain available'
            gi.call_method('SetProofProgressContext', (QA_SLOT, before, list(gi.get_editor_property('Notebook'))))
            snap('barefoot_key_blocked_known_replay_explicitly_allowed')
            use_boot(); S['ready'] = t + .6; S['phase'] = 4
        elif S['phase'] == 4 and t > S['ready']:
            row = snap('dressing_started_no_early_wear')
            assert row['pending'] and row['boot'] == 'Searched' and not row['boots_visible'], row
            assert not door.call_method('CanInteract', ('Use', 'Key'))
            S['ready'] = t + 8.1; S['phase'] = 5
        elif S['phase'] == 5 and t > S['ready']:
            row = snap('WorkDone_wears_boots_and_unlocks_key_attempt')
            assert not row['pending'] and row['boot'] == 'Worn' and row['boots_visible'], row
            assert row['items'].count('Key') == 1 and not row['door_active'], row
            assert door.call_method('CanInteract', ('Use', 'Key'))
            unreal.SystemLibrary.execute_console_command(world, 'Shot showui filename=P:/FoA/Saved/Integration/pacing_boots_worn.png -nosuffix', controller)
            return finish('early_block_cancel_contact_dressing_and_replay_gate_passed')
    except Exception as exc:
        S['rows'].append(dict(error=repr(exc)))
        if boot.get_editor_property('bPendingRow'):
            boot.call_method('CancelPendingRow', (True,))
        finish('error')


S['handle'] = unreal.register_slate_post_tick_callback(tick)
print('PACING_PROOF scheduled25s after real phone atT1; direct interface attempts and actual boot interaction handler')
