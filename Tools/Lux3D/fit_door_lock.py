"""Door_Bedroom's lock, props art pass (world lane): the Cube ToolPlate, Cube ToolKeyhole and Cylinder ToolScrew0-3 that
BP_Door's tool graph shows and hides become the Lux3D escutcheon plate and slotted screws, as per-instance component
overrides on the placed door (BP_Door's template is the gameplay lane's; its tool positions stay valid).
  $env:FOA_ACTORS='Door_Bedroom'; $env:FOA_AREAS='/Game/FoA/Props'; python Tools/Unreal/ue_remote.py Tools/Lux3D/fit_door_lock.py
Layout (door-local, cm): face of the door at x -0.475 (the old plate's back), plate centre (-, -84, 87.3): its keyhole
sits 0.35 cm under BP_Door's key point (z 87) and its holes 0.35 cm over the screw rows (z 91.5 / 82.5). The screw
positions are BP_Door's (y -86.1 / -81.9, z 91.5 / 82.5); the plate is scaled so its four holes land under them."""
import unreal

PLATE = '/Game/FoA/Props/DoorLock/SM_DoorLockPlate'
PLATE_MI = '/Game/FoA/Props/DoorLock/MI_DoorLockPlate'
SCREW = '/Game/FoA/Props/DoorLock/SM_DoorLockScrew'
SCREW_MI = '/Game/FoA/Props/DoorLock/MI_DoorLockScrew'
FACE = -0.475                    # the door's surface, door-local x (room side is -x)
SX, SD, SZ = 0.42, 0.20, 0.349   # plate 15 x 3.49 x 31.6 cm -> 6.3 wide, 0.7 deep, 11.0 tall: its holes 3.7 x 9.0 apart
SS = 0.42                        # screw 3.8 cm long, head 2.17 cm -> 0.9 cm head
HEAD_BACK = 0.42                 # the head underside sits this far (scaled) in front of the screw origin
# BP_Door's screw y (-86.1 / -81.9) sit 0.25 cm in, onto the holes; the screwdriver tip is that close (sub-pixel at the tool camera)
SCREWS = ((-85.85, 91.5), (-82.15, 91.5), (-85.85, 82.5), (-82.15, 82.5))

door = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
            if a.get_actor_label() == 'Door_Bedroom')


def part(name):
    """Fetched fresh for every property: each edit re-runs the door's construction script, which replaces the
    component (the old one becomes TRASH_*) and carries the edited value over as instance data."""
    return next(c for c in door.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == name)


plate_d = 3.49 * SD
front = FACE - plate_d                                           # the plate's front face


def put(name, prop, value):
    c = part(name)
    c.modify()
    c.set_editor_property(prop, value)


def fit(name, mesh, mi, loc, rot, scale):
    for prop, value in (('static_mesh', unreal.load_asset(mesh)), ('override_materials', [unreal.load_asset(mi)]),
                        ('relative_location', unreal.Vector(*loc)),
                        ('relative_rotation', unreal.Rotator(roll=rot[2], pitch=rot[0], yaw=rot[1])),
                        ('relative_scale3d', unreal.Vector(*scale)), ('cast_shadow', True)):
        put(name, prop, value)
    print('fit', part(name).get_name(), loc, rot, scale)


fit('ToolPlate', PLATE, PLATE_MI, (FACE - plate_d / 2, -84.0, 87.3), (0, 90, 0), (SX, SD, SZ))
for i, (y, z) in enumerate(SCREWS):
    fit(f'ToolScrew{i}', SCREW, SCREW_MI, (front + HEAD_BACK, y, z), (0, 0, 0), (SS, SS, SS))
# The plate has its own keyhole: the old black slot shrinks into it (BP_Door still toggles it with the plate).
put('ToolKeyhole', 'relative_location', unreal.Vector(front + 0.05, -84.0, 87.0))
put('ToolKeyhole', 'relative_scale3d', unreal.Vector(0.0002, 0.0002, 0.0002))
print('door lock fitted; save the level with editor_lock.py save_level world')
