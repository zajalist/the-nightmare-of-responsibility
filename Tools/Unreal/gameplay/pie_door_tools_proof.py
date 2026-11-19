"""Bounded42s native Blueprint-API tool proof, injected after realFE/phone free roam atT1.
Explicit tool precondition: EnterBeat4 +inventoryKey. Production turning/cancel/reset functions do all work.
This fixture verifies the gameplay API; OS D/A/Q mapping is separately observed and never claimed fromAPI calls.
"""
import json
import math
import os
import datetime
from pathlib import Path
import time
import unreal

w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w
p = unreal.GameplayStatics.get_player_character(w, 0)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
d = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
door = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_Door.BP_Door_C'))
inv = p.get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'))
ia = p.get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
out = Path('P:/FoA/Saved/Integration/door_tools_runtime.json')
shots=Path('P:/FoA/Saved/Integration/door_tools')/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')
shots.mkdir(parents=True,exist_ok=True)
NATIVE = os.environ.get('FOA_TOOL_NATIVE') == '1'
DRIVER = 'native D/A/Q input' if NATIVE else 'native Blueprint API; OS mapping unverified'
S = dict(t0=time.time(), last=time.time(), phase=0, ready=0, rows=[], h=None, done=False, held=False, screw=-1, markers=set(), saw_d=False, saw_q=False)


def sample_contact(t):
    """Measure the rendered tool and actual retargeted arm throughout each turn."""
    if t < S.get('contact_after', 0):return
    S['contact_after'] = t + .1
    if not door.get_editor_property('bToolActive') or not door.get_editor_property('bToolReady') or str(door.get_editor_property('ToolMode')) != 'Screwdriver':return
    body = p.get_editor_property('Body')
    tool = p.get_editor_property('HeldTool')
    if not tool.is_visible():return
    mesh = tool.get_editor_property('static_mesh'); box = mesh.get_bounding_box()
    # This shipped mesh's blade tip is the centre of its positive-Z end.
    local_tip = unreal.Vector((box.min.x + box.max.x)/2, (box.min.y + box.max.y)/2, box.max.z)
    xf = tool.get_world_transform()
    tip = unreal.MathLibrary.transform_location(xf, local_tip)
    shaft = xf.rotation.rotate_vector(unreal.Vector(0,0,1)); shaft.normalize()
    parts = {c.get_name(): c for c in door.get_components_by_class(unreal.SceneComponent)}
    target = parts['ToolContact'].get_world_location()
    normal = parts['Pivot'].get_forward_vector()
    shoulder, elbow, wrist = [body.get_socket_location(n) for n in ('upperarm_r','lowerarm_r','hand_r')]
    upper, lower = shoulder-elbow, wrist-elbow
    length = upper.length()+lower.length()
    dot = lambda a,b: a.x*b.x + a.y*b.y + a.z*b.z
    cosine = max(-1., min(1., dot(upper,lower)/(upper.length()*lower.length())))
    axis_cosine = max(-1., min(1., dot(shaft,normal)))
    grip = p.get_editor_property('HeldToolGrip').get_world_location()
    expected_grip = p.get_editor_property('ToolGripWorld')
    S.setdefault('contact_samples', []).append(dict(t=t, screw=door.get_editor_property('ToolStepIndex'),
        turn=door.get_editor_property('ToolAngle'), tip_error_cm=(tip-target).length(),
        axis_error_deg=math.degrees(math.acos(axis_cosine)), grip_error_cm=(grip-expected_grip).length(),
        elbow_flex_deg=180-math.degrees(math.acos(cosine)), reach_ratio=(wrist-shoulder).length()/length,
        shoulder=list(shoulder.to_tuple()), elbow=list(elbow.to_tuple()), wrist=list(wrist.to_tuple()),
        tip=list(tip.to_tuple()), screw_target=list(target.to_tuple()), pawn=list(p.get_actor_location().to_tuple())))


def key_down(name):
    key = unreal.Key(); key.set_editor_property('key_name', name)
    return pc.is_input_key_down(key)


def marker(name):
    if name not in S['markers']:
        S['markers'].add(name); snap(name, True)


