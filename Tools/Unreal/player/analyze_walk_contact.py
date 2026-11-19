"""Reconstruct rendered sock soles and measure planted surface drift, offline.
No acceptance from ankle/ball proxies or from selecting horizontally stationary points.
"""
import json,sys
from pathlib import Path
import numpy as np
from sleep_skin_contact import matrix

folder=Path(sys.argv[1]) if len(sys.argv)>1 else Path(json.loads(Path('Saved/CharacterShots/walk_contact/latest.json').read_text())['folder'])
data=json.loads((folder/'capture.json').read_text());assert data['reason']=='captured_requires_contact_and_visual_review',data.get('error')
base=Path('Saved/WakeUp/teen_socks_skin_cache');meta=json.loads(base.with_suffix('.json').read_text())
assert data['config']['mesh'].split('.')[0]==meta['source_mesh']
with np.load(base.with_suffix('.npz')) as z:cache={k:z[k] for k in z.files}
names=cache['bone_names'].tolist();ref=cache['reference_matrices'];inv=np.linalg.inv(ref)
verts=np.c_[cache['vertices_cm'],np.ones(len(cache['vertices_cm']))]
ids=np.repeat(np.arange(len(verts)),np.diff(cache['vertex_offsets']))
weights=cache['weight_values'];wb=cache['weight_bones']
sole={}
for side in ('l','r'):
    side_weights=np.zeros(len(verts));side_bones=[i for i,n in enumerate(names) if n.endswith('_'+side) and n.startswith(('foot_','ball_'))]
    np.add.at(side_weights,ids,weights*np.isin(wb,side_bones))
    candidates=np.flatnonzero(side_weights>.8);assert len(candidates)>12
    # Fixed reference surface vertices, not a joint axis or frame-dependent lowest point.
    sole[side]=candidates[verts[candidates,2]<verts[candidates,2].min()+1.6]
    assert len(sole[side])>=6
surface=[]
for row in data['rows']:
    bones={b['name']:b for b in row['bones']};assert {names[i] for i in set(wb)}<=set(bones)
    pose=ref.copy()
    for i in set(wb):
        b=bones[names[i]];pose[i]=matrix(b['position'],b['rotation'],b['scale'])
    # No inactive-helper fallback permitted for a contact-quality result.
    assert not any(np.linalg.norm(pose[i,:3,3])<.001 and np.linalg.norm(ref[i,:3,3])>2 for i in set(wb))
    transforms=pose@inv;points=np.zeros((len(verts),4))
    np.add.at(points,ids,np.einsum('nij,nj->ni',transforms[wb],verts[ids])*weights[:,None])
    world=row['world'];surface.append((points@matrix(world['position'],world['rotation'],world['scale']).T)[:,:3])
surface=np.asarray(surface);times=np.array([r['t'] for r in data['rows']]);dt=np.diff(times)
result=dict(reason='measured_requires_visual_review',capture=str(folder/'capture.json'),mesh=meta['source_mesh'],
    cache_bind_error_cm=meta['max_bone_bind_error_cm'],sole_vertex_ids={k:cache['source_vertex_ids'][v].tolist() for k,v in sole.items()},
    method='Fixed actual sock sole vertices. Plant candidate requires surface height within1cm of traced plane, abs vertical speed<5cm/s, flat sole interquartile height<1.5cm. Horizontal speed never determines plant selection. Fixed contact patch tracked within each span.',
    phases={},feet={},limitations=['Skin reconstruction excludes material WPO; compare actual matching footage.','Single straight room lane and normal starter socks only.','Contact classification thresholds are diagnostic, not a zero-slide acceptance threshold.'])
for phase in dict.fromkeys(r['phase'] for r in data['rows']):
    index=[i for i,r in enumerate(data['rows']) if r['phase']==phase];speed=np.array([data['rows'][i]['speed'] for i in index])
    result['phases'][phase]=dict(duration_s=float(times[index[-1]]-times[index[0]]),speed_median_cm_s=float(np.median(speed)),speed_max_cm_s=float(max(speed)),ground_speed_median=float(np.median([data['rows'][i]['ground_speed'] for i in index])))
for side,selected in sole.items():
    points=surface[:,selected];heights=[]
    for row,q in zip(data['rows'],points):
        ground=row['ground'][side];assert ground,'Missing ground trace'
        normal=np.array(ground['normal']);assert normal[2]>.95,'Nonflat support requires per-vertex traces'
        heights.append((q-np.array(ground['point']))@normal)
    heights=np.array(heights);mid=np.median(heights,axis=1);vertical=np.r_[np.inf,np.abs(np.diff(mid)/dt)]
    low=np.quantile(heights,.1,axis=1);spread=np.quantile(heights,.75,axis=1)-np.quantile(heights,.25,axis=1)
    planted=(np.abs(low)<1)&(vertical<5)&(spread<1.5)
    spans=[];begin=None
    for i,active in enumerate(np.r_[planted,False]):
        if active and begin is None:begin=i
        if begin is not None and (not active or (i<len(times) and data['rows'][i]['phase']!=data['rows'][begin]['phase'])):
            end=i-1
            if times[end]-times[begin]>=.12:
                patch=np.flatnonzero(np.abs(heights[begin])<.9)
                if len(patch)>=3:
                    center=np.mean(points[begin:end+1,patch],axis=1)
                    distance=np.linalg.norm(center[:,:2]-center[0,:2],axis=1)
                    path=np.linalg.norm(np.diff(center[:,:2],axis=0),axis=1).sum()
                    capsule=np.array([r['position'] for r in data['rows'][begin:end+1]])
                    travel=np.linalg.norm(np.diff(capsule[:,:2],axis=0),axis=1).sum()
                    spans.append(dict(start=float(times[begin]),end=float(times[end]),phase=data['rows'][begin]['phase'],
                        patch_vertices=len(patch),peak_world_drift_cm=float(max(distance)),world_path_cm=float(path),
                        capsule_travel_cm=float(travel),drift_speed_cm_s=float(path/(times[end]-times[begin]))))
            begin=i if active and i<len(times) else None
    result['feet'][side]=dict(sole_min_height_cm=float(heights.min()),sole_low_height_range_cm=[float(low.min()),float(low.max())],plant_spans=spans,
        matched_frames=[f for f in data['frames'] if any(s['start']<=f['t']<=s['end'] for s in spans)])
assert len(times)>100,'Insufficient motion samples'
(folder/'contact_metrics.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('sole_vertex_ids','feet')},indent=1))
for side,values in result['feet'].items():print(side,'spans',len(values['plant_spans']),'peak drift',[round(s['peak_world_drift_cm'],2) for s in values['plant_spans']])
