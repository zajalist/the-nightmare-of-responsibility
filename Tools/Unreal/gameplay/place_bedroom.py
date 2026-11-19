"""Turns the bedroom's props into T2-T6 interactables, keeping every mesh, material and world transform.
  python Tools/Unreal/ue_remote.py Tools/Unreal/gameplay/place_bedroom.py FOA_STEP=import|probe|convert
import   brings in the CC0 Poly Haven screwdriver (P:/FoA-Assets/polyhaven/models/screwdriver) once.
probe    prints the meshes' bounds and collision this script relies on.
convert  replaces each StaticMeshActor by its Blueprint, re-pivots hinges, sets Poses, Carried and Linked, adds the
         screwdriver (on the desk) and the wire hanger (on the coat rail by the door). Rerunnable: converted actors
         are skipped, placed ones are moved back into place. Save the level afterwards (Hayba level_save)."""
import os

import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL = unreal.EditorAssetLibrary
D = "/Game/FoA/Gameplay"
SCREW = "/Game/FoA/Props/screwdriver"
HANGER_MESH = "/Game/FoA/Lux3D/wire_hanger/SM_Lux3D_WireHanger"
SHIRT_MESH = "/Game/FoA/Lux3D/the_shirt_enemy/SM_Lux3D_ShirtEnemy"
V, R, X = unreal.Vector, unreal.Rotator, unreal.Transform


def cls(name):
    return unreal.load_asset(f"{D}/{name}").generated_class()


def actors():
    return {a.get_actor_label(): a for a in EAS.get_all_level_actors()}


def comp(actor, name):
    for c in actor.get_components_by_class(unreal.SceneComponent):
        if c.get_name() == name:
            return c
    raise KeyError(f"{actor.get_actor_label()} has no component {name}")


def setp(actor, **props):
    import re
    for k, v in props.items():
        try:
            actor.set_editor_property(k, v)
        except Exception:  # Python may expose Blueprint variables under snake_case names
            actor.set_editor_property(re.sub(r"(?<!^)(?=[A-Z])", "_", k).lower(), v)


def rot(yaw=0.0, pitch=0.0, roll=0.0):
    return R(roll=roll, pitch=pitch, yaw=yaw)


def spawn(cls_name, label, folder, mesh, mats, world, pivot=None):
    """A Blueprint interactable whose Mesh lands exactly on `world`; the actor origin sits at `pivot` (a hinge)."""
    rotation = world.rotation.rotator()
    origin = X(location=pivot if pivot is not None else world.translation, rotation=rotation)
    a = EAS.spawn_actor_from_class(cls(cls_name), origin.translation, rotation)
    a.set_actor_transform(origin, False, True)
    m = comp(a, "Mesh")
    m.set_static_mesh(mesh)
    for i, mat in enumerate(mats):
        m.set_material(i, mat)
    m.set_relative_transform(world.make_relative(origin), False, True)
    a.set_actor_label(label)
    a.set_folder_path(folder)
    return a


def convert(label, cls_name, pivot=None, **props):
    a = actors().get(label)
    assert a, f"no actor {label}"
    if a.get_class() != unreal.StaticMeshActor.static_class():
        setp(a, **props)  # already converted: only refresh its settings
        return a
    smc = a.static_mesh_component
    world, folder = a.get_actor_transform(), a.get_folder_path()
    mesh, mats = smc.static_mesh, list(smc.get_materials())
    EAS.destroy_actor(a)
    new = spawn(cls_name, label, folder, mesh, mats, world, pivot)
    setp(new, **props)
    return new


def bounds(a):
    """World box of the actor's static meshes only. Actor bounds would add a Blueprint's 128 cm editor sprite, and
    the colliding-only variant is empty for meshes without collision (the coat rail, a fresh import)."""
    lo, hi = None, None
    for m in a.get_components_by_class(unreal.StaticMeshComponent):
        o, e, _ = unreal.SystemLibrary.get_component_bounds(m)
        lo = o - e if lo is None else V(min(lo.x, o.x - e.x), min(lo.y, o.y - e.y), min(lo.z, o.z - e.z))
        hi = o + e if hi is None else V(max(hi.x, o.x + e.x), max(hi.y, o.y + e.y), max(hi.z, o.z + e.z))
    assert lo is not None, f"{a.get_actor_label()} has no static mesh"
    return lo, hi


def pose(yaw=0.0, pitch=0.0, roll=0.0, move=(0.0, 0.0, 0.0)):
    return X(location=V(*move), rotation=rot(yaw, pitch, roll))


def world_of(actor, local_pose, local_point):
    """Where a point (relative to the actor) ends up after the Pivot takes `local_pose`."""
    return actor.get_actor_transform().transform_location(local_pose.transform_location(local_point))


def screw_meshes():
    return [p for p in EAL.list_assets(SCREW, True, False)
            if "/StaticMeshes/" in p] if EAL.does_directory_exist(SCREW) else []