def snap(label, shot=False):
    parts = {c.get_name(): c for c in door.get_components_by_class(unreal.SceneComponent)}
    row = dict(label=label, t=round(time.time() - S['t0'], 3), state=str(door.get_editor_property('State')),
        mode=str(door.get_editor_property('ToolMode')), active=door.get_editor_property('bToolActive'),
        ready=door.get_editor_property('bToolReady'), releasing=door.get_editor_property('bToolReleasing'),
        angle=door.get_editor_property('ToolAngle'), attempted=door.get_editor_property('ToolInputAngle'),
        screw=door.get_editor_property('ToolStepIndex'), items=[str(x) for x in inv.get_editor_property('Items')],
        selected=inv.get_editor_property('Selected'),
        move_ignored=pc.is_move_input_ignored(), look_ignored=pc.is_look_input_ignored(),
        owns_locks=door.get_editor_property('bToolOwnsLocks'), view=pc.get_view_target().get_class().get_name(),
        camera=str(pc.player_camera_manager.get_camera_location()), contact=str(parts['ToolContact'].get_world_location()))
    row['D_down'], row['Q_down'] = key_down('D'), key_down('Q')
    row['task_light'] = parts['ToolTaskLight'].is_visible()
    row['cached_controller_is_real'] = door.get_editor_property('ToolController') == pc
    row['step_timer_active'] = unreal.SystemLibrary.is_timer_active(door, 'StepDoorTool')
    row['step_timer_elapsed'] = unreal.SystemLibrary.get_timer_elapsed_time(door, 'StepDoorTool')
    row['tool_last_time'] = door.get_editor_property('ToolLastTime')
    row['game_time'] = unreal.GameplayStatics.get_time_seconds(w)
    row['mouse_delta'] = list(pc.get_input_mouse_delta())
    stick = unreal.Key(); stick.set_editor_property('key_name', 'Gamepad_RightX')
    row['right_stick'] = pc.get_input_analog_key_state(stick)
    row['tool_rotation']=str(parts['ToolPivot'].get_editor_property('relative_rotation'))
    source_anim=p.get_editor_property('Mesh').get_anim_instance()
    row['grip_weight']=source_anim.get_editor_property('GripWeight')
    row['key_grip_selected']=source_anim.get_editor_property('KeyGrip')
    row['visible_screws']=[parts['ToolScrew'+str(i)].is_visible() for i in range(4)]
    row['contact_times'] = {str(n): float(v) for n, v in door.get_editor_property('ToolContactTimes').items()}
    current = p.get_current_montage()
    row['current_montage'] = current.get_path_name() if current else None
    S['rows'].append(row)
    out.write_text(json.dumps(dict(status='running', driver=DRIVER, folder=str(shots),rows=S['rows']), indent=1))
    if shot:
        def xf(tr):
            return dict(position=list(tr.translation.to_tuple()),rotation=list(tr.rotation.to_tuple()),scale=list(tr.scale3d.to_tuple()))
        for component_name in ('Mesh','Body'):
            component=p.get_editor_property(component_name)
            bones=[dict(name=str(component.get_bone_name(i)),**xf(component.get_socket_transform(component.get_bone_name(i),unreal.RelativeTransformSpace.RTS_COMPONENT)))
                   for i in range(component.get_num_bones())]
            (shots/(label+'_'+component_name.lower()+'_pose.json')).write_text(json.dumps(dict(
                mesh=component.get_skeletal_mesh_asset().get_path_name(),space='component',world=xf(component.get_world_transform()),bones=bones),indent=1))
        unreal.SystemLibrary.execute_console_command(w, 'Shot showui filename='+str(shots/(label+'.png'))+' -nosuffix', pc)
    return row


def begin():
    ia.call_method('SetFocus', (door,)); ia.call_method('Refresh', (True,))
    assert str(ia.get_editor_property('Verb')) == 'Use'
    ia.call_method('Interact', ())
    assert door.get_editor_property('bToolActive'), 'Real Use failed to start the tool'


