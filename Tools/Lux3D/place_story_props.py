"""Place the Lux3D story props (2026-11-09) as set dressing. Idempotent: finds each by label, spawns it once, then sets
the transform below (a re-run after a hand move would undo it, so re-run only before the user has touched them).
  $env:FOA_ACTORS_NEW='Dress_Lux3D_'; python Tools/Unreal/ue_remote.py Tools/Lux3D/place_story_props.py
GLBs are centred on their origin, so z = the surface + half the scaled height. Surfaces: desk top z 60 (Desk bounds),
floor 0, east wall inner face x 375. Each prop is checked against the interactables it must not cover
(Screwdriver_DeskDrawer x -350..-330 y 213-225 on the desk, RoomTakeover's desk clues (papers, button, dust) at
x -330..-310 y 180-196, the desk lamp base x -366..-318 y 101..167, the Stubbs painting y
-110..-10 and the door frame from y 30 on the east wall)."""
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL = unreal.EditorAssetLibrary
PROPS = [  # label, item, location, yaw, scale, height_cm (unscaled GLB)
    ('Dress_Lux3D_CoffeeMug', 'cold_coffee_mug', (-311.0, 150.0, 60.0), 200.0, (1.0, 1.0, 1.0), 9.5),
    ('Dress_Lux3D_Worksheets', 'worksheet_stack', (-362.0, 236.0, 60.0), 75.0, (0.6, 0.6, 0.25), 19.4),
    ('Dress_Lux3D_Backpack', 'school_backpack', (-262.0, 268.0, 0.0), 200.0, (0.75, 0.75, 0.75), 48.0),
    ('Dress_Lux3D_Calendar', 'wall_calendar', (373.4, 8.0, 150.0), -90.0, (1.4, 1.4, 1.4), 0.0),   # hung: z is its centre
]


def mesh_of(item):
    for p in EAL.list_assets(f'/Game/FoA/Lux3D/{item}', recursive=True, include_folder=False):
        a = EAL.load_asset(p)
        if isinstance(a, unreal.StaticMesh):
            return a
    return None


A = {a.get_actor_label(): a for a in EAS.get_all_level_actors()}
for label, item, (x, y, z), yaw, s, h in PROPS:
    m = mesh_of(item)
    if not m:
        print('not imported yet:', item)
        continue
    loc = unreal.Vector(x, y, z + h * s[2] / 2.0)
    a = A.get(label)
    if not a:
        a = EAS.spawn_actor_from_object(m, loc, unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw))
        a.set_actor_label(label)
        a.set_folder_path('Room/Dressing/Lux3D')
    a.set_actor_location(loc, False, False)
    a.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw), False)
    a.set_actor_scale3d(unreal.Vector(*s))
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    c.set_collision_profile_name('NoCollision' if item in ('wall_calendar', 'worksheet_stack', 'cold_coffee_mug') else 'BlockAll')
    o, e = a.get_actor_bounds(False)
    print(label, 'bottom z %.1f top z %.1f' % (o.z - e.z, o.z + e.z), 'xy %.0f..%.0f, %.0f..%.0f' % (o.x - e.x, o.x + e.x, o.y - e.y, o.y + e.y))
