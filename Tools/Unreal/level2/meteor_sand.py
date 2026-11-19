"""Make a small procedural Gaussian sand sphere with the Level 1 sand channels."""
from math import cos, sin, sqrt, tau
from pathlib import Path
import random
import sys

OUT=Path('P:/FoA/Saved/Integration/l2_followup')
NAME='SM_L2SandMeteor'


def generate():
    sys.path.insert(0,'P:/FoA/Tools/Splats')
    from make_sand_splats import Splats
    rng=random.Random(46)
    points=Splats(rng)
    for i in range(3000):
        z=rng.uniform(-1,1)
        angle=rng.random()*tau
        ring=sqrt(1-z*z)
        normal=(ring*cos(angle),ring*sin(angle),z)
        radius=rng.uniform(48,69) if i<2500 else rng.uniform(70,106)
        xyz=tuple(axis*radius for axis in normal)
        points.add(0,xyz,rng.uniform(1.6,5.2),rng.uniform(.02,.11),.9 if i<2500 else .5,normal)
    _, manifest=points.write(OUT,NAME,{'mode':3})
    assert manifest['splats']==3000 and all(100 < n-p < 215 for n,p in zip(
        manifest['rest_bounds_cm']['max'],manifest['rest_bounds_cm']['min']))


def install():
    import unreal as u
    from free_drive_setup import templates
    root='/Game/FoA/Level2/Drive'
    path=f'{root}/{NAME}/StaticMeshes/{NAME}'
    mesh=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else None
    if not mesh:
        pipeline=u.InterchangeGenericAssetsPipeline()
        pipeline.get_editor_property('material_pipeline').set_editor_property('import_materials',False)
        meshes=pipeline.get_editor_property('mesh_pipeline')
        meshes.set_editor_property('build_nanite',False)
        meshes.set_editor_property('distance_field_resolution_scale',0.)
        common=pipeline.get_editor_property('common_meshes_properties')
        for key,val in [('recompute_normals',False),('recompute_tangents',False),
                        ('use_full_precision_u_vs',True),('remove_degenerates',False)]:
            common.set_editor_property(key,val)
        options=u.InterchangePipelineStackOverride();options.add_pipeline(pipeline)
        task=u.AssetImportTask()
        for key,value in [('filename',str(OUT/(NAME+'.gltf'))),('destination_path',str(Path(path).parent).replace('\\','/')),
                          ('automated',True),('options',options)]:task.set_editor_property(key,value)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh=u.load_asset(path)
    assert mesh and mesh.get_num_triangles(0)==6000
    for key in ('positive_bounds_extension','negative_bounds_extension'):
        mesh.set_editor_property(key,u.Vector(30,30,30))
    material=u.load_asset('/Game/FoA/VFX/Splats/Instances/MI_Sand_AlarmClock')
    assert material
    mesh.set_material(0,material)
    assert u.EditorAssetLibrary.save_loaded_asset(mesh)
    bp,*_,cs=templates(root+'/BP_Meteor')
    body=cs['Shadow'];body.set_static_mesh(mesh);body.set_material(0,material)
    body.set_editor_property('relative_scale3d',u.Vector(1,1,1))
    body.set_editor_property('relative_location',u.Vector(0,0,2600))
    body.set_collision_profile_name('NoCollision')
    body.set_editor_property('cast_shadow',False)
    assert u.EditorAssetLibrary.save_loaded_asset(bp)


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='generate':generate()
    else:
        import os
        assert os.environ.get('FOA_LEASE')
        sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
        install()
