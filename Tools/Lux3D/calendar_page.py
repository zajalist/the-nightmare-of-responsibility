"""The exact-count calendar page on the Lux3D wall calendar (Dress_Lux3D_Calendar): MI_Lux3D_WallCalendar_Page (child of
MI_Lux3D_WallCalendar, base colour = T_Lux3D_WallCalendar_Page from make_calendar_page.py, 1K) on a thin plane attached
in front of the calendar's page. Idempotent. FOA_ROLL flips the plane if the texture reads mirrored or turned.
  $env:FOA_ACTORS='Dress_Lux3D_Calendar'; $env:FOA_ACTORS_NEW='Dress_Lux3D_Calendar_Page'
  python Tools/Unreal/ue_remote.py Tools/Lux3D/calendar_page.py"""
import os

import unreal

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ROOT = '/Game/FoA/Lux3D/wall_calendar'
MI = ROOT + '/MI_Lux3D_WallCalendar_Page'
TP = ROOT + '/T_Lux3D_WallCalendar_Page.T_Lux3D_WallCalendar_Page'
tex = unreal.find_object(None, TP) or unreal.load_object(None, TP)   # a fresh Hayba import may not be on disk yet
tex.set_editor_property('max_texture_size', 1024)
tex.set_editor_property('srgb', True)
EAL.save_loaded_asset(tex, only_if_is_dirty=False)
mi = EAL.load_asset(MI)
if not mi:
    mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset('MI_Lux3D_WallCalendar_Page', ROOT, unreal.MaterialInstanceConstant,
                                                                   unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property('parent', EAL.load_asset(ROOT + '/MI_Lux3D_WallCalendar'))
MEL.set_material_instance_texture_parameter_value(mi, 'BaseColorTexture', tex)
EAL.save_asset(MI, only_if_is_dirty=False)

A = {a.get_actor_label(): a for a in EAS.get_all_level_actors()}
cal = A['Dress_Lux3D_Calendar']
o, e = cal.get_actor_bounds(False)
front_x = o.x - e.x - 0.15                     # the calendar hangs on the east wall facing -X; 1.5 mm proud of its page
page = A.get('Dress_Lux3D_Calendar_Page')
if not page:
    page = EAS.spawn_actor_from_object(EAL.load_asset('/Engine/BasicShapes/Plane'), unreal.Vector(front_x, o.y, o.z))
    page.set_actor_label('Dress_Lux3D_Calendar_Page')
    page.set_folder_path('Room/Dressing/Lux3D')
roll = float(os.environ.get('FOA_ROLL', '-90'))
page.set_actor_location(unreal.Vector(front_x, o.y, o.z - 0.012 * e.z * 2), False, False)   # a touch low: the rings stay clear
page.set_actor_rotation(unreal.Rotator(roll=roll, pitch=0.0, yaw=90.0), False)   # U -> world +Y (viewer's right), normal -> -X
w = (e.y * 2) * 0.94 / 100.0
page.set_actor_scale3d(unreal.Vector(w, w * 0.97, 1.0))
c = page.get_component_by_class(unreal.StaticMeshComponent)
c.set_editor_property('override_materials', [mi])
c.set_editor_property('cast_shadow', False)
c.set_collision_profile_name('NoCollision')
page.attach_to_actor(cal, '', unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
po, pe = page.get_actor_bounds(False)
print('page at', [round(v, 1) for v in po.to_tuple()], 'ext', [round(v, 2) for v in pe.to_tuple()], 'calendar front x', round(front_x, 2))
