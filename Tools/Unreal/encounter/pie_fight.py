"""In-engine T8 driver: plays the running BP_Encounter from a Slate post-tick callback, so there is no per-step
python_exec round trip (each one stalls the game 1-3 s; the remote pie_drive.py could not finish a fight in a window).
  run inside a PIE burst (no lease of its own): python Tools/Unreal/integration/run_read.py Tools/Unreal/encounter/pie_fight.py FOA_MODE=win|lose
win   the sim's policy (stun a telegraphed attacker, mirror when low, else progress the weakest garment), perfect keys
lose  eight tie Strikes through ApplySelf on the first player turn, then Flee
(Replaces the remote pie_drive.py, whose 1-3 s exec round trips could not finish a fight inside a PIE window.)
Bounded: unregisters itself at Victory/Defeat, when PIE ends, or after FOA_CAP seconds (default 45). Writes
Saved/EncounterCaptures/fight_<mode>.json (turn log + MARK times) and takes 'Shot showui' frames every 0.25 s.
Production key windows and turn pauses stay intact; only global time dilation x FOA_SPEED (default3) changes."""
import json
import os
import time

import unreal

MODE = os.environ.get('FOA_MODE', 'win')
CAP = float(os.environ.get('FOA_CAP', '45'))
SPEED = float(os.environ.get('FOA_SPEED', '3'))
SHOT_INTERVAL = float(os.environ.get('FOA_SHOT_INTERVAL', '0.25'))
OUT = f'P:/FoA/Saved/EncounterCaptures/fight_{MODE}.json'
DATA = '/Game/FoA/Gameplay/Encounter/Data/DA_Move_'
MOVES = {"ButtonUp": (10, "SleeveLabyrinth"), "PullOn": (5, "Mismatched"), "StepIn": (5, "TwistedLeg"),
         "TieKnot": (5, "Constricted")}
CLEAR = {"SleeveLabyrinth": "FindArmhole", "Mismatched": "MatchPair", "TwistedLeg": "UntwistLeg",
         "Constricted": "Loosen"}
STUN = {"Trousers": "UntwistLeg", "Tie": "Loosen"}
TELEGRAPHED = {"Kick", "Strike"}
S = dict(t0=time.time(), log=[], marks={}, acted=False, key_idx=-1, shot=0.0, done=False, h=None, turns=0, lost=False)


def mark(label):
    if label not in S['marks']:
        S['marks'][label] = round(time.time(), 2)
        S['log'].append(dict(t=round(time.time() - S['t0'], 2), mark=label))


def name(o, prefix):
    return o.get_name().replace(prefix, '') if o else None


def snapshot(e):
    gs = []
    for g in e.get_editor_property('Garments'):
        d, i = g.get_editor_property('Data'), g.get_editor_property('Intent')
        gs.append(dict(id=name(d, 'DA_Opponent_'), p=g.get_editor_property('Progress'),
                       r=d.get_editor_property('Resistance'), s=str(g.get_editor_property('State')),
                       act=[m.get_name().replace('DA_Move_', '') for m in d.get_editor_property('ActMoves')],
                       intent=name(i, 'DA_Move_')))
    return dict(c=e.get_editor_property('Composure'), r=e.get_editor_property('Resolve'),
                st=[str(s) for s in e.get_editor_property('Statuses')], target=e.get_editor_property('Target'), g=gs)


def choose(s):
    """The sim's policy (sim_party.py), as in pie_drive.py."""
    alive = [(i, g) for i, g in enumerate(s['g']) if g['s'] != 'Defeated']
    for i, g in alive:
        if g['intent'] in TELEGRAPHED and g['id'] in STUN and g['s'] != 'Stunned':
            return i, STUN[g['id']]
    if s['c'] <= 25 and s['r'] >= 5:
        return None, 'CheckMirror'
    i, g = min(alive, key=lambda ig: (ig[1]['r'] - ig[1]['p'], ig[1]['r']))
    prog = next(m for m in g['act'] if m in MOVES)
    cost, blocker = MOVES[prog]
    if blocker in s['st']:
        return i, CLEAR[blocker]
    if s['r'] < cost:
        if 'Constricted' in s['st']:
            tie = next((j for j, h in alive if h['id'] == 'Tie'), None)
            return (tie, 'Loosen') if tie is not None else (None, 'CheckMirror')
        return None, 'DeepBreath'
    return i, prog


