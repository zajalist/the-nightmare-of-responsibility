"""Offline full-source Dream A conversion, preserving the already-placed mesh frame.

Run with python -I Tools/Splats/prepare_dream_density.py. No engine/network calls.
Writes a staged same-name glTF; import_l2_dream.py consumes it after a writer grant.
"""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ply_to_splatmesh import convert

SOURCE=Path('P:/FoA-Assets/level2/aholo/dream_a/world.spz')
BASELINE=Path('P:/FoA-Assets/splatmesh/SM_DreamA.splatmesh.json')
OUTPUT=Path('P:/FoA-Assets/splatmesh/dream_dense/SM_DreamA.gltf')

def prepare(source=SOURCE,baseline=BASELINE,output=OUTPUT):
    old=json.loads(baseline.read_text());data=source.read_bytes()
    doc,blob,side=convert(data,old['source_splats'],old['seed'],'SM_DreamA',src=str(source),
                          max_radius=old['max_radius'],lean=True,origin=old['offset_m'],covariance=True)
    assert side['splats']==side['candidates'] and side['splats']>old['splats']
    assert side['offset_m']==old['offset_m'],'Placed frame changed'
    side['density_upgrade']=dict(previous_splats=old['splats'],ratio=round(side['splats']/old['splats'],4),
        source_sha256=hashlib.sha256(data).hexdigest(),fixed_origin_m=old['offset_m'],
        triangles=side['splats']*2,vertices=side['splats']*4,buffer_bytes=len(blob))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.with_suffix('.bin').write_bytes(blob)
    output.write_text(json.dumps(doc,separators=(',',':'),allow_nan=False))
    output.with_suffix('.splatmesh.json').write_text(json.dumps(side,indent=1,allow_nan=False))
    print(json.dumps(side['density_upgrade']))
    return side

if __name__=='__main__':prepare()
