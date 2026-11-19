"""Read-only: member variables and function graphs of the Blueprints the world lane hooks into.
  $env:FOA_AREAS='VFX'; python Tools/Unreal/ue_remote.py Tools/Splats/world_probe_bps.py [WP_BPS=/Game/..,/Game/..]"""
import os
import unreal

OUT = open('P:/FoA/Saved/WorldShots/probe_bps.txt', 'w')
_print = print
print = lambda *a: _print(*a, file=OUT)  # noqa: E731  the transport truncates long output

BEL = unreal.BlueprintEditorLibrary
BPS = os.environ.get('WP_BPS', '/Game/FoA/PostProcess/BP_DreamDirector,/Game/FoA/Gameplay/GI_FoA,'
                     '/Game/FoA/Gameplay/BP_BeatDirector,/Game/FoA/Characters/Player/BP_Nightmare').split(',')
for path in BPS:
    bp = unreal.load_asset(path)
    if not bp:
        print('MISSING', path)
        continue
    cdo = unreal.get_default_object(bp.generated_class())
    vals = []
    for v in BEL.list_member_variable_names(bp):
        try:
            x = cdo.get_editor_property(str(v))
            s = str(x)
            vals.append(f'{v}={s[:60]}')
        except Exception:  # noqa: BLE001
            vals.append(str(v))
    print('==', path)
    print('  VARS', '; '.join(vals))
    print('  GRAPHS', [str(g) for g in BEL.list_graph_names(bp)])
OUT.close()
