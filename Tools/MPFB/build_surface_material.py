"""Own lightweight morph-capable skin/tongue/lash materials instead of plugin import placeholders."""
import sys
import shutil
import tempfile
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as hc
root='/Game/FoA/Characters/Teen/Materials'
mat=root+'/M_FoA_TeenSurface'
owner='character_finish'
def call(cmd,**kw):
    r=hc.call(cmd,kw,owner=owner)
    assert r.get('ok'),r
    d=r.get('data',{})
    assert not d.get('errors'),d
    return d
assert not call('editor_get_state')['pie_running']
token=hc.lease_acquire(owner,['asset:'+root,'asset:/Game/FoA/Characters/Teen/Hair/M_FoA_TeenHair'],ttl_s=120,wait_s=20)
try:
    if not Path('P:/FoA/Content/FoA/Characters/Teen/Materials/M_FoA_TeenSurface.uasset').exists():
        call('material_create',package_path=root,name='M_FoA_TeenSurface')
    call('material_set_property',material_path=mat,properties={'used_with_skeletal_meshes':True,'used_with_morph_targets':True})
    info=call('material_get_info',path=mat)
    ids={}
    for key,cls,pos,props in [
        ('tex','TextureSampleParameter2D',[-700,0],{'ParameterName':'Albedo','Texture':'/Game/FoA/Characters/Teen/Mesh/T_Teen_young_lightskinned_male_diffuse_Freckles'}),
        ('tint','VectorParameter',[-700,300],{'ParameterName':'Tint','DefaultValue':[1,1,1,1]}),
        ('color','Multiply',[-360,0],{}),('rough','Constant',[-360,210],{'R':.65}),('spec','Constant',[-360,340],{'R':.3})]:
        old=next((e for e in info['expressions'] if [e.get('x'),e.get('y')]==pos),None)
        ids[key]=old['id'] if old else call('material_add_node',material_path=mat,expression_class='MaterialExpression'+cls,node_pos=pos,properties=props)['node_id']
    for src,pin in [('tex','A'),('tint','B')]:
        call('material_connect_nodes',material_path=mat,from_node=ids[src],from_output_index=0,to_node=ids['color'],to_input=pin)
    for src,prop in [('color','base_color'),('rough','roughness'),('spec','specular')]:
        call('material_connect_nodes',material_path=mat,from_node=ids[src],from_output_index=0,to_property=prop)
    if not info.get('comments'):
        call('material_add_comment',material_path=mat,text='Character surface',node_pos=[-770,-70],size=[650,660],color=[.25,.32,.35])
    for comment in call('material_get_info',path=mat).get('comments',[]):
        call('material_set_comment',material_path=mat,comment_id=comment['id'],show_bubble=True,color_bubble=True)
    call('material_validate',material_path=mat)
    print(call('material_compile',material_path=mat))
    scalp_source=Path('P:/FoA-Assets/character/mpfb/export/hair/T_Teen_Skin_Groom.png')
    if scalp_source.exists() and not Path('P:/FoA/Content/FoA/Characters/Teen/Materials/T_Teen_Skin_Groom.uasset').exists():
        stage=Path(tempfile.gettempdir())/'hayba-asset-connectors/FoA/teen_skin'
        stage.mkdir(parents=True,exist_ok=True)
        shutil.copy2(scalp_source,stage/scalp_source.name)
        call('asset_import',source_file=str(stage/scalp_source.name),destination_path=root,asset_type='texture')
        call('texture_set_settings',path=root+'/T_Teen_Skin_Groom',properties={'srgb':True,'max_texture_size':2048})
        call('asset_save',asset_paths=[root+'/T_Teen_Skin_Groom'])
    for name,tex,tint in [('Skin','/Game/FoA/Characters/Teen/Mesh/T_Teen_young_lightskinned_male_diffuse_Freckles',[1,1,1,1]),
                          ('Tongue','/Game/FoA/Characters/Teen/Mesh/T_Teen_tongue01_diffuse',[1,1,1,1]),
                          ('Lashes','/Engine/EngineResources/WhiteSquareTexture',[.015,.012,.01,1]),
                          ('Skin_Groom',root+'/T_Teen_Skin_Groom',[1,1,1,1])]:
        if name=='Skin_Groom' and not scalp_source.exists():
            continue
        path=root+'/MI_Teen_'+name
        if not Path('P:/FoA/Content/FoA/Characters/Teen/Materials/MI_Teen_'+name+'.uasset').exists():
            call('material_create_instance',parent_material_path=mat,package_path=root,name='MI_Teen_'+name)
        call('material_set_param',instance_path=path,param_name='Albedo',value=tex)
        call('material_set_param',instance_path=path,param_name='Tint',value=tint)
    hair='/Game/FoA/Characters/Teen/Hair/M_FoA_TeenHair'
    call('material_set_property',material_path=hair,properties={'used_with_morph_targets':True})
    call('material_validate',material_path=hair)
    print(call('material_compile',material_path=hair))
finally:
    hc.release(owner,token)
