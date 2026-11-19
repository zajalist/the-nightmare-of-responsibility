"""Append the player look callback to the existing settings library, without rebuilding its save/audio graphs."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
path = '/Game/FoA/UI/Framework/BPFL_FoASettings'
g = Graph(path, 'ApplySettings')
if not any(str(BEL.get_node_title(n)).replace(' ', '') == 'ApplyLookSettings' for n in g.ed.list_all_nodes()):
    entry = entry_node(g)
    tail = entry
    while True:
        pin = BEL.find_then_pin(tail)
        linked = [PIN.get_owning_node(p) for p in PIN.list_connected_pins(pin)] if PIN.is_valid(pin) else []
        if not linked:
            break
        assert len(linked) == 1
        tail = linked[0]
    point = BEL.get_node_pos(tail)
    x, y = point.x + 384, point.y
    player = g.call('/Script/Engine.GameplayStatics:GetPlayerCharacter', x, y + 224, PlayerIndex=0)
    names = [n for n in g.ed.list_available_nodes([]) if n.replace(' ', '').endswith('CastToBP_ThirdPersonCharacter')]
    assert names
    cast = g.at(g.ed.create_node_from_name(names[0], V2(x + 320, y), []), x + 320, y)
    look = g.call('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter.BP_ThirdPersonCharacter_C:ApplyLookSettings', x + 672, y)
    g.link(player, 'ReturnValue', cast, 'Object'); g.exec_chain(tail, cast, look)
    g.link(cast, 'AsBP_ThirdPersonCharacter', look, 'self'); g.link(entry, 'Settings', look, 'Settings')
    g.comment('Apply look settings', '', [player, cast, look], C_DATA)
unreal.EditorAssetLibrary.save_loaded_asset(g.bp, False)
print('Live look callback ready for Hayba compile')
