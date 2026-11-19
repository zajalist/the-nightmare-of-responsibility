"""L_L2_DreamTest, the Level 2 Dream A scratch map (world lane). Runs only inside the map-switch procedure of
docs/agents/editor-rules.md (one EXCLUSIVE hold: dirty check, open, work, reopen the bedroom, verify, release):
  python Tools/Unreal/integration/run_read.py Tools/Splats/l2_dream_map.py FOA_L2MAP=count|open|build|back
count  prints the open map's actor count and whether Encounter_T8, a BP_BeatDirector and a PlayerStart are in it
open   opens the test map (creates it, blank, the first time)
build  fills the open test map, re-run safe: DreamA_Splats (SM_DreamA, M_SplatWorld_Lean), DreamA_Sky (M_L2_PanoSky on
       a 200 m sphere with the procedural dark atmosphere), L2_Post (manual exposure, nothing else), L2_Cam, a PlayerStart, GameModeBase (no FoA flow); saves it
back   reopens L_Tutorial_Bedroom"""
import os

import unreal

WORLD = os.environ.get('FOA_L2WORLD', 'dream')   # dream: L_L2_DreamTest, city: L_L2_CityTest (Toronto, Queen St)
MAP = {'dream': '/Game/FoA/Level2/Maps/L_L2_DreamTest', 'city': '/Game/FoA/Level2/Maps/L_L2_CityTest'}[WORLD]
CITY_SRC = 'P:/FoA-Assets/level2/toronto/processed/queen_600m'
CITY_CAM_Z = 5000.0   # top-down rig: 50 m up with a 90 deg lens frames about 100 m (splat_feasibility.md: ~8 cm/px)
BEDROOM = '/Game/FoA/Maps/L_Tutorial_Bedroom'
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
STEP = os.environ['FOA_L2MAP']


def current():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name().split('.')[0]


def count():
    acts = EAS.get_all_level_actors()
    labels = {a.get_actor_label() for a in acts}
    classes = {a.get_class().get_name() for a in acts}
    print('L2MAP count', current(), len(acts), 'enc', 'Encounter_T8' in labels,
          'beat', any(c.startswith('BP_BeatDirector') for c in classes), 'ps', 'PlayerStart' in classes)


def actor(label, cls, loc, rot=(0.0, 0.0, 0.0)):
    old = [a for a in EAS.get_all_level_actors() if a.get_actor_label() == label]
    a = old[0] if old else EAS.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))
    a.set_actor_label(label)
    a.set_actor_location(unreal.Vector(*loc), False, False)
    return a


def mesh_actor(label, mesh, mat, scale):
    a = actor(label, unreal.StaticMeshActor, (0.0, 0.0, 0.0))
    c = a.static_mesh_component
    c.set_static_mesh(unreal.load_asset(mesh))
    c.set_material(0, unreal.load_asset(mat))
    c.set_editor_property('cast_shadow', False)
    c.set_collision_profile_name('NoCollision')
    a.set_actor_scale3d(unreal.Vector(scale, scale, scale))


def build():
    assert current() == MAP, current()
    splat_mat='/Game/FoA/Level2/M_SplatWorld_Aniso' if unreal.EditorAssetLibrary.does_asset_exist('/Game/FoA/Level2/M_SplatWorld_Aniso') else '/Game/FoA/Level2/M_SplatWorld_Lean'
    mesh_actor('DreamA_Splats', '/Game/FoA/Level2/Dream/SM_DreamA/StaticMeshes/SM_DreamA', splat_mat, 1.0)
    mesh_actor('DreamA_Sky', '/Engine/BasicShapes/Sphere', '/Game/FoA/Level2/Dream/M_L2_PanoSky', 200.0)
    pp = actor('L2_Post', unreal.PostProcessVolume, (0.0, 0.0, 0.0))
    pp.set_editor_property('unbound', True)
    s = pp.get_editor_property('settings')
    for k, v in (('override_auto_exposure_method', True), ('auto_exposure_method', unreal.AutoExposureMethod.AEM_MANUAL),
                 ('override_auto_exposure_apply_physical_camera_exposure', True), ('auto_exposure_apply_physical_camera_exposure', False),
                 ('override_auto_exposure_bias', True), ('auto_exposure_bias', 0.0)):
        s.set_editor_property(k, v)
    pp.set_editor_property('settings', s)
    cam = actor('L2_Cam', unreal.CameraActor, (0.0, 0.0, 160.0))
    cam.camera_component.set_editor_property('field_of_view', 90.0)
    actor('PlayerStart', unreal.PlayerStart, (0.0, 0.0, 100.0))
    ws = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
    ws.set_editor_property('default_game_mode', unreal.GameModeBase.static_class())
    LES.save_current_level()
    print('L2MAP built', [a.get_actor_label() for a in EAS.get_all_level_actors()])


