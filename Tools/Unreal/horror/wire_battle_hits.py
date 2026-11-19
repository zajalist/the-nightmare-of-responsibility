"""Audio lane: the fight's hit set in story's existing cue functions (patched in place; main's GO 2026-11-10).
  $env:HAYBA_AGENT_ID='horror'; python Tools/Unreal/horror/wire_battle_hits.py
The cues run right after the dispatcher broadcasts (OnDamage, OnGarmentEquipped, OnEncounterWon), so each sound shares the
frame with BP_BattleSand's bound handlers (world: none of its bursts is deferred).
  BP_Encounter.CueDamage        the pawn: S_Battle_PlayerHit (thump plus grunt; the separate breath pin is emptied, so
                                the grunt isn't doubled); a garment: S_Battle_GarmentHit at it
  BP_Encounter.CueEquip         S_Battle_Defeat first (the garment collapsing into sand), then its per-garment equip sound
  BP_Encounter.CueWon           S_Battle_Victory instead of the reverse swell (the duck push stays)
  BP_Encounter.ApplyPlayerMove  after a garment's State is set to Stunned: S_Battle_Stun at that garment
  BP_Encounter.CueSandBurst     (now on arrival) then S_Battle_Worn, the put-on settle
  BP_Garment.PickIntent         the telegraph by GarmentId: Socks elastic, Tie knot, anything else cloth
Idempotent: pins are matched by their current sound, and inserted nodes are skipped when already there. Each graph is
one Hayba batch, compiled; saved only on a clean 0/0 compile, otherwise its new nodes and pin changes are rolled back."""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402

E = '/Game/FoA/Gameplay/Encounter/BP_Encounter'
G = '/Game/FoA/Gameplay/Encounter/BP_Garment'
GC = G + '.BP_Garment_C'
OPP_C = '/Game/FoA/Gameplay/Encounter/PDA_Opponent.PDA_Opponent_C'
MS = '/Game/FoA/Audio/MetaSounds/'
GS, K, A = '/Script/Engine.GameplayStatics:', '/Script/Engine.KismetMathLibrary:', '/Script/Engine.Actor:'


def snd(rel):
    return MS + rel + '.' + rel.rsplit('/', 1)[1]


def node_with_sound(ns, rel):
    return [n['node_id'] for n in ns if 'PlaySound' in n['title']
            and any(p['name'] == 'Sound' and p.get('default_value') == snd(rel) for p in n.get('pins', []))]


def has_sound(ns, rel):
    return bool(node_with_sound(ns, rel))


def apply(b, undo_pins):
    """One batch: compile, save on 0/0; else remove its new nodes, restore the pins it changed, recompile."""
    if not b.ops:
        print(b.graph, 'already wired')
        return True
    r = h.call('blueprint_graph_batch', dict(path=b.path, graph_name=b.graph, ops=b.ops, compile=True, save=False), timeout=120)
    d = r.get('data') or {}
    c = d.get('compile') or {}
    clean = (r.get('ok') and not d.get('compile_error') and c.get('ok', True) and c.get('compiled', True)
             and not c.get('error_count', 0) and not c.get('warning_count', 0))
    if clean:
        assert h.call('asset_save', {'asset_paths': [b.path]}).get('ok')
        print(b.graph, 'ok', d.get('applied'), '/', d.get('total'))
        return True
    made = list((d.get('refs') or {}).values())
    if made:
        h.call('blueprint_remove_nodes', dict(path=b.path, graph_name=b.graph, node_ids=made))
    if undo_pins:
        h.call('blueprint_graph_batch', dict(path=b.path, graph_name=b.graph, compile=False, save=False,
                                             ops=[dict(op='set_pin', node_id=n, pin_name=p, value=v) for n, p, v in undo_pins]))
    c2 = h.call('blueprint_compile', {'path': b.path}).get('data') or {}
    print(b.graph, 'FAILED and rolled back; recompile', {k: c2.get(k) for k in ('error_count', 'warning_count')},
          d.get('failed_index'), r.get('error') or d.get('error') or c.get('errors'))
    sys.exit(1)


def repin(b, ns, old, new, undo):
    for n in node_with_sound(ns, old):
        b.pin(n, 'Sound', snd(new) if new else '')
        undo.append((n, 'Sound', snd(old)))


def damage():
    ns, _ = inspect(E, 'CueDamage')
    b, undo = Batch(E, 'CueDamage'), []
    repin(b, ns, 'Battle/S_Battle_FabricWhoosh', 'Battle/S_Battle_PlayerHit', undo)
    repin(b, ns, 'Breath/S_Breath_Effort', None, undo)  # S_Battle_PlayerHit carries its own grunt
    repin(b, ns, 'Battle/S_Battle_ClothSnap', 'Battle/S_Battle_GarmentHit', undo)
    apply(b, undo)


def won():
    ns, _ = inspect(E, 'CueWon')
    b, undo = Batch(E, 'CueWon'), []
    repin(b, ns, 'Dream/S_Dream_ReverseSwell', 'Battle/S_Battle_Victory', undo)
    apply(b, undo)


