"""Battle audio cues (docs/design/horror/audio_wiring.md, story lane rows). Hayba only; idempotent; each batch compiles
0/0 before it saves. BP_Encounter gets small cue functions, called right after the dispatcher broadcasts that already
carry the moment (so every listener and the sound agree):
  OnDamage(Who)            garment: S_Battle_ClothSnap at it; the pawn: S_Battle_FabricWhoosh + S_Breath_Effort
  OnGarmentEquipped(G)     Shirt S_Battle_Button, Trousers S_Battle_Zipper, Socks S_Foley_ClothMove, Tie S_Battle_ClothSnap
  OnSandBurst              S_Sand_Burst
  OnEncounterWon           S_Dream_ReverseSwell with SMX_StoryDuck pushed for 2 s
BP_Garment.PickIntent: a garment going to Telegraph plays S_Battle_FabricWhoosh at itself.
  python Tools/Unreal/encounter/wire_battle_audio.py"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

E = '/Game/FoA/Gameplay/Encounter/BP_Encounter'
EC = E + '.BP_Encounter_C'
G = '/Game/FoA/Gameplay/Encounter/BP_Garment'
GC = G + '.BP_Garment_C'
OPP = '/Game/FoA/Gameplay/Encounter/PDA_Opponent.PDA_Opponent_C'
MS = '/Game/FoA/Audio/MetaSounds/'
DUCK = '/Game/FoA/Audio/Mix/SMX_StoryDuck.SMX_StoryDuck'
GS, KS, K, A = ('/Script/Engine.GameplayStatics:', '/Script/Engine.KismetSystemLibrary:',
                '/Script/Engine.KismetMathLibrary:', '/Script/Engine.Actor:')
EQUIP = (('Shirt', 'Battle/S_Battle_Button'), ('Trousers', 'Battle/S_Battle_Zipper'),
         ('Socks', 'Foley/S_Foley_ClothMove'), ('Tie', 'Battle/S_Battle_ClothSnap'))


def snd(path):
    return MS + path + '.' + path.rsplit('/', 1)[1]


def fresh(path, name, inputs=None):
    if not h.call('blueprint_inspect_graph', {'path': path, 'graph_name': name}).get('ok'):
        r = h.call('blueprint_add_function', {'path': path, 'function_name': name, **({'inputs': inputs} if inputs else {})})
        assert r.get('ok'), r
    ns, _ = inspect(path, name)
    entry = find(ns, name)
    b = Batch(path, name)
    old = [n['node_id'] for n in ns if n['node_id'] != entry]
    return b, entry, old


def built(path, name):
    r = h.call('blueprint_inspect_graph', {'path': path, 'graph_name': name})
    return r.get('ok') and len(inspect(path, name)[0]) > 2


def cue_functions():
    made = []
    if not built(E, 'CueDamage'):
        b, e, old = fresh(E, 'CueDamage', [{'name': 'Who', 'type': 'object:/Script/Engine.Actor'}])
        if old:
            b.ops.append(dict(op='remove', node_ids=old))
        b.fn('pawn', GS + 'GetPlayerPawn', 0, 300, PlayerIndex=0)
        b.fn('me', K + 'EqualEqual_ObjectObject', 250, 300)
        b.link(e, 'Who', 'me', 'A')
        b.link('pawn', 'ReturnValue', 'me', 'B')
        b.node('hurt', 'branch', 500, 0)
        b.link('me', 'ReturnValue', 'hurt', 'Condition')
        b.link(e, 'then', 'hurt', 'execute')
        b.fn('whoosh', GS + 'PlaySound2D', 800, -200, Sound=snd('Battle/S_Battle_FabricWhoosh'))
        b.fn('breath', GS + 'PlaySound2D', 1100, -200, Sound=snd('Breath/S_Breath_Effort'))
        b.link('hurt', 'then', 'whoosh', 'execute')
        b.chain('whoosh', 'breath')
        b.fn('valid', KS + 'IsValid', 800, 300)
        b.link(e, 'Who', 'valid', 'Object')
        b.node('garment', 'branch', 800, 100)
        b.link('valid', 'ReturnValue', 'garment', 'Condition')
        b.link('hurt', 'else', 'garment', 'execute')
        b.fn('where', A + 'K2_GetActorLocation', 1100, 300)
        b.link(e, 'Who', 'where', 'self')
        b.fn('snap', GS + 'PlaySoundAtLocation', 1400, 100, Sound=snd('Battle/S_Battle_ClothSnap'))
        b.link('where', 'ReturnValue', 'snap', 'Location')
        b.link('garment', 'then', 'snap', 'execute')
        b.comment('Damage cue', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
        b.run()
        made.append('CueDamage')
    if not built(E, 'CueEquip'):
        b, e, old = fresh(E, 'CueEquip', [{'name': 'Garment', 'type': 'object:/Script/Engine.Actor'}])
        if old:
            b.ops.append(dict(op='remove', node_ids=old))
        b.node('cast', 'cast', 250, 0, class_path=GC)
        b.link(e, 'Garment', 'cast', 'Object')
        b.link(e, 'then', 'cast', 'execute')
        b.get('data', 'Data', 500, 300, GC)
        b.link('cast', 'AsBP Garment', 'data', 'self')
        b.get('gid', 'GarmentId', 750, 300, OPP)
        b.link('data', 'Data', 'gid', 'self')
        prev = ('cast', 'then')
        for i, (gid, path) in enumerate(EQUIP):
            x = 1000 + i * 600
            b.fn('is%d' % i, K + 'EqualEqual_NameName', x, 300, B=gid)
            b.link('gid', 'GarmentId', 'is%d' % i, 'A')
            b.node('b%d' % i, 'branch', x, 0)
            b.link('is%d' % i, 'ReturnValue', 'b%d' % i, 'Condition')
            b.link(prev[0], prev[1], 'b%d' % i, 'execute')
            b.fn('s%d' % i, GS + 'PlaySound2D', x + 300, -200, Sound=snd(path))
            b.link('b%d' % i, 'then', 's%d' % i, 'execute')
            prev = ('b%d' % i, 'else')
        b.comment('Equip cue', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
        b.run()
        made.append('CueEquip')
    if not built(E, 'CueSandBurst'):
        b, e, old = fresh(E, 'CueSandBurst')
        b.fn('burst', GS + 'PlaySound2D', 300, 0, Sound=snd('Sand/S_Sand_Burst'))
        b.link(e, 'then', 'burst', 'execute')
        b.comment('Sand burst cue', ['burst'])
        b.run()
        made.append('CueSandBurst')
    if not built(E, 'PopStoryDuck'):
        b, e, old = fresh(E, 'PopStoryDuck')
        b.fn('pop', GS + 'PopSoundMixModifier', 300, 0, InSoundMixModifier=DUCK)
        b.link(e, 'then', 'pop', 'execute')
        b.comment('Release the duck', ['pop'])
        b.run()
        made.append('PopStoryDuck')
    if not built(E, 'CueWon'):
        b, e, old = fresh(E, 'CueWon')
        b.fn('duck', GS + 'PushSoundMixModifier', 300, 0, InSoundMixModifier=DUCK)
        b.fn('swell', GS + 'PlaySound2D', 600, 0, Sound=snd('Dream/S_Dream_ReverseSwell'))
        b.fn('later', KS + 'K2_SetTimer', 900, 0, FunctionName='PopStoryDuck', Time=2.0, bLooping='false')
        b.link(e, 'then', 'duck', 'execute')
        b.chain('duck', 'swell', 'later')
        b.comment('Victory cue', ['duck', 'swell', 'later'])
        b.run()
        made.append('CueWon')
    return made


def after_broadcasts():
    """Call the cue right after each broadcast, with the broadcast's own inputs."""
    plan = {'Call On Damage': ('CueDamage', 'Who'), 'Call On Garment Equipped': ('CueEquip', 'Garment'),
            'Call On Sand Burst': ('CueSandBurst', None), 'Call On Encounter Won': ('CueWon', None)}
    made = []
    for graph in ('ApplyPlayerMove', 'EnemyAct', 'EventGraph'):
        ns, es = inspect(E, graph)
        by = {n['node_id']: n for n in ns}
        b = Batch(E, graph)
        for n in ns:
            if n['title'] not in plan:
                continue
            fn, arg = plan[n['title']]
            nxt = [e for e in es if e['from_node'] == n['node_id'] and e['from_pin'] == 'then']
            if any(by[e['to_node']]['title'] == fn for e in nxt):
                continue                                      # already wired
            ref = 'cue_' + n['node_id'][:8]
            b.fn(ref, EC + ':' + fn, 9000 + 320 * len(made), 4000)  # a clear strip below the graph (no layout data)
            if arg:
                src = next(e for e in es if e['to_node'] == n['node_id'] and e['to_pin'] == arg)
                b.link(src['from_node'], src['from_pin'], ref, arg)
            for e in nxt:
                b.cut(n['node_id'], 'then', e['to_node'], e['to_pin'])
                b.link(ref, 'then', e['to_node'], e['to_pin'])
            b.link(n['node_id'], 'then', ref, 'execute')
            made.append((graph, fn))
        if b.ops:
            b.run()
    return made


