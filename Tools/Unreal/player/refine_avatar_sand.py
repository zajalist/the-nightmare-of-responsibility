"""Scope idle sand to the body and preserve face visibility; narrow in-place edit, then C++ compile/save."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())

PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer'
g = Graph(PLAYER, 'SetSandOverlay')
title = lambda n: BEL.get_node_title(n).replace(' ', '').replace('\n', '')
if not any(title(n).startswith('Greater') for n in g.ed.list_all_nodes()):
    overlays = [n for n in g.ed.list_all_nodes() if title(n).startswith('SetOverlayMaterial')]
    face = None
    for n in overlays:
        connected = PIN.list_connected_pins(g.pin(n, 'self', 'in'))
        if connected and 'Face' in title(PIN.get_owning_node(connected[0])):
            face = n
            break
    assert face, 'Face overlay target missing'
    incoming = PIN.list_connected_pins(g.pin(face, 'execute', 'in'))
    outgoing = PIN.list_connected_pins(BEL.find_then_pin(face))
    assert len(incoming) == 1 and len(outgoing) == 1
    face_source = PIN.list_connected_pins(g.pin(face, 'self', 'in'))[0]
    source_node = PIN.get_owning_node(incoming[0])
    next_node = PIN.get_owning_node(outgoing[0])
    PIN.break_pin_links(g.pin(face, 'execute', 'in')); PIN.break_pin_links(BEL.find_then_pin(face))
    e = entry_node(g)
    amount = g.call('/Script/Engine.KismetMathLibrary:Greater_DoubleDouble', 3000, 560, B=0.85)
    br = g.branch(3300, 0)
    clear = g.call('/Script/Engine.MeshComponent:SetOverlayMaterial', 3600, 560)
    g.link(e, 'Amount', amount, 'A'); g.link(amount, 'ReturnValue', br, 'Condition')
    g.exec_chain(source_node, br)
    g.link(br, 'True', face, 'execute'); g.link(br, 'False', clear, 'execute')
    assert PIN.try_create_connection(face_source, g.pin(clear, 'self', 'in'))
    g.exec_chain(face, next_node); g.exec_chain(clear, next_node)
    g.comment('Cinematic face sand', '', [amount, br, clear], C_VISUAL)

g = Graph(PLAYER)
baseline = [n for n in g.ed.list_all_nodes() if title(n).startswith('SetSandOverlay')]
assert len(baseline) == 1, 'Expected one BeginPlay sand baseline'
g.default(baseline[0], 'Amount', 0.06)
compile_save(PLAYER)
