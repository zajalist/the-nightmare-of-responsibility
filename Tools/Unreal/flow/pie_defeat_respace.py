"""Story lane, in PIE (run_chase_final.py pie_defeat_respace, one EXCLUSIVE window): the user's battle bug of 2026-11-10,
"when they get eliminated they move back to recenter in the battle in front of him".
Fixture as encounter/pie_outcomes_proof.py (front end, SkipWakeUp, EnterBeat(8), the battle intro skipped through
BattleIntroDone), then encounter/pie_fight.py's win policy with real SubmitKey turns. Every frame it samples each
garment in BP_Encounter.Garments, in the encounter's local space: actor location, Body world location, MotionHome,
State and Body visibility. It stops 3 game seconds after the FIRST garment is Defeated.
Checks (GREEN only if all; main's design: a defeated garment is put ON, it flies to its own slot on him):
  no_snap_back        the defeated garment's visible parts never move away from his slot by more than 5 cm between
                      frames (no teleport back to MotionHome, no detour to the line centre)
  arrives_at_slot     its last visible frame is within 15 cm of Data.EquipSocket on his Mesh
  not_to_origin       no visible part ever comes within 20 cm of his actor origin (unless the slot itself is that close)
  gone_after_arrival  nothing of it is visible 1 s after the defeat
  worn_on_arrival     his worn piece is not visible before the arrival frame and is visible after it
  survivors_respace   the survivors' homes end evenly spaced (max gap / min gap < 1.15) and centred (|mean Y| < 10)
  survivors_smooth    no survivor actor jumps more than 25 cm in one frame after the defeat
Result: Saved/StoryShots/defeat_respace.json; frames Saved/StoryShots/defeat_respace/*.png."""
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

OUT = Path('P:/FoA/Saved/StoryShots/defeat_respace.json')
SHOTS = 'P:/FoA/Saved/StoryShots/defeat_respace/'
Path(SHOTS).mkdir(parents=True, exist_ok=True)
ROOT = '/Game/FoA/'
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
S = dict(t0=time.time(), phase=0, rows=[], done=False, h=None, dts=[], defeat=None, scope=None, shot=0.0, intro_at=None)


