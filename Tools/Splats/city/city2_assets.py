"""Native Hayba assets for city2, one short resource lease per invocation."""
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode=True
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player','P:/FoA/Tools/Splats']
import hayba_call as h
import editor_lock
from held_tool_graphs import Batch,inspect
from build_splat_world_lean import nodes,custom,link
ROOT='/Game/FoA/Level2/City/Expanded'
BP=ROOT+'/BP_City2Sector'
FOG=ROOT+'/M_City2_EdgeFog'
OUT=Path('P:/FoA/Saved/Codex/city2');OUT.mkdir(parents=True,exist_ok=True)
os.environ.update(FOA_AGENT='city2',HAYBA_AGENT_ID='city2')


def call(cmd,**args):
    r=h.call(cmd,args,timeout=30)
    assert r.get('ok'),r
    d=r.get('data') or {};assert not d.get('has_errors') and d.get('ok',True),d
    return d


def fog():
    if not h.call('material_get_info',{'path':FOG}).get('ok'):
        call('material_create',package_path=ROOT,name='M_City2_EdgeFog')
    call('material_set_property',material_path=FOG,properties={'domain':'PostProcess','shading_model':'Unlit'})
    shader='''float2 outside=max(abs(P.xy-float2(70000,0))-float2(66000,46000),0);
float m=saturate(max(outside.x,outside.y)/22000.0); m=m*m*(3-2*m);
float grain=frac(sin(dot(floor(P.xy/22.0),float2(12.9898,78.233)))*43758.5453);
return lerp(Scene.rgb,float3(.022,.022,.022),m*(.80+.15*grain));'''
    ids,info=nodes(FOG,[('scene','SceneTexture',[-650,-100],{'SceneTextureId':'PPI_PostProcessInput0'}),
        ('world','WorldPosition',[-650,140],{}),('fog','Custom',[-280,0],custom('Night edge fog','CMOT_Float3',('Scene','P'),shader))])
    link(FOG,ids,'scene','fog','Scene');link(FOG,ids,'world','fog','P')
    call('material_connect_nodes',material_path=FOG,from_node=ids['fog'],from_output_index=0,to_property='emissive_color')
    if not info.get('comments'):call('material_add_comment',material_path=FOG,text='Night edge fog',node_pos=[-780,-230],size=[900,620],color=[.16,.16,.16])
    call('material_validate',material_path=FOG)
    result=call('material_compile',material_path=FOG)
    (OUT/'fog_compile.json').write_text(json.dumps(result,indent=2))


def sector_blueprint():
    if not h.call('blueprint_get_info',{'path':BP}).get('ok'):
        call('blueprint_create',name='BP_City2Sector',package_path=BP,parent_class_path='/Script/Engine.Actor')
    info=call('blueprint_get_info',path=BP)
    have={v['name'] for v in info['variables']}
    for name,typ in [('SectorPackage','string'),('Stream','object:/Script/Engine.LevelStreamingDynamic')]:
        if name not in have:call('blueprint_add_variable',path=BP,variable_name=name,variable_type=typ,instance_editable=name=='SectorPackage',category='City streaming')
    if 'Root' not in {c['name'] for c in info.get('components',[])}:
        call('blueprint_add_component',path=BP,component_name='Root',component_class_path='/Script/Engine.SceneComponent')
    if 'UpdateSector' not in info['functions']:call('blueprint_add_function',path=BP,function_name='UpdateSector')
    n,_=inspect(BP,'UpdateSector')
    if len(n)<=2:
        entry=next(x['node_id'] for x in n if 'Entry' in x.get('type','') or x.get('title')=='UpdateSector')
        b=Batch(BP,'UpdateSector')
        b.node('self','self',0,500)
        b.fn('manager','/Script/Engine.GameplayStatics:GetPlayerCameraManager',0,750,PlayerIndex=0)
        b.link('self','self','manager','WorldContextObject')
        b.fn('camera','/Script/Engine.PlayerCameraManager:GetCameraLocation',300,750);b.link('manager','ReturnValue','camera','self')
        b.fn('centre','/Script/Engine.Actor:K2_GetActorLocation',300,950)
        b.fn('distance','/Script/Engine.KismetMathLibrary:Vector_Distance2D',600,850)
        b.link('camera','ReturnValue','distance','V1');b.link('centre','ReturnValue','distance','V2')
        b.fn('near','/Script/Engine.KismetMathLibrary:Less_DoubleDouble',900,850,B=26000)
        b.link('distance','ReturnValue','near','A')
        b.get('stream','Stream',0,200)
        b.fn('valid','/Script/Engine.KismetSystemLibrary:IsValid',280,200);b.link('stream','Stream','valid','Object')
        b.node('has','branch',550,0);b.link(entry,'then','has','execute');b.link('valid','ReturnValue','has','Condition')
        b.fn('visible','/Script/Engine.LevelStreaming:SetShouldBeVisible',900,0)
        b.link('has','then','visible','execute');b.link('stream','Stream','visible','self');b.link('near','ReturnValue','visible','bInShouldBeVisible')
        b.fn('loaded','/Script/Engine.LevelStreaming:SetShouldBeLoaded',1250,0)
        b.chain('visible','loaded');b.link('stream','Stream','loaded','self');b.link('near','ReturnValue','loaded','bInShouldBeLoaded')
        b.node('first','branch',900,350);b.link('has','else','first','execute');b.link('near','ReturnValue','first','Condition')
        b.get('level','SectorPackage',1100,650)
        b.fn('load','/Script/Engine.LevelStreamingDynamic:LoadLevelInstance',1250,350,Location='0,0,0',Rotation='0,0,0')
        b.link('first','then','load','execute');b.link('self','self','load','WorldContextObject');b.link('level','SectorPackage','load','LevelName')
        b.set('remember','Stream',1700,350);b.chain('load','remember');b.link('load','ReturnValue','remember','Stream')
        b.comment('Camera distance',['self','manager','camera','centre','distance','near'])
        b.comment('Load nearby sectors',['stream','valid','has','visible','loaded','first','level','load','remember'])
        b.run()
    n,_=inspect(BP,'EventGraph')
    if not any(x.get('title','').replace(' ','')=='UpdateSector' for x in n):
        b=Batch(BP,'EventGraph')
        b.ops.append({'op':'add_event','ref':'tick','event_name':'ReceiveTick','x':0,'y':400})
        b.fn('update',BP+'.BP_City2Sector_C:UpdateSector',380,400);b.chain('tick','update')
        b.ops.append({'op':'add_event','ref':'begin','event_name':'ReceiveBeginPlay','x':0,'y':0})
        b.fn('interval','/Script/Engine.Actor:SetActorTickInterval',350,0,TickInterval=.75);b.chain('begin','interval')
        b.fn('initial',BP+'.BP_City2Sector_C:UpdateSector',700,0);b.chain('interval','initial')
        b.comment('Streaming interval',['begin','interval','initial','tick','update']);b.run()
    result=call('blueprint_compile',path=BP);assert not result.get('error_count'),result
    call('asset_save',asset_paths=[BP]);(OUT/'streaming_compile.json').write_text(json.dumps(result,indent=2))


