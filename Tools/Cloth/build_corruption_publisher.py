"""One occasional bone-following cloth patch and sparse smoke, on the existing 10 Hz gate.
Apply only after the coordinator releases BP_FoAPlayer. No new timer.
"""
import sys
sys.path.insert(0,'P:/FoA/Tools/Unreal')
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch,inspect,find
P='/Game/FoA/Characters/Player/BP_FoAPlayer';C=P+'.BP_FoAPlayer_C'
K='/Script/Engine.KismetMathLibrary:';SC='/Script/Engine.SceneComponent:'
FN='UpdateClothCorruption'
def call(cmd,**args):
    r=h.call(cmd,args);assert r.get('ok'),r
    return r.get('data',{})
def setup():
    info=call('blueprint_get_info',path=P)
    names={c['name'] for c in info.get('components',[])}
    if 'ClothSmoke' not in names:call('blueprint_add_component',path=P,component_name='ClothSmoke',component_class_path='/Script/Niagara.NiagaraComponent')
    call('object_set_property',path=C+':ClothSmoke_GEN_VARIABLE',properties={'Asset':'/Game/FoA/VFX/Cloth/NS_ClothSmoke','bAutoActivate':False,'CastShadow':False})
    call('blueprint_add_variable',path=P,variable_name='bCorruptionSmoking',variable_type='bool',default_value='false',instance_editable=False,update_existing=True,category='Cloth')
    if FN not in info['functions']:call('blueprint_add_function',path=P,function_name=FN)
    call('blueprint_compile',path=P)
