"""Read-only (TMP actors, destroyed in the same run): attach parent, socket and relative transform of the head
components of BP_MHC_Protagonist and BP_FoAPlayer instances. Writes Saved/AnimShots/groom_xform.txt.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/groom_xform_probe.py FOA_ACTORS_NEW=TMP_anim_"""
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
L = []
for path in ("/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/BP_MHC_Protagonist", "/Game/FoA/Characters/Player/BP_FoAPlayer"):
    a = EAS.spawn_actor_from_class(unreal.EditorAssetLibrary.load_blueprint_class(path), unreal.Vector(0, 0, -2000), unreal.Rotator())
    a.set_actor_label("TMP_anim_Probe")
    try:
        for c in a.get_components_by_class(unreal.SceneComponent):
            n = c.get_name()
            if not any(k in n for k in ("Face", "Hair", "Eyebrows", "Body", "Mesh", "Root", "Collision", "Outfit", "Shirt")):
                continue
            p = c.get_attach_parent()
            r, l = c.get_editor_property("relative_rotation"), c.get_editor_property("relative_location")
            L.append(f"{path.split('/')[-1]:20s} {n:14s} parent={p.get_name() if p else None} socket={c.get_attach_socket_name()} "
                     f"loc=({l.x:.1f},{l.y:.1f},{l.z:.1f}) rot=(p{r.pitch:.1f},y{r.yaw:.1f},r{r.roll:.1f}) "
                     f"world_z={c.get_world_location().z + 2000:.1f}")
            if isinstance(c, unreal.SkinnedMeshComponent):
                lead = c.get_editor_property("leader_pose_component")
                L.append(f"    leader={lead.get_name() if lead else None} mesh={c.get_editor_property('skeletal_mesh_asset').get_name() if c.get_editor_property('skeletal_mesh_asset') else None} visible={c.is_visible()} anim={c.get_anim_instance().get_class().get_name() if c.get_anim_instance() else None}")
    finally:
        EAS.destroy_actor(a)
with open("P:/FoA/Saved/AnimShots/groom_xform.txt", "w") as f:
    f.write("\n".join(L) + "\n")
print(len(L))