def build_city():
    """514 splat parts at their manifest positions, the 4K ground on a 600 m plane at the median ground height, a
    top-down L2_Cam over the start of the drive, manual exposure, GameModeBase. Re-run safe; saves the map."""
    import json
    assert current() == MAP, current()
    have = {a.get_actor_label(): a for a in EAS.get_all_level_actors()}
    mf = json.load(open(f'{CITY_SRC}/manifest.json'))
    placed = 0
    for e in mf['meshes']:
        sm = unreal.load_asset(f"/Game/FoA/Level2/City/Meshes/{e['name']}/StaticMeshes/{e['name']}")
        if not sm:
            continue
        a = have.get('City_' + e['name']) or EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*e['actor_location_cm']))
        a.set_actor_label('City_' + e['name'])
        a.set_actor_location(unreal.Vector(*e['actor_location_cm']), False, False)
        c = a.static_mesh_component
        c.set_static_mesh(sm)
        c.set_editor_property('cast_shadow', False)
        c.set_collision_profile_name('NoCollision')
        a.set_folder_path('City')
        placed += 1
    g = actor('City_Ground', unreal.StaticMeshActor, (30000.0, 0.0, (89.41 - mf['z_origin_m']) * 100.0))
    g.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
    g.static_mesh_component.set_material(0, unreal.load_asset('/Game/FoA/Level2/City/M_City_Ground'))
    g.set_actor_scale3d(unreal.Vector(600.0, 600.0, 1.0))
    pp = actor('L2_Post', unreal.PostProcessVolume, (0.0, 0.0, 0.0))
    pp.set_editor_property('unbound', True)
    st = pp.get_editor_property('settings')
    for k, v in (('override_auto_exposure_method', True), ('auto_exposure_method', unreal.AutoExposureMethod.AEM_MANUAL),
                 ('override_auto_exposure_apply_physical_camera_exposure', True), ('auto_exposure_apply_physical_camera_exposure', False),
                 ('override_auto_exposure_bias', True), ('auto_exposure_bias', 0.0)):
        st.set_editor_property(k, v)
    pp.set_editor_property('settings', st)
    cam = actor('L2_Cam', unreal.CameraActor, (5000.0, 0.0, CITY_CAM_Z), (-89.9, 0.0, 0.0))
    cam.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=-89.9, yaw=0.0), False)
    cam.camera_component.set_editor_property('field_of_view', 90.0)
    cam.camera_component.set_editor_property('constrain_aspect_ratio', False)   # no letterbox bars in the stills
    actor('PlayerStart', unreal.PlayerStart, (5000.0, 0.0, 200.0))
    ws = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
    ws.set_editor_property('default_game_mode', unreal.GameModeBase.static_class())
    LES.save_current_level()
    print('L2MAP city built', placed, 'parts of', len(mf['meshes']))


if STEP == 'count':
    count()
elif STEP == 'open':
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        LES.load_level(MAP)
    else:
        LES.new_level(MAP)
    print('L2MAP open', current())
elif STEP == 'build':
    build_city() if WORLD == 'city' else build()
elif STEP == 'back':
    LES.load_level(BEDROOM)
    print('L2MAP back', current())
