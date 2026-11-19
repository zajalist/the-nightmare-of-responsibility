"""Small array-node authoring gap; compile/save remains native Hayba."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py',encoding='utf-8').read())
INV_PATH='/Game/FoA/Gameplay/BPC_Inventory'
g=Graph.function(INV_PATH,'ClearPhysicalInventory');e=entry_node(g)
items=g.get('Items',0,250)
clear=g.call('/Script/Engine.KismetArrayLibrary:Array_Clear',300,0)
g.link(items,'Items',clear,'TargetArray')
select=g.call(INV_PATH+'.BPC_Inventory_C:Select',650,0,Index=-1)
g.exec_chain(e,clear,select)
c=g.ed.add_comment_to_nodes('Empty physical slots and refresh the HUD',list(g.ed.list_all_nodes()),40)
BEL.set_comment_color(c,C_DATA);house_comment_flags(c)
print('Physical inventory reset graph authored; native compile/save required')
