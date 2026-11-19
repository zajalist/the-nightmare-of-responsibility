"""Reuse RoomAudio's existing crossfade for Dream, City and CV battle music."""
import os
import sys
sys.path[:0]=['P:/FoA/Tools/Unreal/level2','P:/FoA/Tools/Unreal/player','P:/FoA/Tools/Unreal']
from build_drive import call, K
from held_tool_graphs import Batch, inspect
import hayba_call as h
P='/Game/FoA/Audio/BP_RoomAudio'


def main():
    assert h.leases_of(os.environ['FOA_AGENT'])
    assert not call('editor_get_state')['pie_running']
    info=call('blueprint_get_info',path=P)
    if not any(v['name']=='MusicOverride' for v in info['variables']):
        call('blueprint_add_variable',path=P,variable_name='MusicOverride',variable_type='name',default_value='None',category='Music')
    ns,es=inspect(P,'UpdateMusic')
    if not any(n['title']=='Journey music' for n in ns):
        state=next(n['node_id'] for n in ns if n['title'].replace(' ','')=='SetMusicState')
        edge=next(e for e in es if e['to_node']==state and e['to_pin']=='MusicState')
        source=edge['from_node'];pin=edge['from_pin']
        consumers=[e for e in es if e['from_node']==source and e['from_pin']==pin]
        assert len(consumers)==3,consumers
        b=Batch(P,'UpdateMusic')
        b.get('override','MusicOverride',5550,1400)
        b.fn('valid',K+'NotEqual_NameName',5800,1400,B='None')
        b.link('override','MusicOverride','valid','A')
        b.fn('choose',K+'SelectName',6050,1400)
        b.link('override','MusicOverride','choose','A');b.link('valid','ReturnValue','choose','bPickA')
        b.link(source,pin,'choose','B')
        for edge in consumers:
            b.cut(source,pin,edge['to_node'],edge['to_pin']);b.link('choose','ReturnValue',edge['to_node'],edge['to_pin'])
        b.comment('Journey music',['override','valid','choose']);b.run()
    call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/journey_music_defaults.py',resources=['asset:'+P])
    call('blueprint_compile',path=P);call('asset_save',asset_paths=[P])

if __name__=='__main__':main()
