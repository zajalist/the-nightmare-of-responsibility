"""Final position/comment-only cleanup; preserve every executable/data edge."""
import os,sys
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import Batch,inspect
P='/Game/FoA/Gameplay/Encounter/BP_Garment';owner='character_contact_layout';os.environ['HAYBA_AGENT_ID']=owner
assert not h.call('editor_get_state')['data']['pie_running']
token=h.lease_acquire(owner,['asset:'+P],ttl_s=25,wait_s=3)
norm=lambda s:''.join(s.lower().split())
try:
    for graph in ('StartPlayerContact','StopPlayerContact'):
        ns,edges=inspect(P,graph)
        removed=[n['node_id'] for n in ns if n['title']=='Comment' or (graph=='StartPlayerContact' and norm(n['title'])=='getcontactfill')]
        r=h.call('blueprint_remove_nodes',dict(path=P,graph_name=graph,node_ids=removed));assert r.get('ok'),r
        b=Batch(P,graph)
        positions=({'setlightingchannels':(2050,0),'getrig':None,'andboolean':(900,450)} if graph.startswith('Start') else {
            'stopplayercontact':(0,0),'setintensity':(250,0),'setlightingchannels':(600,0),'branch':(950,0),
            'setrelativelocation':(1250,0),'setbplayercontact':(1600,0),'setplayercontacthand':(1900,0),
            'getcontactfill':(250,250),'getrig':(600,250),'getbplayercontact':(950,250),'getbody':(1250,300),'getplayercontacthome':(1600,300)})
        rigs=[n['node_id'] for n in ns if norm(n['title'])=='getrig']
        for n in ns:
            if n['node_id'] in removed:continue
            title=norm(n['title']);xy=positions.get(title)
            if graph.startswith('Start') and title=='getrig' and n['node_id']==rigs[-1]:xy=(2050,300)
            if xy:b.ops.append(dict(op='move',node_id=n['node_id'],x=xy[0],y=xy[1]))
        b.comment('Begin measured contact' if graph.startswith('Start') else 'Restore contact and lighting',[n['node_id'] for n in ns if n['node_id'] not in removed]);b.run()
        after,after_edges=inspect(P,graph);assert edges==after_edges,'Layout changed connections'
finally:h.release(owner,token)
