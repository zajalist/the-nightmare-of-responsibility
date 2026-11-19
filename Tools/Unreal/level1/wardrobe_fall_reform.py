"""level1 lane, T6 polish (coordinator 14:05): the wide shot after the fall had 1.7 s of dead air (a static fallen
wardrobe, him hidden), the get-up happened half out of frame, and the cut into the wide shot was a 0.35 s camera blend
from his head on the floor (a smear through the room). BP_BeatDirector only; run after wardrobe_fall_getup.py.
New timeline (seconds from the fall's start; the sequence still stops at 3.15):
  3.15  hard cut to the wide shot (EnterTopDown's wardrobe blend 0.35 -> 0; its camera-cut flag was already there)
  3.15-3.75  he crumbles where he lies (PlayerTransition 1 -> 0) with a sand burst every 0.35 s rising over the wardrobe
  3.75  WardrobeVanish: hidden, door gone; the get-up montage starts unseen; sand blooms at the re-form spot
  4.20  WardrobeReappear at the re-form spot, in the lower right third of the wide shot, facing the camera; he forms
        from sand lying in the bloom (PlayerTransition 0 -> 1 by 5.0; no bursts here), the hidden hold is 0.45 s
  4.90-6.60  the get-up (AM_FoA_WakeUp from 0.275 s at 1.5); the sand skin fades 5.7-6.8; control at 6.8
  StageWrongWall moves with the re-form (1.85 -> 1.05 s after the cut), as it did before (5.0 vs 5.05).
The wide shot turns 8 deg right and 4 deg down (pitch -19 -> -23, yaw 47 -> 55, same position) so the floor in front
of the fallen wardrobe is in frame. Idempotent (value pins are set, nodes added only once).
  $env:HAYBA_AGENT_ID='level1'; python Tools/Unreal/level1/wardrobe_fall_reform.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
WAKE = '/Game/FoA/Characters/Player/Montages/AM_FoA_WakeUp.AM_FoA_WakeUp'
SAND = '/Game/FoA/VFX/Sand/BPL_SandFX.BPL_SandFX_C:SpawnSandBloom'
CUT, VANISH, REAPPEAR, FORMED, FINISH = 3.15, 3.75, 4.2, 5.0, 6.8
GETUP, RATE = 4.9, 1.5
START = round(2.0 - (GETUP - VANISH) * RATE, 3)       # WakeUp holds its lying frame for 2.0 s of montage time
# lying from y 103 (feet) to 257 (head), 83 cm from the fallen wardrobe's face: at (85, 150) the sand bloom and bursts
# reached over the wardrobe's top edge as a jagged sheet
SPOT, SPOT_YAW = (55.0, 165.0), -90.0
BLOOM_AT, BLOOM_SIZE = '55,180,0', 1.2
assert CUT < VANISH < REAPPEAR < FORMED < FINISH and REAPPEAR - VANISH <= 0.5 and 0 < START < 2.0
# WardrobeSandTick literals, old -> new (3.15, the 0.35 s burst spacing and the 1.1 s sand fade keep their values)
SAND_TICK = {'4.15': VANISH, '1.0': VANISH - CUT, '5.05': REAPPEAR, '1.05': FORMED - REAPPEAR, '6.1': FINISH - 1.1, '7.2': FINISH}


def nodes(fn):
    ns, es = inspect(P, fn)
    return ns, es, {n['node_id']: n['title'].split('\n')[0] for n in ns}


def pinval(n, name):
    return next((p.get('default_value') for p in n['pins'] if p['name'] == name), None)


def same(a, b):
    try:
        return abs(float(a) - float(b)) < 1e-4
    except (TypeError, ValueError):
        return str(a).replace(' ', '') == str(b).replace(' ', '')


def setpins(fn, picks):
    """picks: [(node_id, pin, value)]: only the ones that differ."""
    ns, _, _ = nodes(fn)
    byid = {n['node_id']: n for n in ns}
    todo = [(i, p, v) for i, p, v in picks if not same(pinval(byid[i], p), v)]
    if not todo:
        return 'kept'
    b = Batch(P, fn)
    for i, p, v in todo:
        b.pin(i, p, v)
    b.run()
    return 'set %d' % len(todo)


def timers():
    ns, _, t = nodes('PlayWardrobeFall')
    want = {'WardrobeVanish': VANISH, 'WardrobeReappear': REAPPEAR, 'FinishWardrobeTransition': FINISH}
    picks = [(n['node_id'], 'Time', want[pinval(n, 'FunctionName')]) for n in ns if pinval(n, 'FunctionName') in want and 'Set Timer' in t[n['node_id']]]
    assert len(picks) == 3, picks
    ns2, _, t2 = nodes('WardrobeFallDone')
    stage = [(n['node_id'], 'Time', round(REAPPEAR - CUT, 3)) for n in ns2 if pinval(n, 'FunctionName') == 'StageWrongWall']
    assert len(stage) == 1
    return setpins('PlayWardrobeFall', picks), setpins('WardrobeFallDone', stage)


def sand_tick():
    ns, _, t = nodes('WardrobeSandTick')
    lits = [n for n in ns if 'Literal' in t[n['node_id']]]
    vals = sorted(pinval(n, 'Value') for n in lits)
    if '%g' % FINISH in [('%g' % float(v)) for v in vals]:
        return 'kept'
    picks = [(n['node_id'], 'Value', round(SAND_TICK[pinval(n, 'Value')], 3)) for n in lits if pinval(n, 'Value') in SAND_TICK]
    assert len(picks) == 9, (vals, picks)  # 4.15 x2, 1.0, 5.05 x3, 1.05, 6.1, 7.2
    return setpins('WardrobeSandTick', picks)


def cut():
    ns, _, t = nodes('EnterTopDown')
    sel = [n['node_id'] for n in ns if t[n['node_id']] == 'SelectFloat' and (same(pinval(n, 'A'), 0.35) or same(pinval(n, 'A'), 0.0))]
    assert len(sel) == 1, sel
    return setpins('EnterTopDown', [(sel[0], 'A', 0.0)])


def frame():
    ns, _, t = nodes('SetWardrobeShot')
    rot = [n['node_id'] for n in ns if t[n['node_id']] == 'MakeRotator']
    assert len(rot) == 1
    return setpins('SetWardrobeShot', [(rot[0], 'Pitch', -23.0), (rot[0], 'Yaw', 55.0)])


def reappear():
    ns, es, t = nodes('WardrobeReappear')
    tp = next(i for i, x in t.items() if x == 'Teleport')
    mk = next(x['from_node'] for x in es if x['to_node'] == tp and x['to_pin'] == 'DestLocation')
    links = {x['to_pin']: x for x in es if x['to_node'] == mk}
    b = Batch(P, 'WardrobeReappear')
    for axis in ('X', 'Y'):
        if axis in links:  # the old spot was computed from the fallen wardrobe's bounds: out of frame
            x = links[axis]
            b.cut(x['from_node'], x['from_pin'], mk, axis)
    b.pin(mk, 'X', SPOT[0])
    b.pin(mk, 'Y', SPOT[1])
    b.pin(tp, 'DestRotation', '0,%g,0' % SPOT_YAW)
    if 'X' in links:  # drop the pure nodes that only fed X and Y (Z keeps the capsule half height + 2)
        alive = [x for x in es if not (x['to_node'] == mk and x['to_pin'] in ('X', 'Y'))]
        pure = {n['node_id'] for n in ns if not any(p['name'] in ('execute', 'then') for p in n['pins'])
                and t[n['node_id']] not in ('Comment', 'WardrobeReappear') and n['node_id'] != mk}
        def unused(edges):
            dead = set()
            while True:
                more = {i for i in pure - dead if not any(x['from_node'] == i and x['to_node'] not in dead for x in edges)}
                if not more:
                    return dead
                dead |= more
        dead = unused(alive) - unused(es)  # leave nodes that were unused before (an old CharacterMovement getter)
        assert len(dead) == 9, sorted(t[i] for i in dead)  # bounds, 2 BreakVector, wardrobe, radius, 24, three maths
        b.ops.append(dict(op='remove', node_ids=sorted(dead)))
    b.run()
    return 'spot %s yaw %g' % (SPOT, SPOT_YAW)


def vanish():
    ns, es, t = nodes('WardrobeVanish')
    if 'Montage_Play' in t.values() or 'Montage Play' in t.values():
        bloom = next(i for i, x in t.items() if x == 'SpawnSandBloom')
        return 'kept, bloom ' + setpins('WardrobeVanish', [(bloom, 'Location', BLOOM_AT), (bloom, 'Size', BLOOM_SIZE)])
    old = next(i for i, x in t.items() if x == 'PlayAnimMontage')
    mode = next(i for i, x in t.items() if x == 'SetAnimationMode')
    mesh = next(x['from_node'] for x in es if x['to_node'] == mode and x['to_pin'] == 'self')
    b = Batch(P, 'WardrobeVanish')
    b.ops.append(dict(op='remove', node_ids=[old]))
    b.fn('anim', '/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 3900, 300)
    b.link(mesh, 'Mesh', 'anim', 'self')
    b.fn('play', '/Script/Engine.AnimInstance:Montage_Play', 3900, 0, MontageToPlay=WAKE, InPlayRate=RATE,
         InTimeToStartMontageAt=START, bStopAllMontages='true')
    b.link('anim', 'ReturnValue', 'play', 'self')
    b.fn('bloom', SAND, 4300, 0, Location=BLOOM_AT, Size=BLOOM_SIZE, Seconds=REAPPEAR - VANISH + 0.25, Crumble='true')
    b.link(mode, 'then', 'play', 'execute')
    b.chain('play', 'bloom')
    b.comment('Get up from the held lying frame; sand gathers where he re-forms', ['anim', 'play', 'bloom'])
    b.run()
    return 'montage from %.3f s, bloom' % START


def no_reform_burst():
    """The burst's grains fly out toward the camera and motion-blur into a jagged sheet across the wardrobe's top, and
    an outward burst is the opposite of sand gathering: the re-form keeps only the bloom and the sand-skin fade-in.
    Bursts stay for the crumble (3.15 to 3.75 s, behind the wardrobe) and the vanish."""
    out = []
    ns, es, t = nodes('WardrobeReappear')
    burst = [i for i, x in t.items() if x == 'WardrobeBodyBurst']
    if burst:
        b = Batch(P, 'WardrobeReappear')
        b.ops.append(dict(op='remove', node_ids=burst))
        b.run()
        out.append('reappear burst removed')
    ns, es, t = nodes('WardrobeSandTick')
    orb = next(i for i, x in t.items() if x == 'OR Boolean')
    ge = next(x['from_node'] for x in es if x['to_node'] == orb and x['to_pin'] == 'B')
    lit = next(x['from_node'] for x in es if x['to_node'] == ge and x['to_pin'] == 'B')
    out.append('periodic re-form bursts ' + setpins('WardrobeSandTick', [(lit, 'Value', 99.0)]))
    return ', '.join(out)


if __name__ == '__main__':
    print('REFORM', dict(timers=timers(), sand_tick=sand_tick(), cut=cut(), frame=frame(), reappear=reappear(), vanish=vanish(), bursts=no_reform_burst()))
