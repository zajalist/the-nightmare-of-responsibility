"""Localized wet cloth and sand breakup, preserving the existing wrinkle normals."""
import json, sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
MAT='/Game/FoA/Characters/Teen/Cloth/M_FoA_TeenCloth'

def call(cmd,**p):
    r=h.call(cmd,p);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True) and not d.get('errors') and not d.get('has_errors'),d
    return d

def build():
    info=call('material_get_info',path=MAT);ids={}
    def node(k,cls,x,y,**props):
        old=next((e for e in info['expressions'] if (e['x'],e['y'])==(x,y)),None)
        ids[k]=old['id'] if old else call('material_add_node',material_path=MAT,expression_class='MaterialExpression'+cls,node_pos=[x,y],properties=props)['node_id']
        if old and props:call('material_set_node',material_path=MAT,node_id=old['id'],properties=props)
    def link(a,b=None,pin=None,prop=None,out=0):
        p=dict(material_path=MAT,from_node=ids.get(a,a),from_output_index=out)
        p.update(dict(to_node=ids[b],to_input=pin) if b else dict(to_property=prop))
        call('material_connect_nodes',**p)
    def custom(k,x,y,typ,code,inputs):
        node(k,'Custom',x,y,Description=k,OutputType='CMOT_'+typ,Code=code,Inputs=[{'InputName':n} for n in inputs])
    original=lambda x,y:next(e['id'] for e in info['expressions'] if(e['x'],e['y'])==(x,y))
    ids.update(fabric=original(-400,-950),rough=original(-400,-650),micro=next(e['id'] for e in info['expressions'] if e.get('parameter_name')=='MicroFabric'))
    node('position','WorldPosition',300,100,WorldPositionShaderOffset='WPT_ExcludeAllShaderOffsets')
    node('center','VectorParameter',300,350,ParameterName='CorruptionCenter',DefaultValue=[0,0,0,18])
    node('pulse','ScalarParameter',300,550,ParameterName='CorruptionPulse',DefaultValue=0)
    node('time','Time',300,750)
    custom('patch',650,100,'Float1',
           'float3 q=(P-C.xyz)/max(C.w,1.0); float ripple=0.07*sin(q.x*11+T*2.1)*sin(q.z*9-T*1.7); return (1-smoothstep(0.48,1.0,length(q)+ripple))*saturate(Pulse);',
           ['P','C','T','Pulse'])
    for a,p,o in [('position','P',0),('center','C',5),('time','T',0),('pulse','Pulse',0)]:link(a,'patch',p,out=o)
    custom('wet_colour',1100,-950,'Float3','return lerp(F,F*0.12,Mask*0.9);',['F','Mask'])
    custom('wet_roughness',1100,-650,'Float1','return lerp(R,lerp(0.19,0.88,smoothstep(0.55,0.95,Pulse)),Mask);',['R','Mask','Pulse'])
    custom('sand_edge',1100,-350,'Float1','float2 cell=floor(Grain*800); float grains=frac(sin(dot(cell,float2(12.9898,78.233)))*43758.5453); return 1-Mask*smoothstep(0.6,0.94,Pulse)*smoothstep(0.75,0.95,grains);',['Mask','Pulse','Grain'])
    for a,b,p in [('fabric','wet_colour','F'),('patch','wet_colour','Mask'),('rough','wet_roughness','R'),('patch','wet_roughness','Mask'),('pulse','wet_roughness','Pulse'),('patch','sand_edge','Mask'),('pulse','sand_edge','Pulse')]:link(a,b,p)
    link(original(-1400,-700),'sand_edge','Grain')
    node('vertex_normal','VertexNormalWS',300,1000)
    custom('surface_drift',1100,150,'Float3','return Mask*(N*(0.09+0.06*sin(T*3.1+P.z*0.18))+float3(0,0,0.35)*smoothstep(0.65,0.95,Pulse));',['Mask','N','T','P','Pulse'])
    for a,p in [('patch','Mask'),('vertex_normal','N'),('time','T'),('position','P'),('pulse','Pulse')]:link(a,'surface_drift',p)
    call('material_set_property',material_path=MAT,properties={'blend_mode':'Masked','opacity_mask_clip_value':0.35})
    for a,p in [('wet_colour','base_color'),('wet_roughness','roughness'),('sand_edge','opacity_mask'),('surface_drift','world_position_offset')]:link(a,prop=p)
    if not any(c.get('text')=='Localized cloth change' for c in info.get('comments',[])):
        call('material_add_comment',material_path=MAT,text='Localized cloth change',node_pos=[220,-1040],size=[1300,2310],color=[.21,.28,.31])
    r=call('material_compile',material_path=MAT)
    call('asset_save',asset_paths=[MAT])
    Path('P:/FoA/Saved/ClothShots/corruption_compile.json').write_text(json.dumps(r,indent=2))
    print('Cloth patch shader compiled; pulse defaults to zero until runtime publisher is installed')

if __name__=='__main__':
    assert not call('editor_get_state')['pie_running']
    token=h.lease_acquire(h.agent_id(),['asset:'+MAT],ttl_s=120,wait_s=30)
    try:build()
    finally:h.release(h.agent_id(),token)
