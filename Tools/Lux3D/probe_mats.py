"""Read-only: texture count and parent of materials (FOA_ASSETS comma list); who in the level uses each."""
import os
import unreal

OUT = open('P:/FoA/Saved/WorldShots/probe_mats.txt', 'w')

MEL = unreal.MaterialEditingLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
paths = [p for p in os.environ['FOA_ASSETS'].split(',') if p]
users = {p: [] for p in paths}
for a in EAS.get_all_level_actors():
    for c in a.get_components_by_class(unreal.MeshComponent):
        for i in range(c.get_num_materials()):
            m = c.get_material(i)
            for p in paths:
                if m and m.get_path_name().split('.')[0] == p:
                    users[p].append(f'{a.get_actor_label()}.{c.get_name()}[{i}]')
for p in paths:
    m = unreal.load_asset(p)
    tex = [t.get_name() for t in MEL.get_material_used_textures(m)]
    parent = m.get_editor_property('parent').get_name() if isinstance(m, unreal.MaterialInstance) else '-'
    print(p.rsplit('/', 1)[1], 'parent', parent, 'tex', tex, 'users', len(users[p]), users[p], file=OUT)
OUT.close()
