"""Scoped new-map population. Caller owns exclusive map-switch lease and return.

Existing L_L2_CityTest and its514 actors are never edited. New maps contain only
surveyed-frame splat geometry and the reused sector streaming controllers.
"""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
import city_streaming as c
import unreal


def main():
    ues=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert ues.get_game_world() is None,'User PIE must end before map edits'
    eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eal=unreal.EditorAssetLibrary
    mode=os.environ['CITY_STREAM_STEP']
    if mode=='inventory':
        current=ues.get_editor_world().get_path_name().split('.')[0]
        assert current=='/Game/FoA/Maps/L_Tutorial_Bedroom',current
        actors=eas.get_all_level_actors()
        labels={a.get_actor_label() for a in actors};classes={a.get_class().get_name() for a in actors}
        result=dict(map=current,actors=len(actors),encounter='Encounter_T8' in labels,
                    beat=any(n.startswith('BP_BeatDirector') for n in classes),player_start='PlayerStart' in classes)
        assert all(result[k] for k in ('encounter','beat','player_start')),result
        where=os.environ['CITY_STREAM_INVENTORY'];assert where in ('before','after')
        folder=Path('P:/FoA/Saved/Integration/city_streaming')
        if where=='after':assert result==json.loads((folder/'bedroom_before.json').read_text()),result
        (folder/('bedroom_'+where+'.json')).write_text(json.dumps(result,indent=2))
        eas.select_nothing();print(json.dumps(result));return
    plan=json.loads(Path('P:/FoA/Saved/Integration/city_streaming/plan.json').read_text())
    if mode=='hide_collision':
        from free_drive_setup import templates
        bp,_,_,_,_,components=templates('/Game/FoA/Level2/Drive/BP_L2RoadNetwork')
        component=components['CityCollision']
        before=(component.get_editor_property('relative_location'),component.get_editor_property('relative_scale3d'),component.get_collision_enabled())
        component.set_editor_property('visible',False);component.set_editor_property('hidden_in_game',True)
        after=(component.get_editor_property('relative_location'),component.get_editor_property('relative_scale3d'),component.get_collision_enabled())
        assert before==after,'Collision shape/transform must remain unchanged'
        assert eal.save_loaded_asset(bp,False)
        print('CityCollision visuals hidden; collision and transform preserved');return
    if mode=='validate':
        paths=[plan['master']]+[s['package'] for s in plan['sectors']]
        meshes=[m for s in plan['sectors'] for m in s['meshes']]+plan['overview']
        paths += [mesh_path(m) for m in meshes]
        paths += [m['material'] for m in meshes]+[c.BP]
        missing=[p for p in sorted(set(paths)) if not eal.does_asset_exist(p)]
        folder=Path('P:/FoA/Saved/Integration/city_streaming')
        parts=(len(plan['overview'])+len(plan['sectors'])+c.MASTER_ACTORS_PER_PASS-1)//c.MASTER_ACTORS_PER_PASS
        missing_receipts=[f'{name}_{index}.json' for name,total in (('sector',len(plan['sectors'])),('master',parts))
                          for index in range(total) if not (folder/f'{name}_{index}.json').is_file()]
        result=dict(ok=not missing and not missing_receipts,missing=missing,missing_receipts=missing_receipts,
                    sector_count=len(plan['sectors']),mesh_count=len(meshes))
        (folder/'validation.json').write_text(json.dumps(result,indent=2))
        assert result['ok'],result
        print(json.dumps(result));return
    current=ues.get_editor_world().get_path_name().split('.')[0]
    index=int(os.environ.get('CITY_STREAM_INDEX','0'))
    expected=plan['master'] if mode=='master' else plan['sectors'][index]['package']
    assert current==expected,('Wrong map; no edits made',current,expected)
    have={a.get_actor_label():a for a in eas.get_all_level_actors()}
    def actor(label,cls,position):
        old=have.get(label)
        if old:
            assert old.get_class()==cls,('Class differs',label)
            assert (old.get_actor_location()-unreal.Vector(*position)).length()<.1,('Actor moved; preserve user placement',label)
            return old
        value=eas.spawn_actor_from_class(cls,unreal.Vector(*position));assert value,label
        value.set_actor_label(label);have[label]=value;return value
    def splat(row):
        mesh=unreal.load_asset(mesh_path(row));material=unreal.load_asset(row['material'])
        assert mesh and material,row['name']
        item=actor('CityDense_'+row['name'],unreal.StaticMeshActor.static_class(),row['actor_location_cm'])
        item.set_folder_path('City/Splats/'+row['lod'])
        component=item.static_mesh_component;component.set_static_mesh(mesh);component.set_material(0,material)
        component.set_collision_profile_name('NoCollision');component.set_editor_property('cast_shadow',False)
        component.set_editor_property('ld_max_draw_distance',0. if row['lod']=='far' else 13500.)
        component.set_editor_property('allow_cull_distance_volume',False)
        for slot,value in ((3,-63.),(4,-2. if row['kind']=='ground' else 0.),(5,2. if row['lod']=='far' else 1.)):
            component.set_default_custom_primitive_data_float(slot,value)
    if mode=='master':
        overview=plan['overview'];sectors=plan['sectors'];width=c.MASTER_ACTORS_PER_PASS
        start=index*width;end=start+width
        assert 0<=start<len(overview)+len(sectors),index
        for row in overview[start:end]:splat(row)
        sector_class=unreal.load_class(None,c.BP+'.BP_City2Sector_C');assert sector_class
        for row in sectors[max(0,start-len(overview)):max(0,end-len(overview))]:
            x,y=row['cell'];item=actor(f'CityDense_Stream_{x}_{y}',sector_class,row['centre'])
            item.set_folder_path('City/Streaming')
            for name,value in dict(SectorPackage=row['package'],LoadRadius=c.LOAD_CM,UnloadRadius=c.UNLOAD_CM,
                SectorHalfExtent=unreal.Vector(2500,2500,0),BootstrapPoint=unreal.Vector(*c.ENTRY),
                BootstrapPending=True,DesiredLoaded=False,Ready=False).items():item.set_editor_property(name,value)
        # Preserve the active city's authored manual exposure; this density
        # replacement must not introduce a second automatic-exposure look.
        post=actor('CityDense_Post',unreal.PostProcessVolume.static_class(),(0,0,0))
        post.set_editor_property('unbound',True);settings=post.get_editor_property('settings')
        for key,value in (('override_auto_exposure_method',True),('auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL),
                          ('override_auto_exposure_apply_physical_camera_exposure',True),('auto_exposure_apply_physical_camera_exposure',False),
                          ('override_auto_exposure_bias',True),('auto_exposure_bias',0.),
                          ('override_motion_blur_amount',True),('motion_blur_amount',0.)):
            settings.set_editor_property(key,value)
        post.set_editor_property('settings',settings)
        light=actor('CityDense_CarLight',unreal.DirectionalLight.static_class(),(0,0,20000))
        light.set_actor_rotation(unreal.Rotator(pitch=-45,yaw=25,roll=0),False)
        light.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        light.light_component.set_editor_property('intensity',1.6)
        light.light_component.set_forward_shading_priority(10)
        light.light_component.set_editor_property('cast_shadows',False)
    else:
        assert mode=='sector',mode
        for row in plan['sectors'][index]['meshes']:splat(row)
    ues.get_editor_world().get_world_settings().set_editor_property('default_game_mode',unreal.GameModeBase.static_class())
    assert les.save_current_level()
    print(json.dumps(dict(map=current,mode=mode,actors=len(eas.get_all_level_actors()))))


def mesh_path(row):
    return row.get('asset_path',row.get('asset',f"{c.ASSET_ROOT}/{row['name']}/StaticMeshes/{row['name']}"))


if __name__=='__main__':main()
