"""Short structural input/default setup, only inside the coordinator's editor lease."""
import os
import sys
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
import journey_data as D

def events():
    scope={}
    exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py').read(),scope)
    Graph,make=scope['Graph'],scope['make']
    bp=unreal.load_asset(D.BP)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    g=Graph(D.BP)
    # Preserve phone/assist hooks installed by the phone lane; only add missing owned events.
    titles=[str(unreal.BlueprintEditorLibrary.get_node_title(n)) for n in g.ed.list_all_nodes()]
    for action,function,y in [('IA_L2Continue','Confirm',0),('IA_Interact','UseStop',600),('IA_L2Brace','UseStop',1200)]:
        if any(action in title for title in titles):continue
        event=make(g,0,y,action)
        invoke=g.call(D.BP+'.BP_L2Journey_C:'+function,400,y)
        g.link(event,'Started',invoke,'execute')
        g.comment('Journey '+('confirmation' if function=='Confirm' else 'stop action'),'',[event,invoke])
    unreal.EditorAssetLibrary.save_loaded_asset(bp)
    print('Journey input event authored; native compile required')

def notes():
    bp=unreal.load_asset('/Game/FoA/Gameplay/GI_FoA')
    cdo=unreal.get_default_object(bp.generated_class())
    values=dict(cdo.get_editor_property('NotebookLines'))
    for row in D.STOPS:values[unreal.Name(row['flag'])]=unreal.Text(row['note'])
    values[unreal.Name('Knows.L2CVSent')]=unreal.Text('C.V sent.')
    values[unreal.Name('Knows.CVPattern')]=unreal.Text('Give a specific example. Explain what you did. Say what you can actually promise.')
    cdo.set_editor_property('NotebookLines',values)
    del cdo
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
    print('Five Level 2 notebook definitions merged; no save game accessed')

{'events':events,'notes':notes}[os.environ['FOA_JOURNEY_SETUP']]()
