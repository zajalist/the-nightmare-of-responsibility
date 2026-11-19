"""Own monochrome marker family and a small ring mesh. No external assets or generating calls."""
import base64
import json
import math
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).parent))
from build_drive import D, call, h, editor_lock


def ring():
    vertices=[];indices=[]
    for i in range(65):
        a=i*math.tau/64
        for r in (.475,.5):vertices.extend((r*math.cos(a),0,r*math.sin(a)))
    for i in range(64):
        a=2*i;indices.extend((a,a+2,a+1,a+1,a+2,a+3))
    vb=struct.pack('<'+'f'*len(vertices),*vertices);ib=struct.pack('<'+'H'*len(indices),*indices);blob=vb+ib
    doc={'asset':{'version':'2.0','generator':'FoA drive ring'},'scene':0,'scenes':[{'nodes':[0]}],
         'nodes':[{'mesh':0,'name':'SM_L2Ring'}],
         'meshes':[{'name':'SM_L2Ring','primitives':[{'attributes':{'POSITION':0},'indices':1}]}],
         'buffers':[{'byteLength':len(blob),'uri':'data:application/octet-stream;base64,'+base64.b64encode(blob).decode()}],
         'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(vb),'target':34962},
                        {'buffer':0,'byteOffset':len(vb),'byteLength':len(ib),'target':34963}],
         'accessors':[{'bufferView':0,'componentType':5126,'count':len(vertices)//3,'type':'VEC3','min':[-.5,0,-.5],'max':[.5,0,.5]},
                      {'bufferView':1,'componentType':5123,'count':len(indices),'type':'SCALAR'}]}
    assert len(indices)==384 and max(indices)==129
    out=Path('P:/FoA/Saved/Codex/l2_drive/generated');out.mkdir(parents=True,exist_ok=True)
    (out/'SM_L2Ring.gltf').write_text(json.dumps(doc))
    print('Ring generated: 130 vertices, 128 triangles')


def materials():
    mat=D.ROOT+'/M_L2Flat'
    if not h.call('material_get_info',{'path':mat}).get('ok'):
        call('material_create',package_path=mat,name='M_L2Flat',shading_model='Unlit')
    info=call('material_get_info',path=mat)
    node='MaterialExpressionVectorParameter_0'
    if 'Ink' not in str(info):
        node=call('material_add_node',material_path=mat,expression_class='MaterialExpressionVectorParameter',node_pos=[-320,0],
                  properties={'ParameterName':'Ink','DefaultValue':{'R':.9,'G':.9,'B':.9,'A':1}})['node_id']
        call('material_add_comment',material_path=mat,text='Monochrome surface',node_pos=[-370,-70],size=[300,250],color=[.2,.2,.2],font_size=18)
    call('material_connect_nodes',material_path=mat,from_node=node,from_output='RGB',to_property='EmissiveColor')
    call('material_set_property',material_path=mat,properties={'shading_model':'unlit','two_sided':True})
    call('material_validate',material_path=mat);call('material_compile',material_path=mat)
    mi=D.ROOT+'/MI_L2Dark'
    if not h.call('material_get_info',{'path':mi}).get('ok'):
        call('material_create_instance',parent_material_path=mat,package_path=D.ROOT,name='MI_L2Dark')
    call('material_set_param',instance_path=mi,param_name='Ink',value=[.009,.009,.009,1])
    call('asset_save',asset_paths=[mat,mi])
    car_materials()


def car_materials():
    # The car needs readable surface planes; the unlit marker material erases them.
    for name,color,rough,metal in (('MI_L2CarPaint',.38,.3,.2),('MI_L2CarTrim',.018,.25,.1)):
        path=D.ROOT+'/'+name
        call('material_create_instance',parent_material_path='/Game/FoA/Materials/M_Greybox',package_path=D.ROOT,name=name)
        for param,value in (('Color',[color,color,color,1]),('Roughness',rough),('Metallic',metal),('Emissive',0.)):
            call('material_set_param',instance_path=path,param_name=param,value=value)
        call('asset_save',asset_paths=[path])


if __name__=='__main__':
    if sys.argv[1]=='ring':ring()
    else:
        import os
        D.OWNER=os.environ.get('FOA_AGENT',D.OWNER)
        os.environ['FOA_AGENT']=os.environ['HAYBA_AGENT_ID']=D.OWNER
        editor_lock.acquire(D.OWNER,wait_s=300,ttl=180,areas=[D.ROOT])
        try:{'materials':materials,'car_materials':car_materials}[sys.argv[1]]()
        finally:editor_lock.release(D.OWNER)
