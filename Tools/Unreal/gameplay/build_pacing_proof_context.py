"""Narrow native GI context setter for isolated runtime proofs of EditDefaultsOnly fields.
Only the proof fixture calls it. Original progress is restored; its save slot is never written.
"""
import unreal
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())
GI = '/Game/FoA/Gameplay/GI_FoA'
g = Graph.function(GI, 'SetProofProgressContext', inputs=[('Slot', ptype('string')),
    ('Known', BEL.get_set_type(ptype('name'))), ('Lines', BEL.get_array_type(ptype('text')))])
e = g.at(entry_node(g), 0, 0); last = e
for i, (name, value) in enumerate((('SaveSlot', 'Slot'), ('Knowledge', 'Known'), ('Notebook', 'Lines'))):
    node = g.set(name, 300 + i * 300, 0); g.link(e, value, node, name); g.exec_chain(last, node); last = node
c = g.ed.add_comment_to_nodes('Isolate and restore runtime proof progress', list(g.ed.list_all_nodes()), 48)
BEL.set_comment_color(c, C_DATA); house_comment_flags(c)
compile_save(GI)
