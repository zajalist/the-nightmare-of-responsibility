"""Read-only dump of every hand-on-object anchor for the grip twins (anim lane, after the 2026-11-10 playtest): for each
interaction actor, its transform and every scene component (class, world transform, static mesh, its local and world
bounds, its sockets). Writes Saved/AnimShots/grip_anchors.json; the twins re-solve in place from it.
  FOA_AREAS=Level python Tools/Unreal/ue_remote.py Tools/Unreal/player/dump_grip_anchors.py"""
import json

import unreal

WANT = ("Door_Bedroom", "DoorFrame_Bedroom", "Commode", "Hanger_CoatRail", "Dress_CoatRail_Door", "Shirt_T7", "Boot_L", "Boot_R",
        "Bed", "Key_Lux3D", "Screwdriver_DeskDrawer", "Desk", "PlayerStart")


def xf(t):
    return dict(loc=[t.translation.x, t.translation.y, t.translation.z],
                quat=[t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w], scale=[t.scale3d.x, t.scale3d.y, t.scale3d.z])


def comp_info(c):
    try:
        return _comp_info(c)
    except Exception as e:  # one odd component must not lose the dump
        return dict(name=c.get_name(), cls=c.get_class().get_name(), error=repr(e))


def _comp_info(c):
    d = dict(name=c.get_name(), cls=c.get_class().get_name(), world=xf(c.get_world_transform()),
             rel=xf(c.get_relative_transform()), parent=c.get_attach_parent().get_name() if c.get_attach_parent() else None,
             visible=bool(c.is_visible()))
    if isinstance(c, unreal.StaticMeshComponent) and c.static_mesh:
        m = c.static_mesh
        b = m.get_bounding_box()
        d["mesh"] = m.get_path_name()
        d["local_box"] = [[b.min.x, b.min.y, b.min.z], [b.max.x, b.max.y, b.max.z]]
        o, e, _ = unreal.SystemLibrary.get_component_bounds(c)
        d["world_box"] = [[o.x - e.x, o.y - e.y, o.z - e.z], [o.x + e.x, o.y + e.y, o.z + e.z]]
        d["sockets"] = {str(n): xf(c.get_socket_transform(n, unreal.RelativeTransformSpace.RTS_WORLD))  # world (Sockets is protected)
                        for n in c.get_all_socket_names()}
    return d


out = {}
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    label = a.get_actor_label()
    if not any(label == w or label.startswith(w) for w in WANT):
        continue
    out[label] = dict(cls=a.get_class().get_name(), world=xf(a.get_actor_transform()),
                      comps=[comp_info(c) for c in a.get_components_by_class(unreal.SceneComponent)])
    for p in ("State", "InteractionKey", "Linked"):
        try:
            v = a.get_editor_property(p)
            out[label][p] = [x.get_actor_label() for x in v] if isinstance(v, unreal.Array) else str(v)
        except Exception:
            pass
path = unreal.Paths.project_saved_dir() + "AnimShots/grip_anchors.json"
with open(path, "w") as f:
    json.dump(out, f, indent=1)
print("GRIP_ANCHORS", len(out), "actors:", ", ".join(sorted(out)), "->", path)
