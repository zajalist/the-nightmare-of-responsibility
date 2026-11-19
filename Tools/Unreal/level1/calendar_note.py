"""level1 lane, round 3: an optional discovery that rewards curiosity, with no new art or panel. The Lux3D wall calendar
by the door (October, seventeen days crossed out) becomes something he can look at; the lines answer the intro card
("Seventeen days. Not that anyone's counting."): it is Mom who keeps the count now.
  rows     DT_Interactions gains two rows for InteractionKey Calendar (Look and Use, no state change, no event, no
           montage). Every other row is kept as it is (export, append, re-import, read back).
  convert  Dress_Lux3D_Calendar (a dressing StaticMeshActor, not one of the user's hand-placed pieces) becomes a
           BP_Interactable with the same label, folder, transform, mesh and materials (place_bedroom.py's convert
           pattern). Its page decal plane (Dress_Lux3D_Calendar_Page) is untouched.
Idempotent.  FOA_STEP=rows|convert  FOA_AREAS=Gameplay FOA_ACTORS=Dress_Lux3D_Calendar python Tools/Unreal/ue_remote.py Tools/Unreal/level1/calendar_note.py"""
import json
import os

import unreal

KEY = 'Calendar'
ROWS = [
    ('900_Calendar_None_Look_None', 'Look', 'Look at the calendar', "Seventeen crosses. Mom does the crosses now."),
    ('901_Calendar_None_Use_None', 'Use', 'Count the days', "Seventeen. Not that anyone's counting."),
]


def step_rows():
    dt = unreal.load_asset('/Game/FoA/Gameplay/DT_Interactions')
    rows = json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(dt))
    kept = [r for r in rows if r['Interactable'] != KEY]
    tpl = next(r for r in rows if r['Name'] == '014_Boot_R_None_Look_None')
    new = [dict(tpl, Name=name, Interactable=KEY, State='None', Verb=verb, Item='None', Requires='None', NextState='None',
                Prompt=prompt, Line=line, Give='None', Event='None', Montage='None') for name, verb, prompt, line in ROWS]
    assert unreal.DataTableFunctionLibrary.fill_data_table_from_json_string(dt, json.dumps(kept + new)), 'import failed'
    back = json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(dt))
    assert len(back) == len(kept) + len(new), (len(back), len(kept), len(new))
    assert sum(1 for r in back if r['Interactable'] == KEY) == len(ROWS)
    assert unreal.EditorAssetLibrary.save_loaded_asset(dt, False)
    print('ROWS', len(back), 'calendar', [r['Name'] for r in back if r['Interactable'] == KEY])


def step_convert():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
    a = acts['Dress_Lux3D_Calendar']
    cls = unreal.load_class(None, '/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C')
    if a.get_class() != unreal.StaticMeshActor.static_class():
        a.set_editor_property('InteractionKey', unreal.Name(KEY))
        print('CONVERT kept', a.get_class().get_name())
        return
    smc = a.static_mesh_component
    world, folder, mesh, mats = a.get_actor_transform(), a.get_folder_path(), smc.static_mesh, list(smc.get_materials())
    eas.destroy_actor(a)
    new = eas.spawn_actor_from_class(cls, world.translation, world.rotation.rotator())
    new.set_actor_transform(world, False, True)
    m = next(c for c in new.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == 'Mesh')
    m.set_static_mesh(mesh)
    for i, mat in enumerate(mats):
        m.set_material(i, mat)
    m.set_relative_transform(unreal.Transform(), False, True)
    new.set_actor_label('Dress_Lux3D_Calendar')
    new.set_folder_path(folder)
    new.set_editor_property('InteractionKey', unreal.Name(KEY))
    o, e, _ = unreal.SystemLibrary.get_component_bounds(m)
    print('CONVERT', new.get_class().get_name(), [round(v) for v in o.to_tuple()], [round(v) for v in e.to_tuple()],
          'collision', str(m.get_collision_enabled()), 'mesh', mesh.get_name())


{'rows': step_rows, 'convert': step_convert}[os.environ['FOA_STEP']]()
