"""Short structural UE operations; city2_run.py owns leases and map-return guards."""
import json
import os
from pathlib import Path
import unreal
SRC=Path('P:/FoA-Assets/level2/toronto/processed/queen_1600m')
OUT=Path('P:/FoA/Saved/Codex/city2');OUT.mkdir(parents=True,exist_ok=True)
ROOT='/Game/FoA/Level2/City/Expanded'
MAP='/Game/FoA/Level2/Maps/L_L2_CityTest2'
BED='/Game/FoA/Maps/L_Tutorial_Bedroom'
EAL=unreal.EditorAssetLibrary
LES=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EAS=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
UES=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)


def current():return UES.get_editor_world().get_path_name().split('.')[0]
def sanity():
    import sys
    checks={'engine':unreal.SystemLibrary.get_engine_version(),'python':sys.version,'map':current(),
        'import':hasattr(unreal.AssetToolsHelpers.get_asset_tools(),'import_asset_tasks'),
        'uv_count':hasattr(unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem),'get_num_uv_channels'),
        'capture':hasattr(unreal.RenderingLibrary,'export_render_target'),
        'graphs':hasattr(unreal.FoAGraphToolsLibrary,'capture_graph_png')}
    save_json('ue59_sanity.json',checks);assert checks['engine'].startswith('5.9.'),checks
    assert all(checks[k] for k in ['import','uv_count','capture','graphs']),checks
    print(json.dumps(checks))
def save_json(name,value):(OUT/name).write_text(json.dumps(value,indent=2))
def count():
    actors=EAS.get_all_level_actors();names={a.get_actor_label() for a in actors};classes={a.get_class().get_name() for a in actors}
    return {'map':current(),'actors':len(actors),'encounter':'Encounter_T8' in names,
            'beat':any(n.startswith('BP_BeatDirector') for n in classes),'player_start':'PlayerStart' in classes}


def import_meshes():
    manifest=json.loads((SRC/'manifest.json').read_text());m=manifest['meshes']+manifest['overview']
    start=int(os.environ['CITY2_FROM']);part=m[start:start+int(os.environ.get('CITY2_N','4'))]
    tasks=[]
    for e in part:
        dest=f"{ROOT}/Meshes/{e['name']}/StaticMeshes/{e['name']}"
        if EAL.does_asset_exist(dest):continue
        t=unreal.AssetImportTask()
        for k,v in [('filename',str(SRC/e['gltf'])),('destination_path',ROOT+'/Meshes'),('automated',True),('replace_existing',False),('save',False)]:t.set_editor_property(k,v)
        tasks.append(t)
    if tasks:unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    smes=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    material=unreal.load_asset('/Game/FoA/Level2/M_SplatCity_Lean');assert material
    for e in part:
        path=f"{ROOT}/Meshes/{e['name']}/StaticMeshes/{e['name']}"
        sm=unreal.load_asset(path);assert sm,path
        ns=smes.get_nanite_settings(sm);ns.set_editor_property('enabled',False);smes.set_nanite_settings(sm,ns,False)
        bs=smes.get_lod_build_settings(sm,0)
        for k,v in [('recompute_normals',False),('recompute_tangents',False),('generate_lightmap_u_vs',False),('use_full_precision_u_vs',False),('distance_field_resolution_scale',0.),('remove_degenerates',False)]:bs.set_editor_property(k,v)
        smes.set_lod_build_settings(sm,0,bs);sm.set_material(0,material);EAL.save_loaded_asset(sm)
        assert smes.get_num_uv_channels(sm,0)>=(2 if 'Overview' in e['name'] else 3),e['name']
        assert sm.get_num_triangles(0)==e['splats']*2,(e['name'],sm.get_num_triangles(0),e['splats'])
    save_json('import_progress.json',{'through':start+len(part),'total':len(m)})
    print('CITY2 imported',start,len(part),flush=True)


