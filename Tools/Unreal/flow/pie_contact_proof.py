"""Story lane, in PIE (run_chase_final.py pie_contact_proof, one EXCLUSIVE window): montage rows commit again at the
restored InteractionContact notify, with REAL E presses (the runner relays them with editor_pie_press_key).
  menu -> Wake up -> intro -> skip -> T0 phone -> FirstSteps + the bed Look (fixture preconditions for T3, labelled)
  -> CommodeDrawer: the normal Scan must focus "Open the drawer", real E, the drawer must reach Open (AM_FoA_OpenDrawer)
  -> Boot_L: Scan must focus "Look inside the boot", real E, the boot must reach Searched with the Key in the bag
     (AM_FoA_PickUp_Floor, the same montage as the chase reaches).
Shots: Saved/StoryShots/contact_proof/*.png. Result: Saved/StoryShots/contact_proof.json (reason 'drawer_and_boot_passed')."""
import json
import os
import time
from pathlib import Path

import unreal
import importlib
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402  the player's save stays untouched (main's rule 2026-11-10)
importlib.reload(proof_save)

OUT = Path('P:/FoA/Saved/StoryShots/contact_proof.json')
SHOTS = 'P:/FoA/Saved/StoryShots/contact_proof'
INPUTS = Path('P:/FoA/Saved/StoryShots/contact_proof_input.json')
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)  # before the splash: every save of this run goes to the QA slot
pc = unreal.GameplayStatics.get_player_controller(w, 0)
os.makedirs(SHOTS, exist_ok=True)
for f in os.listdir(SHOTS):
    os.remove(os.path.join(SHOTS, f))
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, shot=0.0, n=0, input_id=0, tries=0, pressed=0.0)


def cls(path):
    return unreal.load_class(None, path)


D = unreal.GameplayStatics.get_actor_of_class(w, cls('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
P = unreal.GameplayStatics.get_player_character(w, 0)
IA = P.get_component_by_class(cls('/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
BAG = P.get_component_by_class(cls('/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'))
ACTORS = {}
for _a in unreal.GameplayStatics.get_all_actors_of_class(w, cls('/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C')):
    ACTORS.setdefault(_a.get_actor_label(), _a)
    ACTORS.setdefault(str(_a.get_editor_property('InteractionKey')), _a)  # rows name the InteractionKey
GI = unreal.GameplayStatics.get_game_instance(w)
# (label, prompt the Scan must offer, state that proves the commit, item that must arrive or None)
TARGETS = [('CommodeDrawer', 'Open the drawer', 'Open', None), ('Boot_L', 'Look inside the boot', 'Searched', 'Key')]


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def log(kind, **kw):
    tgt = prop(IA, 'Target')
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, beat=prop(D, 'BeatIndex'), stage=prop(GI, 'InteractionStage'),
               target=tgt.get_actor_label() if tgt else None, prompt=str(prop(IA, 'Prompt')),
               items=[str(i) for i in (prop(BAG, 'Items') or [])], **kw)
    S['rows'].append(row)
    unreal.log('[contact_proof] ' + json.dumps(row, default=str))
    return row


def shot(tag):
    if time.time() - S['shot'] < 0.2:
        return
    S['n'] += 1
    unreal.SystemLibrary.execute_console_command(w, 'Shot showui filename=%s/%03d_%s.png -nosuffix' % (SHOTS, S['n'], tag), pc)
    S['shot'] = time.time()


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    if S['h'] is not None:
        unreal.unregister_slate_post_tick_callback(S['h'])
    try:  # back to the player's slot before the runner stops PIE
        proof_save.restore(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), PROOF)
    except Exception as exc:  # noqa: BLE001  never lose the run's outputs over the restore
        unreal.log_warning('[proof_save] restore failed: %r' % exc)
    OUT.write_text(json.dumps(dict(reason=reason, rows=S['rows']), indent=1, default=str))
    unreal.log('[contact_proof] finished ' + reason)


def cmd(c):
    unreal.SystemLibrary.execute_console_command(w, c, pc)


def wait(sec):
    S['after'] = time.time() + sec
    S['phase'] += 1


def aim(a, k):
    """Stand k cm in front of the actor (toward the room centre) and look at its bounds centre."""
    o, e = a.get_actor_bounds(False)
    v = unreal.Vector(-o.x, -o.y, 0)
    v.normalize()
    stand = unreal.Vector(o.x + v.x * k, o.y + v.y * k, P.get_actor_location().z)
    ok = P.teleport(stand, P.get_actor_rotation())
    pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(pc.player_camera_manager.get_camera_location(), o))
    return ok, stand.to_tuple()


def tick(dt):
    try:
        if S['done']:
            return
        if not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
            return finish('pie_gone')
        el = time.time() - S['t0']
        if el > 46:
            return finish('timeout_phase_%d' % S['phase'])
        ph = S['phase']
        if ph >= 7:
            shot('p%d' % ph)
        if time.time() < S['after']:
            return
        if ph == 0:
            cmd('ke * OnSplashFinished'); wait(0.8)
        elif ph == 1:
            cmd('ke * OnTitleConfirmed'); wait(1.2)
        elif ph == 2:
            cmd('ke * WakeUp'); wait(6.2)
        elif ph == 3:
            cmd('ke * OnStoryFinished'); wait(2.6)
        elif ph == 4:
            cmd('ke * SkipWakeUp'); wait(0.6)
        elif ph == 5:
            if prop(D, 'BeatIndex') != 0:
                return
            cmd('ke * ReportEvent PhoneWakeUp'); cmd('ke * ClosePhone'); wait(0.6)
        elif ph == 6:  # fixture preconditions, not under test: T1 FirstSteps and the T2 bed Look open T3
            D.call_method('ReportEvent', ('FirstSteps',))
            ACTORS['Bed'].call_method('Interact', ('Look', 'None'))
            log('fixture_T3'); wait(0.6)
        elif ph in (7, 9):  # stand, aim; next phase checks focus and asks for a real E
            label = TARGETS[(ph - 7) // 2][0]
            ok, at = aim(ACTORS[label], (75, 95, 60, 115)[S['tries'] % 4])
            log('aim', at=at, ok=ok, actor=label, state=str(prop(ACTORS[label], 'State'))); wait(0.6)
        elif ph in (8, 10):
            label, prompt, state, item = TARGETS[(ph - 8) // 2]
            a = ACTORS[label]
            if not S['pressed']:
                tgt = prop(IA, 'Target')
                if not tgt or tgt != a or str(prop(IA, 'Prompt')) != prompt:
                    log('no_focus', actor=label)
                    S['tries'] += 1
                    if S['tries'] > 6:
                        return finish('scan_never_focused_' + label)
                    S['phase'] -= 1
                    return
                S['input_id'] += 1
                INPUTS.write_text(json.dumps(dict(id=S['input_id'], key='E')))
                S['pressed'] = time.time()
                log('press_E', actor=label, state=str(prop(a, 'State')))
                return
            row = log('after_E', actor=label, state=str(prop(a, 'State')), pending=prop(a, 'bPendingRow'))
            if row['state'] == state and (item is None or item in row['items']):
                log('committed', actor=label, seconds=round(time.time() - S['pressed'], 2))
                S['pressed'] = 0.0
                S['tries'] = 0
                if ph == 10:
                    return finish('drawer_and_boot_passed')
                wait(0.4)
                return
            if time.time() - S['pressed'] > 5.0:
                return finish('no_commit_' + label)
            S['after'] = time.time() + 0.25
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


INPUTS.unlink(missing_ok=True)
OUT.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started')
