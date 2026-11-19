"""Destroy level actors by exact label (cleanup of TMP actors). FOA_ACTORS=<label>,<label>; the run must hold
actor leases on those labels: pass the same list as FOA_ACTORS (leases) and FOA_DELETE (targets). Prints what it removed."""
import os
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
want = set(filter(None, (os.environ.get("FOA_DELETE") or os.environ.get("FOA_ACTORS", "")).split(",")))  # ue_remote keeps FOA_ACTORS for the leases
gone = []
for a in eas.get_all_level_actors():
    if a.get_actor_label() in want:
        gone.append(a.get_actor_label())
        eas.destroy_actor(a)
print("FOA_DELETED", gone, "missing", sorted(want - set(gone)))
