"""Narrow native rebuild: extraction helpers and its side camera only."""
import os,sys
from build_clothing_chase import P,call,h,write_queue,build_motion
from clothing_hanger_graphs import build

os.environ['HAYBA_AGENT_ID']='clothing_search'
assert not call('editor_get_state')['pie_running']
token=h.lease_acquire('clothing_search',['asset:'+P],ttl_s=120,wait_s=3)
try:
    if '--hands-only' not in sys.argv:
        write_queue('BeginClothingToss',4,5,1)
        build_motion()
    build()
finally:
    h.release('clothing_search',token)
