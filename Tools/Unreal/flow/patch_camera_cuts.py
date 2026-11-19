"""Every hard cut the story lane owns is flagged as a camera cut (main 2026-11-10): UE motion-blurs and TAA-ghosts across
a view-target change unless that frame is a cut, so the chase cutaway's first frame was a smear. One node per cut:
PlayerCameraManager.SetGameCameraCutThisFrame, on the same frame as the SetViewTarget or camera teleport.
  TryClothingInspection  into every chase/clue/vase cutaway; its 0.2 s blend (from his head to the cutaway camera,
                         through his body) becomes a cut (BlendTime 0).
  CancelClothingInspection, ExitTopDownCut, PayoffShot, PayoffShotCut   the cuts back/out.
  EnterTopDown           its blend is 0 in the wardrobe transition (a cut there; harmless on the 1.5 s blend).
  FrameClothingBoss      the vase -> boss camera teleport.
  TickClothingFlight     the toss's under-bed -> wide teleport, flagged once (bClothingWideCut, reset when a cutaway
                         starts), not every tick (that would throw away TAA history all shot long).
Hayba only; idempotent.  python Tools/Unreal/flow/patch_camera_cuts.py"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
GS, K = '/Script/Engine.GameplayStatics:', '/Script/Engine.KismetMathLibrary:'
CUT = '/Script/Engine.PlayerCameraManager:SetGameCameraCutThisFrame'
os.environ['HAYBA_AGENT_ID'] = 'story'


def next_of(es, node, pin='then'):
    hits = [x for x in es if x['from_node'] == node and x['from_pin'] == pin]
    return hits[0] if hits else None


def has_cut(ns):
    return any(n['title'] in ('SetGameCameraCutThisFrame', 'Set Game Camera Cut This Frame') for n in ns)


def flag_after(graph, titles, blend_zero=False):
    ns, es = inspect(P, graph)
    if has_cut(ns):
        return 'kept'
    node = next(n['node_id'] for n in ns if n['title'] in titles)
    after = next_of(es, node)
    b = Batch(P, graph)
    if blend_zero:
        b.pin(node, 'BlendTime', 0)
    b.fn('cam', GS + 'GetPlayerCameraManager', 0, 400, PlayerIndex=0)
    b.fn('cut', CUT, 0, 250)
    b.link('cam', 'ReturnValue', 'cut', 'self')
    if after:
        b.cut(node, 'then', after['to_node'], after['to_pin'])
        b.link('cut', 'then', after['to_node'], after['to_pin'])
    b.link(node, 'then', 'cut', 'execute')
    b.run()
    return 'flagged' + (' (blend 0)' if blend_zero else '')


def flag_wide_once():
    ns, es = inspect(P, 'TickClothingFlight')
    if has_cut(ns):
        return 'kept'
    move = next(n['node_id'] for n in ns if n['title'] == 'Set World Location And Rotation'
                and any(x['to_node'] == n['node_id'] and x['to_pin'] == 'self' for x in es
                        if any(m['node_id'] == x['from_node'] and m['title'] == 'Get TopDownCamera' for m in ns)))
    early = next(n['node_id'] for n in ns if n['title'] in ('float < float', 'Less_DoubleDouble', 'Less (double)')
                 and any(p['name'] == 'B' and (p.get('default_value') or '').startswith('1.8') for p in n['pins']))
    after = next_of(es, move)
    b = Batch(P, 'TickClothingFlight')
    b.get('done', 'bClothingWideCut', 5300, 1600)
    b.fn('late', K + 'Not_PreBool', 5300, 1450)
    b.link(early, 'ReturnValue', 'late', 'A')
    b.fn('notyet', K + 'Not_PreBool', 5500, 1600)
    b.link('done', 'bClothingWideCut', 'notyet', 'A')
    b.fn('first', K + 'BooleanAND', 5700, 1500)
    b.link('late', 'ReturnValue', 'first', 'A')
    b.link('notyet', 'ReturnValue', 'first', 'B')
    b.node('once', 'branch', 5400, 0)
    b.link('first', 'ReturnValue', 'once', 'Condition')
    b.fn('cam', GS + 'GetPlayerCameraManager', 5600, 400, PlayerIndex=0)
    b.fn('cut', CUT, 5700, -150)
    b.link('cam', 'ReturnValue', 'cut', 'self')
    b.set('mark', 'bClothingWideCut', 6000, -150)
    b.pin('mark', 'bClothingWideCut', 'true')
    if after:
        b.cut(move, 'then', after['to_node'], after['to_pin'])
    b.link(move, 'then', 'once', 'execute')
    b.link('once', 'then', 'cut', 'execute')
    b.chain('cut', 'mark')
    if after:
        b.link('mark', 'then', after['to_node'], after['to_pin'])
        b.link('once', 'else', after['to_node'], after['to_pin'])
    b.comment('The wide cut, flagged once', ['done', 'late', 'notyet', 'first', 'once', 'cam', 'cut', 'mark'])
    b.run()
    return 'flagged once'


def reset_wide_flag():
    ns, es = inspect(P, 'TryClothingInspection')
    if any(n['title'] == 'Set bClothingWideCut' for n in ns):
        return 'kept'
    hud = next(n['node_id'] for n in ns if n['title'] == 'SetStoryHUDHidden')
    after = next_of(es, hud)
    b = Batch(P, 'TryClothingInspection')
    b.set('reset', 'bClothingWideCut', 0, -350)
    b.pin('reset', 'bClothingWideCut', 'false')
    b.cut(hud, 'then', after['to_node'], after['to_pin'])
    b.link(hud, 'then', 'reset', 'execute')
    b.link('reset', 'then', after['to_node'], after['to_pin'])
    b.run()
    return 'reset when a cutaway starts'


assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + P], ttl_s=300, wait_s=240)
try:
    r = h.call('blueprint_add_variable', dict(path=P, variable_name='bClothingWideCut', variable_type='bool',
                                              category='Story|Cinematics', update_existing=True), owner='story')
    assert r.get('ok'), r
    view = ('SetViewTargetWithBlend',)
    move = ('Set World Location And Rotation',)
    report = dict(TryClothingInspection=flag_after('TryClothingInspection', view, blend_zero=True),
                  CancelClothingInspection=flag_after('CancelClothingInspection', view),
                  ExitTopDownCut=flag_after('ExitTopDownCut', view),
                  PayoffShot=flag_after('PayoffShot', view),
                  PayoffShotCut=flag_after('PayoffShotCut', view),
                  EnterTopDown=flag_after('EnterTopDown', view),
                  FrameClothingBoss=flag_after('FrameClothingBoss', move),
                  TickClothingFlight=flag_wide_once(), WideReset=reset_wide_flag())
    Path('P:/FoA/Saved/StoryShots/camera_cuts.json').write_text(json.dumps(report, indent=1))
    print('camera cuts', report)
finally:
    h.release('story', token)
