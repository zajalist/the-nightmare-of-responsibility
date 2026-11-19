"""Requests whole-graph PNGs of the encounter graphs (FoAGraphToolsLibrary.capture_graph_png, zoom to fit).
  python Tools/Unreal/ue_remote.py Tools/Unreal/encounter/capture_graphs.py [FOA_GRAPHS=BP_Encounter:EventGraph,...]
Returns at once; the PNGs land in Saved/GraphShots/enc_<asset>_<graph>.png a few seconds later (poll from outside)."""
import os

import unreal

ENC = '/Game/FoA/Gameplay/Encounter'
SHOTS = 'P:/FoA/Saved/GraphShots/'
DEFAULT = ('BP_Encounter:EventGraph,BP_Encounter:ApplyPlayerMove,BP_Encounter:EnemyAct,BP_Encounter:SpawnFrom,'
           'BP_Encounter:PickIntentsFrom,BP_Encounter:ApplySelf,BP_Encounter:SetState,BP_Garment:EventGraph,'
           'BP_Garment:PickIntent,BP_Garment:Setup,BP_Garment:StatusLine,WBP_Encounter:EventGraph,'
           'WBP_Encounter:RefreshRow,WBP_Encounter:RefreshAct')


def main():
    os.makedirs(SHOTS, exist_ok=True)
    for spec in os.environ.get('FOA_GRAPHS', DEFAULT).split(','):
        name, graph = spec.split(':')
        png = f'{SHOTS}enc_{name}_{graph}.png'
        unreal.FoAGraphToolsLibrary.capture_graph_png(unreal.load_asset(f'{ENC}/{name}'), graph, png, True)
        print(png)


main()
