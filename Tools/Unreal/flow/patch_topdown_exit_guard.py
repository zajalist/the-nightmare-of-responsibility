"""ExitTopDown's deferred cut must never fire after another system took the camera. ExitTopDown now fades for 0.2 s and
cuts on a timer (patch_topdown_exit_cut.py), so a caller that moves on at once (StartShirtFight starts the battle camera
and shows the T8 Nightmare; ResetHouse hands over to the morning) would get the view pulled back to the pawn, and the
Nightmare hidden, 0.2 s later. Fix: the cut is pending-guarded and those callers finish it on the spot.
  ExitTopDown:     sets bTopDownCutPending before the fade and the timer.
  ExitTopDownCut:  runs only while bTopDownCutPending (clears it first), so the late timer is a no-op once finished.
  StartShirtFight: ExitTopDown, ExitTopDownCut (now), StartShirtEncounter, ShowNightmare.
  ResetHouse:      ExitTopDown, ExitTopDownCut (now), then the timers and the rest of the reset.
Hayba only; idempotent; build_director.py matches.  python Tools/Unreal/flow/patch_topdown_exit_guard.py"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
C = P + '.BP_BeatDirector_C'
FLAG = 'bTopDownCutPending'
os.environ['HAYBA_AGENT_ID'] = 'story'


def call(name, **args):
    r = h.call(name, args, owner='story', timeout=60)
    assert r.get('ok'), r
    return r.get('data', {})


def exit_top_down():
    ns, es = inspect(P, 'ExitTopDown')
    if any(n['title'] == 'Set ' + FLAG for n in ns):
        return 'kept'
    setter = find(ns, 'Set bTopDown')
    after = next(x for x in es if x['from_node'] == setter and x['from_pin'] == 'then')
    b = Batch(P, 'ExitTopDown')
    b.cut(setter, 'then', after['to_node'], after['to_pin'])
    b.set('pending', FLAG, 600, -200)
    b.pin('pending', FLAG, 'true')
    b.link(setter, 'then', 'pending', 'execute')
    b.link('pending', 'then', after['to_node'], after['to_pin'])
    b.run()
    return 'flag set before the fade'


def exit_cut():
    ns, es = inspect(P, 'ExitTopDownCut')
    if any(n['title'] == 'Set ' + FLAG for n in ns):
        return 'kept'
    e = find(ns, 'ExitTopDownCut')
    first = next(x for x in es if x['from_node'] == e and x['from_pin'] == 'then')
    b = Batch(P, 'ExitTopDownCut')
    b.cut(e, 'then', first['to_node'], first['to_pin'])
    b.get('ispending', FLAG, 0, -300)
    b.node('only', 'branch', 100, -200)
    b.link('ispending', FLAG, 'only', 'Condition')
    b.set('done', FLAG, 200, -400)
    b.pin('done', FLAG, 'false')
    b.link(e, 'then', 'only', 'execute')
    b.link('only', 'then', 'done', 'execute')
    b.link('done', 'then', first['to_node'], first['to_pin'])
    b.comment('Once per exit', ['ispending', 'only', 'done'])
    b.run()
    return 'guarded'


def finish_now(graph):
    ns, es = inspect(P, graph)
    exits = [n['node_id'] for n in ns if n['title'] == 'ExitTopDown']
    assert len(exits) == 1, (graph, exits)
    ex = exits[0]
    after = next(x for x in es if x['from_node'] == ex and x['from_pin'] == 'then')
    if any(n['node_id'] == after['to_node'] and n['title'] == 'ExitTopDownCut' for n in ns):
        return 'kept'
    b = Batch(P, graph)
    b.cut(ex, 'then', after['to_node'], after['to_pin'])
    b.fn('now', C + ':ExitTopDownCut', 300, 200)
    b.link(ex, 'then', 'now', 'execute')
    b.link('now', 'then', after['to_node'], after['to_pin'])
    b.run()
    return 'cut finished on the spot'


assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + P], ttl_s=180, wait_s=240)
try:
    call('blueprint_add_variable', path=P, variable_name=FLAG, variable_type='bool', category='Story|TopDown', update_existing=True)
    report = dict(ExitTopDown=exit_top_down(), ExitTopDownCut=exit_cut(),
                  StartShirtFight=finish_now('StartShirtFight'), ResetHouse=finish_now('ResetHouse'))
    Path('P:/FoA/Saved/StoryShots/topdown_exit_guard.json').write_text(json.dumps(report, indent=1))
    print('top-down exit guarded', report)
finally:
    h.release('story', token)
