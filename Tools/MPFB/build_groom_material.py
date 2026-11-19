"""Small native Hair shader for the approved short01 groom."""
import json
from pathlib import Path
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc

ROOT='/Game/FoA/Characters/Teen/Hair'
MAT=ROOT+'/M_FoA_TeenStrands'
OWNER='character_finish'
def call(cmd, **args):
    result=hc.call(cmd,args,owner=OWNER)
    assert result.get('ok'),result
    data=result.get('data',{})
    assert not data.get('errors') and not data.get('unknown_props'),data
    return data

assert not call('editor_get_state')['pie_running']
token=hc.lease_acquire(OWNER,['asset:'+MAT],ttl_s=90,wait_s=10)
try:
    if not Path('P:/FoA/Content/FoA/Characters/Teen/Hair/M_FoA_TeenStrands.uasset').exists():
        call('material_create',package_path=ROOT,name='M_FoA_TeenStrands')
    call('material_set_property',material_path=MAT,properties={'shading_model':'hair'})
    call('material_set_property',material_path=MAT,properties={'used_with_hair_strands':True})
    info=call('material_get_info',path=MAT)
    for cls,pos,props,pin in [('VectorParameter',[-400,0],{'ParameterName':'HairColor','DefaultValue':[.025,.018,.012,1]},'base_color'),
                              ('ScalarParameter',[-400,220],{'ParameterName':'HairRoughness','DefaultValue':.6},'roughness'),
                              ('ScalarParameter',[-400,350],{'ParameterName':'HairSpecular','DefaultValue':.3},'specular')]:
        old=next((e for e in info['expressions'] if [e.get('x'),e.get('y')]==pos),None)
        node=old['id'] if old else call('material_add_node',material_path=MAT,expression_class='MaterialExpression'+cls,node_pos=pos,properties=props)['node_id']
        call('material_connect_nodes',material_path=MAT,from_node=node,from_output_index=0,to_property=pin)
    if not info.get('comments'):
        call('material_add_comment',material_path=MAT,text='Short hair',node_pos=[-470,-70],size=[420,560],color=[.25,.32,.35])
    for comment in call('material_get_info',path=MAT).get('comments',[]):
        call('material_set_comment',material_path=MAT,comment_id=comment['id'],show_bubble=True,color_bubble=True)
    call('material_validate',material_path=MAT)
    result=call('material_compile',material_path=MAT)
    Path('P:/FoA/Saved/CharacterShots/mpfb/hair/ue_hair_compile.json').write_text(json.dumps(result,indent=2))
    print(result)
finally:
    hc.release(OWNER,token)
