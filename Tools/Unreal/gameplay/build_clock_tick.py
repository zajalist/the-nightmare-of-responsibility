"""Native Hayba build: tick existing clock hands around their authored spindle."""
import json, os, sys
from pathlib import Path
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h
PATH = '/Game/FoA/Gameplay/BP_ClockTick'
# The clock face points along local +Y, so negative pitch turns clockwise.
HANDS = {'Hours': -1/120, 'Minutes': -.1, 'Seconds': -6.}
owner = os.environ.get('HAYBA_AGENT_ID', 'main:finish')
assert not h.call('editor_get_state')['data']['pie_running']
lease = h.lease_acquire(owner, ['asset:'+PATH], ttl_s=60, wait_s=5)
def call(cmd, **params):
    r=h.call(cmd,params,owner=owner,lease=lease)
    assert r.get('ok'),r
    d=r.get('data',{}); assert d.get('ok',True),d
    return d
try:
    graph=call('blueprint_inspect_graph',path=PATH,graph_name='EventGraph')
    stale=[n['node_id'] for n in graph['nodes'] if n['title'] not in ('Event BeginPlay','ClockTick')]
    if stale: call('blueprint_graph_batch',path=PATH,graph_name='EventGraph',ops=[dict(op='remove',node_ids=stale)])
    for name in HANDS:
        call('blueprint_add_variable',path=PATH,variable_name=name,variable_type='object:/Script/Engine.Actor',instance_editable=True,category='Clock',update_existing=True)
    ops=[]
    def add(ref,typ,x,y,**kw): ops.append(dict(op='add_node',ref=ref,node_type=typ,x=x,y=y,**kw))
    def connect(a,b,ap='then',bp='execute'): ops.append(dict(op='connect',from_node=a,to_node=b,from_pin=ap,to_pin=bp))
    def value(n,p,v): ops.append(dict(op='set_pin',node_id=n,pin_name=p,value=str(v)))
    ops.append(dict(op='add_event',ref='begin',event_name='ReceiveBeginPlay',x=0,y=0))
    add('timer','timer_by_function',340,0)
    value('timer','FunctionName','ClockTick'); value('timer','Time','1.0'); value('timer','bLooping','true')
    connect('begin','timer')
    add('tick','custom_event',0,600,event_name='ClockTick')
    previous='tick'
    for i,(name,degrees) in enumerate(HANDS.items()):
        x=340+i*680
        add(name,'variable_get',x,950,variable_name=name)
        add(name+'Valid','macro',x,600,macro_name='IsValid')
        add(name+'Turn','call_function',x+300,600,function_name='/Script/Engine.Actor:K2_AddActorLocalRotation')
        connect(name,name+'Valid',name,'InputObject'); connect(name,name+'Turn',name,'self')
        value(name+'Turn','DeltaRotation',f'{degrees}, 0, 0'); value(name+'Turn','bTeleport','true')
        connect(previous,name+'Valid',bp='exec'); connect(name+'Valid',name+'Turn','Is Valid')
        if i: connect(last+'Valid',name+'Valid','Is Not Valid','exec')
        previous,last=name+'Turn',name
    ops += [dict(op='comment',title='One tick each second',node_ids=['begin','timer'],color=[.2,.32,.55]),
            dict(op='comment',title='Clock hand steps',node_ids=['tick']+[n+s for n in HANDS for s in ('','Valid','Turn')],color=[.42,.3,.14]),dict(op='fit_comments')]
    r=call('blueprint_graph_batch',path=PATH,graph_name='EventGraph',ops=ops,compile=True,save=True)
    Path('P:/FoA/Saved/Integration/clock_graph.json').write_text(json.dumps(r,indent=2))
    print(json.dumps({k:v for k,v in r.items() if k not in ('results','refs')}))
finally: h.release(owner,lease)
