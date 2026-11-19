"""qa lane, read-only: is there a navmesh in the editor world (the playtest walks on it when present)?"""
import unreal

w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
nav = [a.get_class().get_name() for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)
       if 'Nav' in a.get_class().get_name()]
print('nav actors', nav)
p = unreal.NavigationSystemV1.find_path_to_location_synchronously(w, unreal.Vector(200, 0, 90), unreal.Vector(-200, 100, 90))
print('path', p and [tuple(round(c) for c in v.to_tuple()) for v in p.path_points])
