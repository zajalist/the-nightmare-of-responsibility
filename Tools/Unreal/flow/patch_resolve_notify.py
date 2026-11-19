"""Regression fix (the user's playtest, 2026-11-10): patch_inventory_set.resolve() replaced Resolve's FindRow(Verb, Held)
with FindCarriedRow(Verb), so Notify rows, whose Item is the notifier's new state ("HandleOff", "Open", "Searched",
"Arrived"), never matched: the wardrobe stayed Standing after the handle came off (stuck at T6), and the boot's key,
container reveals and the T10 door's Notify Open broke the same way.
Now the bare-row FindRow's Item is SelectName(Held if Verb == Notify else None): Notify matches the passed state exactly as
the original FindRow(Verb, Held) did; Look/Use/Take keep the carried row first, then the bare-hand row. (A Notify can't
hit a carried row: no Notify row's Item names an item.) Hayba, BP_Interactable (anim's), idempotent.
  python Tools/Unreal/flow/patch_resolve_notify.py"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

ITB = '/Game/FoA/Gameplay/BP_Interactable'
K = '/Script/Engine.KismetMathLibrary:'
os.environ['HAYBA_AGENT_ID'] = 'story'


def fix():
    ns, es = inspect(ITB, 'Resolve')
    if any(n['title'] == 'SelectName' for n in ns):
        return 'kept'
    e = find(ns, 'Resolve')
    bare = find(ns, 'FindRow')  # the only FindRow left: (Verb, None) feeding the second return node
    b = Batch(ITB, 'Resolve')
    b.fn('isnotify', K + 'EqualEqual_NameName', 200, 450, B='Notify')
    b.link(e, 'Verb', 'isnotify', 'A')
    b.fn('item', K + 'SelectName', 450, 400, B='None')
    b.link(e, 'Held', 'item', 'A')
    b.link('isnotify', 'ReturnValue', 'item', 'bPickA')
    b.link('item', 'ReturnValue', bare, 'Item')
    b.comment('A Notify matches its state exactly', ['isnotify', 'item'])
    b.run()
    return 'Notify rows match the passed state again'


if __name__ == '__main__':
    assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    token = h.lease_acquire('story', ['asset:' + ITB], ttl_s=180, wait_s=240)
    try:
        print('resolve', fix())
    finally:
        h.release('story', token)
