"""Requests whole-graph PNGs (FoAGraphToolsLibrary, zoom to fit) of any graphs; returns at once, PNGs land ~1.5 s later.
  python Tools/Unreal/ue_remote.py Tools/Unreal/gameplay/cap_graph.py FOA_GRAPHS=/Game/FoA/Gameplay/BPC_Interactor:PlayRowMontage,...
  [FOA_SUFFIX=_after]  ->  Saved/GraphShots/<Asset>_<Graph><suffix>.png"""
import os

import unreal


def main():
    for spec in os.environ["FOA_GRAPHS"].split(","):
        path, graph = spec.split(":")
        png = f"P:/FoA/Saved/GraphShots/{path.rsplit('/', 1)[1]}_{graph}{os.environ.get('FOA_SUFFIX', '')}.png"
        unreal.FoAGraphToolsLibrary.capture_graph_png(unreal.load_asset(path), graph, png, True)
        print(png)


main()
