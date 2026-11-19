"""Set PP_DreamMono's blendables (post-process lane). Rule: take a PP material off the volume before rebuilding it.
  python Tools/Unreal/ue_remote.py Tools/Unreal/pp_blendables.py BLENDS=M_PP_DreamMono,M_PP_DreamLens
Assets are looked up under /Game/FoA/PostProcess; order = order in the array. Save the level afterwards (Hayba level_save)."""
import os

import unreal


def run(names):
    ppv = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
               if isinstance(a, unreal.PostProcessVolume) and a.get_actor_label() == "PP_DreamMono")
    s = ppv.get_editor_property("settings")
    blends = []
    for n in names:
        wb = unreal.WeightedBlendable()
        wb.set_editor_property("weight", 1.0)
        wb.set_editor_property("object", unreal.load_asset("/Game/FoA/PostProcess/" + n))
        blends.append(wb)
    wbs = unreal.WeightedBlendables()
    wbs.set_editor_property("array", blends)
    s.set_editor_property("weighted_blendables", wbs)
    ppv.set_editor_property("settings", s)
    print("PP_DreamMono blendables:", [b.get_editor_property("object").get_name() for b in blends])


run([n for n in os.environ.get("BLENDS", "").split(",") if n])
