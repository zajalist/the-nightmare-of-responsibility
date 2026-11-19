"""Create the wrinkle function signatures and caches; graph bodies are authored through Hayba."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py',encoding='utf-8').read())
p='/Game/FoA/Characters/Player/BP_FoAPlayer'
real=BEL.get_basic_type_by_name('real');vec=BEL.get_struct_type(unreal.Vector.static_struct())
color=BEL.get_struct_type(unreal.LinearColor.static_struct())
Graph.function(p,'ClothBendWeight',pure=True,inputs=[('A',vec),('B',vec),('Low',real),('High',real)],outputs=[('Weight',real)])
Graph.function(p,'UpdateClothWrinkles')
bp=unreal.load_asset(p);ed=GE.get_graph_editor_by_name(bp,'EventGraph')
existing=set(str(n) for n in BEL.list_member_variable_names(bp,False))
for name,t,default in [('ClothLastUpdate',real,'0.0'),('ClothDistance',real,'0.0')]+[(n,color,'(R=0,G=0,B=0,A=0)') for n in ('WrinkleWeightsL','WrinkleWeightsR','WrinklePhasesL','WrinklePhasesR')]:
    if name not in existing:assert ed.add_member_variable(name,t,default),name
unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
print('Wrinkle signatures ready; native compile and graph bodies required')
