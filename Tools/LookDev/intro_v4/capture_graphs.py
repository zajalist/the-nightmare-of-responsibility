"""Capture WBP_IntroStory's graphs and M_IntroPlate to Saved/GraphShots/intro_v4_<graph>.png (intro lane).
  python Tools/Unreal/ue_remote.py Tools/LookDev/intro_v4/capture_graphs.py INTRO_GRAPHS=NextPanel,UpdateFrame FOA_AREAS=/Game/FoA/UI/Intro
Each capture opens the asset's editor for a moment; close it and compile+save the widget afterwards (editor rules 7)."""
import os

import unreal

L = unreal.FoAGraphToolsLibrary
names = os.environ.get('INTRO_GRAPHS', 'NextPanel').split(',')
for g in names:
    if g == 'M_IntroPlate':
        L.capture_graph_png(unreal.load_asset('/Game/FoA/UI/Intro/M_IntroPlate'), '', 'P:/FoA/Saved/GraphShots/intro_v4_M_IntroPlate.png', True)
    else:
        L.capture_graph_png(unreal.load_asset('/Game/FoA/UI/Intro/WBP_IntroStory'), g, f'P:/FoA/Saved/GraphShots/intro_v4_{g}.png', True)
print('capture scheduled', names)
