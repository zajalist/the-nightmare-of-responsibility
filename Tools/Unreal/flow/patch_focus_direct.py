"""Prefer the visible crosshair surface over a sticky sphere-sweep neighbour.

Offline-safe plan builder. Apply only after the direct-ray pickup diagnostic confirms
the intended object is actually visible. Keeps all reach, interface and hold checks.
"""
import os
import sys
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import Batch,inspect

P='/Game/FoA/Gameplay/BPC_Interactor'
K='/Script/Engine.KismetMathLibrary:'
MARKER='Prefer the crosshair surface'

def norm(s):return s.replace(' ','').lower()

def plan(nodes,edges):
    b=Batch(P,'FindBest')
    if any(norm(n['title']) in ('linetraceforobjects','linetracesingleforobjects') for n in nodes):return b
    by={n['node_id']:n for n in nodes}
    def only(title):
        found=[n['node_id'] for n in nodes if norm(n['title'])==norm(title)]
        assert len(found)==1,(title,found)
        return found[0]
    sphere=only('Multi Sphere Trace For Objects');hit=only('BreakHitResult')
    before=next(e for e in edges if e['to_node']==sphere and e['to_pin']=='execute')
    setcost=only('Set BestCost')
    cost=next(e for e in edges if e['to_node']==setcost and e['to_pin']=='BestCost')
    consumers=[e for e in edges if e['from_node']==cost['from_node'] and e['from_pin']==cost['from_pin']]
    assert len(consumers)==2,consumers
    b.fn('direct_ray','/Script/Engine.KismetSystemLibrary:LineTraceSingleForObjects',1000,-600,
         bTraceComplex='true',bIgnoreSelf='true')
    for pin in ('Start','End','ObjectTypes'):
        source=next(e for e in edges if e['to_node']==sphere and e['to_pin']==pin)
        b.link(source['from_node'],source['from_pin'],'direct_ray',pin)
    b.cut(before['from_node'],before['from_pin'],sphere,'execute')
    b.link(before['from_node'],before['from_pin'],'direct_ray','execute');b.chain('direct_ray',sphere)
    b.fn('direct_hit','/Script/Engine.GameplayStatics:BreakHitResult',1400,-600)
    b.link('direct_ray','OutHit','direct_hit','Hit')
    b.fn('on_crosshair',K+'EqualEqual_ObjectObject',1800,-600)
    b.link('direct_hit','HitActor','on_crosshair','A');b.link(hit,'HitActor','on_crosshair','B')
    b.fn('ray_bonus',K+'SelectFloat',2100,-600,A=180,B=0)
    b.link('on_crosshair','ReturnValue','ray_bonus','bPickA')
    b.fn('ray_cost',K+'Subtract_DoubleDouble',2400,-600)
    b.link(cost['from_node'],cost['from_pin'],'ray_cost','A');b.link('ray_bonus','ReturnValue','ray_cost','B')
    for e in consumers:
        b.cut(e['from_node'],e['from_pin'],e['to_node'],e['to_pin'])
        b.link('ray_cost','ReturnValue',e['to_node'],e['to_pin'])
    b.comment(MARKER,['direct_ray','direct_hit','on_crosshair','ray_bonus','ray_cost'])
    return b

def main():
    owner='main-level1-focus';os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner)
    assert not h.call('editor_get_state',{},owner=owner)['data']['pie_running']
    token=h.lease_acquire(owner,['asset:'+P],ttl_s=60,wait_s=3)
    os.environ['FOA_LEASE']=token
    try:
        batch=plan(*inspect(P,'FindBest'))
        if batch.ops:batch.run()
    finally:
        h.release(owner,token);os.environ.pop('FOA_LEASE',None)

if __name__=='__main__':main()
