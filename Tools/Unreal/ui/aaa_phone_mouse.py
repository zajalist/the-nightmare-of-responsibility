"""BP_Phone mouse input (main's decision: keyboard and pad stay primary; the wheel scrolls, left click activates the
focused item). Hayba has no InputKey node yet (gap reported), so the three key events are made here in editor Python,
the same pattern as the existing key events: Key -> Get bOpen -> Branch -> PhoneUp / PhoneDown / PhoneConfirm.
  FOA_STEP=find   read-only: print the palette entries for the three keys
  FOA_STEP=add    add the events (apply in the coordinated BP_Phone window only), then compile with Hayba"""
import os

exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())

PHONE = '/Game/FoA/UI/Game/BP_Phone'  # not P: bp_graph defines P(x, y)
KEYS = (('Mouse Wheel Up', 'PhoneUp', 'Wheel scrolls up'), ('Mouse Wheel Down', 'PhoneDown', 'Wheel scrolls down'),
        ('Left Mouse Button', 'PhoneConfirm', 'Click activates'))
g = Graph(PHONE)
pal = [str(n) for n in g.ed.list_available_nodes([])]
hits = {k: [n for n in pal if n == 'Input|MouseEvents|' + k.replace(' ', '')] for k, _, _ in KEYS}
if os.environ.get('FOA_STEP', 'find') == 'find':
    for k, v in hits.items():
        print(k, v[:3])
else:
    for i, (k, fn, title) in enumerate(KEYS):
        mine = [n for n in g.ed.list_all_nodes() if str(BEL.get_node_title(n)).replace('\n', ' ').startswith(k)]
        if [n for n in mine if PIN.list_connected_pins(g.pin(n, 'Pressed'))]:
            print(k, 'exists')
            continue
        if mine:  # an unwired event left by a run that stopped half-way (00:45: P shadowed bp_graph's P())
            g.ed.remove_nodes(mine)
            print(k, 'removed an unwired leftover')
        x, y = 0, 3200 + i * 260
        ev = g.node(hits[k][0], x, y)
        op = g.get('bOpen', x + 200, y + 120)
        br = g.branch(x + 420, y)
        call = g.call(f'{PHONE}.BP_Phone_C:{fn}', x + 680, y)
        g.link(ev, 'Pressed', br, 'execute')
        g.link(op, 'bOpen', br, 'Condition')
        g.link(br, 'True', call, 'execute')
        g.comment(title, '', [ev, op, br, call], C_EVENT)
    unreal.EditorAssetLibrary.save_loaded_asset(g.bp, False)
    print('mouse events added; compile BP_Phone with Hayba blueprint_compile')
