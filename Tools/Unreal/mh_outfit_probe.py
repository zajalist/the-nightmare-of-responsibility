"""Read-only: post-process AnimBPs on the built body and outfit meshes, the player's body component flag, and the
parents of the body's arm corrective joints (what drives the shirt's shoulder/sleeve weights)."""
import unreal
B = "/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/"
for p in ("Body/SKM_MHC_Protagonist_BodyMesh", "Clothing/MHC_Protagonist_Outfits", "Face/SKM_MHC_Protagonist_FaceMesh"):
    m = unreal.load_asset(B + p)
    pp = m.get_editor_property("post_process_anim_blueprint")
    print("OUTFIT_PP", p.split("/")[-1], pp.get_path_name() if pp else None)
c = unreal.SkeletalMeshComponent()
c.set_skeletal_mesh_asset(unreal.load_asset(B + "Body/SKM_MHC_Protagonist_BodyMesh"))
names = [str(c.get_bone_name(i)) for i in range(c.get_num_bones())]
arm = [n for n in names if n.endswith("_l") and any(k in n for k in ("upperarm", "clavicle", "lowerarm"))]
print("OUTFIT_ARM", [(n, str(c.get_parent_bone(n))) for n in arm])
SDS = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
LIB = unreal.SubobjectDataBlueprintFunctionLibrary
for bp_path in ("/Game/FoA/Characters/Player/BP_FoAPlayer", B + "BP_MHC_Protagonist"):
    bp = unreal.load_asset(bp_path)
    for h in SDS.k2_gather_subobject_data_for_blueprint(bp):
        o = LIB.get_object(LIB.get_data(h))
        if isinstance(o, unreal.SkeletalMeshComponent):
            print("OUTFIT_COMPPP", bp.get_name(), o.get_name(), "disable_pp", o.get_editor_property("disable_post_process_blueprint"),
                  "anim", o.get_editor_property("anim_class"))
