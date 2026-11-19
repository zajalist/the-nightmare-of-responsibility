"""Prints transform plus mesh-local and world bounds for actors (Hayba's bounds tools are blocked by its Python policy).
  python Tools/Unreal/ue_remote.py Tools/Unreal/probe_bounds.py FOA_LABELS=Door_Bedroom,Bed"""
import os

import unreal

labels = {s.strip() for s in os.environ.get("FOA_LABELS", "").split(",") if s.strip()}
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_actor_label() not in labels:
        continue
    l, r, s = a.get_actor_location(), a.get_actor_rotation(), a.get_actor_scale3d()
    origin, extent = a.get_actor_bounds(False)
    line = (f"{a.get_actor_label()} loc=({l.x:.1f},{l.y:.1f},{l.z:.1f}) rot(p,y,r)=({r.pitch:.1f},{r.yaw:.1f},{r.roll:.1f}) "
            f"scale=({s.x:.3f},{s.y:.3f},{s.z:.3f}) world_min=({origin.x - extent.x:.1f},{origin.y - extent.y:.1f},{origin.z - extent.z:.1f}) "
            f"world_max=({origin.x + extent.x:.1f},{origin.y + extent.y:.1f},{origin.z + extent.z:.1f})")
    if isinstance(a, unreal.StaticMeshActor) and a.static_mesh_component.static_mesh:
        box = a.static_mesh_component.static_mesh.get_bounding_box()
        line += (f" mesh={a.static_mesh_component.static_mesh.get_path_name()} local_min=({box.min.x:.1f},{box.min.y:.1f},{box.min.z:.1f})"
                 f" local_max=({box.max.x:.1f},{box.max.y:.1f},{box.max.z:.1f})")
    print(line)
