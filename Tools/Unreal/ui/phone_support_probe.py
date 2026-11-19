"""Phone grasp cameras and render-surface readback; test runtime only."""
import unreal,os,json
from pathlib import Path
phase=os.environ.get('PHONE_PHASE','read')
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if phase=='clear_failed_proof':
 assert not w,'Never clear a live proof context'
 for name in ('_foa_support_lens','_foa_phone_progress_restore','_foa_phone_long_restore'):
  if hasattr(unreal,name):delattr(unreal,name)
 unreal.GameplayStatics.delete_game_in_slot('FoA_QA_PhoneLayout',0)
else:assert w
klass=unreal.load_class(None,'/Game/FoA/UI/Game/BP_Phone.BP_Phone_C');phone=unreal.GameplayStatics.get_actor_of_class(w,klass) if w else None
if phase in ('support_side','support_back'):
 frame=phone.get_actor_transform();camera=phone.get_editor_property('PhoneCam')
 local=unreal.Vector(-10,25,-27) if phase=='support_side' else unreal.Vector(-14,20,24)
 location=unreal.MathLibrary.transform_location(frame,local);target=unreal.MathLibrary.transform_location(frame,unreal.Vector(-8,2,-2))
 camera.set_world_location_and_rotation(location,unreal.MathLibrary.find_look_at_rotation(location,target),False,False)
 if not hasattr(unreal,'_foa_support_lens'):unreal._foa_support_lens=(camera.get_editor_property('focus_settings'),camera.get_editor_property('current_aperture'))
 focus=unreal.CameraFocusSettings();focus.set_editor_property('focus_method',unreal.CameraFocusMethod.MANUAL);focus.set_editor_property('manual_focus_distance',(target-location).length());focus.set_editor_property('smooth_focus_changes',False)
 camera.focus_settings=focus;camera.current_aperture=8.
if phase in ('restore_contact','cleanup') and hasattr(unreal,'_foa_support_lens'):
 camera=phone.get_editor_property('PhoneCam');focus,aperture=unreal._foa_support_lens;camera.focus_settings=focus;camera.current_aperture=aperture;assert camera.focus_settings.export_text()==focus.export_text();assert camera.current_aperture==aperture;Path('P:/FoA/Saved/UIShots/phone_support_lens_restore.json').write_text(json.dumps(dict(focus_exact=True,aperture_exact=True,focus=focus.export_text(),aperture=aperture),indent=2));del unreal._foa_support_lens
if phase!='clear_failed_proof':exec(open('P:/FoA/Tools/Unreal/ui/phone_pie_probe.py').read())
if phase=='message':
 def xf(c):return c.get_world_transform().export_text()
 def material(m):
  if not m:return None
  base=m.get_base_material()
  return dict(path=m.get_path_name(),base=base.get_path_name(),blend=str(base.get_editor_property('blend_mode')))
 rows=[]
 for a in unreal.GameplayStatics.get_all_actors_of_class(w,klass):
  parts=[]
  for c in a.get_components_by_class(unreal.PrimitiveComponent):
   row=dict(name=c.get_name(),class_name=c.get_class().get_name(),visible=c.is_visible(),world=xf(c),materials=[material(c.get_material(i)) for i in range(c.get_num_materials())])
   if isinstance(c,unreal.WidgetComponent):row['draw_size']=list(c.get_draw_size().to_tuple());row['widget']=str(c.get_user_widget_object())
   parts.append(row)
  rows.append(dict(actor=a.get_path_name(),hidden=a.get_editor_property('bHidden'),parts=parts))
 Path('P:/FoA/Saved/UIShots/phone_support_scene.json').write_text(json.dumps(rows,indent=2))
