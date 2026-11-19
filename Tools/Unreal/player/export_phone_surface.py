"""Read the placed phone's native triangle surface under an owned editor lease."""
import json
import sys
from pathlib import Path
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
import hand_engine_probe
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
phone = unreal.GameplayStatics.get_actor_of_class(world,unreal.load_class(None,'/Game/FoA/UI/Game/BP_Phone.BP_Phone_C'))
data = hand_engine_probe.surface(phone.get_component_by_class(unreal.StaticMeshComponent))
Path('P:/FoA/Saved/AnimShots/review/phone_surface.json').write_text(json.dumps(data))
print('PHONE_SURFACE',len(data['positions']),len(data['triangles']))
