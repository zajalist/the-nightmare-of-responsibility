"""Bounded graph stills; close each material preview before the next capture."""
import time
from pathlib import Path
import unreal

items=[('/Game/FoA/Characters/Teen/Materials/M_FoA_TeenSurface','teen_surface_graph.png'),
       ('/Game/FoA/Characters/Teen/Hair/M_FoA_TeenStrands','teen_strands_graph.png')]
out=Path('P:/FoA/Saved/CharacterShots/mpfb')
state={'index':0,'next':0,'asset':None,'handle':None}
def tick(_dt):
    if time.time()<state['next']:
        return
    if state['asset']:
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(state['asset'])
        state['asset']=None
    if state['index']==len(items):
        unreal.unregister_slate_post_tick_callback(state['handle'])
        (out/'_graphs_done.txt').write_text('done')
        return
    path,name=items[state['index']]
    state['asset']=unreal.load_asset(path)
    unreal.FoAGraphToolsLibrary.capture_graph_png(state['asset'],'',str(out/name),True)
    state['index']+=1
    state['next']=time.time()+3
state['handle']=unreal.register_slate_post_tick_callback(tick)
