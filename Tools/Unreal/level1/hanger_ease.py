"""level1 lane, T7 (the user: "the animation of taking clothing out of bed still needs some work"). Measured per 0.1 s
in PIE (plan L1HD, run_20261118_1415): the arm's IK weight jumped 0 -> 1 in one frame as he knelt (the arm swung to
the hook), the pull ran at a constant 29 cm/s with a dead start and a dead stop, and after the release flick the hand
stayed frozen in the air with the hanger for 1.6 s, visible in the wide shot, because UpdateClothingHanger stops
ticking at the end of the flight with the weight still 1. BP_BeatDirector only:
  UpdateClothingHanger  ToolHandWeight and HeldToolWeight = ease(min(t / 0.5, (2.6 - t) / 0.6)): the hand eases onto
                        the hook over the first 0.5 s of the kneel and back to the kneel animation, with the hanger,
                        from 2.0 to 2.6 s (after the 1.8 s release flick, before the flight ends at 2.65 s).
                        The pull (0.6 to 1.8 s) is eased in and out (FInterpEaseInOut, exponent 2) instead of linear.
  TickClothingFlight    the shirt's pull uses the same easing, so it stays on the hook all the way.
Idempotent: skips a graph that already has its FInterpEaseInOut.
  $env:HAYBA_AGENT_ID='level1'; python Tools/Unreal/level1/hanger_ease.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
K = '/Script/Engine.KismetMathLibrary:'
REACH, RELAX0, RELAX1 = 0.5, 2.0, 2.6
EASE = 'FInterpEaseInOut'


def graph(fn):
    ns, es = inspect(P, fn)
    return ns, es, {n['node_id']: n['title'].split('\n')[0] for n in ns}


def pin(n, name):
    return next((p.get('default_value') for p in n['pins'] if p['name'] == name), None)


def ease_node(b, ref, x, y):
    b.fn(ref, K + EASE, x, y, A=0.0, B=1.0, Exponent=2.0)


def update():
    ns, es, t = graph('UpdateClothingHanger')
    if any(EASE in x for x in t.values()):
        return 'kept'
    byid = {n['node_id']: n for n in ns}
    pull = next(i for i, x in t.items() if x == 'Clamp (Float)' and any(
        e['from_node'] == i and t[e['to_node']] == 'float * float' and pin(byid[e['to_node']], 'B') == '40.0' for e in es))
    elapsed = next(i for i, x in t.items() if x == 'float - float' and any(
        e['to_node'] == i and t[e['from_node']] == 'GetTimeSeconds' for e in es))
    hand_w = next(i for i, x in t.items() if x == 'Set ToolHandWeight')
    tool_w = next(i for i, x in t.items() if x == 'Set HeldToolWeight')
    users = [e for e in es if e['from_node'] == pull and pin(byid[e['to_node']], 'B') in ('40.0', '12')]
    assert len(users) == 2, users  # the hook's travel along the pull and its rise
    b = Batch(P, 'UpdateClothingHanger')
    ease_node(b, 'pullease', 2000, 1100)
    b.link(pull, 'ReturnValue', 'pullease', 'Alpha')
    for e in users:
        b.cut(pull, 'ReturnValue', e['to_node'], e['to_pin'])
        b.link('pullease', 'ReturnValue', e['to_node'], e['to_pin'])
    b.fn('inraw', K + 'Divide_DoubleDouble', 900, 2300, B=REACH)
    b.link(elapsed, 'ReturnValue', 'inraw', 'A')
    b.fn('outleft', K + 'Subtract_DoubleDouble', 900, 2500, A=RELAX1)
    b.link(elapsed, 'ReturnValue', 'outleft', 'B')
    b.fn('outraw', K + 'Divide_DoubleDouble', 1200, 2500, B=RELAX1 - RELAX0)
    b.link('outleft', 'ReturnValue', 'outraw', 'A')
    b.fn('both', K + 'FMin', 1500, 2400)
    b.link('inraw', 'ReturnValue', 'both', 'A')
    b.link('outraw', 'ReturnValue', 'both', 'B')
    b.fn('wclamp', K + 'FClamp', 1800, 2400, Min=0.0, Max=1.0)
    b.link('both', 'ReturnValue', 'wclamp', 'Value')
    ease_node(b, 'weight', 2100, 2400)
    b.link('wclamp', 'ReturnValue', 'weight', 'Alpha')
    b.link('weight', 'ReturnValue', hand_w, 'ToolHandWeight')
    b.link('weight', 'ReturnValue', tool_w, 'HeldToolWeight')
    b.comment('The hand eases onto the hook and off it after the release; the pull eases in and out',
              ['pullease', 'inraw', 'outleft', 'outraw', 'both', 'wclamp', 'weight'])
    b.run()
    return 'eased'


def tick():
    ns, es, t = graph('TickClothingFlight')
    if any(EASE in x for x in t.values()):
        return 'kept'
    lerp = [e for e in es if t[e['to_node']] == 'Lerp (Transform)' and e['to_pin'] == 'Alpha'
            and t[e['from_node']] == 'Clamp (Float)' and any(
                f['to_node'] == e['from_node'] and t[f['from_node']] == 'float / float' and any(
                    g['to_node'] == f['from_node'] and t[g['from_node']] == 'float - float' and pin(
                        next(n for n in ns if n['node_id'] == g['from_node']), 'B') == '0.6' for g in es) for f in es)]
    assert len(lerp) == 1, lerp  # the pull: clamp((t - 0.6) / 1.2) -> TLerp(From, clear point)
    e = lerp[0]
    b = Batch(P, 'TickClothingFlight')
    ease_node(b, 'pullease', 1500, 1100)
    b.cut(e['from_node'], e['from_pin'], e['to_node'], 'Alpha')
    b.link(e['from_node'], e['from_pin'], 'pullease', 'Alpha')
    b.link('pullease', 'ReturnValue', e['to_node'], 'Alpha')
    b.comment('The pull eases in and out (matches UpdateClothingHanger)', ['pullease'])
    b.run()
    return 'eased'


if __name__ == '__main__':
    print('HANGER_EASE', dict(update=update(), tick=tick()))
