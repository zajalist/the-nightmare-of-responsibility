"""Door-only readiness gate for the existing eased hand IK. No animation changes."""
import os,sys
sys.path.insert(0,'P:/FoA/Tools/Unreal')
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch,inspect,find,DOOR
C=DOOR+'.BP_Door_C';KS='/Script/Engine.KismetSystemLibrary:'
owner='clothing_search';os.environ['HAYBA_AGENT_ID']=owner
def call(name,**kw):
    r=h.call(name,kw,owner=owner);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True),d;return d
assert not call('editor_get_state')['pie_running'],'User PIE active'
token=h.lease_acquire(owner,['asset:'+DOOR],ttl_s=60,wait_s=3)
try:
    if not h.call('blueprint_inspect_graph',dict(path=DOOR,graph_name='MarkDoorToolReady'),owner=owner).get('ok'):
        call('blueprint_add_function',path=DOOR,function_name='MarkDoorToolReady')
    ns,es=inspect(DOOR,'MarkDoorToolReady');e=find(ns,'MarkDoorToolReady')
    if len(ns)<3:
        b=Batch(DOOR,'MarkDoorToolReady');b.get('active','bToolActive',0,300)
        b.node('owned','branch',300,0);b.link('active','bToolActive','owned','Condition')
        b.set('ready','bToolReady',600,0);b.pin('ready','bToolReady','true')
        b.fn('refresh',C+':RefreshDoorTool',900,0);b.chain(e,'owned','ready','refresh');b.run()
    ns,es=inspect(DOOR,'HoldDoorToolPose')
    if not any(n['title']=='RefreshDoorTool' for n in ns):
        ready=find(ns,'Set bToolReady');assert not any(x['from_node']==ready and x['from_pin']=='then' for x in es)
        b=Batch(DOOR,'HoldDoorToolPose');b.fn('contact',C+':RefreshDoorTool',1800,0)
        b.set('wait','bToolReady',2100,0);b.pin('wait','bToolReady','false')
        b.fn('settled',KS+'K2_SetTimer',2400,0,FunctionName='MarkDoorToolReady',Time=.75,bLooping='false')
        b.chain(ready,'contact','wait','settled');b.run()
    ns,es=inspect(DOOR,'RestoreDoorTool')
    if not any(p.get('default_value')=='MarkDoorToolReady' for n in ns for p in n.get('pins',[])):
        e=find(ns,'RestoreDoorTool');edge=next(x for x in es if x['from_node']==e and x['from_pin']=='then')
        b=Batch(DOOR,'RestoreDoorTool');b.fn('clear',KS+'K2_ClearTimer',-300,0,FunctionName='MarkDoorToolReady')
        b.cut(e,'then',edge['to_node'],edge['to_pin']);b.chain(e,'clear');b.link('clear','then',edge['to_node'],edge['to_pin']);b.run()
    print('Door hand settlement saved; repeat actual ready/turn/cancel proof required')
finally:h.release(owner,token)
