"""Canonical native Hayba builder for BP_Encounter.MoveDetail, run after encounter rules.

Only creates the missing helper; never rebuilds existing encounter graphs.
"""
import json
from pathlib import Path
import sys
import re
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc

BP = '/Game/FoA/Gameplay/Encounter/BP_Encounter'
MC = '/Game/FoA/Gameplay/Encounter/PDA_Move.PDA_Move_C'
KML = '/Script/Engine.KismetMathLibrary:'
KTL = '/Script/Engine.KismetTextLibrary:'
OWNER = 'battle_move_detail'
TOKEN = None


def call(cmd, **params):
    result = hc.call(cmd, params, owner=OWNER, lease=TOKEN)
    assert result.get('ok'), result
    data = result.get('data', {})
    assert data.get('ok', True) and not data.get('failed'), data
    return data


def main():
    global TOKEN
    assert not call('editor_get_state')['pie_running']
    TOKEN = hc.lease_acquire(OWNER, ['asset:' + BP], ttl_s=90, wait_s=15)
    try:
        info = hc.call('blueprint_inspect_graph', dict(path=BP, graph_name='MoveDetail'), owner=OWNER, lease=TOKEN)
        if info.get('ok') and info.get('data', {}).get('node_count', 0) > 2:
            print('Existing MoveDetail preserved; validate_move_detail.py checks its behavior.')
            return
        if not info.get('ok'):
            call('blueprint_add_function', path=BP, function_name='MoveDetail',
                 inputs=[dict(name='Move', type='object:' + MC)],
                 outputs=[dict(name='Detail', type='text')], pure=True)
        g = call('blueprint_inspect_graph', path=BP, graph_name='MoveDetail')
        entry = next(n['node_id'] for n in g['nodes'] if n['title'] == 'MoveDetail')
        ret = next(n['node_id'] for n in g['nodes'] if n['title'] == 'Return Node')
        ops = []
        def node(ref, kind='call_function', x=0, y=0, **kw):
            ops.append(dict(op='add_node', ref=ref, node_type=kind, x=x, y=y, **kw))
            return ref
        def link(a, ap, b, bp):
            ops.append(dict(op='connect', from_node=a, from_pin=ap, to_node=b, to_pin=bp))
        def pin(n, p, v):
            if str(v) == '': return
            ops.append(dict(op='set_pin', node_id=n, pin_name=p, value=str(v)))
        def field(ref, name, x, y):
            node(ref, 'variable_get', x, y, variable_name=name, class_path=MC)
            link(entry, 'Move', ref, 'self')
            return ref, name
        def member(ref, name, x, y):
            node(ref, 'variable_get', x, y, variable_name=name)
            return ref, name
        def fmt(ref, template, x, y, values):
            parts = re.split(r'\{(\w+)\}', template)
            previous = None
            for i in range(1, len(parts), 2):
                name = parts[i]; current = ref if i == 1 else ref+'_'+str(i)
                typ = 'Double' if name == 'W' else 'Int'
                node(current, x=x+(i-1)*140, y=y, function_name='/Script/Engine.KismetStringLibrary:BuildString_'+typ)
                if previous: link(*previous, current, 'AppendTo')
                pin(current, 'Prefix', parts[0] if i == 1 else '')
                pin(current, 'Suffix', parts[i+1])
                link(*values[name], current, 'In'+typ)
                previous = current, 'ReturnValue'
            return previous
        def select(ref, yes, no, cond, x, y):
            node(ref, x=x, y=y, function_name=KML+'SelectString')
            for p, value in [('A', yes), ('B', no), ('bPickA', cond)]:
                if isinstance(value, tuple): link(*value, ref, p)
                else: pin(ref, p, value)
            return ref, 'ReturnValue'

        # Same non-null Move precondition as MoveCost and CanUseMove.
        link(entry, 'then', ret, 'execute')

        breathe = fmt('breath_text', 'Restore up to {R} Resolve and {C} Composure.', 600, 0,
                      dict(R=field('res_delta', 'ResolveDelta', 200, 0), C=field('comp_delta', 'ComposureDelta', 200, 130)))
        mirror = fmt('mirror_text', 'Restore up to {C} Composure. Reveal the next enemy moves.', 600, 320,
                     dict(C=('comp_delta', 'ComposureDelta')))
        armhole = fmt('armhole_text', 'Clear tangled sleeves. Next Button Up timing window x{W}.', 600, 620,
                      dict(W=member('widen', 'WidenFactor', 200, 620)))
        button = fmt('button_text', 'Fasten {P} button. Perfect timing doubles progress.', 600, 920,
                     dict(P=field('progress', 'ProgressDelta', 200, 920)))
        effects = [
            ('DeepBreath', breathe), ('CheckMirror', mirror), ('FindArmhole', armhole),
            ('ButtonUp', button), ('MatchPair', 'Match the socks so Pull On can finish one.'),
            ('PullOn', 'Dress the selected sock.'),
            ('UntwistLeg', 'Untwist the leg. Cancel this garment\'s next action.'),
            ('StepIn', 'Complete the pants if the timing succeeds.'),
            ('Loosen', 'Release constriction. Cancel this garment\'s next action.'),
            ('TieKnot', 'Complete the tie if the timing succeeds.')]
        previous = 'Choose an action.'
        for i, (move, effect) in enumerate(effects):
            y = i * 260
            eq = node('is_'+move, x=1100, y=y, function_name=KML+'EqualEqual_ObjectObject')
            link(entry, 'Move', eq, 'A')
            pin(eq, 'B', '/Game/FoA/Gameplay/Encounter/Data/DA_Move_'+move+'.DA_Move_'+move)
            previous = select('effect_'+move, effect, previous, (eq, 'ReturnValue'), 1450+i*300, y)

        # Exactly the same predicates as CanUseMove, with human remedies.
        cost = node('cost', x=4400, y=-450, function_name=BP+'.BP_Encounter_C:MoveCost')
        link(entry, 'Move', cost, 'Move')
        resolve = member('resolve', 'Resolve', 4400, -600)
        node('shortfall', x=4700, y=-600, function_name=KML+'Less_IntInt')
        link(*resolve, 'shortfall', 'A'); link(cost, 'Cost', 'shortfall', 'B')
        need = fmt('need', 'Need {Cost} Resolve. You have {Resolve}.', 4700, -300,
                   dict(Cost=(cost, 'Cost'), Resolve=resolve))
        blocked = field('blocked_by', 'BlockedBy', 4400, 300)
        node('usable', x=4400, y=400, function_name=BP+'.BP_Encounter_C:CanUseMove')
        link(entry, 'Move', 'usable', 'Move')
        node('not_usable', x=4800, y=400, function_name=KML+'Not_PreBool')
        link('usable','bCan','not_usable','A')
        remedy = 'Blocked by an active condition.'
        for i, (status, text) in enumerate([
            ('SleeveLabyrinth', 'Blocked. Find Armhole to clear tangled sleeves.'),
            ('Mismatched', 'Blocked. Match Pair before pulling on a sock.'),
            ('TwistedLeg', 'Blocked. Untwist Leg before stepping in.'),
            ('Constricted', 'Blocked. Loosen the tie first.')]):
            eq = node('cond'+str(i), x=4400, y=800+i*290, function_name=KML+'EqualEqual_NameName')
            link(*blocked, eq, 'A'); pin(eq, 'B', status)
            remedy = select('hint'+str(i), text, remedy, (eq, 'ReturnValue'), 4770+i*300, 800+i*290)
        previous = select('available', remedy, previous, ('not_usable', 'ReturnValue'), 6100, 100)
        previous = select('funded', need, previous, ('shortfall', 'ReturnValue'), 6100, -300)
        node('as_text', x=6400, y=100, function_name=KTL+'Conv_StringToText')
        link(*previous, 'as_text', 'InString'); link('as_text', 'ReturnValue', ret, 'Detail')
        ops += [dict(op='move', node_id=entry, x=-200, y=-600), dict(op='move', node_id=ret, x=6500, y=-600)]
        # Separate the four functional groups before comment bounds are fitted.
        for i,(name,_) in enumerate(effects):
            ops += [dict(op='move',node_id='is_'+name,x=1400,y=i*260),
                    dict(op='move',node_id='effect_'+name,x=1800,y=i*260)]
        positions = [('resolve',2800,-600),('cost',2800,-450),('shortfall',3200,-600),
                     ('need',3200,-300),('need_3',3480,-300),('funded',4200,-300),
                     ('blocked_by',2800,300),('usable',2800,400),('not_usable',3200,400),
                     ('available',3800,100),('as_text',4600,100)]
        positions += [(ref, x, 800+i*290) for i in range(4) for ref,x in [('cond'+str(i),2800),('hint'+str(i),3200)]]
        ops += [dict(op='move',node_id=ref,x=x,y=y) for ref,x,y in positions]
        groups = [('Current move values', ['res_delta','comp_delta','breath_text','breath_text_3','mirror_text','widen','armhole_text','progress','button_text']),
                  ('Action consequences', [r for move, _ in effects for r in ['is_'+move, 'effect_'+move]]),
                  ('Resolve requirement', ['cost','resolve','shortfall','need','need_3','funded']),
                  ('Status remedies', ['blocked_by','usable','not_usable','available'] + [r for i in range(4) for r in ['cond'+str(i),'hint'+str(i)]])]
        for title, refs in groups:
            ops.append(dict(op='comment', title=title, node_ids=refs, color=[.12,.21,.28]))
        ops.append(dict(op='fit_comments', title_only=True))
        out = Path('Saved/Integration/battle_move_detail'); out.mkdir(parents=True, exist_ok=True)
        (out/'ops.json').write_text(json.dumps(ops, indent=2))
        receipt = call('blueprint_graph_batch', path=BP, graph_name='MoveDetail', ops=ops, compile=True, save=True)
        (out/'mutation.json').write_text(json.dumps(receipt, indent=2))
        assert receipt['applied'] == receipt['total'], receipt
        assert receipt['compile']['compiled'] and receipt['compile']['saved'], receipt['compile']
        print(json.dumps(receipt.get('compile', receipt), indent=2))
    finally:
        hc.release(OWNER, TOKEN)


if __name__ == '__main__': main()
