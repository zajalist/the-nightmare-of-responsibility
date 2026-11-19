"""The dropped hanger gets noticed (QA S2 UX note, main 2026-11-10): a dark wire on a dark floor is easy to miss, so once
he is back in his eyes after the T7 top-down he says (story_text.HANGER_FELL) "The hanger's on the floor now. Of course
it is." Only when the fall knocked it down and it is still lying there, once per drop.
  SayHangerFell: DroppedHanger valid, not said yet, its State Available -> mark said -> BPC_Interactor.Narrate(line).
  ExitTopDownCut: timer SayHangerFell 0.6 s (after the fade-up), at its end.
  DropCoatRailHanger: a fresh drop clears the "said" mark.
Hayba only; idempotent.  python Tools/Unreal/flow/patch_hanger_line.py"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal/flow']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402
from story_text import HANGER_FELL  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
BASE = '/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C'
INTER = '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'
GS, KS, K = '/Script/Engine.GameplayStatics:', '/Script/Engine.KismetSystemLibrary:', '/Script/Engine.KismetMathLibrary:'
os.environ['HAYBA_AGENT_ID'] = 'story'


def call(name, **args):
    r = h.call(name, args, owner='story', timeout=60)
    assert r.get('ok'), r
    return r.get('data', {})


def next_of(es, node, pin='then'):
    hits = [x for x in es if x['from_node'] == node and x['from_pin'] == pin]
    return hits[0] if hits else None


def say():
    if not h.call('blueprint_inspect_graph', {'path': P, 'graph_name': 'SayHangerFell'}).get('ok'):
        call('blueprint_add_function', path=P, function_name='SayHangerFell')
    ns, es = inspect(P, 'SayHangerFell')
    if any(n['title'] == 'Narrate' for n in ns):
        return 'kept'
    e = find(ns, 'SayHangerFell')
    b = Batch(P, 'SayHangerFell')
    b.get('hanger', 'DroppedHanger', 0, 300)
    b.fn('valid', KS + 'IsValid', 200, 300)
    b.link('hanger', 'DroppedHanger', 'valid', 'Object')
    b.get('said', 'bHangerLineSaid', 200, 450)
    b.fn('notsaid', K + 'Not_PreBool', 400, 450)
    b.link('said', 'bHangerLineSaid', 'notsaid', 'A')
    b.fn('both', K + 'BooleanAND', 600, 350)
    b.link('valid', 'ReturnValue', 'both', 'A')
    b.link('notsaid', 'ReturnValue', 'both', 'B')
    b.node('fresh', 'branch', 300, 0)
    b.link('both', 'ReturnValue', 'fresh', 'Condition')
    b.node('item', 'cast', 600, 0, class_path=BASE)
    b.link('hanger', 'DroppedHanger', 'item', 'Object')
    b.get('state', 'State', 600, 300, BASE)
    b.link('item', 'AsBP Interactable', 'state', 'self')
    b.fn('lying', K + 'EqualEqual_NameName', 850, 300, B='Available')
    b.link('state', 'State', 'lying', 'A')
    b.node('still', 'branch', 900, 0)
    b.link('lying', 'ReturnValue', 'still', 'Condition')
    b.set('mark', 'bHangerLineSaid', 1150, 0)
    b.pin('mark', 'bHangerLineSaid', 'true')
    b.fn('pawn', GS + 'GetPlayerPawn', 1150, 300, PlayerIndex=0)
    b.fn('comp', '/Script/Engine.Actor:GetComponentByClass', 1400, 300, ComponentClass=INTER)
    b.link('pawn', 'ReturnValue', 'comp', 'self')
    b.node('voice', 'cast', 1400, 0, class_path=INTER)
    b.link('comp', 'ReturnValue', 'voice', 'Object')
    b.fn('line', '/Script/Engine.KismetTextLibrary:Conv_StringToText', 1650, 300, InString=HANGER_FELL)
    b.fn('narrate', INTER + ':Narrate', 1700, 0)
    b.link('voice', 'AsBPC Interactor', 'narrate', 'self')
    b.link('line', 'ReturnValue', 'narrate', 'Line')
    b.link(e, 'then', 'fresh', 'execute')
    b.link('fresh', 'then', 'item', 'execute')
    b.link('item', 'then', 'still', 'execute')
    b.link('still', 'then', 'mark', 'execute')
    b.chain('mark', 'voice', 'narrate')
    b.comment('He notices where it went', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()
    return 'built'


def after_cut():
    ns, es = inspect(P, 'ExitTopDownCut')
    if any(n['title'] == 'Set Timer by Function Name' and any(p['name'] == 'FunctionName' and p.get('default_value') == 'SayHangerFell'
                                                           for p in n['pins']) for n in ns):
        return 'kept'
    ends = [n['node_id'] for n in ns if n['title'] in ('HandoffFadeUp', 'StartCameraFade') and next_of(es, n['node_id']) is None]
    b = Batch(P, 'ExitTopDownCut')
    b.fn('later', KS + 'K2_SetTimer', 2400, 0, FunctionName='SayHangerFell', Time=0.6, bLooping='false')
    for end in ends:
        b.link(end, 'then', 'later', 'execute')
    b.run()
    return 'timer after %d fade-up ends' % len(ends)


def fresh_drop():
    ns, es = inspect(P, 'DropCoatRailHanger')
    if any(n['title'] == 'Set bHangerLineSaid' for n in ns):
        return 'kept'
    keep = find(ns, 'Set DroppedHanger')
    after = next_of(es, keep)
    b = Batch(P, 'DropCoatRailHanger')
    b.set('unsaid', 'bHangerLineSaid', 2100, -200)
    b.pin('unsaid', 'bHangerLineSaid', 'false')
    b.cut(keep, 'then', after['to_node'], after['to_pin'])
    b.link(keep, 'then', 'unsaid', 'execute')
    b.link('unsaid', 'then', after['to_node'], after['to_pin'])
    b.run()
    return 'a fresh drop clears the mark'


assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + P], ttl_s=240, wait_s=240)
try:
    call('blueprint_add_variable', path=P, variable_name='bHangerLineSaid', variable_type='bool', category='Story|T7 hanger',
         update_existing=True)
    report = dict(Say=say(), ExitTopDownCut=after_cut(), Drop=fresh_drop())
    Path('P:/FoA/Saved/StoryShots/hanger_line_patch.json').write_text(json.dumps(report, indent=1))
    print('hanger line', report)
finally:
    h.release('story', token)
