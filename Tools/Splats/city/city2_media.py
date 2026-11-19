"""Offline data previews and measured native proof packaging, always Idle."""
import csv
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import time
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).parent))
import city2 as C
import numpy as np
from PIL import Image
OUT=Path('P:/FoA/Saved/Codex/city2')


def load(entries):
    renderer=C.base.module('splat_preview');positions=[];radii=[];colours=[]
    for e in entries:
        p,r,col,_=renderer.load(str(C.OUT/e['gltf']))
        p[:,0]+=r;p[:,2]-=r
        off=e.get('offset_gltf_m') or [e['actor_location_cm'][k]/100 for k in [0,2,1]]
        p+=off;positions.append(p);radii.append(r.copy());colours.append(col.copy())
    return renderer,np.concatenate(positions),np.concatenate(radii),np.concatenate(colours)


def preview():
    m=C.read('manifest.json');dest=C.OUT/'previews';dest.mkdir(exist_ok=True)
    ren,p,r,col=load(m['overview']);ren.W,ren.H=1600,1200
    p[:,1]=0;eye=np.array([700.,1600.,0.]);rot=ren.look(eye,np.array([700.,0.,0.]))
    image=ren.render(p,r,col,eye,rot,fov_deg=2*math.degrees(math.atan(.5)),rmax=4,bg=(0,0,0))
    white=col.copy();white[:,:3]=1
    alpha=ren.render(p,r,white,eye,rot,fov_deg=2*math.degrees(math.atan(.5)),rmax=4,bg=(0,0,0))[:,:,0]/255
    ground=np.asarray(Image.open(C.OUT/'ground_overview.png').resize((1600,1200)))
    Image.fromarray(np.clip(image+ground[:,:,None]*(1-alpha[:,:,None]),0,255).astype(np.uint8)).save(dest/'overview_offline.png')
    del ren,p,r,col,white,alpha,ground,image
    for name,u,direction in [('street_east',155,1),('street_west',800,-1)]:
        entries=[e for e in m['meshes'] if abs((e['bounds_uv_m'][0][0]+e['bounds_uv_m'][1][0])/2-u)<125 and abs((e['bounds_uv_m'][0][1]+e['bounds_uv_m'][1][1])/2)<125]
        ren,p,r,col=load(entries);ren.W,ren.H=1280,720
        eye=np.array([float(u),1.07,0.]);target=eye+np.array([direction*90.,12.,-15.])
        Image.fromarray(ren.render(p,r,col,eye,ren.look(eye,target),fov_deg=75,rmax=8)).save(dest/(name+'_offline.png'))
        del ren,p,r,col
    C.save('previews/notes.json',{'renderer':'Existing splat_preview.py Gaussian discs, weighted OIT; not native baked-quad UE output',
        'overview':'Distant overview LOD flattened for orthographic coverage, composited over ground',
        'oblique':'Full detail within 125m of each camera, aerial facade holes retained; ground omitted', 'memory':C.base.memory()})
    print('offline previews complete',C.base.memory(),flush=True)


def frame_metrics(frame,selected):
    image=Image.open(frame['file']);assert image.size==(1920,1080)
    pixels=np.asarray(image.convert('RGB'))
    border=np.concatenate([pixels[:8].reshape(-1,3),pixels[-8:].reshape(-1,3),pixels[:,:8].reshape(-1,3),pixels[:,-8:].reshape(-1,3)])
    camera=frame['camera_cm'];centre_count=0
    pitch=math.radians(frame['pitch_degrees']);yaw=math.radians(frame['yaw_degrees'])
    forward=np.array([math.cos(pitch)*math.cos(yaw),math.cos(pitch)*math.sin(yaw),-math.sin(pitch)])
    right=np.array([-math.sin(yaw),math.cos(yaw),0]);up=np.cross(right,forward)
    assert np.allclose(np.array([forward,right,up])@np.array([forward,right,up]).T,np.eye(3))
    for e in selected:
        ren,p,r,col=load([e]);delta=p[:,[0,2,1]]-np.array(camera)/100
        d=delta@forward;horizontal=delta@right;vertical=delta@up
        in_view=(d>0)&(abs(horizontal)<=d+r*math.sqrt(2))&(abs(vertical)<=d*9/16+r*math.sqrt(2))
        if 'Overview' in e['name']:
            a=np.array(e['actor_location_cm'])/100
            if np.linalg.norm(np.array(camera)/100-a)<300:in_view[:]=False
        centre_count+=int(in_view.sum())
    return {'file':frame['file'],'pitch_degrees':frame['pitch_degrees'],'frustum_splats_upper_bound':centre_count,
            'border_exact_black_fraction':float(np.all(border==0,axis=1).mean())}


