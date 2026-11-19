"""Anim lane graph captures for review and the devlog (FoAGraphTools, off-screen PNGs in Saved/GraphShots/anim_*.png).
Captures one graph per run (each opens its asset editor): FOA_SHOT=<key> from SHOTS below.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/graph_shots.py FOA_AREAS=/Game/FoA/Characters/Player FOA_SHOT=animgraph"""
import os

import unreal

P = "/Game/FoA/Characters/Player"
SHOTS = {
    "animgraph": (P + "/ABP_FoAPlayer", "AnimGraph"),
    "abp_events": (P + "/ABP_FoAPlayer", "EventGraph"),
    "walk_state": (P + "/ABP_FoAPlayer", "Walk / Run"),
    "abp_mh": (P + "/ABP_FoAPlayer_MH", "AnimGraph"),
    "player_events": (P + "/BP_FoAPlayer", "EventGraph"),
    "set_cinematic": (P + "/BP_FoAPlayer", "SetCinematic"),
}
key = os.environ["FOA_SHOT"]
path, graph = SHOTS[key]
out = f"P:/FoA/Saved/GraphShots/anim_{key}.png"
unreal.FoAGraphToolsLibrary.capture_graph_png(unreal.load_asset(path), graph, out, True)
print("GRAPH_SHOT scheduled", out)
