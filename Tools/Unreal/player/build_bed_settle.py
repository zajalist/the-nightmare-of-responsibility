"""Bed settle for the wake-up beat: the duvet keeps a body-shaped dent while the player lies in bed and relaxes flat
once they get up. Cheap by design (no cloth sim): a world-position-offset dent plus a slight crease darkening,
timed by one MPC scalar that BP_FoAPlayer sets when the wake-up montage starts (PlayInteraction).
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/build_bed_settle.py FOA_STEP=mpc|assign
'assign' puts the material on the level's Bedding_Lux3D (its mesh and transform are untouched); then Hayba level_save."""
import os

import unreal

P = "/Game/FoA/Characters/Player"
MPC_PATH, MAT_PATH = P + "/MPC_FoAPlayer", P + "/Bed/M_FoA_BeddingSettle"
TEX = "/Game/FoA/Lux3D/bedding_fixed/T_Lux3D_Bedding_BaseColor"
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()


def mpc():
    c = unreal.load_asset(MPC_PATH) or AT.create_asset("MPC_FoAPlayer", P, unreal.MaterialParameterCollection,
                                                       unreal.MaterialParameterCollectionFactoryNew())
    s = unreal.CollectionScalarParameter()
    s.set_editor_property("parameter_name", "BedSettleStart")
    s.set_editor_property("default_value", 1.0e7)  # far future: the dent holds until the player gets up
    c.set_editor_property("scalar_parameters", [s])
    EAL.save_loaded_asset(c, False)
    return c


def step_mpc():
    """Only the parameter collection: the material graph itself is built with Hayba's C++ material tools
    (editor-rules: no Python material-graph edits); the node plan is in the module docstring of this file's history."""
    print("MPC ok:", mpc().get_path_name())


def step_assign():
    m = unreal.load_asset(MAT_PATH)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    bed = [a for a in eas.get_all_level_actors() if a.get_actor_label() == "Bedding_Lux3D"]
    assert len(bed) == 1, f"Bedding_Lux3D actors: {len(bed)}"
    smc = bed[0].get_component_by_class(unreal.StaticMeshComponent)
    smc.set_material(0, m)
    print("assigned to", bed[0].get_actor_label(), "at", bed[0].get_actor_location())


{"mpc": step_mpc, "assign": step_assign}[os.environ.get("FOA_STEP", "mpc")]()