def finish(why):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    S['log'].append(dict(t=round(time.time() - S['t0'], 2), end=why))
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(dict(mode=MODE, result=why, turns=S['turns'], marks=S['marks'], log=S['log']), fh, indent=1)
    unreal.log(f'[t8] {MODE} -> {why} after {S["turns"]} turns ({OUT})')


def tick(_dt):
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not w:
        return finish('pie_gone')
    if time.time() - S['t0'] > CAP:
        return finish('cap')
    e = unreal.GameplayStatics.get_actor_of_class(
        w, unreal.load_class(None, '/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C'))
    if not e:
        return
    if time.time() - S['shot'] > SHOT_INTERVAL:
        S['shot'] = time.time()
        unreal.SystemLibrary.execute_console_command(w, 'Shot showui')
    if unreal.GameplayStatics.get_global_time_dilation(w) < SPEED - 0.01 and \
            unreal.GameplayStatics.get_global_time_dilation(w) > 0.5:  # hit-stop drops it to 0.05 and back to 1
        unreal.GameplayStatics.set_global_time_dilation(w, SPEED)
    state = str(e.get_editor_property('BattleState'))
    if not e.get_editor_property('bActive'):
        return
    mark('intro')
    if state in ('Victory', 'Defeat'):
        mark(state.lower())
        return finish(state)
    if e.get_editor_property('Composure') < 100:
        mark('hit')
    if e.get_editor_property('bAwaitingKey'):
        idx = e.get_editor_property('InputIndex')
        if idx != S['key_idx']:
            S['key_idx'] = idx
            e.call_method('SubmitKey', (e.get_editor_property('InputKeys')[idx],))
        return
    if not e.get_editor_property('bPlayerTurn'):
        S['acted'] = False
        return
    if S['acted']:
        return
    S['acted'] = True
    S['turns'] += 1
    mark('command')
    s = snapshot(e)
    if any(g['s'] == 'Telegraph' for g in s['g']):
        mark('telegraph')
    if MODE == 'lose':
        if not S['lost']:
            S['lost'] = True
            for _ in range(8):
                e.call_method('ApplySelf', (unreal.load_asset(DATA + 'Strike'),))
        e.call_method('Flee', ())
        S['log'].append(dict(t=round(time.time() - S['t0'], 2), turn=S['turns'], move='8x Strike, Flee', c=s['c']))
        return
    idx, mv = choose(s)
    if idx is not None and idx != s['target']:
        e.call_method('CycleTarget', (idx - s['target'],))
    e.call_method('ChooseMove', (unreal.load_asset(DATA + mv),))
    S['key_idx'] = -1
    S['log'].append(dict(t=round(time.time() - S['t0'], 2), turn=S['turns'], move=mv, target=idx, c=s['c'], r=s['r'],
                         st=s['st'], left=sum(1 for g in s['g'] if g['s'] != 'Defeated')))


def setup():
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    e = unreal.GameplayStatics.get_actor_of_class(
        w, unreal.load_class(None, '/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C')) if w else None
    assert e, 'no BP_Encounter in the PIE world'
    # Actor.set_editor_property can reconstruct the actor's SCS during PIE and invalidate live components.
    # Use production timing and a runtime function for time dilation; never mutate editor properties here.
    unreal.GameplayStatics.set_global_time_dilation(w, SPEED)
    S['h'] = unreal.register_slate_post_tick_callback(tick)
    print('t8 fight scheduled', MODE, '->', OUT)


setup()
