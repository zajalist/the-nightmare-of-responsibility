"""Read-only: how BP_MHC_Protagonist (the character lane's reference assembly) wires body, face, grooms and outfit.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/probe_mhc.py"""
import unreal

ROOT = "/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist"


def run():
    bp = unreal.load_asset(ROOT + "/BP_MHC_Protagonist")
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        d = lib.get_data(h)
        obj = lib.get_object_for_blueprint(d, bp)
        if not obj:
            continue
        info = [str(lib.get_variable_name(d)), obj.get_class().get_name()]
        for prop in ("skeletal_mesh_asset", "groom_asset", "binding_asset", "anim_class", "render_custom_depth",
                     "custom_depth_stencil_value", "leader_pose_component", "attach_parent"):
            try:
                v = obj.get_editor_property(prop)
                info.append(f"{prop}={v.get_path_name() if hasattr(v, 'get_path_name') else v}")
            except Exception:
                pass
        print(" | ".join(info))
    graphs = [str(g) for g in unreal.BlueprintEditorLibrary.list_graph_names(bp)]
    print("graphs:", graphs)
    for gname in graphs:
        ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, gname)
        titles = [unreal.BlueprintEditorLibrary.get_node_title(n).replace("\n", " ") for n in ed.list_all_nodes()]
        hits = [t for t in titles if any(k in t for k in ("Leader", "Outfit", "Groom", "Clothing", "Set Skeletal", "Retarget"))]
        if hits:
            print(gname, hits[:20])
    for path in ("Body/SKM_MHC_Protagonist_BodyMesh", "Face/SKM_MHC_Protagonist_FaceMesh", "Clothing/MHC_Protagonist_Outfits"):
        a = unreal.load_asset(f"{ROOT}/{path}")
        sk = a.get_editor_property("skeleton").get_path_name() if isinstance(a, unreal.SkeletalMesh) else None
        print(path, "->", a.get_class().get_name() if a else None, "| skeleton:", sk)


run()
