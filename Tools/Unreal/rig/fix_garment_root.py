"""The garment skeletons' reference root carries scale 100 (how the rigs were first imported); the new takes keyed
root at scale 1, which shrinks the whole garment 100x (invisible in battle). Drop the root track so root takes the
reference transform. Idempotent.
  $env:FOA_AREAS='Characters'; python Tools/Unreal/ue_remote.py Tools/Unreal/rig/fix_garment_root.py"""
import unreal

E = unreal.EditorAssetLibrary
done = []
for g, att in (("Shirt", "Lash"), ("Trousers", "Kick"), ("Sock", "Hop"), ("Tie", "CoilStrike")):
    for t in ("Idle", "Telegraph", att, "HitReact", "Stun", "Defeat"):
        p = f"/Game/FoA/Characters/Garments/SK_Garment_{g}Armature_{t}"
        a = unreal.load_asset(p)
        c = a.get_editor_property("controller")
        names = [str(n) for n in a.get_editor_property("data_model").get_bone_track_names()] if hasattr(a.get_editor_property("data_model"), "get_bone_track_names") else None
        c.open_bracket("Drop root track", False)
        c.remove_bone_track("root", False)
        c.close_bracket(False)
        E.save_loaded_asset(a, False)
        done.append(t)
    print("ROOT_FIX", g, done[-6:])
AP = unreal.AnimPoseExtensions
a = unreal.load_asset("/Game/FoA/Characters/Garments/SK_Garment_ShirtArmature_Idle")
pose = AP.get_anim_pose_at_time(a, 0.0, unreal.AnimPoseEvaluationOptions())
print("ROOT_FIX check shirt idle root scale", AP.get_bone_pose(pose, "root", unreal.AnimPoseSpaces.LOCAL).scale3d)
