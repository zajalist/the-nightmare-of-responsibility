"""Place BP_Phone (the diegetic phone) face up on the nightstand, once: BP_BeatDirector's ShowPhone beats (T0, T10) open it
through BP_FoAFrontEnd.OpenPhone, which finds it with GetActorOfClass. Re-runs move the existing one. Env FOA_PHONE_POSE
= "x,y,z,yaw" (the phone lies screen up: roll 180, because SM_Phone's screen is its -Z face)."""
import os
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cls = unreal.load_class(None, '/Game/FoA/UI/Game/BP_Phone.BP_Phone_C')
x, y, z, yaw = (float(v) for v in os.environ.get('FOA_PHONE_POSE', '338,-52,80.22,200').split(','))
loc, rot = unreal.Vector(x, y, z), unreal.Rotator(roll=180.0, pitch=0.0, yaw=yaw)
found = [a for a in eas.get_all_level_actors() if a.get_class() == cls]
a = found[0] if found else eas.spawn_actor_from_class(cls, loc, rot)
a.set_actor_label('Phone_Nightstand')
a.set_folder_path('Gameplay/Phone')
a.set_actor_location_and_rotation(loc, rot, False, False)
# A placed override must not push the player when this prop follows his hand.
a.get_editor_property('Mesh').set_collision_profile_name('NoCollision')
assert str(a.get_editor_property('Mesh').get_collision_profile_name()) == 'NoCollision'
p, r = a.get_actor_location(), a.get_actor_rotation()
print('phone', a.get_actor_label(), round(p.x, 1), round(p.y, 1), round(p.z, 2), round(r.pitch), round(r.yaw), round(r.roll), 'existing' if found else 'new')