def textures():
    rows=json.loads((SRC/'ground_manifest.json').read_text())['tiles']+[{'name':'T_City2_Skirt','file':'ground/T_City2_Skirt.png'}]
    for e in rows[int(os.environ.get('CITY2_FROM','0')):int(os.environ.get('CITY2_FROM','0'))+4]:
        t=unreal.AssetImportTask()
        for k,v in [('filename',str(SRC/e['file'])),('destination_path',ROOT),('destination_name',e['name']),('automated',True),('replace_existing',True),('save',False)]:t.set_editor_property(k,v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
        tex=unreal.load_asset(ROOT+'/'+e['name']);assert tex,e['name']
        tex.set_editor_property('srgb',True)
        tex.set_editor_property('address_x',unreal.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',unreal.TextureAddress.TA_CLAMP)
        EAL.save_loaded_asset(tex)
    print('CITY2 textures imported')


def new_actor(cls,label,location):
    actor=next((a for a in EAS.get_all_level_actors() if a.get_actor_label()==label),None)
    if actor:return actor
    actor=EAS.spawn_actor_from_class(cls,unreal.Vector(*location));assert actor,label
    actor.set_actor_label(label);actor.set_folder_path('City2')
    return actor


def sector():
    sx,sy=map(int,os.environ['CITY2_SECTOR'].split(','))
    path=f'/Game/FoA/Level2/Maps/City2/L_City2_S{sx}_{sy}'
    assert current()==path,current()
    m=json.loads((SRC/'manifest.json').read_text())
    entries=[e for e in m['meshes'] if e['sector']==[sx,sy]]
    for e in entries:
        sm=unreal.load_asset(f"{ROOT}/Meshes/{e['name']}/StaticMeshes/{e['name']}");assert sm,e['name']
        a=new_actor(unreal.StaticMeshActor,'City2_'+e['name'],e['actor_location_cm'])
        component=a.static_mesh_component;component.set_static_mesh(sm);component.set_editor_property('cast_shadow',False)
        component.set_collision_profile_name('NoCollision');component.set_editor_property('ld_max_draw_distance',18000.)
        component.set_editor_property('allow_cull_distance_volume',False)
        component.set_default_custom_primitive_data_float(2,e['cell']*.013)
        component.set_default_custom_primitive_data_float(3,-63.000091552734716)
    UES.get_editor_world().get_world_settings().set_editor_property('default_game_mode',unreal.GameModeBase.static_class())
    assert LES.save_current_level();print('CITY2 sector saved',sx,sy,len(entries))


def master():
    assert current()==MAP,current()
    m=json.loads((SRC/'manifest.json').read_text())
    ground=json.loads((SRC/'ground_manifest.json').read_text())['tiles']
    ground.append({'name':'T_City2_Skirt','actor_location_cm':[70000,0,-75],'scale':[2000,1600,1]})
    for e in ground:
        a=new_actor(unreal.StaticMeshActor,'City2_'+e['name'],e['actor_location_cm'])
        component=a.static_mesh_component;component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
        component.set_material(0,unreal.load_asset(ROOT+'/MI'+e['name'][1:]))
        component.set_editor_property('cast_shadow',False);component.set_collision_profile_name('NoCollision')
        a.set_actor_scale3d(unreal.Vector(*e.get('scale',[400,400,1])))
    cls=unreal.load_class(None,ROOT+'/BP_City2Sector.BP_City2Sector_C');assert cls
    for e in m['overview']:
        a=new_actor(unreal.StaticMeshActor,'City2_'+e['name'],e['actor_location_cm'])
        component=a.static_mesh_component
        component.set_static_mesh(unreal.load_asset(f"{ROOT}/Meshes/{e['name']}/StaticMeshes/{e['name']}"))
        component.set_editor_property('min_draw_distance',30000.)
        component.set_editor_property('cast_shadow',False);component.set_collision_profile_name('NoCollision')
    for sx,sy in m['sectors']:
        a=new_actor(cls,f'City2_Stream_{sx}_{sy}',[(-100+sx*200+100)*100,-(-600+sy*200+100)*100,0])
        package=f'/Game/FoA/Level2/Maps/City2/L_City2_S{sx}_{sy}'
        a.set_editor_property('SectorPackage',package)
    pp=new_actor(unreal.PostProcessVolume,'City2_Post',[0,0,0]);pp.set_editor_property('unbound',True)
    settings=pp.get_editor_property('settings')
    for k,v in [('override_auto_exposure_method',True),('auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL),
                ('override_auto_exposure_apply_physical_camera_exposure',True),('auto_exposure_apply_physical_camera_exposure',False),
                ('override_auto_exposure_bias',True),('auto_exposure_bias',0.),
                ('override_motion_blur_amount',True),('motion_blur_amount',0.)]:settings.set_editor_property(k,v)
    settings.set_editor_property('weighted_blendables',unreal.WeightedBlendables([unreal.WeightedBlendable(1.,unreal.load_asset(ROOT+'/M_City2_EdgeFog'))]))
    pp.set_editor_property('settings',settings)
    fog=new_actor(unreal.ExponentialHeightFog,'City2_HeightFog',[0,0,-2000])
    fc=fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    for k,v in [('fog_density',.006),('fog_height_falloff',.05),('fog_max_opacity',.65),('start_distance',5000.)]:fc.set_editor_property(k,v)
    fc.set_editor_property('fog_inscattering_color',unreal.LinearColor(.025,.025,.025,1))
    sun=new_actor(unreal.DirectionalLight,'City2_ShadowDirection',[0,0,20000])
    sun.set_actor_rotation(unreal.Rotator(pitch=-45,yaw=-45,roll=0),False)
    sun.light_component.set_editor_property('intensity',1.)
    sun.light_component.set_editor_property('cast_shadows',False)
    cam=new_actor(unreal.CameraActor,'City2_Camera',[15500,0,4937])
    cam.set_actor_rotation(unreal.Rotator(pitch=-90,yaw=-90,roll=0),False)
    cam.camera_component.set_editor_property('field_of_view',90.)
    cam.camera_component.set_editor_property('constrain_aspect_ratio',False)
    cam.set_editor_property('auto_activate_for_player',unreal.AutoReceiveInput.PLAYER0)
    new_actor(unreal.PlayerStart,'City2_PlayerStart',[15500,0,100])
    UES.get_editor_world().get_world_settings().set_editor_property('default_game_mode',unreal.GameModeBase.static_class())
    assert LES.save_current_level();print('CITY2 master saved',count())


def capture_graphs():
    for asset,graph,file in [(ROOT+'/M_City2_EdgeFog','','edge_fog_graph.png'),(ROOT+'/BP_City2Sector','UpdateSector','streaming_graph.png'),(ROOT+'/BP_City2Sector','EventGraph','streaming_events.png')]:
        obj=unreal.load_asset(asset);unreal.FoAGraphToolsLibrary.capture_graph_png(obj,graph,str(OUT/file),True)
    material=unreal.load_asset(ROOT+'/M_City2_EdgeFog')
    assert material.get_editor_property('material_domain')==unreal.MaterialDomain.MD_POST_PROCESS
    print('CITY2 graphs queued; fog domain verified')


def cleanup_variables():
    bp=unreal.load_asset(ROOT+'/BP_City2Sector')
    EAS.select_nothing();unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    ed=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'UpdateSector')
    old=[n for n in ed.list_all_nodes() if str(unreal.BlueprintEditorLibrary.get_node_title(n)).split('\n')[0] in ['Get Sector Level','Get SectorLevel','Load Level Instance (by Object Reference)']]
    ed.remove_nodes(old)
    unreal.BlueprintEditorLibrary.remove_member_variable(bp,'SectorLevel')
    unreal.BlueprintEditorLibrary.compile_blueprint(bp);EAL.save_loaded_asset(bp)


step=os.environ['CITY2_STEP']
if step=='before':
    assert current()==BED,current();save_json('bedroom_before.json',count())
elif step=='back':
    if current()!=BED:assert LES.load_level(BED)
    before=json.loads((OUT/'bedroom_before.json').read_text());after=count()
    save_json('bedroom_after.json',after);assert before==after,(before,after)
    print('CITY2 bedroom restored',after)
else:globals()[step]()
