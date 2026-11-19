"""Read-only (TMP actors destroyed in the same run): runtime state of the Hair groom on a BP_FoAPlayer and a
BP_MHC_Protagonist instance: world transform, bounds, materials, attach chain. Writes Saved/AnimShots/groom_runtime.txt.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/groom_runtime_probe.py FOA_ACTORS_NEW=TMP_anim_"""
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
SL = unreal.SystemLibrary
L = []
made = []
try:
    for label, path, z in (("ours", "/Game/FoA/Characters/Player/BP_FoAPlayer", 90.0),
                           ("mh", "/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/BP_MHC_Protagonist", 0.0)):
        a = EAS.spawn_actor_from_class(unreal.EditorAssetLibrary.load_blueprint_class(path), unreal.Vector(0, 0, -3000 + z),
                                       unreal.Rotator())
        a.set_actor_label(f"TMP_anim_{label}")
        made.append(a)
        for g in a.get_components_by_class(unreal.GroomComponent):
            if not g.get_editor_property("groom_asset"):
                continue
            o, e, r = SL.get_component_bounds(g)
            t = g.get_world_transform()
            chain, c = [], g
            while c:
                chain.append(f"{c.get_name()}@{c.get_attach_socket_name()}")
                c = c.get_attach_parent()
            mats = [m.get_name() if m else None for m in g.get_materials()]
            L.append(f"{label} {g.get_name()} loc=({t.translation.x:.0f},{t.translation.y:.0f},{t.translation.z + 3000:.0f}) "
                     f"rot={t.rotation.rotator()} scale={t.scale3d} bounds_o=({o.x:.0f},{o.y:.0f},{o.z + 3000:.0f}) ext=({e.x:.0f},{e.y:.0f},{e.z:.0f}) "
                     f"visible={g.is_visible()} mats={mats} chain={' <- '.join(chain)}")
        for s in a.get_components_by_class(unreal.SkeletalMeshComponent):
            o, e, r = SL.get_component_bounds(s)
            lead = s.get_editor_property("leader_pose_component")
            L.append(f"{label} skm {s.get_name()} visible={s.is_visible()} lod={s.get_predicted_lod_level() if hasattr(s, 'get_predicted_lod_level') else '?'} "
                     f"bounds_o=({o.x:.0f},{o.y:.0f},{o.z + 3000:.0f}) ext=({e.x:.0f},{e.y:.0f},{e.z:.0f}) leader={lead.get_name() if lead else None}")
finally:
    for a in made:
        EAS.destroy_actor(a)
with open("P:/FoA/Saved/AnimShots/groom_runtime.txt", "w") as f:
    f.write("\n".join(L) + "\n")
print(len(L), "lines")
