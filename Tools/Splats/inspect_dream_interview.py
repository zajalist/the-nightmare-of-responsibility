"""Offline source-only interview staging measurements and previews. Run with python -I."""
import json
import os
from pathlib import Path
import sys
sys.path[:0]=[str(Path(__file__).resolve().parent),str(Path(os.environ['APPDATA'])/'Python/Python314/site-packages')]
import numpy as np
import splat_preview as preview

SOURCE=Path('P:/FoA-Assets/splatmesh/dream_interview/SM_DreamInterview.gltf')
OUT=Path('P:/FoA/Saved/Integration/splat_visual_20261112')

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    points,radii,colours,eye=preview.load(str(SOURCE))
    side=json.loads(SOURCE.with_suffix('.splatmesh.json').read_text())
    replacement=side.get('world_id')=='3FO4K4V8IV6O'
    near=np.linalg.norm((points-eye)[:,[0,2]],axis=1)<2
    low=points[near & (points[:,1]<eye[1]-.7),1]
    edges=np.arange(0,eye[1],.02)
    bins,_=np.histogram(low,bins=edges)
    floor=float(edges[np.argmax(bins)]+.01)
    rows=dict(splats=len(points),bounds_ue_cm=(points[:,[0,2,1]]*100).min(0).tolist()+
              (points[:,[0,2,1]]*100).max(0).tolist(),capture_ue_cm=(eye[[0,2,1]]*100).tolist(),
              near_capture_floor_z_cm=floor*100,near_capture_floor_samples=len(low))
    rows['corridor_floor']=[]
    y=2.33 if replacement else .2
    for x in ((-1.2,-.4,.2,.8,1.5,1.8) if replacement else (1.,2.,3.,4.,4.7)):
        samples=points[(abs(points[:,0]-x)<.35)&(abs(points[:,2]-y)<.35)&(points[:,1]<.8),1]
        assert len(samples),'Staging candidate has no measured floor'
        histogram,edges=np.histogram(samples,bins=np.arange(0,.8,.02))
        rows['corridor_floor'].append(dict(x_cm=x*100,y_cm=y*100,samples=len(samples),
                                           floor_z_cm=round(float(edges[histogram.argmax()]+.01)*100,1)))
    rows['recommended_staging_local_cm']=dict(mesh=[0,0,-30],desk=[200,20,0],interviewer=[105,20,0],
                                             player=[345,20,0],camera=[470,20,155],camera_yaw=180,
                                             verification='offline only; confirm native framing')
    if replacement:rows['recommended_staging_local_cm'].update(mesh=[0,0,-27],desk=[-40,233,10],
        interviewer=[-120,233,0],player=[80,320,0],camera=[170,233,155])
    rows['world_id']=side.get('world_id')
    (OUT/'interview_measurements.json').write_text(json.dumps(rows,indent=1))
    print(json.dumps(rows))
    preview.sheet(str(SOURCE),str(OUT/'interview_offline.png'))
