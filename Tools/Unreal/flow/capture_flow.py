"""Requests PNGs of every mech_flow graph (FoAGraphTools); they appear in Saved/GraphShots/flow_* a few ticks later.
    python Tools/Unreal/ue_remote.py Tools/Unreal/flow/capture_flow.py [FOA_GRAPHS=EventGraph,MoveDoor]"""
import os

import unreal

SHOTS = 'P:/FoA/Saved/GraphShots/'
ONLY = [g for g in os.environ.get('FOA_GRAPHS', '').split(',') if g]


def main():
    for path in ('/Game/FoA/Gameplay/GI_FoA', '/Game/FoA/Gameplay/BP_BeatDirector'):
        bp = unreal.load_asset(path)
        short = path.rsplit('/', 1)[1]
        for g in unreal.BlueprintEditorLibrary.list_graph_names(bp):
            g = str(g)
            if (ONLY and g not in ONLY) or g == 'UserConstructionScript':
                continue
            png = f'{SHOTS}flow_{short}_{g}.png'
            unreal.FoAGraphToolsLibrary.capture_graph_png(bp, g, png, True)
            print('requested', png)


main()
