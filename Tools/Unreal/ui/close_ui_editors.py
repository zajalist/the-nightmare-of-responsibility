"""Close asset editors for FOA_ASSETS (comma list) before Hayba edits them (an open editor overwrites Hayba's edits)."""
import os
import unreal

sub = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
for p in [s for s in os.environ.get('FOA_ASSETS', '').split(',') if s]:
    a = unreal.load_asset(p)
    if a:
        sub.close_all_editors_for_asset(a)
print('closed')
