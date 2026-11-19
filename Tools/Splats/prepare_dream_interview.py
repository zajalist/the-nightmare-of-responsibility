"""Offline conversion of the ONE user-authorized Aholo interview world; never generates/downloads."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ply_to_splatmesh import convert

SOURCE=Path('P:/FoA-Assets/level2/aholo/dream_interview_20261112')
OUT=Path('P:/FoA-Assets/splatmesh/dream_interview')

def prepare(count=500000,max_radius=None,source=SOURCE,world_id='3FO4K4V8IRTN'):
    source=Path(source)
    assert source==SOURCE or world_id!='3FO4K4V8IRTN','Replacement requires its actual world ID'
    data=(source/'world.spz').read_bytes()
    doc,blob,side=convert(data,count,1,'SM_DreamInterview',src=str(source/'world.spz'),max_radius=max_radius,lean=True,covariance=True)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'SM_DreamInterview.bin').write_bytes(blob)
    (OUT/'SM_DreamInterview.gltf').write_text(json.dumps(doc,separators=(',',':'),allow_nan=False))
    side['source_sha256']=hashlib.sha256(data).hexdigest()
    side['world_id']=world_id
    (OUT/'SM_DreamInterview.splatmesh.json').write_text(json.dumps(side,indent=1))
    (source/'SOURCES.txt').write_text(
        'Aholo World / SpatialGen\nUser-authorized one generation on 2026-11-12.\n'
        f'World ID: {world_id}\nProject uses the existing approved Aholo pipeline.\n'
        'No external asset downloads or additional generation by the conversion helper.\n'
        'The supplied panorama is not imported or used as sky.\n',encoding='utf-8')
    print(json.dumps(dict(splats=side['splats'],source=side['source_splats'],bounds=side['bounds_m'],offset=side['offset_m'])))
    return side

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--count',type=int,default=500000)
    ap.add_argument('--max-radius',type=float);ap.add_argument('--source',type=Path,default=SOURCE)
    ap.add_argument('--world-id',default='3FO4K4V8IRTN')
    args=ap.parse_args();prepare(args.count,args.max_radius,args.source,args.world_id)
