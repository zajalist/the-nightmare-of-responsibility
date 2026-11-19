"""Root-coordinated short editor window; no PIE, material graphs only."""
import json,os,sys,time,subprocess
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
LANE='room-takeover-graphs'
os.environ['HAYBA_AGENT_ID']=os.environ['FOA_AGENT']=LANE
OUT=Path('P:/FoA/Saved/GraphShots/RoomTakeover')
receipt=OUT/'materials_complete.json'
def state():
 r=h.call('editor_get_state',{});assert r.get('ok'),r
 return r['data']
assert not state()['pie_running'],'User PIE active'
token=h.lease_acquire(LANE,['global'],ttl_s=25,wait_s=10)
try:
 assert not state()['pie_running'],'PIE started while waiting'
 receipt.unlink(missing_ok=True)
 p=subprocess.run([sys.executable,'Tools/Unreal/integration/run_read.py','Tools/Splats/capture_takeover_graphs.py','FOA_MATERIAL_GRAPHS=1'],capture_output=True,text=True,timeout=7)
 print(p.stdout,p.stderr,flush=True);assert p.returncode==0
 start=time.monotonic()
 while not receipt.exists() and time.monotonic()-start<13:time.sleep(.4)
 assert receipt.exists(),'Material graph capture did not finish'
 paths=json.loads(receipt.read_text())
 assert len(paths)==2 and all(Path(x).is_file() for x in paths),paths
 print(json.dumps(paths),flush=True)
finally:h.release(LANE,token)
