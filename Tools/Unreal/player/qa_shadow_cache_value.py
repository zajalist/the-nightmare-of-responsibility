"""Small fallback: this editor build does not register native editor_cvar_get/set."""
import unreal,json,os
from pathlib import Path
path=Path('P:/FoA/Saved/Integration/cinematic_audit/shadow_cache_value.json')
name='r.Shadow.Virtual.Cache';old=unreal.SystemLibrary.get_console_variable_int_value(name)
value=int(os.environ.get('FOA_SHADOW_VALUE','0'))
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(w,name+' '+str(value))
actual=unreal.SystemLibrary.get_console_variable_int_value(name);assert actual==value,(actual,value)
path.write_text(json.dumps(dict(prior=old,actual=actual)))