def step_import():
    """Interchange imports finish on later ticks, so `saveimport` (a separate run) saves the results."""
    if screw_meshes():
        print("screwdriver already imported", screw_meshes())
        return
    t = unreal.AssetImportTask()
    for k, v in (("filename", "P:/FoA-Assets/polyhaven/models/screwdriver/screwdriver_1k.gltf"),
                 ("destination_path", SCREW), ("automated", True), ("replace_existing", False), ("save", True)):
        t.set_editor_property(k, v)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    print("import started", EAL.list_assets(SCREW, True, False))


def step_saveimport():
    ok = EAL.save_directory(SCREW, only_if_is_dirty=True, recursive=True)
    print("saved screwdriver assets", ok, screw_meshes())


def step_probe():
    for p in [p for p in EAL.list_assets(SCREW, True, False) if "StaticMesh" in str(EAL.find_asset_data(p).asset_class_path)] \
            + [HANGER_MESH, "/Game/FoA/Props/GothicCabinet_01/GothicCabinet_01_1k/StaticMeshes/GothicCabinet_01_cabinet",
               "/Game/FoA/Lux3D/door_key/SM_Lux3D_DoorKey", SHIRT_MESH,
               "/Game/FoA/Props/Door/SM_Door_Bedroom"]:
        m = unreal.load_asset(p)
        b = m.get_bounds()
        geom = m.get_editor_property("body_setup").get_editor_property("agg_geom")
        n = {k: len(geom.get_editor_property(k)) for k in ("box_elems", "convex_elems", "sphyl_elems", "sphere_elems")}
        print(p, "origin", b.origin, "extent", b.box_extent, "collision", n,
              m.get_editor_property("body_setup").get_editor_property("collision_trace_flag"))


def step_convert():
    have = actors()
    # ---- the door: the leaf swings on the hinge it already pivots on ----
    door = convert("Door_Bedroom", "BP_Door", InteractionKey="Door", State="Locked")
    for yaw in (-95.0, 95.0):  # open into the room (towards -X)
        free = world_of(door, pose(yaw), V(0.0, -90.0, 100.0))
        if free.x < 370.0:
            setp(door, Poses={"Open": pose(yaw)})
            print("door opens with yaw", yaw, "free edge", free)
            break

    # ---- commode drawers slide 30 cm towards the room (-Y) ----
    for n in ("Commode_GothicCommode_01_door01", "Commode_GothicCommode_01_door02", "Commode_GothicCommode_01_door03"):
        d = convert(n, "BP_Container", InteractionKey="CommodeDrawer", State="Closed")
        out = d.get_actor_transform().inverse_transform_direction(V(0.0, -30.0, 0.0))
        setp(d, Poses={"Closed": pose(), "Open": pose(move=(out.x, out.y, out.z))})

    # ---- wardrobe doors swing out on their outer edges ----
    doors = []
    body_lo, body_hi = bounds(have["Wardrobe"])
    mid_x = (body_lo.x + body_hi.x) / 2
    for n in ("Wardrobe_GothicCabinet_01_door1", "Wardrobe_GothicCabinet_01_door2", "Wardrobe_GothicCabinet_01_door3",
              "Wardrobe_GothicCabinet_01_door4"):
        a = actors()[n]
        if a.get_class() == unreal.StaticMeshActor.static_class():
            lo, hi = bounds(a)
            right = (lo.x + hi.x) / 2 > mid_x
            hinge = V(hi.x if right else lo.x, lo.y, 0.0)
            free_x = lo.x if right else hi.x
            d = convert(n, "BP_Container", pivot=hinge, InteractionKey="WardrobeDoor", State="Closed")
        else:
            d = convert(n, "BP_Container")
            free_x = None
        if free_x is not None:
            for yaw in (100.0, -100.0):
                local = d.get_actor_transform().inverse_transform_location(V(free_x, lo.y, 150.0))
                if world_of(d, pose(yaw), local).y < lo.y - 30.0:
                    setp(d, Poses={"Closed": pose(), "Open": pose(yaw)})
                    break
        poses = dict(d.get_editor_property('Poses'))
        if unreal.Name('Closed') not in poses:
            poses['Closed'] = pose()
            setp(d, Poses=poses)
        doors.append(d)

    # ---- the wardrobe falls forward (-Y) about its front bottom edge, doors riding along ----
    w = actors()["Wardrobe"]
    front = min(bounds(a)[0].y for a in doors + [w])
    lo, hi = bounds(w)
    pivot = V((lo.x + hi.x) / 2, front, 0.0)
    if w.get_class() == unreal.StaticMeshActor.static_class():
        w = convert("Wardrobe", "BP_Topple", pivot=pivot)
    else:
        repivot(w, pivot)
    # the top edge of the front face: after a forward fall it should lie on the floor, about its height away
    top = w.get_actor_transform().inverse_transform_location(V(w.get_actor_location().x, w.get_actor_location().y,
                                                                bounds(w)[1].z))
    fallen = None
    for p in (pose(roll=-90.0), pose(roll=90.0), pose(pitch=-90.0), pose(pitch=90.0)):
        land = world_of(w, p, top)
        if land.y < w.get_actor_location().y - 150.0 and abs(land.z) < 15.0:
            fallen = p
            break
    assert fallen, "no fall pose lands the top towards the room"
    setp(w, InteractionKey="Wardrobe", State="Standing", Carried=doors,
         Poses={"Standing": X(), "Falling": fallen, "Fallen": fallen})
    print("wardrobe falls with", fallen.rotation.rotator(), "top lands at", world_of(w, fallen, top))

    # ---- boots, key, bed, desk ----
    key = convert("Key_Lux3D", "BP_Pickup", InteractionKey="Key", State="Hidden")
    left_boot = convert("Boot_L", "BP_Container", InteractionKey="Boot_L", State="Closed", Linked=[key])
    if 'BootProgressionSource' in [str(n) for n in unreal.BlueprintEditorLibrary.list_member_variable_names(unreal.load_asset(D + '/BP_Interactable'))]:
        setp(door, BootProgressionSource=left_boot)
    convert("Boot_R", "BP_Container", InteractionKey="Boot_R", State="Closed")
    convert("Bed", "BP_Interactable", InteractionKey="Bed", State="Idle")
    desk = convert("Desk", "BP_Interactable", InteractionKey="Desk", State="Idle")
    setp(actors()["Door_Bedroom"], Linked=[w])

    # ---- new pickups: the screwdriver on the desk, the wire hanger on the coat rail by the door ----
    folder = "Interactables/Items"
    spot = actors()["Spot_Screwdriver_DeskDrawer"].get_actor_location()
    desk_top = bounds(desk)[1].z
    screw_mesh = unreal.load_asset(screw_meshes()[0])
    sd = place("Screwdriver_DeskDrawer", "BP_Pickup", folder, screw_mesh, X(location=spot, rotation=rot(28.0, 90.0)),
               InteractionKey="Screwdriver", State="Available")
    rest_on(sd, desk_top)
    rail = actors()["Dress_CoatRail_Door"]
    rlo, rhi = bounds(rail)
    hanger_mesh = unreal.load_asset(HANGER_MESH)
    h = place("Hanger_CoatRail", "BP_Pickup", folder, hanger_mesh,
              X(location=V(rlo.x - 1.0, rlo.y + 0.72 * (rhi.y - rlo.y), rhi.z), rotation=rot(90.0)),
              InteractionKey="Hanger", State="Available")
    hang_from(h, rail)
    # T7 (mech_flow stages it with Interact Notify Open): the Lux3D shirt, hidden on the floor where the door moves to
    shirt = place("Shirt_T7", "BP_Pickup", folder, unreal.load_asset(SHIRT_MESH),
                  X(location=V(-318.0, -190.0, 40.0), rotation=rot(-90.0)), InteractionKey="Shirt", State="Hidden")
    rest_on(shirt, 0.0)
    for n in ("Door_Bedroom", "Wardrobe", "Screwdriver_DeskDrawer", "Hanger_CoatRail", "Key_Lux3D", "Shirt_T7"):
        a = actors()[n]
        lo, hi = bounds(a)
        print("PLACED", n, a.get_class().get_name(), "loc", a.get_actor_location(), "bounds", lo, hi)