def graph():
    nodes,_=inspect(P,FN);entry=find(nodes,FN);b=Batch(P,FN)
    old=[n['node_id'] for n in nodes if n['node_id']!=entry]
    if old:b.ops.append(dict(op='remove',node_ids=old))
    b.fn('now','/Script/Engine.KismetSystemLibrary:GetGameTimeInSeconds',0,250)
    b.fn('delay',K+'Subtract_DoubleDouble',250,250,B=18);b.link('now','ReturnValue','delay','A')
    b.fn('elapsed',K+'FMax',500,250,B=0);b.link('delay','ReturnValue','elapsed','A')
    b.fn('phase',K+'Percent_FloatFloat',750,250,B=32);b.link('elapsed','ReturnValue','phase','A')
    b.fn('fraction',K+'FClamp',1000,250,Min=0,Max=5);b.link('phase','ReturnValue','fraction','Value')
    b.fn('radians',K+'Multiply_DoubleDouble',1250,250,B=.6283185307179586);b.link('fraction','ReturnValue','radians','A')
    b.fn('pulse',K+'Sin',1500,250);b.link('radians','ReturnValue','pulse','A')
    b.fn('cycle',K+'Divide_DoubleDouble',750,600,B=32);b.link('elapsed','ReturnValue','cycle','A')
    b.fn('floor',K+'FFloor',1000,600);b.link('cycle','ReturnValue','floor','A')
    b.fn('site',K+'Percent_IntInt',1250,600,B=3);b.link('floor','ReturnValue','site','A')
    for ref,value,y in [('arm',1,850),('leg',2,1100)]:
        b.fn(ref,K+'EqualEqual_IntInt',1500,y,B=value);b.link('site','ReturnValue',ref,'A')
    # Measured from the normalized UE bind pose and actual garment surface.
    for ref,fn,a,c,y in [('bone01','SelectName','upperarm_l','spine_03',600),('offset01','SelectVector','-1.054337,-9.932869,6.382617','-2.655079,-5.973332,20.680532',900),('radius01','SelectFloat',7,10,1200)]:
        b.fn(ref,K+fn,1800,y,A=a,B=c);b.link('arm','ReturnValue',ref,'bPickA')
    for ref,fn,a,prev,y in [('bone','SelectName','thigh_r','bone01',600),('offset','SelectVector','4.791206,-15.179744,-10.586212','offset01',900),('radius','SelectFloat',9,'radius01',1200)]:
        b.fn(ref,K+fn,2100,y,A=a);b.link(prev,'ReturnValue',ref,'B');b.link('leg','ReturnValue',ref,'bPickA')
    b.get('body','Body',2350,600);b.fn('frame',SC+'GetSocketTransform',2600,600,TransformSpace='RTS_World')
    b.link('body','Body','frame','self');b.link('bone','ReturnValue','frame','InSocketName')
    b.fn('point',K+'TransformLocation',2900,650);b.link('frame','ReturnValue','point','T');b.link('offset','ReturnValue','point','Location')
    b.fn('xyz',K+'BreakVector',3150,650);b.link('point','ReturnValue','xyz','InVec')
    b.fn('center',K+'MakeColor',3400,650)
    for x,c in zip('XYZ','RGB'):b.link('xyz',x,'center',c)
    b.link('radius','ReturnValue','center','A')
    tail=entry
    for i,part in enumerate(('StartOutfit','StartPants','Shirt','Trousers','Suit')):
        x=3700+i*600;b.get(part,part,x,300)
        for param,kind,value in [('CorruptionCenter','Color','center'),('CorruptionPulse','Scalar','pulse')]:
            ref=part+param;b.fn(ref,'/Script/Engine.MeshComponent:Set'+kind+'ParameterValueOnMaterials',x,0 if kind=='Color' else 150,ParameterName=param)
            b.link(part,part,ref,'self');b.link(value,'ReturnValue',ref,'ParameterValue');b.chain(tail,ref);tail=ref
    b.get('smoke','ClothSmoke',6800,350);b.fn('position',SC+'K2_SetWorldLocation',6800,0)
    b.link('smoke','ClothSmoke','position','self');b.link('point','ReturnValue','position','NewLocation');b.chain(tail,'position')
    b.fn('emit',K+'Greater_DoubleDouble',6800,650,B=.6);b.link('pulse','ReturnValue','emit','A')
    b.get('previous','bCorruptionSmoking',6800,850);b.fn('changed',K+'NotEqual_BoolBool',7100,650)
    b.link('emit','ReturnValue','changed','A');b.link('previous','bCorruptionSmoking','changed','B')
    b.node('edge','branch',7100,0);b.link('changed','ReturnValue','edge','Condition');b.chain('position','edge')
    b.set('remember','bCorruptionSmoking',7400,0);b.link('emit','ReturnValue','remember','bCorruptionSmoking');b.chain('edge','remember')
    b.node('active','branch',7700,0);b.link('emit','ReturnValue','active','Condition');b.chain('remember','active')
    for ref,fn,y in [('start','Activate',-150),('stop','Deactivate',150)]:
        b.fn(ref,'/Script/Niagara.NiagaraComponent:'+fn,8000,y);b.link('smoke','ClothSmoke',ref,'self')
    b.chain('active','start');b.link('active','else','stop','execute')
    b.comment('Cloth patch and smoke',[o['ref'] for o in b.ops if 'ref' in o]);b.run()

def wire():
    nodes,edges=inspect(P,'UpdateClothWrinkles')
    if not any(n['title'].replace(' ','')==FN for n in nodes):
        tails=[n for n in nodes if n['title'].replace(' ','')=='SetColorParameterValueOnMaterials' and not any(e['from_node']==n['node_id'] and e['from_pin']=='then' for e in edges)]
        assert len(tails)==1,[(n['title'],n['node_id']) for n in tails]
        hook=Batch(P,'UpdateClothWrinkles');hook.fn('corruption',C+':'+FN,15800,0);hook.chain(tails[0]['node_id'],'corruption');hook.run()
if __name__=='__main__':
    assert not call('editor_get_state')['pie_running']
    token=h.lease_acquire(h.agent_id(),['asset:'+P],ttl_s=120,wait_s=30)
    try:setup();graph();wire()
    finally:h.release(h.agent_id(),token)
