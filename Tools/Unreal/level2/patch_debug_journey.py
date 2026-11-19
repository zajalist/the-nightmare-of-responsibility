"""Extend the existing gated F6 action to the dream path and Level 2 journey."""
import os
import sys
sys.path[:0]=['P:/FoA/Tools/Unreal/level2','P:/FoA/Tools/Unreal/player','P:/FoA/Tools/Unreal']
from build_threshold import BP, STORY, FRONT, JOURNEY
from build_drive import G, call, cls, GS
from held_tool_graphs import Batch, inspect
import hayba_call as h
GI='/Game/FoA/Gameplay/GI_FoA'

def main():
    assert h.leases_of(os.environ['FOA_AGENT'])
    assert not call('editor_get_state')['pie_running']
    info=call('blueprint_get_info',path=FRONT)
    if 'DebugLevelStep' not in info['functions']:call('blueprint_add_function',path=FRONT,function_name='DebugLevelStep')
    g=G(FRONT,'DebugLevelStep')
    game=g.cast(g.f(GS+'GetGameInstance'),cls(GI),'GI Fo A')
    g.do(cls(GI)+':SetProofProgressContext',self=game,Slot='FoA_QA_DebugSkip',
        Known=g.getv('Knowledge',game,GI),Lines=g.getv('Notebook',game,GI))
    threshold=g.do(GS+'GetActorOfClass',ActorClass=cls(BP))
    threshold=g.cast(threshold,cls(BP),'BP Dream Threshold');tc=g.tail
    path=g.branch(g.math('EqualEqual_IntInt',A=g.getv('Phase',threshold,BP),B=3));g.side(path)
    g.do(cls(BP)+':BeginFall',self=threshold)
    g.side(path,False)
    journey=g.do(GS+'GetActorOfClass',ActorClass=cls(JOURNEY))
    journey=g.cast(journey,cls(JOURNEY),'BP L2Journey');jc=g.tail
    g.do(cls(JOURNEY)+':DebugNextStep',self=journey)
    g.tail=tc;g._side='CastFailed'
    story=g.do(GS+'GetActorOfClass',ActorClass=cls(STORY));fallback=story[0]
    g.link(jc,'CastFailed',fallback,'execute')
    story=g.cast(story,cls(STORY),'BP Beat Director')
    g.do(cls(STORY)+':DebugNextStep',self=story);g.finish()
    ns,es=inspect(FRONT,'DebugNextStep')
    if not any(n['title']=='Level-aware playtest skip' for n in ns):
        old=next(n['node_id'] for n in ns if n['title'].split('\n')[0].replace(' ','')=='DebugNextStep' and any(p['name']=='self' for p in n['pins']))
        edge=next(e for e in es if e['to_node']==old and e['to_pin']=='execute')
        b=Batch(FRONT,'DebugNextStep')
        b.cut(edge['from_node'],edge['from_pin'],old,'execute')
        b.fn('advance',cls(FRONT)+':DebugLevelStep',1800,0)
        b.link(edge['from_node'],edge['from_pin'],'advance','execute')
        b.comment('Level-aware playtest skip',['advance']);b.run()
    call('blueprint_compile',path=FRONT);call('asset_save',asset_paths=[FRONT])

if __name__=='__main__':main()