def repivot(a, pivot):
    """Move the actor origin (the hinge) without moving its mesh."""
    m = comp(a, "Mesh")
    keep = m.get_world_transform()
    a.set_actor_location(pivot, False, True)
    m.set_world_transform(keep, False, True)


def place(label, cls_name, folder, mesh, world, **props):
    a = actors().get(label)
    if a is None:
        a = spawn(cls_name, label, folder, mesh, [], world)
    else:
        a.set_actor_transform(world, False, True)
        m = comp(a, "Mesh")
        if m.static_mesh != mesh:  # a reference lost when an unsaved import vanished in a restart
            m.set_static_mesh(mesh)
            m.set_relative_transform(X(), False, True)
    setp(a, **props)
    return a


def rest_on(a, z):
    """Drop the actor so its lowest point touches z (nothing floats)."""
    lo, _ = bounds(a)
    a.set_actor_location(a.get_actor_location() + V(0.0, 0.0, z - lo.z), False, True)


def hang_from(a, rail):
    """Hook the hanger's top over the rail's front edge: top 2 cm under the rail top, body clear of the wall."""
    lo, hi = bounds(a)
    rlo, rhi = bounds(rail)
    a.set_actor_location(a.get_actor_location() + V(rlo.x + 1.5 - hi.x, 0.0, rhi.z - 2.0 - hi.z), False, True)


def step_save():
    """Fallback when Hayba level_save is unavailable: save the open level (and its external actor packages)."""
    print("saved", unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level())


try:
    {"import": step_import, "saveimport": step_saveimport, "probe": step_probe, "convert": step_convert,
     "save": step_save}[os.environ.get("FOA_STEP", "probe")]()
except Exception:  # the Hayba transport truncates tracebacks; keep the whole one
    import traceback
    with open("P:/FoA/Saved/mech_core_last_error.txt", "w", encoding="utf-8") as fh:
        fh.write(traceback.format_exc())
    raise
