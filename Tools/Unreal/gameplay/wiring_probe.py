"""Read-only wiring audit probe (gameplay lane): for each system asset, does it exist and who references it; which
system actors are placed in L_Tutorial_Bedroom; the MPC parameter names. Writes Saved/Integration/wiring_probe.json.
  FOA_AREAS=Gameplay python Tools/Unreal/ue_remote.py Tools/Unreal/gameplay/wiring_probe.py"""
import json

import unreal

AR = unreal.AssetRegistryHelpers.get_asset_registry()
ASSETS = [
    "/Game/FoA/UI/Game/WBP_Phone", "/Game/FoA/UI/Game/BP_Phone", "/Game/FoA/UI/Game/WBP_HUD",
    "/Game/FoA/UI/Game/WBP_DayRollover", "/Game/FoA/UI/Game/WBP_SkipHint", "/Game/FoA/UI/Menu/WBP_Pause",
    "/Game/FoA/UI/Widgets/Menus/WBP_Pause", "/Game/FoA/UI/Widgets/Menus/WBP_Settings", "/Game/FoA/UI/Widgets/Menus/WBP_Credits",
    "/Game/FoA/UI/Widgets/Menus/WBP_MainMenu", "/Game/FoA/UI/Framework/BP_FoAFrontEnd", "/Game/FoA/UI/Framework/SG_FoASettings",
    "/Game/FoA/PostProcess/BP_DreamDirector", "/Game/FoA/PostProcess/MPC_Dream", "/Game/FoA/VFX/Sand/BPL_SandFX",
    "/Game/FoA/VFX/Sand/BP_SandMaterialize", "/Game/FoA/VFX/Sand/BP_SandMorph", "/Game/FoA/VFX/Sand/M_SandOverlay",
    "/Game/FoA/Characters/Player/BP_FoAPlayer", "/Game/FoA/Characters/Player/BP_Nightmare",
    "/Game/FoA/Characters/Player/MPC_FoAPlayer", "/Game/FoA/Gameplay/SG_FoA", "/Game/FoA/Gameplay/GI_FoA",
    "/Game/FoA/Gameplay/Encounter/BP_Encounter", "/Game/FoA/Cinematics/LS_WakeUp", "/Game/FoA/Cinematics/BP_WakeUpCinematic",
]


def refs(path):
    o = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True,
                                              include_searchable_names=False, include_soft_management_references=False,
                                              include_hard_management_references=False)
    return [str(r) for r in (AR.get_referencers(path, o) or [])]


def find(pattern_dirs, needle):
    flt = unreal.ARFilter(package_paths=pattern_dirs, recursive_paths=True)
    return sorted(str(a.package_name) for a in AR.get_assets(flt) if needle.lower() in str(a.asset_name).lower())


out = {"assets": {}, "search": {}, "level": {}, "mpc": {}}
for p in ASSETS:
    ok = unreal.EditorAssetLibrary.does_asset_exist(p)
    out["assets"][p] = {"exists": ok, "referencers": refs(p) if ok else []}
for needle in ("Phone", "SFX_FE", "MS_", "Ambience", "Ambient", "Footstep", "SandMorph", "Materialize", "Nightmare",
               "Settings", "Credits", "Pause", "DayRollover", "Bloom"):
    out["search"][needle] = find(["/Game/FoA"], needle)[:40]
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    cls = a.get_class().get_name()
    lab = a.get_actor_label()
    if any(k in cls + lab for k in ("Phone", "Dream", "Sand", "Nightmare", "Morph", "Materialize", "Clock", "Encounter",
                                    "FrontEnd", "Director", "Ambient", "Audio", "Sound", "PostProcess")):
        out["level"][lab] = cls
for mp in ("/Game/FoA/PostProcess/MPC_Dream", "/Game/FoA/Characters/Player/MPC_FoAPlayer"):
    m = unreal.load_asset(mp)
    if m:
        out["mpc"][mp] = {"scalars": [str(s.get_editor_property("parameter_name")) for s in m.get_editor_property("scalar_parameters")],
                          "vectors": [str(s.get_editor_property("parameter_name")) for s in m.get_editor_property("vector_parameters")]}
json.dump(out, open("P:/FoA/Saved/Integration/wiring_probe.json", "w", encoding="utf-8"), indent=1)
print("wiring probe ->", len(out["assets"]), "assets", len(out["level"]), "level actors")
