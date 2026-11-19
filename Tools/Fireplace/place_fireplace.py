"""Places (or re-seats) the fireplace in the open level and saves it. Idempotent; never touches other lanes' actors.

  python Tools/Unreal/ue_remote.py Tools/Fireplace/place_fireplace.py

All parts share one pivot: the chimney-breast face centre on the floor, world (-330, 0, 0), yaw 0.
Surround and hearth block (simple box collision on the mesh); insert, firebox and coal are NoCollision.
Replaces the old greybox firebox back. (The trim lane's Trim_Base_09a/b already stop at the plinths, |y| 67.5.)
"""
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
M = "/Game/FoA/Fireplace/Meshes/{0}/{0}/StaticMeshes/{0}"
PARTS = {"Fireplace_Surround": ("SM_FP_Surround", "BlockAll"), "Fireplace_Hearth": ("SM_FP_Hearth", "BlockAll"),
         "Fireplace_Insert": ("SM_FP_Insert", "NoCollision"), "Fireplace_Firebox": ("SM_FP_Firebox", "NoCollision"),
         "Fireplace_Coal": ("SM_FP_Coal", "NoCollision")}
PIVOT = unreal.Vector(-330.0, 0.0, 0.0)

by_label = {}
for a in EAS.get_all_level_actors():
    by_label.setdefault(a.get_actor_label(), []).append(a)

for label, (mesh, profile) in PARTS.items():
    sm = unreal.load_asset(M.format(mesh))
    if not sm:
        raise RuntimeError("missing mesh " + mesh)
    actor = (by_label.get(label) or [None])[0]
    if actor is None:
        actor = EAS.spawn_actor_from_class(unreal.StaticMeshActor, PIVOT, unreal.Rotator(0.0, 0.0, 0.0))
        actor.set_actor_label(label)
    actor.set_actor_location_and_rotation(PIVOT, unreal.Rotator(0.0, 0.0, 0.0), False, False)
    actor.set_folder_path("Room/Chimney")
    smc = actor.static_mesh_component
    smc.set_static_mesh(sm)
    smc.set_collision_profile_name(profile)
    smc.set_editor_property("cast_shadow", True)
    print("placed", label, profile)

for a in by_label.get("Chimney_FireboxBack", []):  # superseded by SM_FP_Firebox
    EAS.destroy_actor(a)
    print("deleted Chimney_FireboxBack")
print("level saved", LES.save_current_level())
