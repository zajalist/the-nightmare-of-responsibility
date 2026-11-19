"""The inventory stops being a player-facing system (the user, 2026-11-10: "i dont even think an inventory system is
needed"; main's brief). Hayba graph edits, idempotent.
  BPC_Inventory  Add: no capacity; an item already held is a no-op that still returns true (no duplicates).
                 IsFull: always false (its last callers are dead gates). Combine stays as dead code for Level 2's
                 C.V beat (main, 2026-11-10; restore_inventory_combine.py put it back after a first pass deleted it).
  BP_Interactable (anim)  FindCarriedRow(Verb): in table order, the rows for this state and verb whose Item he carries
                 (and whose Requires he knows); the first that changes the state wins over the first that doesn't.
                 Resolve: that row, else the bare-hand row. The held/Selected item no longer matters.
  BPC_Interactor (anim)  Interact: the "hands are full" Take gate is gone.
  BP_BeatDirector  ToolsDone(Event) first in ReportEvent: KeySnapped -> the key (now KeyStub) leaves; LatchFreed -> the
                 screwdriver leaves (the plate was its only job); ClothingUnhooked -> the hanger leaves.
                 ReachClothingVase and ClothingBossFormed lose their "My hands are full." branches.
  python Tools/Unreal/flow/patch_inventory_set.py"""
import json
import os
import sys
from pathlib import Path

INV = '/Game/FoA/Gameplay/BPC_Inventory'
ITB = '/Game/FoA/Gameplay/BP_Interactable'
ITR = '/Game/FoA/Gameplay/BPC_Interactor'
DIR = '/Game/FoA/Gameplay/BP_BeatDirector'

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

K = '/Script/Engine.KismetMathLibrary:'
ARR = '/Script/Engine.KismetArrayLibrary:'
GS = '/Script/Engine.GameplayStatics:'
INV_C, ITB_C, ITR_C, DIR_C = INV + '.BPC_Inventory_C', ITB + '.BP_Interactable_C', ITR + '.BPC_Interactor_C', DIR + '.BP_BeatDirector_C'
ROW = '/Game/FoA/Gameplay/S_Interaction.S_Interaction'
F_STATE, F_VERB, F_ITEM = 'State_1_380D1B9262595A2999341F170D15DBF4', 'Verb_2_0B4A16D1B3055F00A6DB17090814B332', 'Item_3_FC1E104EE60B5D9C9A79EE4EF2BC34FB'
F_REQ, F_NEXT = 'Requires_4_FE81269A2B125C5985FA6258255A2792', 'NextState_5_1B1047BED8DF52B89DF5702C7FE3C4D1'
os.environ['HAYBA_AGENT_ID'] = 'story'


def call(name, **args):
    r = h.call(name, args, owner='story', timeout=60)
    assert r.get('ok'), r
    return r.get('data', {})


def titles(ns, t):
    return [n['node_id'] for n in ns if n['title'] == t]


def remove(b, ids):
    ids = sorted(set(ids))
    if ids:
        b.ops.append(dict(op='remove', node_ids=ids))


def inventory_add():
    """One return node (Hayba's function_result add hands back the existing one): bAdded = Item != None, true for a new
    item and for one already carried, false only for None. Only a new item is appended."""
    ns, es = inspect(INV, 'Add')
    if titles(ns, 'Has'):
        return 'kept'
    e = next(n['node_id'] for n in ns if n['title'] == 'Add' and not any(p['name'] == 'execute' for p in n['pins']))  # the entry
    br = find(ns, 'Branch')
    ne = find(ns, 'Not Equal (Name)')
    ret = find(ns, 'Return Node')
    told = find(ns, 'Call On Inventory Changed')
    b = Batch(INV, 'Add')
    remove(b, titles(ns, 'Length') + titles(ns, 'Get Capacity') + titles(ns, 'integer < integer') + titles(ns, 'AND Boolean') +
           [x['from_node'] for x in es if x['to_pin'] == 'TargetArray' and x['to_node'] in titles(ns, 'Length')])
    b.fn('has', INV_C + ':Has', 300, 400)
    b.link(e, 'Item', 'has', 'Item')
    b.fn('new', K + 'Not_PreBool', 550, 400)
    b.link('has', 'bHas', 'new', 'A')
    b.fn('both', K + 'BooleanAND', 800, 300)
    b.link(ne, 'ReturnValue', 'both', 'A')
    b.link('new', 'ReturnValue', 'both', 'B')
    b.link('both', 'ReturnValue', br, 'Condition')
    b.link(told, 'then', ret, 'execute')
    b.link(ne, 'ReturnValue', ret, 'bAdded')
    b.comment('Carried already: nothing to add, still true', ['has', 'new', 'both'])
    b.run()
    return 'no capacity, no duplicates'


