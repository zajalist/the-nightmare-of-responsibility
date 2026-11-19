"""Small project-owned Niagara cloth smoke, using the engine lightweight emitter."""
import sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
ROOT='/Game/FoA/VFX/Cloth'
SYSTEM=ROOT+'/NS_ClothSmoke'
MAT=ROOT+'/M_ClothSmoke'

def call(cmd,**p):
    r=h.call(cmd,p);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True) and not d.get('errors') and not d.get('failed') and not d.get('has_errors'),d
    return d

def build():
    if not Path('P:/FoA/Content/FoA/VFX/Cloth/M_ClothSmoke.uasset').exists():
        call('material_create',package_path=ROOT,name='M_ClothSmoke')
    info=call('material_get_info',path=MAT);ids={}
    for name,cls,pos,props in [
        ('uv','TextureCoordinate',[-700,0],{}),('age','ParticleRelativeTime',[-700,200],{}),
        ('time','Time',[-700,400],{}),('black','Constant3Vector',[-250,-200],{'Constant':[.008,.008,.008]}),
        ('alpha','Custom',[-250,0],{'Description':'Thin drifting smoke','OutputType':'CMOT_Float1',
          'Inputs':[{'InputName':x} for x in ('UV','Age','T')],
          'Code':'float2 p=UV*2-1; float n=0.55+0.2*sin(p.x*7+T*1.4+sin(p.y*9-T))*sin(p.y*6-T*1.7); float edge=1-smoothstep(0.2,0.95,length(p)+0.12*sin(p.x*12+T)); return edge*saturate(n)*sin(saturate(Age)*3.14159265)*0.32;'})]:
        old=next((e for e in info['expressions'] if [e['x'],e['y']]==pos),None)
        ids[name]=old['id'] if old else call('material_add_node',material_path=MAT,expression_class='MaterialExpression'+cls,node_pos=pos,properties=props)['node_id']
        if old and props:call('material_set_node',material_path=MAT,node_id=old['id'],properties=props)
    for src,pin in [('uv','UV'),('age','Age'),('time','T')]:
        call('material_connect_nodes',material_path=MAT,from_node=ids[src],from_output_index=0,to_node=ids['alpha'],to_input=pin)
    for src,prop in [('black','emissive_color'),('alpha','opacity')]:
        call('material_connect_nodes',material_path=MAT,from_node=ids[src],from_output_index=0,to_property=prop)
    call('material_set_property',material_path=MAT,properties={'blend_mode':'Translucent','shading_model':'Unlit','two_sided':True})
    call('material_set_property',material_path=MAT,properties={'used_with_niagara_sprites':True})
    if not info.get('comments'):call('material_add_comment',material_path=MAT,text='Sparse cloth smoke',node_pos=[-780,-280],size=[960,900],color=[.21,.28,.31])
    call('material_compile',material_path=MAT)
    if not h.call('object_get_property',dict(path=SYSTEM,names=['EmitterHandles'])).get('ok'):
        call('asset_duplicate',source_path='/Niagara/DefaultAssets/Templates/Systems/FountainLightweight',destination_path=SYSTEM)
    base=SYSTEM+'.NS_ClothSmoke:Fountain_1'
    def put(path,**props):return call('object_set_property',path=path,properties=props)
    # The stateless distributions keep runtime Min/Max and editor channels in agreement.
    def uniform(lo,hi=None):
        hi=lo if hi is None else hi
        return f'(Min={lo},Max={hi},Mode={"UniformConstant" if lo==hi else "UniformRange"},ChannelConstantsAndRanges=({lo}{"" if lo==hi else ","+str(hi)}))'
    put(base,SpawnInfos=[{'Type':'Rate','Rate':{'Min':10,'Max':10,'Mode':'UniformConstant','ChannelConstantsAndRanges':[10]}}],FixedBounds='(Min=(X=-40,Y=-40,Z=-20),Max=(X=40,Y=40,Z=70),IsValid=True)')
    put(base+'.NiagaraStatelessModule_InitializeParticle_0',LifetimeDistribution=uniform(.8,1.4),
        SpriteSizeDistribution='(Min=(X=8,Y=8),Max=(X=16,Y=16),Mode=UniformRange,ChannelConstantsAndRanges=(8,16))')
    put(base+'.NiagaraStatelessModule_AddVelocity_0',VelocityType='InCone',ConeVelocityDistribution=uniform(8,14),ConeAngle=25)
    put(base+'.NiagaraStatelessModule_GravityForce_0',bModuleEnabled=False)
    put(base+'.NiagaraStatelessModule_ShapeLocation_0',ShapePrimitive='Sphere',SphereRadius=uniform(3))
    put(base+'.Renderer',Material=MAT)
    call('asset_save',asset_paths=[MAT,SYSTEM])
    read=call('object_get_property',path=base,names=['SpawnInfos'])['properties']['SpawnInfos']
    assert '10.000000' in read,read
    print('Niagara smoke saved: 10 particles/sec, 1.4sec maximum lifetime, 8-16cm wisps. Runtime proof pending.')

if __name__=='__main__':
    assert not call('editor_get_state')['pie_running']
    token=h.lease_acquire(h.agent_id(),['asset:'+ROOT],ttl_s=90,wait_s=30)
    try:build()
    finally:h.release(h.agent_id(),token)
