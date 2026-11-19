"""Rig lane, in PIE (rig/run_fight_film.py, one EXCLUSIVE window): films ~3 battle turns from the battle camera so the
garment clips (Idle, Telegraph, attack, HitReact, Stun, Defeat on BP_Garment's Rig) can be judged in motion.
Fixture copied from flow/pie_defeat_respace.py (story lane): proof_save isolate/restore, front end, SkipWakeUp,
EnterBeat(8), BattleIntroDone when the intro has not started the fight after 1 s, then encounter/pie_fight.py's win
policy with real SubmitKey turns at FOA_SPEED (default 1.5). Every ~0.066 s wall it writes a 'Shot showui' frame and
samples each garment's State / ClipState / Rig playing. Stops after FILM_TURNS player turns have fully resolved (the
4th command), at Victory/Defeat, or the 44 s cap; always restores the player's save context.
Result: Saved/RigShots/garments/fight_film.json; frames Saved/RigShots/garments/fight_film/f_*.png."""
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

TURNS = int(os.environ.get('FILM_TURNS', '3'))
SPEED = os.environ.get('FILM_SPEED', '1.5')
POLICY = os.environ.get('FILM_POLICY', 'hit')  # hit: reactions without kills; win: pie_fight's own policy
SKIP_INTRO = os.environ.get('FILM_SKIP_INTRO', '0') == '1'  # the old LS_BattleIntro skip left a black fade (story, 2026-11-10)
OUT = Path('P:/FoA/Saved/RigShots/garments/fight_film.json')
SHOTS = 'P:/FoA/Saved/RigShots/garments/fight_film/'
Path(SHOTS).mkdir(parents=True, exist_ok=True)
for f in Path(SHOTS).glob('f_*.png'):
    f.unlink()
ROOT = '/Game/FoA/'
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
S = dict(t0=time.time(), phase=0, rows=[], done=False, h=None, dts=[], scope=None, shot=0.0, n=0, intro_at=None, end_t=None)


def actor(path):
    return unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, ROOT + path))


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def sample(enc):
    gs = []
    for g in enc.get_editor_property('Garments') or []:
        d, rig = prop(g, 'Data'), prop(g, 'Rig')
        gs.append([d.get_name().replace('DA_Opponent_', '') if d else None, str(prop(g, 'State')), str(prop(g, 'ClipState')),
                   bool(rig and rig.is_playing())])
    return dict(t=round(unreal.GameplayStatics.get_time_seconds(w), 3), frame=S['n'], state=str(prop(enc, 'BattleState')),
                c=prop(enc, 'Composure'), g=gs)


def drive():
    values = {'FOA_MODE': 'win', 'FOA_SPEED': SPEED, 'FOA_CAP': '40', 'FOA_SHOT_INTERVAL': '99'}
    saved = {k: os.environ.get(k) for k in values}
    scope = {'__name__': '__main__', '__file__': 'P:/FoA/Tools/Unreal/encounter/pie_fight.py'}
    try:
        os.environ.update(values)
        exec(compile(Path(scope['__file__']).read_text(encoding='utf-8'), scope['__file__'], 'exec'), scope)
    finally:
        for k, v in saved.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
    S['scope'] = scope
    base = scope['choose']

    def hit_no_kill(st):
        """Show the reactions: stun a telegraphed Trousers/Tie, else progress a garment that survives the hit (the Shirt's
        six buttons), else breathe. pie_fight's tick looks choose up in its own globals, so this replaces it."""
        alive = [(i, g) for i, g in enumerate(st['g']) if g['s'] != 'Defeated']
        for i, g in alive:
            if g['intent'] in scope['TELEGRAPHED'] and g['id'] in scope['STUN'] and g['s'] != 'Stunned':
                return i, scope['STUN'][g['id']]
        tough = [(i, g) for i, g in alive if g['r'] - g['p'] > 1]
        if not tough:
            return base(st)
        i, g = tough[0]
        prog = next((m for m in g['act'] if m in scope['MOVES']), None)
        if prog is None or st['r'] < scope['MOVES'][prog][0]:
            return None, 'DeepBreath'
        blocker = scope['MOVES'][prog][1]
        return (i, scope['CLEAR'][blocker]) if blocker in st['st'] else (i, prog)
    if POLICY == 'hit':
        scope['choose'] = hit_no_kill


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    if S['h'] is not None:
        unreal.unregister_slate_post_tick_callback(S['h'])
    sc = S['scope']
    if sc and not sc['S']['done']:
        sc['finish']('film_done')
    try:
        unreal.GameplayStatics.set_global_time_dilation(w, 1)
        proof_save.restore(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), PROOF)
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning('[proof_save] restore failed: %r' % exc)
    clips = sorted({(g[0], g[2]) for r in S['rows'] if 'g' in r for g in r['g']})
    OUT.write_text(json.dumps(dict(reason=reason, frames=S['n'], speed=SPEED, clips_seen=clips, rows=S['rows'],
                                   fight=sc['S']['log'] if sc else None), indent=1, default=str))
    print('RESULT', reason, S['n'], 'frames', json.dumps(clips))