def proof():
    results=[];manifest=C.read('manifest.json')
    lookup={e['name']:e for e in manifest['meshes']+manifest['overview']}
    for name in ['spadina','university','play_corner','overview','drift']:
        data=json.loads((OUT/(name+'_after_proof.json')).read_text());assert data['reason']=='passed',data
        selected=[lookup[n] for n in data['loaded_meshes'] if n in lookup]
        frames=data['frames'] if name!='drift' else [data['frames'][i] for i in [0,len(data['frames'])//2,-1]]
        measured=[frame_metrics(f,selected) for f in frames]
        if name!='overview':assert max(f['frustum_splats_upper_bound'] for f in measured)<=1_500_000
        csvs=[]
        for path in Path('P:/FoA/Saved/Profiling/CSV').glob('Profile(*).csv'):
            started=time.mktime(time.strptime(path.stem,'Profile(%Y%m%d_%H%M%S)'))
            if data['csv_start']-2<=started<=data['csv_start']+3:csvs.append(path)
        values=[]
        for path in csvs:
            with path.open(encoding='utf-8-sig') as f:
                for row in csv.DictReader(f):
                    try:v=float(row['GPUTime'])
                    except (KeyError,ValueError,TypeError):continue
                    if v>0:values.append(v)
        values.sort()
        results.append({'view':name,'frames':measured,'loaded_meshes':len(selected),
            'gpu_samples':len(values),'gpu_ms_median':statistics.median(values) if values else None,
            'gpu_ms_p95':values[min(len(values)-1,int(.95*len(values)))] if values else None,'csv':[str(p) for p in csvs]})
    drift=json.loads((OUT/'drift_after_proof.json').read_text());frames=drift['frames'];assert len(frames)>10
    lines=[]
    for i,frame in enumerate(frames):
        lines.append("file '"+frame['file'].replace('\\','/')+"'")
        duration=(frames[i+1]['seconds']-frame['seconds']) if i+1<len(frames) else 12-(frame['seconds']-frames[0]['seconds'])
        lines.append('duration '+str(duration))
    lines.append("file '"+frames[-1]['file'].replace('\\','/')+"'")
    concat=OUT/'drift_concat.txt';concat.write_text('\n'.join(lines))
    subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-t','12','-vf','fps=30',
                    '-c:v','libx264','-threads','1','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',str(OUT/'city2_drift_12s.mp4')],check=True)
    C.base.save(OUT/'proof_metrics.json',{'views':results,'video_native_frames':len(frames),'video_native_mean_fps':len(frames)/12,
        'counts':'Frustum candidate splats from actually loaded meshes, radius-expanded, excluding distant LOD below 300m. Occlusion can only reduce this count.',
        'gpu_limitation':'Shared editor GPUTime includes editor rendering and native 1080p SceneCapture overhead; not isolated packaged performance.',
        'video':'Native UE SceneCapture frames with recorded wall-clock spacing; encoded at 30 fps with repeats, no optical interpolation.', 'memory':C.base.memory()})
    print(json.dumps(results),flush=True)


def comparisons():
    from PIL import ImageDraw,ImageFont
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',36)
    for pitch in [60,70,90]:
        before=Image.open(OUT/f'spadina_p{pitch}_before.png').convert('RGB')
        after=Image.open(OUT/f'spadina_p{pitch}_after.png').convert('RGB')
        assert before.size==after.size==(1920,1080)
        sheet=Image.new('RGB',(3840,1140),(24,24,24));sheet.paste(before,(0,60));sheet.paste(after,(1920,60))
        draw=ImageDraw.Draw(sheet);draw.text((24,10),f'Old city at {pitch} degrees',font=font,fill='white')
        draw.text((1944,10),f'Expanded city at {pitch} degrees',font=font,fill='white')
        sheet.save(OUT/f'city2_p{pitch}_before_after.png')
    print('Three matched native before/after comparisons written')


if __name__=='__main__':globals()[sys.argv[1]]()
