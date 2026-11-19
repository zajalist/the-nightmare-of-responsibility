"""Read-only graph evidence and placed door camera overrides."""
import json,unreal
from pathlib import Path
root=Path('P:/FoA/Saved/Integration/outcome_handoff');root.mkdir(parents=True,exist_ok=True)
for path,names in [('/Game/FoA/UI/Game/BP_Phone',('OpenPhone','ClosePhone')),('/Game/FoA/UI/Framework/BP_FoAFrontEnd',('OpenPhone','ClosePhone')),('/Game/FoA/Gameplay/BP_BeatDirector',('PayoffLook','PayoffDone','ShowPhone','OpenTheDoor')),('/Game/FoA/Gameplay/Encounter/BP_Encounter',('CompleteWin','RestoreBattleView'))]:
    bp=unreal.load_asset(path)
    for name in names:
        if name in [str(n) for n in unreal.BlueprintEditorLibrary.list_graph_names(bp)]:
            (root/(path.rsplit('/',1)[1]+'_'+name+'.txt')).write_text(unreal.FoAGraphToolsLibrary.export_nodes_text(bp,name))
rows=[]
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_class().get_name()=='BP_Door_C':
        c=next(c for c in a.get_components_by_class(unreal.CameraComponent) if c.get_name()=='ToolCamera')
        rows.append(dict(actor=a.get_path_name(),label=a.get_actor_label(),camera=c.get_path_name(),location=str(c.get_editor_property('relative_location')),rotation=str(c.get_editor_property('relative_rotation'))))
(root/'door_camera_instances.json').write_text(json.dumps(rows,indent=1));print(rows)