def ground_instances():
    src=Path('P:/FoA-Assets/level2/toronto/processed/queen_1600m')
    names=[t['name'] for t in json.loads((src/'ground_manifest.json').read_text())['tiles']]+['T_City2_Skirt']
    for name in names:
        mi='MI'+name[1:]
        if not h.call('material_get_info',{'path':ROOT+'/'+mi}).get('ok'):
            call('material_create_instance',parent_material_path='/Game/FoA/Level2/City/M_City_Ground',package_path=ROOT,name=mi)
        call('material_set_param',instance_path=ROOT+'/'+mi,param_name='Ground',value=ROOT+'/'+name+'.'+name)
        call('asset_save',asset_paths=[ROOT+'/'+mi])


def sector_names():
    info=call('blueprint_get_info',path=BP)
    if 'SectorPackage' not in {v['name'] for v in info['variables']}:
        call('blueprint_add_variable',path=BP,variable_name='SectorPackage',variable_type='string',instance_editable=True,category='City streaming')
    n,_=inspect(BP,'UpdateSector')
    by_title=lambda title:next(v['node_id'] for v in n if v.get('title')==title)
    first=[v['node_id'] for v in n if v.get('title')=='Branch'][-1]
    getter=next((v['node_id'] for v in n if v.get('title')=='Get SectorPackage'),None)
    loader=next((v['node_id'] for v in n if v.get('title')=='Load Level Instance (by Name)'),None)
    try:
        if not getter:getter=call('blueprint_add_node',path=BP,graph_name='UpdateSector',node_type='variable_get',variable_name='SectorPackage',x=1100,y=650)['node_id']
        if not loader:loader=call('blueprint_add_node',path=BP,graph_name='UpdateSector',node_type='call_function',class_path='/Script/Engine.LevelStreamingDynamic',function_name='LoadLevelInstance',x=1250,y=350)['node_id']
        for a,ap,b,bp in [(getter,'SectorPackage',loader,'LevelName'),(by_title('Self-Reference'),'self',loader,'WorldContextObject'),
                          (loader,'ReturnValue',by_title('Set Stream'),'Stream'),(loader,'then',by_title('Set Stream'),'execute'),(first,'then',loader,'execute')]:
            call('blueprint_connect_nodes',path=BP,graph_name='UpdateSector',from_node=a,from_pin=ap,to_node=b,to_pin=bp)
    finally:compile_sector()


def compile_sector():
    result=call('blueprint_compile',path=BP)
    assert not result.get('error_count'),result
    (OUT/'streaming_compile.json').write_text(json.dumps(result,indent=2))


def layout():
    n,_=inspect(BP,'UpdateSector');ops=[]
    positions={'Self-Reference':(0,1000),'GetPlayerCameraManager':(0,1250),'GetCameraLocation':(350,1250),
               'Get Actor Location':(350,1450),'Distance2D (Vector)':(700,1330),'float < float':(1050,1330)}
    for node in n:
        title=node.get('title','').split('\n')[0]
        if title in positions:
            x,y=positions[title];ops.append({'op':'move','node_id':node['node_id'],'x':x,'y':y})
    assert len(ops)>=5,(ops,[x.get('title') for x in n])
    camera={o['node_id'] for o in ops}
    comments={v['node_id'] for v in n if v.get('title')=='Comment'}
    ops += [{'op':'remove','node_ids':sorted(comments)}] if comments else []
    ops += [{'op':'comment','title':'Camera distance','node_ids':sorted(camera),'color':[.16,.16,.16]},
            {'op':'comment','title':'Load nearby sectors','node_ids':[v['node_id'] for v in n if v['node_id'] not in camera|comments],'color':[.16,.16,.16]}]
    call('blueprint_graph_batch',path=BP,graph_name='UpdateSector',ops=ops,compile=True,save=True)
    call('material_validate',material_path=FOG)


if __name__=='__main__':
    editor_lock.acquire('city2',areas=[ROOT],ttl=100,wait_s=20)
    try:globals()[sys.argv[1]]()
    finally:editor_lock.release('city2')