def inventory_isfull():
    ns, es = inspect(INV, 'IsFull')
    if not titles(ns, 'Get Capacity'):
        return 'kept'
    ret = find(ns, 'Return Node')
    b = Batch(INV, 'IsFull')
    remove(b, titles(ns, 'Length') + titles(ns, 'Get Items') + titles(ns, 'integer >= integer') + titles(ns, 'Get Capacity'))
    b.pin(ret, 'bFull', 'false')
    b.run()
    return 'always false'


def carried_row():
    """FindCarriedRow(Verb) -> bFound, Row: one pass over Rows in table order. A row he can do now (state or wildcard,
    verb, Requires known) whose Item he carries is kept; the first one that changes the state wins over the first one
    that doesn't. Locals and one return node (Hayba's function_result add hands back the existing one)."""
    if not h.call('blueprint_inspect_graph', {'path': ITB, 'graph_name': 'FindCarriedRow'}).get('ok'):
        call('blueprint_add_function', path=ITB, function_name='FindCarriedRow', inputs=[dict(name='Verb', type='name')],
             outputs=[dict(name='bFound', type='bool'), dict(name='Row', type='struct:' + ROW)],
             locals=[dict(name='OutRow', type='struct:' + ROW), dict(name='bMoving', type='bool'), dict(name='bAny', type='bool')])
    ns, es = inspect(ITB, 'FindCarriedRow')
    if any('ForEach' in n['title'] for n in ns):
        return 'kept'
    e = find(ns, 'FindCarriedRow')
    ret = find(ns, 'Return Node')
    b = Batch(ITB, 'FindCarriedRow')
    b.get('rows', 'Rows', 0, 300)
    b.node('loop', 'macro', 250, 0, macro_name='ForEachLoop')
    b.link('rows', 'Rows', 'loop', 'Array')
    b.node('row', 'break_struct', 550, 300, struct_path=ROW)
    b.link('loop', 'Array Element', 'row', 'S_Interaction')
    b.get('now', 'State', 550, 700)
    b.fn('s1', K + 'EqualEqual_NameName', 850, 300)
    b.link('row', F_STATE, 's1', 'A'); b.link('now', 'State', 's1', 'B')
    b.fn('s2', K + 'EqualEqual_NameName', 850, 450, B='None')
    b.link('row', F_STATE, 's2', 'A')
    b.fn('sok', K + 'BooleanOR', 1100, 350)
    b.link('s1', 'ReturnValue', 'sok', 'A'); b.link('s2', 'ReturnValue', 'sok', 'B')
    b.fn('vok', K + 'EqualEqual_NameName', 850, 600)
    b.link('row', F_VERB, 'vok', 'A'); b.link(e, 'Verb', 'vok', 'B')
    b.fn('know', ITB_C + ':Knows', 850, 750)
    b.link('row', F_REQ, 'know', 'Flag')
    b.fn('real', K + 'NotEqual_NameName', 850, 900, B='None')
    b.link('row', F_ITEM, 'real', 'A')
    b.fn('who', ITB_C + ':GetInteractor', 600, 1100)
    b.get('bag', 'Inventory', 850, 1100, ITR_C)
    b.link('who', 'Interactor', 'bag', 'self')
    b.fn('has', INV_C + ':Has', 1100, 1050)
    b.link('bag', 'Inventory', 'has', 'self'); b.link('row', F_ITEM, 'has', 'Item')
    prev = 'sok'
    for i, (nxt, pin) in enumerate((('vok', 'ReturnValue'), ('know', 'bKnows'), ('real', 'ReturnValue'), ('has', 'bHas'))):
        b.fn('a%d' % i, K + 'BooleanAND', 1400 + 150 * i, 300 + 150 * i)
        b.link(prev, 'ReturnValue', 'a%d' % i, 'A')
        b.link(nxt, pin, 'a%d' % i, 'B')
        prev = 'a%d' % i
    b.fn('n1', K + 'NotEqual_NameName', 850, 1300, B='None')
    b.link('row', F_NEXT, 'n1', 'A')
    b.fn('n2', K + 'NotEqual_NameName', 850, 1450)
    b.link('row', F_NEXT, 'n2', 'A'); b.link('now', 'State', 'n2', 'B')
    b.fn('moves', K + 'BooleanAND', 1100, 1350)
    b.link('n1', 'ReturnValue', 'moves', 'A'); b.link('n2', 'ReturnValue', 'moves', 'B')
    b.get('gotm', 'bMoving', 1100, 1550)
    b.fn('firstm', K + 'Not_PreBool', 1350, 1550)
    b.link('gotm', 'bMoving', 'firstm', 'A')
    b.fn('takem', K + 'BooleanAND', 1600, 1400)
    b.link('moves', 'ReturnValue', 'takem', 'A'); b.link('firstm', 'ReturnValue', 'takem', 'B')
    b.get('gota', 'bAny', 1350, 1750)
    b.fn('firsta', K + 'Not_PreBool', 1600, 1750)
    b.link('gota', 'bAny', 'firsta', 'A')
    b.node('match', 'branch', 2200, 0)
    b.link(prev, 'ReturnValue', 'match', 'Condition')
    b.node('moving', 'branch', 2450, 0)
    b.link('takem', 'ReturnValue', 'moving', 'Condition')
    b.set('rowm', 'OutRow', 2700, -200)
    b.link('loop', 'Array Element', 'rowm', 'OutRow')
    b.set('setm', 'bMoving', 2950, -200); b.pin('setm', 'bMoving', 'true')
    b.set('seta', 'bAny', 3200, -200); b.pin('seta', 'bAny', 'true')
    b.node('first', 'branch', 2700, 150)
    b.link('firsta', 'ReturnValue', 'first', 'Condition')
    b.set('rowa', 'OutRow', 2950, 150)
    b.link('loop', 'Array Element', 'rowa', 'OutRow')
    b.set('seta2', 'bAny', 3200, 150); b.pin('seta2', 'bAny', 'true')
    b.get('outany', 'bAny', 2400, 500)
    b.get('outrow', 'OutRow', 2400, 650)
    b.link(e, 'then', 'loop', 'Exec')  # the macro's exec input
    b.link('loop', 'LoopBody', 'match', 'execute')
    b.link('match', 'then', 'moving', 'execute')
    b.link('moving', 'then', 'rowm', 'execute')
    b.chain('rowm', 'setm', 'seta')
    b.link('moving', 'else', 'first', 'execute')
    b.link('first', 'then', 'rowa', 'execute')
    b.chain('rowa', 'seta2')
    b.link('loop', 'Completed', ret, 'execute')
    b.link('outany', 'bAny', ret, 'bFound')
    b.link('outrow', 'OutRow', ret, 'Row')
    b.comment('The row he can do with what he carries', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()
    return 'built'


def resolve():
    ns, es = inspect(ITB, 'Resolve')
    if titles(ns, 'FindCarriedRow'):
        return 'kept'
    e = find(ns, 'Resolve')
    br = find(ns, 'Branch')
    fr = [x for x in es if x['to_node'] == br and x['to_pin'] == 'Condition'][0]['from_node']  # FindRow(Verb, Held)
    ret_held = [x for x in es if x['from_node'] == br and x['from_pin'] == 'then'][0]['to_node']
    b = Batch(ITB, 'Resolve')
    remove(b, [fr])
    b.fn('carried', ITB_C + ':FindCarriedRow', 200, -250)
    b.link(e, 'Verb', 'carried', 'Verb')
    b.cut(e, 'then', br, 'execute')
    b.link(e, 'then', 'carried', 'execute')
    b.link('carried', 'then', br, 'execute')
    b.link('carried', 'bFound', br, 'Condition')
    b.link('carried', 'bFound', ret_held, 'bFound')
    b.link('carried', 'Row', ret_held, 'Row')
    b.comment('What he carries decides', ['carried'])
    b.run()
    return 'a carried row first (one that moves the state wins), else bare hands'


def interactor_gate():
    ns, es = inspect(ITR, 'Interact')
    if not titles(ns, 'IsFull'):
        return 'kept'
    outer = [x for x in es if x['to_node'] in titles(ns, 'Branch') and x['from_pin'] == 'then' and
             x['from_node'] in titles(ns, 'Branch')][0]
    gate, top = outer['to_node'], outer['from_node']
    act = [x['to_node'] for x in es if x['from_node'] == gate and x['from_pin'] == 'else'][0]
    b = Batch(ITR, 'Interact')
    narr = titles(ns, 'Narrate')
    remove(b, [gate] + narr + titles(ns, 'IsFull') + titles(ns, 'AND Boolean') + titles(ns, 'Equal (Name)') + titles(ns, 'Get FullLine') +
           [x['from_node'] for x in es if x['to_node'] in titles(ns, 'Equal (Name)') and x['to_pin'] == 'A'] +
           [x['from_node'] for x in es if x['to_node'] in titles(ns, 'IsFull') and x['to_pin'] == 'self'])
    b.link(top, 'then', act, 'execute')
    b.run()
    return 'the hands-full gate is gone'


def vase_gate():
    ns, es = inspect(DIR, 'ReachClothingVase')
    if not titles(ns, 'IsFull'):
        return 'kept'
    stage = [x['to_node'] for x in es if x['from_node'] == find(ns, 'ReachClothingVase') and x['from_pin'] == 'then'][0]
    cancel = find(ns, 'CancelClothingInspection')
    slot = [x['to_node'] for x in es if x['from_node'] == stage and x['from_pin'] == 'then'][0]
    retry = [x['to_node'] for x in es if x['from_node'] == slot and x['from_pin'] == 'else'][0]
    b = Batch(DIR, 'ReachClothingVase')
    remove(b, [slot, retry] + titles(ns, 'GetInteractor') + titles(ns, 'Get Inventory') + titles(ns, 'IsFull') + titles(ns, 'NOT Boolean') +
           titles(ns, 'Has') + titles(ns, 'OR Boolean') + titles(ns, 'To Text (String)') + titles(ns, 'Narrate'))
    b.link(stage, 'then', cancel, 'execute')
    b.run()
    return 'no full-hands refusal at the vase'


def boss_gate():
    ns, es = inspect(DIR, 'ClothingBossFormed')
    if not titles(ns, 'AbortClothingChase'):
        return 'kept'
    add = find(ns, 'Add')
    added = [x['to_node'] for x in es if x['from_node'] == add and x['from_pin'] == 'then'][0]
    off = [x['to_node'] for x in es if x['from_node'] == added and x['from_pin'] == 'then'][0]
    b = Batch(DIR, 'ClothingBossFormed')
    second_cancel = [n for n in titles(ns, 'CancelClothingInspection')
                     if any(x['to_node'] == n and x['from_node'] in titles(ns, 'AbortClothingChase') for x in es)]
    remove(b, [added] + titles(ns, 'AbortClothingChase') + second_cancel + titles(ns, 'To Text (String)') + titles(ns, 'Narrate'))
    b.link(add, 'then', off, 'execute')
    b.run()
    return 'the shirt is always accepted'


def tools_done():
    if not h.call('blueprint_inspect_graph', {'path': DIR, 'graph_name': 'ToolsDone'}).get('ok'):
        call('blueprint_add_function', path=DIR, function_name='ToolsDone', inputs=[dict(name='Event', type='name')])
    ns, es = inspect(DIR, 'ToolsDone')
    if titles(ns, 'Remove'):
        hooked = 'kept'
    else:
        e = find(ns, 'ToolsDone')
        b = Batch(DIR, 'ToolsDone')
        b.fn('pawn', GS + 'GetPlayerCharacter', 0, 600, PlayerIndex=0)
        b.fn('comp', '/Script/Engine.Actor:GetComponentByClass', 250, 600, ComponentClass=INV_C)
        b.link('pawn', 'ReturnValue', 'comp', 'self')
        b.node('bag', 'cast', 250, 0, class_path=INV_C)
        b.link('comp', 'ReturnValue', 'bag', 'Object')
        b.link(e, 'then', 'bag', 'execute')
        checks = (('KeySnapped', ('KeyStub', 'Key')), ('LatchFreed', ('Screwdriver',)), ('ClothingUnhooked', ('Hanger',)))
        for k, (event, items) in enumerate(checks):
            x = 500 + 900 * k
            b.fn('is%d' % k, K + 'EqualEqual_NameName', x, 300, B=event)
            b.link(e, 'Event', 'is%d' % k, 'A')
            b.node('br%d' % k, 'branch', x, 0)
            b.link('is%d' % k, 'ReturnValue', 'br%d' % k, 'Condition')
            for j, item in enumerate(items):
                b.fn('rm%d%d' % (k, j), INV_C + ':Remove', x + 250 + 250 * j, -200, Item=item)
                b.link('bag', 'AsBPC Inventory', 'rm%d%d' % (k, j), 'self')
        b.link('bag', 'then', 'br0', 'execute')
        for k, (event, items) in enumerate(checks):
            chain = ['br%d' % k] + ['rm%d%d' % (k, j) for j in range(len(items))]
            b.link(chain[0], 'then', chain[1], 'execute')
            for a2, b2 in zip(chain[1:], chain[2:]):
                b.link(a2, 'then', b2, 'execute')
            if k + 1 < len(checks):
                b.link(chain[-1], 'then', 'br%d' % (k + 1), 'execute')  # removed, then the next check
                b.link(chain[0], 'else', 'br%d' % (k + 1), 'execute')   # not this event, the next check
        b.comment('Tools leave once their job is done', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
        b.run()
        hooked = 'built'
    ns, es = inspect(DIR, 'ReportEvent')
    if titles(ns, 'ToolsDone'):
        return hooked + ', hooked'
    e = find(ns, 'ReportEvent')
    first = [x for x in es if x['from_node'] == e and x['from_pin'] == 'then'][0]
    b = Batch(DIR, 'ReportEvent')
    b.fn('tools', DIR_C + ':ToolsDone', 150, -250)
    b.link(e, 'Event', 'tools', 'Event')
    b.cut(e, 'then', first['to_node'], first['to_pin'])
    b.link(e, 'then', 'tools', 'execute')
    b.link('tools', 'then', first['to_node'], first['to_pin'])
    b.run()
    return hooked + ', ReportEvent calls it first'


if __name__ == '__main__':
    assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    token = h.lease_acquire('story', ['asset:' + p for p in (INV, ITB, ITR, DIR)], ttl_s=600, wait_s=300)
    try:
        report = dict(Add=inventory_add(), IsFull=inventory_isfull(), FindCarriedRow=carried_row(), Resolve=resolve(),
                      Interact=interactor_gate(), Vase=vase_gate(), Boss=boss_gate(), ToolsDone=tools_done())
        Path('P:/FoA/Saved/StoryShots/inventory_set_patch.json').write_text(json.dumps(report, indent=1))
        print('inventory set', json.dumps(report))
    finally:
        h.release('story', token)
