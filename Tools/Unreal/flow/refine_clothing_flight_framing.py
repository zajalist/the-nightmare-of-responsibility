"""Camera-only final framing: preserve interaction/state/inventory graphs."""
import os
from build_clothing_chase import P,call,h,write_queue,build_motion
os.environ['HAYBA_AGENT_ID']='clothing_search'
assert not call('editor_get_state')['pie_running']
token=h.lease_acquire('clothing_search',['asset:'+P],ttl_s=90,wait_s=3)
try:
    write_queue('EscapeClothingOne',5,6,2)
    write_queue('EscapeClothingTwo',6,7,3)
    build_motion()
finally:h.release('clothing_search',token)
