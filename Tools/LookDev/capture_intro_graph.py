"""Capture one restored intro graph; run via ue_remote with INTRO_GRAPH=name."""
import os
import unreal

def capture():
    name=os.environ.get('INTRO_GRAPH','EventGraph')
    bp=unreal.load_asset('/Game/FoA/UI/Intro/WBP_IntroStory')
    unreal.FoAGraphToolsLibrary.capture_graph_png(bp,name,
        'P:/FoA/Saved/LookDev/intro_restored/'+name+'_graph.png',True)
    print('Capture scheduled:',name)

capture()