def tool_precondition():
    d.call_method('EnterBeat', (4,)); inv.call_method('Add', ('Key',))
    # Explicit isolated-tool fixture: dressing is proven by pie_pacing_proof, not this setup.
    boot = door.get_editor_property('BootProgressionSource')
    if boot:
        boot.call_method('SetState', ('Worn', True))
        d.call_method('ReportEvent', ('BootsWorn',))
        assert str(boot.get_editor_property('State')) == 'Worn'


def restored(row):
    assert not row['active'] and not row['releasing'] and not row['owns_locks'], row
    assert not row['move_ignored'] and not row['look_ignored'] and row['view'] == 'BP_FoAPlayer_C', row


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    if S['h'] is not None:
        unreal.unregister_slate_post_tick_callback(S['h'])
    if door.get_editor_property('bToolActive') or door.get_editor_property('bToolReleasing'):
        door.call_method('CancelDoorTool', ())
    proof=dict(status='complete', reason=reason, driver=DRIVER,folder=str(shots),saw_D=S['saw_d'], saw_Q=S['saw_q'], rows=S['rows'],
               contact_samples=S.get('contact_samples', []))
    out.write_text(json.dumps(proof, indent=1));(shots/'evidence.json').write_text(json.dumps(proof,indent=1))
    print('DOOR_TOOL_PROOF', reason, str(out))


