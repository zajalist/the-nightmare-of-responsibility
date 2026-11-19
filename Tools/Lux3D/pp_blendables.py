"""PP_DreamMono blendables, detach/restore around a post-process material rebuild (editor rule: never recompile a PP
material while it is an active blendable). FOA_PP=detach saves the current array to Saved/WorldShots/pp_blendables.json
and removes the materials named in FOA_PP_NAMES; FOA_PP=restore writes the saved array back exactly (weights included).
  $env:FOA_ACTORS='PP_DreamMono'; python Tools/Unreal/ue_remote.py Tools/Lux3D/pp_blendables.py FOA_PP=detach FOA_PP_NAMES=M_PP_DreamMono,M_PP_DreamLens"""
import json
import os

import unreal

SAVE = 'P:/FoA/Saved/WorldShots/pp_blendables.json'
a = [x for x in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if x.get_actor_label() == 'PP_DreamMono'][0]
s = a.get_editor_property('settings')
wb = s.get_editor_property('weighted_blendables')
cur = [(w.object.get_path_name() if w.object else None, w.weight) for w in wb.array]
if os.environ['FOA_PP'] == 'detach':
    json.dump(cur, open(SAVE, 'w'), indent=1)
    drop = set(os.environ['FOA_PP_NAMES'].split(','))
    keep = [w for w in wb.array if not (w.object and w.object.get_name() in drop)]
    wb.set_editor_property('array', keep)
else:   # put back only what detach removed, at its old index; anything another lane changed meanwhile stays
    saved = json.load(open(SAVE))
    mine = set(os.environ.get('FOA_PP_NAMES', 'M_PP_DreamMono,M_PP_DreamLens').split(','))   # only what detach took
    arr = list(wb.array)
    have = {w.object.get_path_name() for w in arr if w.object}
    for i, (p, wt) in enumerate(saved):
        if p and p not in have and p.rsplit('.', 1)[-1] in mine:
            arr.insert(min(i, len(arr)), unreal.WeightedBlendable(weight=wt, object=unreal.load_asset(p)))
    wb.set_editor_property('array', arr)
s.set_editor_property('weighted_blendables', wb)
a.set_editor_property('settings', s)
print(os.environ['FOA_PP'], 'before', [(p.rsplit('.', 1)[-1] if p else None, wt) for p, wt in cur],
      'after', [(w.object.get_name() if w.object else None, w.weight) for w in a.get_editor_property('settings').get_editor_property('weighted_blendables').array])
