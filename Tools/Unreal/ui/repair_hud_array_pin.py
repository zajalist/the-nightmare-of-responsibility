"""Specialize the array call that the native graph batch leaves as a wildcard."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())
g = Graph('/Game/FoA/UI/Game/WBP_HUD', 'HandleFocusChanged')
nodes = list(g.ed.list_all_nodes())
lengths = [n for n in nodes if str(BEL.get_node_title(n)).strip() == 'Length']
assert len(lengths) == 1
old = lengths[0]
source = list(PIN.list_connected_pins(g.pin(old, 'TargetArray', 'in')))
targets = list(PIN.list_connected_pins(g.pin(old, 'ReturnValue', 'out')))
assert len(source) == 1 and len(targets) == 1
print('array source', PIN.get_pin_type(source[0]).export_text(), 'node', old.get_class().get_name())
pos = BEL.get_node_pos(old)
g.ed.remove_nodes([old])
new = g.call('/Script/Engine.KismetArrayLibrary:Array_Length', pos.x, pos.y)
assert PIN.try_create_connection(source[0], g.pin(new, 'TargetArray', 'in'))
assert PIN.try_create_connection(g.pin(new, 'ReturnValue', 'out'), targets[0])
print('array result', PIN.get_pin_type(g.pin(new, 'TargetArray', 'in')).export_text(), 'node', new.get_class().get_name())
assert 'wildcard' not in PIN.get_pin_type(g.pin(new, 'TargetArray', 'in')).export_text()
