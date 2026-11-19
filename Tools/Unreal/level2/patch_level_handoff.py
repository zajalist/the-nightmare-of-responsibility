"""L1 exit enters the existing dream journey; title and restart dispose that journey.
Surgical patches preserve the existing frontend, debug controls and story event graph.
Run under a coordinator lease for BeatDirector and FoAFrontEnd after threshold compiles.
"""
import os
import sys
sys.path[:0]=['P:/FoA/Tools/Unreal/level2','P:/FoA/Tools/Unreal/player','P:/FoA/Tools/Unreal']
from build_threshold import BP, STORY, FRONT, JOURNEY, spawn
from build_drive import G, call, cls, GS, SL
from held_tool_graphs import Batch, inspect
import hayba_call as h


def open_door():
    g=G(STORY,'OpenTheDoor')
    actor=g.do(GS+'GetActorOfClass',ActorClass=cls(BP))
    valid=g.branch(g.f(SL+'IsValid',Object=actor));g.side(valid,False)
    spawn(g,BP)
    g.finish()


def end_level():
    ns,es=inspect(STORY,'EventGraph')
    if any(n['title']=='Continue into the dream' for n in ns):return
    entry=next(n['node_id'] for n in ns if n['title']=='EndLevel' and not any(p['name']=='self' for p in n['pins']))
    edge=next(e for e in es if e['from_node']==entry and e['from_pin']=='then')
    b=Batch(STORY,'EventGraph')
    b.cut(entry,'then',edge['to_node'],edge['to_pin'])
    b.fn('open',cls(STORY)+':OpenTheDoor',300,2400)
    b.fn('find',GS+'GetActorOfClass',600,2400,ActorClass=cls(BP))
    b.node('cast','cast',900,2400,class_path=cls(BP))
    b.link('find','ReturnValue','cast','Object')
    b.fn('start',cls(BP)+':StartThreshold',1200,2400)
    b.link('cast','AsBP Dream Threshold','start','self')
    b.chain(entry,'open','find','cast','start')
    b.comment('Continue into the dream',['open','find','cast','start']);b.run()


def cleanup(fn):
    ns,es=inspect(FRONT,fn)
    title='Release Level 2 before '+fn
    if any(n['title']==title for n in ns):return
    entry=next(n['node_id'] for n in ns if n['title']==fn and not any(p['name']=='self' for p in n['pins']))
    edge=next(e for e in es if e['from_node']==entry and e['from_pin']=='then')
    b=Batch(FRONT,fn)
    b.cut(entry,'then',edge['to_node'],edge['to_pin'])
    b.fn('find',GS+'GetActorOfClass',-1400,0,ActorClass=cls(BP))
    b.node('cast','cast',-1100,0,class_path=cls(BP))
    b.link('find','ReturnValue','cast','Object');b.chain(entry,'find','cast')
    b.fn('clean',cls(BP)+':Abort',-800,0)
    b.link('cast','AsBP Dream Threshold','clean','self');b.chain('cast','clean')
    b.link('clean','then',edge['to_node'],edge['to_pin'])
    b.link('cast','CastFailed',edge['to_node'],edge['to_pin'])
    b.comment(title,['find','cast','clean']);b.run()


def main():
    assert h.leases_of(os.environ['FOA_AGENT'])
    assert not call('editor_get_state')['pie_running']
    open_door();end_level();cleanup('ReturnToTitle');cleanup('RestartDay')
    for path in (STORY,FRONT):
        result=call('blueprint_compile',path=path)
        assert result.get('error_count',0)==0,result
        call('asset_save',asset_paths=[path])

if __name__=='__main__':main()
