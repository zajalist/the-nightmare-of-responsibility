"""Offline assisted-policy balance estimate. Native play remains authoritative.

Uses the approved +1 assist, truth -1, costs, damage, status/stun and pool rules.
Assumes known opening CVWait for all panels, as the real retry grants knowledge.
No timed inputs, engine imports, asset writes or native state overrides.
"""
import random
import statistics
from cv_data import OPPONENTS
from cv_proof import MOVES, choose_action


def run(attack=2, wait=1, enraged_attack=3, enraged_wait=0, runs=100, seed_start=0):
    wins, losses, caps = [], 0, 0
    for seed in range(seed_start, seed_start+runs):
        rng = random.Random(seed)
        s = dict(composure=100, resolve=40, statuses=[], target=1, free_preview=True,
            sections=[dict(id=n, progress=0, state='Idle', intent='CVWait', actions=d['ActMoves'])
                      for n, d in OPPONENTS.items()])
        for turn in range(1, 151):
            target, name = choose_action(s)
            m, st = MOVES[name], set(s['statuses'])
            cost = 0 if m['bRevealsNext'] and s['free_preview'] else m['ResolveCost']
            if m['bRevealsNext']:s['free_preview'] = False
            s['composure'] = min(100, max(0, s['composure']+m['ComposureDelta']))
            s['resolve'] = min(40, max(0, s['resolve']-cost+m['ResolveDelta']))
            st.discard(m['StatusCleared'])
            if m['StatusApplied']:st.add(m['StatusApplied'])
            if target is not None:
                g = s['sections'][target]
                g['progress'] = min(4, max(0, g['progress']+m['ProgressDelta']))
            if all(g['progress']==4 for g in s['sections']):
                wins.append(turn)
                break
            for i, g in enumerate(s['sections']):
                if g['progress']==4:continue
                if not (i==target and m['bStuns']):
                    e = MOVES[g['intent']]
                    s['composure'] = max(0, s['composure']+e['ComposureDelta'])
                    s['resolve'] = min(40, max(0, s['resolve']+e['ResolveDelta']))
                    g['progress'] = max(0, g['progress']+e['ProgressDelta'])
                    if e['StatusApplied']:st.add(e['StatusApplied'])
                moves = list(OPPONENTS[g['id']]['MoveWeights'])
                weights = [enraged_attack, 1, enraged_wait] if g['progress']==3 else [attack, 1, wait]
                g['intent'] = rng.choices(moves, weights)[0]
            s['statuses'] = list(st)
            s['composure'] = max(0, s['composure']-2)
            if s['composure']==0:
                losses += 1
                break
        else:caps += 1
    ordered = sorted(wins)
    return dict(weights=[attack,1,wait], enraged=[enraged_attack,1,enraged_wait], runs=runs,
        wins=len(wins), losses=losses, caps=caps, median=statistics.median(wins) if wins else None,
        p90=ordered[min(len(ordered)-1, int(.9*len(ordered)))] if wins else None,
        min=min(wins) if wins else None, max=max(wins) if wins else None)


if __name__ == '__main__':
    import json
    for args in ((2,1,3,0), (1,3,2,3), (1,4,2,4), (1,3,1,3), (1,4,1,4), (2,6,3,6)):
        print(json.dumps(run(*args)))
