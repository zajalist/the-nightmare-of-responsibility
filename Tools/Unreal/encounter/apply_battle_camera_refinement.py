"""Keep battle shots on one side of the action axis; patch existing numeric pins only."""
import math,sys,json,os
from pathlib import Path
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import Batch,inspect
from battle_presentation import SHOTS,selftest

P='/Game/FoA/Gameplay/Encounter/BP_Encounter'

def main():
    selftest();assert all(pos[1]>0 for pos,_,_ in SHOTS.values()),'Crosses the action axis'
    assert not h.call('editor_get_state')['data']['pie_running']
    owner=h.agent_id() or 'main:presentation';os.environ['HAYBA_AGENT_ID']=owner
    token=h.lease_acquire(owner,['asset:'+P],ttl_s=40,wait_s=3);os.environ['FOA_LEASE']=token
    try:
        ns,es=inspect(P,'SetBattleShot');nodes={n['node_id']:n for n in ns}
        def source(node,pin):return next(e['from_node'] for e in es if e['to_node']==node and e['to_pin']==pin)
        def dest(node,pin):return next(e['to_node'] for e in es if e['from_node']==node and e['from_pin']==pin)
        b=Batch(P,'SetBattleShot')
        for name,(loc,aim,fov) in SHOTS.items():
            cmp=next(n for n in ns if 'Equal' in n['title'] and any(p['name']=='B' and p.get('default_value')==name for p in n['pins']))
            branch=dest(cmp['node_id'],'ReturnValue');move=dest(branch,'then')
            assert 'RelativeLocationAndRotation' in nodes[move]['title'].replace(' ',''),nodes[move]['title']
            vector=source(move,'NewLocation');rot=source(move,'NewRotation');zoom=dest(move,'then')
            for pin,val in zip('XYZ',loc):b.pin(vector,pin,val)
            delta=[v-u for u,v in zip(loc,aim)]
            b.pin(rot,'Pitch',math.degrees(math.atan2(delta[2],math.hypot(*delta[:2]))))
            b.pin(rot,'Yaw',math.degrees(math.atan2(delta[1],delta[0])));b.pin(rot,'Roll',0)
            b.pin(zoom,'InFieldOfView',fov)
        result=b.run()
        Path('Saved/PresentationReview/battle_camera_applied.json').write_text(json.dumps({'shots':SHOTS,'result':result},indent=1))
    finally:h.release(owner,token);os.environ.pop('FOA_LEASE',None)

if __name__=='__main__':main()
