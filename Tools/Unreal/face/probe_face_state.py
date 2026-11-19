"""Read-only probe for the face lane: PP_DreamMono blendables, BP_FoAPlayer render-stencil setup, MPC face params.
  python Tools/Unreal/integration/run_read.py Tools/Unreal/face/probe_face_state.py
Writes Saved/FaceShots/probe_face_state.json."""
import json

import unreal


def run():
    out = {}
    ppv = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
               if isinstance(a, unreal.PostProcessVolume) and a.get_actor_label() == "PP_DreamMono")
    s = ppv.get_editor_property("settings")
    out["blendables"] = [(b.get_editor_property("object").get_path_name() if b.get_editor_property("object") else None,
                          b.get_editor_property("weight"))
                         for b in s.get_editor_property("weighted_blendables").get_editor_property("array")]
    out["ppv_unbound"] = ppv.get_editor_property("unbound")
    bp = unreal.load_asset("/Game/FoA/Characters/Player/BP_FoAPlayer")
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    comps = {}
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        o = lib.get_object_for_blueprint(lib.get_data(h), bp)
        if not isinstance(o, unreal.PrimitiveComponent):
            continue
        row = {"class": o.get_class().get_name(),
               "custom_depth": o.get_editor_property("render_custom_depth"),
               "stencil": o.get_editor_property("custom_depth_stencil_value"),
               "visible": o.get_editor_property("visible")}
        if isinstance(o, unreal.SkeletalMeshComponent):
            m = o.get_editor_property("skeletal_mesh_asset")
            row["mesh"] = m.get_path_name() if m else None
        if isinstance(o, unreal.GroomComponent):
            g = o.get_editor_property("groom_asset")
            row["groom"] = g.get_path_name() if g else None
        if isinstance(o, unreal.CameraComponent):
            pass
        comps[str(lib.get_variable_name(lib.get_data(h)))] = row
    out["player_components"] = comps
    mpc = unreal.load_asset("/Game/FoA/PostProcess/MPC_Dream")
    out["mpc_face"] = {str(p.get_editor_property("parameter_name")): p.get_editor_property("default_value")
                       for p in mpc.get_editor_property("scalar_parameters")
                       if "Face" in str(p.get_editor_property("parameter_name"))}
    path = "P:/FoA/Saved/FaceShots/probe_face_state.json"
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print("wrote", path)


run()
