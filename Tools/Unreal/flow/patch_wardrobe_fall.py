"""First-person fall through impact, then the existing sand scatter, teleport and visible re-formation.
The sequence must stop before WardrobeReappear or its pawn transform track overwrites the teleport.
SetWardrobeShot caches the camera/HUD before playback; FinishWardrobeTransition owns restoring them and control.
Reset stops the sequence first, preserving the active flag so the existing finish cleanup still runs.
  python Tools/Unreal/flow/patch_wardrobe_fall.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal/flow']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402
import patch_battle_intro as PBI  # noqa: E402

P, C = PBI.P, PBI.C
K, KS, GS = PBI.K, PBI.KS, PBI.GS
LSP, MSP = PBI.LSP, PBI.MSP
INTER = '/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C'
LS = '/Game/FoA/Cinematics/Wardrobe/LS_WardrobeFall.LS_WardrobeFall'
IMPACT, VANISH, REAPPEAR, FINISH = 3.15, 4.15, 5.05, 7.2
assert 0 < IMPACT < VANISH < REAPPEAR < FINISH


def norm(t):
    return t.split('\n')[0].replace(' ', '')


def fresh(fn):
    ns, e = PBI.ensure(fn)
    rest = [n['node_id'] for n in ns if n['node_id'] != e]
    if rest:
        b = Batch(P, fn)
        b.ops.append(dict(op='remove', node_ids=rest))
        b.run()
    return e


def tick():
    e = fresh('WardrobeFallTick')
    b = Batch(P, 'WardrobeFallTick')
    b.get('on', 'bWardrobeTransition', 0, 250)
    b.node('active', 'branch', 250, 0)
    b.link('on', 'bWardrobeTransition', 'active', 'Condition')
    b.fn('rattle', C + ':WardrobeRattle', 500, 0)
    b.link(e, 'then', 'active', 'execute')
    b.link('active', 'then', 'rattle', 'execute')
    b.comment('Two seconds of rattle', ['on', 'active', 'rattle'])
    b.run()


def play():
    e = fresh('PlayWardrobeFall')
    b = Batch(P, 'PlayWardrobeFall')
    b.fn('hud', C + ':SetWardrobeShot', 250, 0, Enable='true')
    b.fn('pawn', GS + 'GetPlayerCharacter', 250, 300, PlayerIndex=0)
    b.fn('mk', LSP + 'CreateLevelSequencePlayer', 500, 0, LevelSequence=LS,
         Settings='(bDisableMovementInput=True,bDisableLookAtInput=True,bHideHud=True)')
    b.set('keep', 'WardrobeFallPlayer', 800, 0)
    b.link('mk', 'ReturnValue', 'keep', 'WardrobeFallPlayer')
    b.node('arr', 'make_array', 800, 300)
    b.link('pawn', 'ReturnValue', 'arr', '[0]')
    b.fn('bind', '/Script/LevelSequence.LevelSequenceActor:SetBindingByTag', 1050, 0, BindingTag='Player',
         bAllowBindingsFromAsset='false')
    b.link('mk', 'OutActor', 'bind', 'self')
    b.link('arr', 'Array', 'bind', 'Actors')
    b.fn('go', MSP + 'Play', 1300, 0)
    b.link('keep', 'Output_Get', 'go', 'self')
    b.fn('done', KS + 'K2_SetTimer', 1550, 0, FunctionName='WardrobeFallDone', Time=IMPACT, bLooping='false')
    tail = 'done'
    for i, (ref, fn, seconds) in enumerate([('sand', 'WardrobeSandTick', .05), ('vanish', 'WardrobeVanish', VANISH),
                                           ('reappear', 'WardrobeReappear', REAPPEAR), ('finish', 'FinishWardrobeTransition', FINISH)]):
        b.fn(ref, KS + 'K2_SetTimer', 1800 + i * 300, 0, FunctionName=fn,
             Time=seconds, bLooping='true' if ref == 'sand' else 'false')
        b.chain(tail, ref)
        tail = ref
    b.link(e, 'then', 'hud', 'execute')
    b.chain('hud', 'mk', 'keep', 'bind', 'go', 'done')
    b.comment('The wardrobe falls, first person', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()


def done():
    e = fresh('WardrobeFallDone')
    b = Batch(P, 'WardrobeFallDone')
    b.fn('c1', KS + 'K2_ClearTimer', 250, 0, FunctionName='WardrobeFallTick')
    b.fn('c2', KS + 'K2_ClearTimer', 500, 0, FunctionName='WardrobeFallDone')
    b.get('sp', 'WardrobeFallPlayer', 500, 300)
    b.fn('valid', KS + 'IsValid', 750, 300)
    b.link('sp', 'WardrobeFallPlayer', 'valid', 'Object')
    b.node('playing', 'branch', 750, 0)
    b.link('valid', 'ReturnValue', 'playing', 'Condition')
    b.fn('stop', MSP + 'Stop', 1000, -150)
    b.link('sp', 'WardrobeFallPlayer', 'stop', 'self')
    b.fn('top', C + ':EnterTopDown', 1250, 0)
    # EnterTopDown normally starts at t=0; keep its room change at t=5 after this later cut.
    b.fn('stage', KS + 'K2_SetTimer', 1550, 0, FunctionName='StageWrongWall',
         Time=5.0 - IMPACT, bLooping='false')
    b.link(e, 'then', 'c1', 'execute')
    b.chain('c1', 'c2', 'playing')
    b.link('playing', 'then', 'stop', 'execute')
    b.link('stop', 'then', 'top', 'execute')
    b.link('playing', 'else', 'top', 'execute')
    b.chain('top', 'stage')
    b.comment('Release sequence ownership before re-forming', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()


def begin():
    ns, es = inspect(P, 'BeginWardrobeTransition')
    t = {n['node_id']: norm(n['title']) for n in ns}
    if 'PlayWardrobeFall' in t.values():
        return 'kept'
    shot = next(i for i, x in t.items() if x == 'SetWardrobeShot')
    col = next(x['from_node'] for x in es if x['to_node'] == shot and x['from_pin'] == 'then')
    assert t[col] == 'SetActorEnableCollision', t[col]
    gone, cur = [], shot
    while True:  # SetWardrobeShot, EnterTopDown and the four timers: the tail of the chain
        gone.append(cur)
        nxt = [x['to_node'] for x in es if x['from_node'] == cur and x['from_pin'] == 'then']
        if not nxt:
            break
        cur = nxt[0]
    assert [t[g] for g in gone][:2] == ['SetWardrobeShot', 'EnterTopDown'], [t[g] for g in gone]
    assert all(t[g] == 'SetTimerbyFunctionName' for g in gone[2:]), [t[g] for g in gone]
    b = Batch(P, 'BeginWardrobeTransition')
    b.ops.append(dict(op='remove', node_ids=gone))
    b.fn('tick', KS + 'K2_SetTimer', 3200, 0, FunctionName='WardrobeFallTick', Time=0.05, bLooping='true')
    b.fn('play', C + ':PlayWardrobeFall', 3500, 0)
    b.link(col, 'then', 'tick', 'execute')
    b.chain('tick', 'play')
    b.comment('Rattle, then the fall in first person', ['tick', 'play'])
    b.run()
    return 'removed %d nodes' % len(gone)


def reset():
    ns, es = inspect(P, 'ResetWardrobeTransition')
    t = {n['node_id']: norm(n['title']) for n in ns}
    if any(n['title'] == 'Get WardrobeFallPlayer' for n in ns):
        # Migrate the old prefix: clearing this flag skipped the real interruption cleanup.
        off = [n['node_id'] for n in ns if norm(n['title']) == 'SetbWardrobeTransition']
        if off:
            assert len(off) == 1
            target = next(x for x in es if x['from_node'] == off[0] and x['from_pin'] == 'then')
            incoming = [x for x in es if x['to_node'] == off[0] and x['to_pin'] == 'execute']
            assert len(incoming) == 2
            b = Batch(P, 'ResetWardrobeTransition')
            b.ops.append(dict(op='remove', node_ids=off))
            for edge in incoming:
                b.link(edge['from_node'], edge['from_pin'], target['to_node'], target['to_pin'])
            b.run()
        return 'kept'
    e = find(ns, 'ResetWardrobeTransition')
    first = next(x for x in es if x['from_node'] == e and x['from_pin'] == 'then')
    b = Batch(P, 'ResetWardrobeTransition')
    b.cut(e, 'then', first['to_node'], first['to_pin'])
    b.fn('c1', KS + 'K2_ClearTimer', -1000, -300, FunctionName='WardrobeFallTick')
    b.fn('c2', KS + 'K2_ClearTimer', -750, -300, FunctionName='WardrobeFallDone')
    b.get('sp', 'WardrobeFallPlayer', -500, 0)
    b.fn('valid', KS + 'IsValid', -500, 150)
    b.link('sp', 'WardrobeFallPlayer', 'valid', 'Object')
    b.node('playing', 'branch', -500, -300)
    b.link('valid', 'ReturnValue', 'playing', 'Condition')
    b.fn('stop', MSP + 'Stop', -250, -450)
    b.link('sp', 'WardrobeFallPlayer', 'stop', 'self')
    b.link(e, 'then', 'c1', 'execute')
    b.chain('c1', 'c2', 'playing')
    b.link('playing', 'then', 'stop', 'execute')
    b.link('stop', 'then', first['to_node'], first['to_pin'])
    b.link('playing', 'else', first['to_node'], first['to_pin'])
    b.comment('Stop the fall first', ['c1', 'c2', 'sp', 'valid', 'playing', 'stop'])
    b.run()
    return 'built'


if __name__ == '__main__':
    assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    token = h.lease_acquire('story', ['asset:' + P], ttl_s=600, wait_s=600)
    try:
        r = h.call('blueprint_add_variable', dict(path=P, variable_name='WardrobeFallPlayer', category='Story|Wardrobe',
                                                  variable_type='object:/Script/LevelSequence.LevelSequencePlayer',
                                                  update_existing=True), owner='story', timeout=60)
        if not r.get('ok'):  # Hayba on 5.9 refuses object: types: add_wardrobe_var.py (editor Python) declares it first
            print('WardrobeFallPlayer via Hayba refused:', str(r.get('error'))[:90])
        tick()
        play()
        done()
        print('wardrobe_fall', dict(begin=begin(), reset=reset()))
    finally:
        h.release('story', token)
