"""Editor Python (Hayba's set_pin refuses an empty value): the Victory phase line in WBP_Encounter
RefreshBattlePresentation (SelectString with A 'You are dressed.') becomes ''. Compile and save with Hayba afterwards.
  python Tools/Unreal/ue_remote.py Tools/Unreal/ui/b3_victory_line.py FOA_AREAS=/Game/FoA/Gameplay/Encounter/WBP_Encounter"""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
g = Graph('/Game/FoA/Gameplay/Encounter/WBP_Encounter', 'RefreshBattlePresentation')
hits = [n for n in g.ed.list_nodes_of_class(unreal.K2Node_CallFunction)
        if str(BEL.get_node_title(n)).startswith('Select') and PIN.get_pin_value(g.pin(n, 'A', 'in')) == 'You are dressed.']
assert len(hits) <= 1, len(hits)
if hits:
    print('cleared', PIN.set_pin_value(g.pin(hits[0], 'A', 'in'), ''), repr(PIN.get_pin_value(g.pin(hits[0], 'A', 'in'))))
else:
    print('victory line already empty')
