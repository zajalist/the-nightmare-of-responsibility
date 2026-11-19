"""Story lane, read only: Spot_Hanger_WardrobeSide (QA S2: maybe the hanger's intended place after the fall) and who
references it. -> Saved/StoryShots/spot_hanger.json"""
import json
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = {}
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if 'Spot_Hanger' in lab or 'Hanger' in lab:
        out[lab] = dict(cls=a.get_class().get_name(), loc=a.get_actor_location().to_tuple(), rot=a.get_actor_rotation().to_tuple(),
                        folder=str(a.get_folder_path()), tags=[str(t) for t in a.tags])
d = next(a for a in eas.get_all_level_actors() if a.get_class().get_name() == 'BP_BeatDirector_C')
refs = {}
for p in ('HangerSpot', 'HangerFallSpot', 'SpotHanger', 'HangerWardrobeSide'):
    try:
        v = d.get_editor_property(p)
        refs[p] = v.get_actor_label() if v else None
    except Exception:  # noqa: BLE001
        pass
out['_director_refs'] = refs
out['_director_label'] = d.get_actor_label()
open('P:/FoA/Saved/StoryShots/spot_hanger.json', 'w').write(json.dumps(out, indent=1, default=str))
