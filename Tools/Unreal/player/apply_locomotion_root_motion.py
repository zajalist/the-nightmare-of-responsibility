"""Set root extraction on each real source AnimInstance; no CDO staging or default mutation."""
import unreal
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Never mutate during user PIE'
path = '/Game/FoA/Characters/Player/ABP_FoAPlayer'
g = Graph(path, 'EventGraph')
existing = [n for n in g.ed.list_all_nodes() if BEL.get_node_title(n).splitlines()[0] == 'SetRootMotionMode']
assert len(existing) <= 1
if not existing:
    initialize = next(n for n in g.ed.list_all_nodes() if 'BlueprintInitializeAnimation' in BEL.get_node_title(n).replace(' ', ''))
    targets = list(PIN.list_connected_pins(BEL.find_then_pin(initialize))); assert targets
    at = BEL.get_node_pos(initialize)
    node = g.call('/Script/Engine.AnimInstance:SetRootMotionMode', at.x + 200, at.y - 250, Value='IgnoreRootMotion')
    PIN.break_pin_links(BEL.find_then_pin(initialize)); g.exec_chain(initialize, node)
    for pin in targets:
        assert PIN.try_create_connection(BEL.find_then_pin(node), pin)
    c = g.ed.add_comment_to_nodes('Keep walking beneath the capsule', [node], 48)
    BEL.set_comment_color(c, C_LOGIC); house_comment_flags(c)
    compile_save(path)
    print('Saved runtime initialization: extract/discard authored root motion before character caching')
else:
    print('Root-motion initialization already installed; no mutation')