def tick(_dt):
    try:
        now = time.time(); dt = min(now - S['last'], .1); S['last'] = now
        S['saw_d'] |= key_down('D'); S['saw_q'] |= key_down('Q')
        t = now - S['t0']
        sample_contact(t)
        if t > 42:
            snap('cap_state', True)
            return finish('cap')
        if not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
            return finish('pie_gone')
        if S['phase'] == 0:
            S['rows'].append(dict(label='explicit_tool_precondition_after_real_FE_phone', inventory_before=[str(x) for x in inv.get_editor_property('Items')]))
            tool_precondition();S['cancel_inventory']=[str(x) for x in inv.get_editor_property('Items')];begin()
            snap('key_inserted', True); S['phase'] = 1
        elif S['phase'] == 1:
            if NATIVE and int(t * 4) != S.get('last_diag', -1):
                S['last_diag'] = int(t * 4); snap('native_input_watch')
            if door.get_editor_property('bToolReady') and door.get_editor_property('bToolActive'):
                if NATIVE:
                    marker('ready_native_D_350ms_then_Q')
                else:
                    door.call_method('AdvanceDoorTool', (1.0, dt))
            if not NATIVE and door.get_editor_property('ToolAngle') >= 20:
                snap('key_cancel_before_snap', True)
                door.call_method('CancelDoorTool', ())
            if not door.get_editor_property('bToolActive'):
                row = snap('key_cancel_restored'); restored(row)
                assert row['state'] == 'Locked' and 'Key' in row['items'] and 'KeyStub' not in row['items'], row
                assert row['items']==S['cancel_inventory'],'Same-day cancel changed physical inventory'
                if NATIVE:
                    assert S['saw_d'] and S['saw_q'], 'Native cancel requires both real D and Q'
                S['ready'] = t + .3; S['phase'] = 2
        elif S['phase'] == 2 and t > S['ready']:
            begin(); S['phase'] = 3
        elif S['phase'] == 3 and door.get_editor_property('bToolReady'):
            stage = door.get_editor_property('ToolStepIndex')
            if NATIVE:
                if stage == 0:marker('ready_native_D_key_until_bind')
                elif stage == 3:marker('ready_native_D_key_retry_3500ms')
            if not S['held'] and stage == 2:
                row = snap('key_bound_at_42', True)
                assert row['active'] and row['state'] == 'Locked' and 'Key' in row['items'], row
                assert abs(row['angle'] - 42.0) < .01,row
                S['held'] = True; S['ready'] = t + .5
            if stage == 2 and t >= S['ready']:
                if not S.get('bind_checked'):
                    row = snap('forward_pressure_cannot_skip_bind', True)
                    assert row['active'] and abs(row['angle'] - 42.0) < .01,row
                    S['bind_checked'] = True
                if NATIVE:marker('ready_native_A_key_ease_1300ms')
            if not NATIVE:
                direction = -1.0 if stage == 2 and t >= S['ready'] else 1.0
                door.call_method('AdvanceDoorTool', (direction, dt))
            if not door.get_editor_property('bToolActive'):
                # The release owns the camera/input until its existing timer ends.
                # A real second Use request must not replace the first session.
                before=snap('key_release_before_reentry')
                assert before['releasing'] and before['owns_locks'],before
                old_view=door.get_editor_property('ToolPreviousView')
                inv.call_method('Add',('Screwdriver',))
                door.call_method('Interact',('Use','Screwdriver'))
                after=snap('key_release_reentry_blocked')
                assert not after['active'] and after['releasing'] and after['mode']=='Key',after
                assert door.get_editor_property('ToolPreviousView')==old_view,after
                committed=list(inv.get_editor_property('Items'))
                door.call_method('FinishDoorTool',())
                assert list(inv.get_editor_property('Items'))==committed,'Repeated finish duplicated a transaction'
                S['phase'] = 4
        elif S['phase'] == 4 and not door.get_editor_property('bToolReleasing'):
            row = snap('key_finish_committed_once'); restored(row)
            assert row['state'] == 'KeyJammed' and row['items'].count('KeyStub') == 1 and 'Key' not in row['items'], row
            begin(); S['phase'] = 5
        elif S['phase'] == 5 and door.get_editor_property('bToolReady'):
            if NATIVE and int(t * 2) != S.get('last_screw_diag', -1):
                S['last_screw_diag'] = int(t * 2); snap('native_screw_watch')
            if NATIVE:
                marker('ready_native_D_screws_11500ms')
            step = door.get_editor_property('ToolStepIndex')
            if step != S['screw']:
                S['screw'] = step; snap('screw_' + str(step + 1) + '_contact', True)
            if not NATIVE:
                door.call_method('AdvanceDoorTool', (1.0, dt))
            if not door.get_editor_property('bToolActive'):
                before=snap('plate_release_before_reentry')
                assert before['releasing'] and before['state']=='PlateOff',before
                door.call_method('Interact',('Use','None'))
                after=snap('plate_release_other_row_blocked')
                assert after['state']=='PlateOff' and after['releasing'] and not after['active'],after
                S['phase'] = 6
        elif S['phase'] == 6 and not door.get_editor_property('bToolReleasing'):
            row = snap('four_screws_removed', True); restored(row)
            assert row['state'] == 'PlateOff' and row['screw'] == 4 and row['items'].count('Screwdriver') == 1, row
            d.call_method('ResetHouse', ()); tool_precondition(); begin()
            S['phase'] = 7
        elif S['phase'] == 7 and door.get_editor_property('bToolReady'):
            if NATIVE:
                marker('ready_native_D_reset_2800ms')
            else:
                door.call_method('AdvanceDoorTool', (1.0, dt))
            if door.get_editor_property('ToolAngle') >= 15:
                before = snap('live_session_before_ResetHouse')
                d.call_method('ResetHouse', ())
                row = snap('ResetHouse_cancelled_and_restored'); restored(row)
                assert row['state'] == 'Locked' and row['items'] == before['items'], row
                gi=unreal.GameplayStatics.get_game_instance(w)
                knowledge=set(gi.get_editor_property('Knowledge'));notebook=list(gi.get_editor_property('Notebook'))
                d.call_method('BeginMorning',())
                morning=snap('new_morning_emptied_physical_slots')
                assert morning['items']==[] and morning['selected']==-1,morning
                assert set(gi.get_editor_property('Knowledge'))==knowledge,'Morning discarded knowledge'
                assert list(gi.get_editor_property('Notebook'))==notebook,'Morning discarded notebook'
                return finish('key_cancel_four_screws_reset_and_new_morning_passed')
    except Exception as exc:
        S['rows'].append(dict(error=repr(exc)))
        finish('error')


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('DOOR_TOOL_PROOF scheduled42s; real Use, mandatory bind/ease/retry, camera/props shots, reset cleanup')
