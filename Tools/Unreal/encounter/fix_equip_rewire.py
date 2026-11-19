"""Story lane, after fix_equip_flight.py (garment + encounter steps compiled): the two existing exec chains, by Hayba
batches (compiled and saved).
  BP_Garment EventGraph   Equip -> FlyToWear (was: StopBattleMotion, which teleported the actor back to MotionHome,
                          then AttachToComponent on GetComponentByClass(SkeletalMesh) of the pawn and a 0.35 s
                          MoveComponentTo whose exec 'then' hid the Body at once, without its children)
  BP_Encounter ApplyPlayerMove, the defeat chain after Set Remaining:
                          ... OnGarmentEquipped, CueEquip, Garment.Equip -> Respace (was: OnSandBurst, CueSandBurst,
                          SpawnSandBurst at the garment actor, Cast + BP_FoAPlayer.Equip on the defeat frame: those now
                          run on the arrival frame in GarmentWorn; world's defeat collapse stays on OnGarmentEquipped)
The removed nodes' pure feeders that feed nothing else go too (lean graphs). Idempotent: a chain already rewired is kept.
  python Tools/Unreal/encounter/fix_equip_rewire.py"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402

GB = '/Game/FoA/Gameplay/Encounter/BP_Garment'
EB = '/Game/FoA/Gameplay/Encounter/BP_Encounter'
os.environ['HAYBA_AGENT_ID'] = 'story'
EXEC_OUT = ('then', 'Completed', 'CastFailed')


def first(t):
    return t.split('\n')[0].replace(' ', '')


def walk(es, start, stop=()):
    """exec successors of start, in order (a simple chain)"""
    out, cur = [], start
    while True:
        nxt = [e for e in es if e['from_node'] == cur and e['from_pin'] in EXEC_OUT and e['to_node'] not in out]
        if not nxt:
            return out
        cur = nxt[0]['to_node']
        if cur in stop:
            return out
        out.append(cur)


def feeders(ns, es, gone):
    """pure nodes whose every outgoing link goes into `gone` (repeated until stable)"""
    gone = set(gone)
    has_exec = {e['to_node'] for e in es if e['to_pin'] in ('execute', 'exec', 'Move')} | \
               {e['from_node'] for e in es if e['from_pin'] in EXEC_OUT}
    while True:
        more = set()
        for n in ns:
            nid = n['node_id']
            if nid in gone or nid in has_exec or first(n['title']).lower() == 'comment':
                continue
            outs = [e['to_node'] for e in es if e['from_node'] == nid]
            if outs and all(o in gone for o in outs):
                more.add(nid)
        if not more:
            return gone
        gone |= more


def garment():
    ns, es = inspect(GB, 'EventGraph')
    title = {n['node_id']: first(n['title']) for n in ns}
    ev = [n['node_id'] for n in ns if title[n['node_id']] in ('Equip', 'EquipCustomEvent')]
    assert len(ev) == 1, ev
    chain = walk(es, ev[0])
    if chain and title[chain[0]] == 'FlyToWear':
        return 'kept'
    assert [title[c] for c in chain][:1] == ['StopBattleMotion'], [title[c] for c in chain]
    gone = feeders(ns, es, chain)
    b = Batch(GB, 'EventGraph')
    b.ops.append(dict(op='remove', node_ids=sorted(gone)))
    b.fn('fly', GB + '.BP_Garment_C:FlyToWear', 400, 0)
    b.link(ev[0], 'then', 'fly', 'execute')
    b.comment('Worn: fly to his slot', ['fly'])
    b.run()
    return 'removed %d nodes: %s' % (len(gone), sorted({title[g] for g in gone}))


def encounter():
    ns, es = inspect(EB, 'ApplyPlayerMove')
    title = {n['node_id']: first(n['title']) for n in ns}
    start = [n for n, t in title.items() if t == 'SetRemaining']
    assert len(start) == 1, start
    chain = walk(es, start[0])
    names = [title[c] for c in chain]
    i = names.index('Equip')  # the garment's Equip (the player's Equip comes later in the old chain)
    rest = chain[i + 1:]
    if rest and title[rest[0]] == 'Respace':
        return 'kept'
    assert names[:i + 1] == ['SetNarration', 'CallOnGarmentEquipped', 'CueEquip', 'Equip'], names
    assert [title[c] for c in rest] == ['CallOnSandBurst', 'CueSandBurst', 'SpawnSandBurst', 'CastToBP_FoAPlayer', 'Equip'], \
        [title[c] for c in rest]
    gone = feeders(ns, es, rest)
    b = Batch(EB, 'ApplyPlayerMove')
    b.ops.append(dict(op='remove', node_ids=sorted(gone)))
    b.fn('respace', EB + '.BP_Encounter_C:Respace', 0, 0)
    b.link(chain[i], 'then', 'respace', 'execute')
    b.comment('Close the line', ['respace'])
    b.run()
    return 'removed %d nodes: %s' % (len(gone), sorted({title[g] for g in gone}))


if __name__ == '__main__':
    assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    token = h.lease_acquire('story', ['asset:' + GB, 'asset:' + EB], ttl_s=240, wait_s=240)
    try:
        print('rewire', dict(garment=garment(), encounter=encounter()))
    finally:
        h.release('story', token)
