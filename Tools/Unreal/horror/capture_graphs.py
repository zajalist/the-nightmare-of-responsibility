"""Whole-graph PNGs of BP_Jumpscare (FoAGraphTools), one per graph, into Saved/GraphShots/BP_Jumpscare_<graph>.png.
  $env:FOA_AREAS='Gameplay'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/capture_graphs.py FOA_GRAPH=Poll"""
import os

import unreal


def main():
    bp = unreal.load_asset('/Game/FoA/Gameplay/Jumpscare/BP_Jumpscare')
    g = os.environ.get('FOA_GRAPH', 'Poll')
    unreal.FoAGraphToolsLibrary.capture_graph_png(bp, g, f'P:/FoA/Saved/GraphShots/BP_Jumpscare_{g}.png', True)
    print('capture queued', g)


main()
