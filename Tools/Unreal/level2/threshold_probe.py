"""Read-only transition integration survey, run inside the lane's lease."""
import json
from pathlib import Path
import unreal

def main():
    w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors=unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor)
    rows=[]
    for a in actors:
        if a.get_class().get_name() in ('BP_BeatDirector_C','BP_DreamDirector_C','BP_FoAPlayer_C') or a.get_actor_label()=='PP_DreamMono':
            row=dict(label=a.get_actor_label(),cls=a.get_class().get_name(),loc=a.get_actor_location().to_tuple())
            if a.get_class().get_name()=='BP_BeatDirector_C':
                for k in ('DoorFrame','Door'):
                    v=a.get_editor_property(k)
                    row[k]=dict(label=v.get_actor_label(),loc=v.get_actor_location().to_tuple(),rot=v.get_actor_rotation().to_tuple()) if v else None
            rows.append(row)
    mesh=unreal.load_asset('/Game/FoA/Level2/Dream/SM_DreamA/StaticMeshes/SM_DreamA')
    rows.append(dict(mesh_bounds=str(mesh.get_bounds())))
    out=Path('P:/FoA/Saved/Codex/dream_transition');out.mkdir(parents=True,exist_ok=True)
    (out/'integration_probe.json').write_text(json.dumps(rows,indent=2))
    mat=unreal.load_asset('/Game/FoA/Level2/M_SplatWorld_Lean')
    nodes=[n for n in unreal.ObjectIterator(unreal.MaterialExpressionCustom) if n.get_outer()==mat]
    snapshot={n.get_name():dict(Code=n.get_editor_property('code'),
              Inputs=[{'InputName':str(i.get_editor_property('input_name'))} for i in n.get_editor_property('inputs')]) for n in nodes}
    (out/'dream_material_snapshot.json').write_text(json.dumps(snapshot,indent=2))
    print(json.dumps(rows))
main()