def equip():
    ns, es = inspect(E, 'CueEquip')
    b = Batch(E, 'CueEquip')
    if not has_sound(ns, 'Battle/S_Battle_Defeat'):
        entry = next(n['node_id'] for n in ns if n['title'] == 'CueEquip')
        nxt = next(e for e in es if e['from_node'] == entry and e['from_pin'] == 'then')
        b.cut(entry, 'then', nxt['to_node'], nxt['to_pin'])
        b.fn('defeat', GS + 'PlaySound2D', 150, -250, Sound=snd('Battle/S_Battle_Defeat'))
        b.link(entry, 'then', 'defeat', 'execute')
        b.link('defeat', 'then', nxt['to_node'], nxt['to_pin'])
    apply(b, [])


def stun():
    ns, es = inspect(E, 'ApplyPlayerMove')
    b = Batch(E, 'ApplyPlayerMove')
    if not has_sound(ns, 'Battle/S_Battle_Stun'):
        st = next(n['node_id'] for n in ns if n['title'] == 'Set State'
                  and any(p['name'] == 'State' and p.get('default_value') == 'Stunned' for p in n.get('pins', [])))
        nxt = next(e for e in es if e['from_node'] == st and e['from_pin'] == 'then')
        who = next(e for e in es if e['to_node'] == st and e['to_pin'] == 'self')
        b.cut(st, 'then', nxt['to_node'], nxt['to_pin'])
        b.fn('at', A + 'K2_GetActorLocation', 0, 400)
        b.link(who['from_node'], who['from_pin'], 'at', 'self')
        b.fn('stun', GS + 'PlaySoundAtLocation', 200, 200, Sound=snd('Battle/S_Battle_Stun'))
        b.link('at', 'ReturnValue', 'stun', 'Location')
        b.link(st, 'then', 'stun', 'execute')
        b.link('stun', 'then', nxt['to_node'], nxt['to_pin'])
    apply(b, [])


def worn():
    """CueSandBurst now fires on the garment's arrival at its body slot (story's equip flight): the put-on settle plays
    right after its sand-burst sound, the same frame as OnGarmentWorn."""
    ns, es = inspect(E, 'CueSandBurst')
    b = Batch(E, 'CueSandBurst')
    if not has_sound(ns, 'Battle/S_Battle_Worn'):
        burst = node_with_sound(ns, 'Sand/S_Sand_Burst')[0]
        nxt = next((e for e in es if e['from_node'] == burst and e['from_pin'] == 'then'), None)
        if nxt:
            b.cut(burst, 'then', nxt['to_node'], nxt['to_pin'])
        b.fn('worn', GS + 'PlaySound2D', 300, -250, Sound=snd('Battle/S_Battle_Worn'))
        b.link(burst, 'then', 'worn', 'execute')
        if nxt:
            b.link('worn', 'then', nxt['to_node'], nxt['to_pin'])
    apply(b, [])


def telegraph():
    ns, es = inspect(G, 'PickIntent')
    b, undo = Batch(G, 'PickIntent'), []
    if not has_sound(ns, 'Battle/S_Battle_TelegraphElastic'):
        play = node_with_sound(ns, 'Battle/S_Battle_FabricWhoosh')[0]
        where = next(e for e in es if e['to_node'] == play and e['to_pin'] == 'Location')
        into = next(e for e in es if e['to_node'] == play and e['to_pin'] == 'execute')
        b.cut(into['from_node'], into['from_pin'], play, 'execute')
        b.get('data', 'Data', 0, 600)
        b.get('gid', 'GarmentId', 200, 600, OPP_C)
        b.link('data', 'Data', 'gid', 'self')
        for i, (ref, gid, rel) in enumerate((('socks', 'Socks', 'TelegraphElastic'), ('tie', 'Tie', 'TelegraphKnot'))):
            b.fn('is' + ref, K + 'EqualEqual_NameName', 400, 600 + i * 150, B=gid)
            b.link('gid', 'GarmentId', 'is' + ref, 'A')
            b.node('br' + ref, 'branch', 400 + i * 250, 300)
            b.link('is' + ref, 'ReturnValue', 'br' + ref, 'Condition')
            b.fn('play' + ref, GS + 'PlaySoundAtLocation', 650 + i * 250, 100, Sound=snd('Battle/S_Battle_' + rel))
            b.link(where['from_node'], where['from_pin'], 'play' + ref, 'Location')
            b.link('br' + ref, 'then', 'play' + ref, 'execute')
        b.link(into['from_node'], into['from_pin'], 'brsocks', 'execute')
        b.link('brsocks', 'else', 'brtie', 'execute')
        b.link('brtie', 'else', play, 'execute')
        repin(b, ns, 'Battle/S_Battle_FabricWhoosh', 'Battle/S_Battle_TelegraphCloth', undo)
    apply(b, undo)


if __name__ == '__main__':
    assert not h.call('editor_get_state', {}).get('data', {}).get('pie_running'), 'PIE is running: wait'
    lease = h.lease_acquire(h.agent_id(), ['asset:' + E, 'asset:' + G], ttl_s=300, wait_s=120)
    try:
        for step in (damage, won, equip, stun, worn, telegraph):
            step()
    finally:
        h.release(h.agent_id(), lease)
