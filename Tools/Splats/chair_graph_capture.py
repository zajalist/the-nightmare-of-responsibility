"""Capture owned graphs sequentially, then close the preview tab; outside PIE only."""
import time
from pathlib import Path
import unreal
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
bp=unreal.load_asset('/Game/FoA/Gameplay/Ambient/BP_ChairNightmare')
out=Path('P:/FoA/Saved/GraphShots/ChairNightmare');out.mkdir(parents=True,exist_ok=True)
graphs=['StartVision','Animate','Crumble','FinishVision','Reset','Poll','EventGraph']
S={'i':0,'start':0,'h':None}
def tick(dt):
    if S['i'] and time.monotonic()-S['start']<2:return
    if S['i']>=len(graphs):
        unreal.unregister_slate_post_tick_callback(S['h'])
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
        (out/'done.txt').write_text('done');return
    name=graphs[S['i']]
    unreal.FoAGraphToolsLibrary.capture_graph_png(bp,name,str(out/(name+'.png')),True)
    S['i']+=1;S['start']=time.monotonic()
S['h']=unreal.register_slate_post_tick_callback(tick)
