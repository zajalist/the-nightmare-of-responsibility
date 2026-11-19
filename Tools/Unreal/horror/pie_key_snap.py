"""Audio lane: PIE proof of the key-snap sound through the real door-tool flow (no ReportEvent shortcut).
Fixture as in gameplay's pie_door_tools_proof.py: EnterBeat 4, the Key in the inventory, the boots worn; then the real
Use on the door starts the key tool, and AdvanceDoorTool turns it (pressure to the 42 degree bind, ease back, on) until
the tool releases and the row commits. Logs the epoch of every door State change, so the recording can be read at
the snap. Ends 4 s after the door reaches KeyJammed (or at 40 s).
Pair with record_audio.sh (FOA_DRIVER=Tools/Unreal/horror/pie_key_snap.py). Writes Saved/HorrorShots/<FOA_RUN>_timeline.json."""
import json
import os
import time

import unreal

RUN = os.environ.get('FOA_RUN', 'keysnap')
OUT = f'P:/FoA/Saved/HorrorShots/{RUN}_timeline.json'
S = {'t0': time.time(), 'last': time.time(), 'log': [], 'h': None, 'done': False, 'phase': 0, 'state': None, 'snap': None,
     'bind_until': None}


def log(kind, **kw):
    S['log'].append(dict(t=round(time.time() - S['t0'], 3), epoch=round(time.time(), 3), kind=kind, **kw))


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    log('end', reason=reason)
    unreal.unregister_slate_post_tick_callback(S['h'])
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(S['log'], fh, indent=1)


def actor(w, path):
    return unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, path))


def tick(_dt):
    try:
        w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not w:
            return finish('pie_gone')
        now = time.time()
        dt, S['last'] = min(now - S['last'], 0.1), now
        t = now - S['t0']
        door = actor(w, '/Game/FoA/Gameplay/BP_Door.BP_Door_C')
        state = str(door.get_editor_property('State'))
        if state != S['state']:
            log('state', state=state)
            S['state'] = state
            if state == 'KeyJammed' and S['snap'] is None:
                S['snap'] = t
        if S['snap'] is not None and t > S['snap'] + 4.0:
            return finish('snapped')
        if t > 40:
            return finish('cap')
        if S['phase'] == 0 and t > 1.0:
            d = actor(w, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
            p = unreal.GameplayStatics.get_player_character(w, 0)
            inv = p.get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'))
            ia = p.get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
            d.call_method('EnterBeat', (4,))
            inv.call_method('Add', ('Key',))
            boot = door.get_editor_property('BootProgressionSource')
            if boot:
                boot.call_method('SetState', ('Worn', True))
                d.call_method('ReportEvent', ('BootsWorn',))
            ia.call_method('SetFocus', (door,))
            ia.call_method('Refresh', (True,))
            ia.call_method('Interact', ())
            log('use', tool_active=bool(door.get_editor_property('bToolActive')), verb=str(ia.get_editor_property('Verb')))
            S['phase'] = 1
        elif S['phase'] == 1 and door.get_editor_property('bToolActive'):
            if door.get_editor_property('bToolReady'):
                stage = door.get_editor_property('ToolStepIndex')
                if stage == 2 and S['bind_until'] is None:
                    S['bind_until'] = t + 0.5  # hold the pressure at the bind, then ease back as the player must
                    log('bind', angle=round(door.get_editor_property('ToolAngle'), 1))
                ease = stage == 2 and S['bind_until'] is not None and t >= S['bind_until']
                door.call_method('AdvanceDoorTool', (-1.0 if ease else 1.0, dt))
        elif S['phase'] == 1 and not door.get_editor_property('bToolActive') and S['state'] == 'Locked' and t > 2.0:
            if not S.get('released'):
                S['released'] = True
                log('tool_released', releasing=bool(door.get_editor_property('bToolReleasing')))
    except Exception as e:  # a broken fixture must still end the run and write its log
        log('error', what=str(e)[:300])
        finish('error')


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('key snap test scheduled ->', OUT)
