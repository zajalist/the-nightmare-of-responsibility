"""Import only the six UV-preserving shards; all materials are reused in the BP."""
import json,os,sys,shutil,tempfile
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h
F='/Game/FoA/Props/VaseFragments';owner='room-takeover'
def c(n,**p):
 r=h.call(n,p);assert r.get('ok'),r
 d=r.get('data',{});assert d.get('ok',True),d
 return d
assert not c('editor_get_state')['pie_running']
lease=h.lease_acquire(owner,['asset:'+F],ttl_s=120,wait_s=15)
try:
 assert not c('editor_get_state')['pie_running']
 cache=Path(tempfile.gettempdir())/'hayba-asset-connectors'/'FoA'/'vase_fragments';cache.mkdir(parents=True,exist_ok=True)
 result=[]
 for row in json.loads(Path('P:/FoA-Assets/procedural/vase_fragments/fragments.json').read_text()):
  if not Path('P:/FoA/Content/FoA/Props/VaseFragments/'+row['name']+'.uasset').exists():
   target=cache/(row['name']+'.fbx');shutil.copyfile(row['file'],target)
   result.append(c('asset_import',source_file=str(target),destination_path=F,asset_type='static_mesh'))
 Path('P:/FoA/Saved/WorldShots/vase_fragments_import.json').write_text(json.dumps(result,indent=1))
 print('Imported six ceramic fragments; material master and textures reused')
finally:h.release(owner,lease)
