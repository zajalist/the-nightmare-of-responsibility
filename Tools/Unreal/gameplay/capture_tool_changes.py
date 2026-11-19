import unreal
bp=unreal.load_asset('/Game/FoA/Gameplay/BP_Door')
for name in ('ApplyRow','RefreshDoorTool'):
    unreal.FoAGraphToolsLibrary.capture_graph_png(bp,name,'P:/FoA/Saved/GraphShots/door_'+name+'_20261106.png',True)
print('Requested door session and feedback graph captures')
