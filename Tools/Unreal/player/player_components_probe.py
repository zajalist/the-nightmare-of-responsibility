"""Read-only: BP_FoAPlayer's skeletal-mesh components (name, parent, mesh, anim class, anim mode, visible, hidden in game),
to find which one is the visible teen in the wake cinematic.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/player_components_probe.py FOA_AREAS=Characters"""
import json

import unreal

bp = unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
rows = []
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    d = lib.get_data(h)
    c = lib.get_object_for_blueprint(d, bp)
    if not isinstance(c, unreal.SkinnedMeshComponent):
        continue
    par = c.get_attach_parent()
    mesh = c.get_skinned_asset() if hasattr(c, 'get_skinned_asset') else None
    anim = c.get_editor_property('anim_class') if isinstance(c, unreal.SkeletalMeshComponent) else None
    rows.append(dict(name=str(lib.get_variable_name(d)), type=type(c).__name__, mesh=mesh.get_name() if mesh else None,
                     anim=anim.get_name() if anim else None, visible=c.get_editor_property('visible'),
                     hidden_in_game=c.get_editor_property('hidden_in_game'),
                     leader=c.get_editor_property('leader_pose_component').get_name() if c.get_editor_property('leader_pose_component') else None))
open('P:/FoA/Saved/AnimShots/player_components.json', 'w').write(json.dumps(rows, indent=1))  # ue_remote cuts long output
print('PLAYER_COMP', len(rows), 'rows -> Saved/AnimShots/player_components.json')
