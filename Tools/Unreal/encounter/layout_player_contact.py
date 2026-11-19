"""Position-only clearance for wide native transform nodes, preserving every edge/default."""
import sys,os
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import inspect
E='/Game/FoA/Gameplay/Encounter/BP_Encounter';G='/Game/FoA/Gameplay/Encounter/BP_Garment'
norm=lambda s:''.join(s.lower().split())
owner='character_contact_layout';os.environ['HAYBA_AGENT_ID']=owner
assert not h.call('editor_get_state')['data']['pie_running']
token=h.lease_acquire(owner,['asset:'+E,'asset:'+G],ttl_s=25,wait_s=3)
try:
    for p,graph in [(E,'BeginPlayerContact'),(G,'StepPlayerContact')]:
        ns,es=inspect(p,graph);ops=[]
        weight_index=0
        for n in ns:
            pos=None;title=norm(n['title'])
            if graph=='BeginPlayerContact':
                for match,xy in [('getactorofclass',(700,0)),('setcontactgarment',(1100,0)),('startplayercontact',(1450,0)),('getbody',(1050,300)),('branch',(350,0)),('isvalid',(350,300))]:
                    if title==match:pos=xy
            elif title=='vector*float':
                pos=(1980,1500+weight_index*310);weight_index+=1
            if pos:ops.append(dict(op='move',node_id=n['node_id'],x=pos[0],y=pos[1]))
        assert ops,(p,graph)
        ops.append(dict(op='fit_comments'))
        r=h.call('blueprint_graph_batch',dict(path=p,graph_name=graph,ops=ops,compile=True,save=True));assert r.get('ok'),r
        after,edges=inspect(p,graph);assert es==edges
        print(graph,'positions only',len(ops)-1)
finally:h.release(owner,token)