def tick(dt):
    try:
        w2 = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not w2:
            return finish('pie_gone')
        t = time.time() - S['t0']
        if t > 46:
            return finish('cap')
        S['dts'].append(dt)
        if len(S['dts']) == 40 and sorted(S['dts'])[20] > 0.066:
            return finish('throttled_fps')  # a minimized editor: proofs void
        d = actor('Gameplay/BP_BeatDirector.BP_BeatDirector_C')
        fe = actor('UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
        enc = actor('Gameplay/Encounter/BP_Encounter.BP_Encounter_C')
        pc = unreal.GameplayStatics.get_player_controller(w, 0)
        p = unreal.GameplayStatics.get_player_character(w, 0)
        ph = S['phase']
        if ph == 0 and t > 0.1:
            fe.call_method('OnSplashFinished', ())
            S['phase'] = 1
        elif ph == 1 and t > 0.4:
            fe.call_method('OnTitleConfirmed', ())
            S['phase'] = 2
        elif ph == 2 and t > 0.7:
            fe.call_method('WakeUp', ())
            S['phase'] = 3
        elif ph == 3:
            story = fe.get_editor_property('Story')
            if story and story.is_in_viewport():
                story.call_method('Finish', ())
            elif fe.get_editor_property('bInGameplay') and d.get_editor_property('SeqPlayer') and not d.get_editor_property('bWakeDone'):
                d.call_method('SkipWakeUp', ())
                S['phase'] = 4
        elif ph == 4 and d.get_editor_property('bWakeDone') and pc.get_view_target() == p and not p.get_editor_property('bCinematic'):
            unreal.SystemLibrary.pause_timer(d, 'PollStoryMoment')
            unreal.SystemLibrary.clear_timer(d, 'TryStoryMoment')
            d.call_method('EnterBeat', (8,))
            S['intro_at'] = t
            S['phase'] = 5
        elif ph == 5:
            if enc.get_editor_property('bActive'):
                drive()
                S['phase'] = 6
            elif SKIP_INTRO and t > S['intro_at'] + 1.0 and not S.get('skipped'):
                S['skipped'] = True
                d.call_method('BattleIntroDone', ())  # the intro's own skip path (hold Space)
        elif ph == 6:
            fs = S['scope']['S']
            if time.time() - S['shot'] > 0.066:
                S['shot'] = time.time()
                S['n'] += 1
                S['rows'].append(sample(enc))
                unreal.SystemLibrary.execute_console_command(w, 'Shot showui filename=%sf_%04d.png -nosuffix' % (SHOTS, S['n']), pc)
            if fs['turns'] > TURNS and S['end_t'] is None:
                S['end_t'] = time.time() + 0.6  # a beat of the 4th command screen, then stop
            if (S['end_t'] and time.time() > S['end_t']) or fs['done']:
                return finish('done' if S['end_t'] else 'fight_ended_' + str(fs['log'][-1:]))
    except Exception as exc:  # noqa: BLE001
        S['rows'].append(dict(kind='error', error=repr(exc)))
        finish('error')


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('fight_film scheduled')
