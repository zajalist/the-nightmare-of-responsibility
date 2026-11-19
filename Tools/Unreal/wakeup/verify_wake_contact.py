"""Offline actual Teen palm and film coverage measurement from the read-only probe."""
import json,math
from pathlib import Path
import wake_math as m

ROOT=Path('P:/FoA/Saved')
data=json.loads((ROOT/'AnimShots/wake_contact_live.json').read_text())
landmark=json.loads((ROOT/'CharacterShots/mpfb/shirt_palm_diagnostic.json').read_text())['palms']['l']
center=(324.79422863406,-91.5,102.08181231)


def palm(row):
    hand=row['components']['Body']['hand_l']
    local=tuple(a*b for a,b in zip(landmark['centroid_ue_cm'],hand['scale']))
    return m.add(hand['position'],m.qrot(hand['rotation'],local)),m.qrot(hand['rotation'],landmark['normal_ue'])


def project(point,camera):
    p=m.qrot(m.qinv(camera['quaternion']),m.sub(point,camera['position']))
    if p[0]<=0:return None
    return (.5+p[1]*camera['focal_mm']/(p[0]*camera['sensor_width']),
            .5-p[2]*camera['focal_mm']/(p[0]*camera['sensor_height']))


assert data['rows'],data['reason']
contact=min(data['rows'],key=lambda r:abs(r['sequence_seconds']-25.3))
point,normal=palm(contact)
before=[r for r in data['rows'] if r['sequence_seconds']<=25.3]
after=[r for r in data['rows'] if r['sequence_seconds']>=25.3]
bracket=None
if before and after:
    a,b=before[-1],after[0]
    gap=b['sequence_seconds']-a['sequence_seconds']
    bracket=[a['sequence_seconds'],b['sequence_seconds']]
    if 0<gap<=.08:
        alpha=(25.3-a['sequence_seconds'])/gap
        pa,na=palm(a);pb,nb=palm(b)
        point,normal=m.lerp(pa,pb,alpha),m.norm(m.lerp(na,nb,alpha))
out={'sample_time':contact['sequence_seconds'],'palm_cm':point,'normal':normal,
     'error_from_clock_top_cm':m.sub(point,center),
     'flat_angle_degrees':math.degrees(math.acos(max(-1,min(1,m.dot(m.norm(normal),(0,0,-1)))))),
     'capture_time_error':abs(contact['sequence_seconds']-25.3),'contact_bracket':bracket,
     'contact_resolved':bool(bracket and bracket[1]-bracket[0]<=.08)}
points=[]
for row in data['rows']:
    if not 24.2<=row['sequence_seconds']<28.4:continue
    camera=row['camera']
    assert abs(camera.get('focal_mm',0)-40)<.1,camera
    assert abs(camera.get('aperture',0)-5.6)<.1,camera
    scene=[row['components']['Body'][b]['position'] for b in ('lowerarm_l','hand_l','middle_01_l','middle_03_l','index_03_l','pinky_03_l') if b in row['components']['Body']]
    scene.append(palm(row)[0])
    scene += [(center[0]+x,center[1]+y,z) for x in (-14,14) for y in (-14,14) for z in (76.12,102.08)]
    screen=[project(p,camera) for p in scene]
    assert all(p is not None for p in screen),row['sequence_seconds']
    points+=screen
out['projected_union_uv']={'min':[min(p[i] for p in points) for i in (0,1)],'max':[max(p[i] for p in points) for i in (0,1)]}
out['contact_within_2cm']=m.length(m.sub(point,center))<2 if out['contact_resolved'] else None
out['palm_flat_within_15deg']=out['flat_angle_degrees']<15 if out['contact_resolved'] else None
out['ten_percent_frame_margin']=all(.1<=p[i]<=.9 for p in points for i in (0,1))
(ROOT/'AnimShots/wake_contact_verified.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
