"""Read-only: do the protagonist groom bindings target the face mesh BP_FoAPlayer uses, and how does the built
MetaHuman Blueprint wire its grooms? Writes Saved/AnimShots/groom_bind.txt.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/groom_bind_probe.py FOA_AREAS=/Game/FoA/Characters/Player"""
import unreal

MHC = "/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist"
L = []
for b in ("Grooms/Hair_S_Messy_Binding", "Grooms/Eyebrows_M_Thick_Binding"):
    ba = unreal.load_asset(f"{MHC}/{b}")
    for k in ("groom", "target_skeletal_mesh", "source_skeletal_mesh", "binding_type", "num_interpolation_points",
              "target_binding_attribute", "matching_section"):
        try:
            v = ba.get_editor_property(k)
            L.append(f"{b} {k} = {v.get_path_name() if hasattr(v, 'get_path_name') else v}")
        except Exception as e:
            L.append(f"{b} {k} ? {str(e)[:100]}")
reg = unreal.AssetRegistryHelpers.get_asset_registry()
for a in unreal.EditorAssetLibrary.list_assets("/Game/FoA/Characters/Protagonist/Built", recursive=True):
    n = a.split("/")[-1]
    if n.startswith(("BP_", "SKM_", "MHC_")) or "Binding" in n:
        L.append(f"asset {a}")
bp_paths = [a for a in unreal.EditorAssetLibrary.list_assets("/Game/FoA/Characters/Protagonist/Built", recursive=True)
            if a.split("/")[-1].startswith("BP_")]
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for p in bp_paths[:2]:
    bp = unreal.load_asset(p.split(".")[0])
    if not isinstance(bp, unreal.Blueprint):
        continue
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        d = lib.get_data(h)
        o = lib.get_object_for_blueprint(d, bp)
        line = f"{p.split('/')[-1]} comp {lib.get_variable_name(d)} {o.get_class().get_name() if o else None}"
        if isinstance(o, unreal.GroomComponent):
            ga, bi = o.get_editor_property("groom_asset"), o.get_editor_property("binding_asset")
            line += f" groom={ga.get_path_name() if ga else None} binding={bi.get_path_name() if bi else None}"
            for k in ("attachment_name", "use_cards", "lod_bias"):
                try:
                    line += f" {k}={o.get_editor_property(k)}"
                except Exception:
                    pass
        if isinstance(o, unreal.SkeletalMeshComponent):
            m = o.get_editor_property("skeletal_mesh_asset")
            line += f" mesh={m.get_path_name() if m else None} anim={o.get_editor_property('anim_class')}"
        L.append(line)
with open("P:/FoA/Saved/AnimShots/groom_bind.txt", "w") as f:
    f.write("\n".join(L) + "\n")
print(len(L), "lines")