def actor(path):
    return unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, ROOT + path))


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def r1(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def gtime():
    return unreal.GameplayStatics.get_time_seconds(w)


def shown(c):
    return c.is_visible() and not c.get_editor_property('hidden_in_game') and not c.get_owner().get_editor_property('hidden')


def sample(enc):
    xf = enc.get_actor_transform()
    local = lambda p: xf.inverse_transform_location(p)  # noqa: E731
    gs = []
    for i, g in enumerate(enc.get_editor_property('Garments') or []):
        body = prop(g, 'Body')
        home = prop(g, 'MotionHome')
        d = prop(g, 'Data')
        gs.append(dict(i=i, id=d.get_name().replace('DA_Opponent_', '') if d else None, state=str(prop(g, 'State')),
                       actor=r1(local(g.get_actor_location())),
                       body=r1(local(body.get_world_location())) if body else None,
                       visible=bool(body and shown(body)),
                       parts=[[c.get_name(), r1(local(c.get_world_location()))] for c in
                              g.get_components_by_class(unreal.PrimitiveComponent) if shown(c)],
                       home=r1(local(home.translation)) if home else None))
    pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
    row = dict(kind='sample', t=round(gtime(), 3), state=str(prop(enc, 'BattleState')), pawn=r1(local(pawn.get_actor_location())), g=gs)
    if S['defeat']:
        g = enc.get_editor_property('Garments')[S['defeat']['i']]
        sock = str(prop(prop(g, 'Data'), 'EquipSocket'))
        mesh = pawn.get_editor_property('mesh')
        row['socket'] = [sock, mesh.does_socket_exist(sock), r1(local(mesh.get_socket_location(sock)))]
        try:  # what the garment's own WearTarget aims at (diagnostic)
            wt = g.call_method('WearTarget')
            loc = wt[0] if isinstance(wt, tuple) else wt
            row['wear_target'] = [r1(local(loc)), str(wt[1]) if isinstance(wt, tuple) else None,
                                  mesh.get_name(), mesh.get_skinned_asset().get_name() if mesh.get_skinned_asset() else None]
        except Exception as exc:  # noqa: BLE001
            row['wear_target'] = repr(exc)[:200]
        part = WORN.get(S['defeat']['id'])
        comp = prop(pawn, part) if part else None
        row['worn'] = [part, bool(comp and comp.is_visible())]
    return row


WORN = {'Shirt': 'Shirt', 'Sock': 'Socks', 'Trousers': 'Trousers', 'Tie': 'Tie'}  # opponent row -> BP_FoAPlayer part


def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** .5


def drive():
    values = {'FOA_MODE': 'win', 'FOA_SPEED': '4', 'FOA_CAP': '44', 'FOA_SHOT_INTERVAL': '99'}
    saved = {k: os.environ.get(k) for k in values}
    scope = {'__name__': '__main__', '__file__': 'P:/FoA/Tools/Unreal/encounter/pie_fight.py'}
    try:
        os.environ.update(values)
        exec(compile(Path(scope['__file__']).read_text(encoding='utf-8'), scope['__file__'], 'exec'), scope)
    finally:
        for k, v in saved.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
    S['scope'] = scope


def checks():
    d = S['defeat']
    if not d:
        return dict(defeat_seen=False)
    after = [r for r in S['rows'] if r.get('kind') == 'sample' and r['t'] >= d['t'] and 'socket' in r]
    gone = [(r, next(g for g in r['g'] if g['i'] == d['i'])) for r in after]
    seen = [(r, g) for r, g in gone if g['parts']]
    away = [max(dist(p[1], r['socket'][2]) for p in g['parts']) for r, g in seen]
    back = max([y - x for x, y in zip(away, away[1:])] or [0.0])
    last_r, last_g = seen[-1] if seen else (None, None)
    end_gap = min(dist(p[1], last_r['socket'][2]) for p in last_g['parts']) if seen else None
    slot_near_origin = bool(after) and dist(after[0]['socket'][2], after[0]['pawn']) < 20
    origin_min = min([dist(p[1], r['pawn']) for r, g in seen for p in g['parts']] or [999.0])
    arrival = seen[-1][0]['t'] if seen else d['t']
    late = [g['parts'] for r, g in gone if r['t'] > d['t'] + 1.0]
    worn_before = any(r['worn'][1] for r in after if r['t'] < arrival and r['worn'][0])
    worn_after = bool(after) and after[-1]['worn'][1]
    last = after[-1] if after else S['rows'][-1]
    homes = sorted(g['home'][1] for g in last['g'] if g['i'] != d['i'] and g['state'] != 'Defeated' and g['home'])
    gaps = [y - x for x, y in zip(homes, homes[1:])]
    even = bool(gaps) and min(gaps) > 1 and max(gaps) / min(gaps) < 1.15 and abs(sum(homes) / len(homes)) < 10
    jumps = 0.0
    for ra, rb in zip(after, after[1:]):
        for ga, gb in zip(ra['g'], rb['g']):
            if ga['i'] != d['i'] and ga['state'] != 'Defeated' and 'Attack' not in (ga['state'], gb['state']):  # a lunge moves
                jumps = max(jumps, dist(ga['actor'], gb['actor']))
    return dict(defeat_seen=True, defeated=d, socket=after[0]['socket'] if after else None,
                flight_frames=len(seen), max_backstep_cm=round(back, 1), no_snap_back=back <= 5,
                end_gap_cm=None if end_gap is None else round(end_gap, 1),
                arrives_at_slot=end_gap is not None and end_gap <= 15,
                origin_min_cm=round(origin_min, 1), not_to_origin=slot_near_origin or origin_min >= 20,
                gone_after_arrival=bool(late) and not any(late), arrival_after_s=round(arrival - d['t'], 3),
                worn_before_arrival=worn_before, worn_on_arrival=(not worn_before) and worn_after,
                survivor_homes_Y=homes, survivor_gaps=gaps, survivors_respace=even,
                survivor_max_frame_jump=round(jumps, 1), survivors_smooth=jumps <= 25)


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    if S['h'] is not None:
        unreal.unregister_slate_post_tick_callback(S['h'])
    sc = S['scope']
    if sc and not sc['S']['done']:
        sc['finish']('defeat_probe_done')
    try:
        unreal.GameplayStatics.set_global_time_dilation(w, 1)
        proof_save.restore(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), PROOF)
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning('[proof_save] restore failed: %r' % exc)
    c = checks()
    ok = reason == 'done' and all(c.get(k) for k in ('defeat_seen', 'no_snap_back', 'arrives_at_slot', 'not_to_origin', 'gone_after_arrival', 'worn_on_arrival', 'survivors_respace', 'survivors_smooth'))
    OUT.write_text(json.dumps(dict(reason=reason, verdict='GREEN' if ok else 'RED', checks=c, rows=S['rows'],
                                   fight=sc['S']['log'] if sc else None), indent=1, default=str))
    print('RESULT', reason, 'GREEN' if ok else 'RED', json.dumps(c, default=str))


def tick(dt):
    try:
        w2 = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if w2 != w:  # ended or replaced: touch nothing cached from the old world
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
            elif t > S['intro_at'] + 1.0 and not S.get('skipped'):
                S['skipped'] = True
                d.call_method('BattleIntroDone', ())  # the intro's own skip path (hold Space)
        elif ph == 6:
            row = sample(enc)
            S['rows'].append(row)
            if not S['defeat']:
                hit = next((g for g in row['g'] if g['state'] == 'Defeated'), None)
                if hit:
                    S['defeat'] = dict(t=row['t'], i=hit['i'], id=hit['id'], body=hit['body'], home=hit['home'])
                    unreal.GameplayStatics.set_global_time_dilation(w, 1)
                    S['scope']['S']['done'] = True  # pie_fight stops driving: watch the aftermath at 1x
                    unreal.unregister_slate_post_tick_callback(S['scope']['S']['h'])
            elif row['t'] > S['defeat']['t'] + 3.0:
                return finish('done')
            if S['defeat'] and time.time() - S['shot'] > 0.25:
                S['shot'] = time.time()
                n = int((row['t'] - S['defeat']['t']) * 100)
                unreal.SystemLibrary.execute_console_command(w, 'Shot showui filename=%sdefeat_%03d.png -nosuffix' % (SHOTS, n), pc)
            if S['scope']['S']['done'] and not S['defeat']:
                return finish('fight_ended_' + str(S['scope']['S']['log'][-1:]))
    except Exception as exc:  # noqa: BLE001
        S['rows'].append(dict(kind='error', error=repr(exc)))
        finish('error')


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('defeat_respace scheduled')