def telegraph():
    ns, es = inspect(G, 'PickIntent')
    if any(n['title'] == 'PlaySoundAtLocation' for n in ns):
        return []
    state = find(ns, 'Set State')
    nxt = [e for e in es if e['from_node'] == state and e['from_pin'] == 'then']
    b = Batch(G, 'PickIntent')
    b.get('st', 'State', 0, 600)
    b.fn('tele', K + 'EqualEqual_NameName', 250, 600, B='Telegraph')
    b.link('st', 'State', 'tele', 'A')
    b.node('is', 'branch', 500, 400)
    b.link('tele', 'ReturnValue', 'is', 'Condition')
    b.fn('where', A + 'K2_GetActorLocation', 500, 700)
    b.fn('whoosh', GS + 'PlaySoundAtLocation', 800, 400, Sound=snd('Battle/S_Battle_FabricWhoosh'))
    b.link('where', 'ReturnValue', 'whoosh', 'Location')
    b.link('is', 'then', 'whoosh', 'execute')
    b.link(state, 'then', 'is', 'execute')
    for e in nxt:
        b.cut(state, 'then', e['to_node'], e['to_pin'])
        b.link('whoosh', 'then', e['to_node'], e['to_pin'])
        b.link('is', 'else', e['to_node'], e['to_pin'])
    b.comment('Telegraph cue', ['st', 'tele', 'is', 'where', 'whoosh'])
    b.run()
    return ['PickIntent']


def main():
    os.environ['HAYBA_AGENT_ID'] = 'story'
    assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    token = h.lease_acquire('story', ['asset:' + E, 'asset:' + G], ttl_s=300, wait_s=180)
    try:
        print('battle audio', cue_functions() + after_broadcasts() + telegraph())
    finally:
        h.release('story', token)


if __name__ == '__main__':
    main()
