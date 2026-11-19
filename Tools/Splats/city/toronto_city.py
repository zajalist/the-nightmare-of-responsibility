"""Offline Queen St pipeline. Run with python -I; no editor or generating services.

Stages: corridor, build, preview, verify, selftest. Run city_sources.py first.
Uses locally installed packages explicitly (isolated Python excludes user site).
city_sources.py downloads only the approved NRCan and Toronto data.
"""
import argparse
import gc
import importlib.util
import json
import math
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
SITE = Path(os.environ['APPDATA']) / 'Python/Python314/site-packages'
sys.path.append(str(SITE))
DEPS = Path('P:/FoA-Assets/level2/toronto/tools/site-packages')
sys.path.append(str(DEPS))
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np
import psutil
from PIL import Image
from pyproj import Transformer
import shapely
from shapely.geometry import shape, Polygon
from shapely.ops import transform

ROOT = Path('P:/FoA-Assets/level2/toronto')
OUT = ROOT / 'processed/queen_600m'
POINT = np.dtype([('u', '<f4'), ('v', '<f4'), ('z', '<f4'), ('intensity', '<u2'),
                  ('cls', 'u1'), ('bid', '<i4')])
SAMPLE = np.dtype(POINT.descr + [('priority', '<f4'), ('roof', 'u1'), ('edge', 'u1')])
URL = ('https://canelevation-lidar-point-clouds.s3.ca-central-1.amazonaws.com/'
       'pointclouds_nuagespoints/TRCA/GTA_2023/'
       'ON_TRCA2023_20230511_NAD83CSRS_UTMZ17_1km_E6290_N{north}_CLASS.copc.laz')
PROC = psutil.Process()
PROC.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)


def module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent.parent / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    tmp.replace(path)


def memory():
    m = PROC.memory_info()
    peak = m.peak_wset
    assert peak < 1_500_000_000, f'memory limit exceeded: {peak}'
    return {'peak_working_set_bytes': peak, 'rss_bytes': m.rss, 'priority': str(PROC.nice())}


def corridor():
    # shortcut: approximate intersection centres, replace anchors after a surveyed route is required.
    anchors = {'queen_spadina': [-79.3965, 43.6488], 'queen_university': [-79.3869, 43.6507]}
    t = Transformer.from_crs(4326, 2958, always_xy=True)
    a, b = (np.array(t.transform(*p)) for p in anchors.values())
    along = (b-a) / np.linalg.norm(b-a)
    left = np.array([-along[1], along[0]])
    corners = [a + u*along + v*left for u, v in [(0,-300),(600,-300),(600,300),(0,300)]]
    result = {'crs': 'EPSG:2958 NAD83(CSRS) / UTM zone 17N', 'anchors_lon_lat': anchors,
              'anchor_accuracy': 'Approximate intersection centres, not surveyed; no geocoding API used.',
              'origin_utm_m': a.tolist(), 'along_utm': along.tolist(), 'left_utm': left.tolist(),
              'bearing_grid_degrees_clockwise_from_north': math.degrees(math.atan2(along[0], along[1])) % 360,
              'length_m': 600, 'width_m': 600, 'intersection_distance_m': float(np.linalg.norm(b-a)),
              'corners_utm_m': [c.tolist() for c in corners],
              'local_frame': 'u east along Queen from Spadina [0,600], v left/north [-300,300], z lidar elevation m',
              'gltf_frame': '(u, elevation - z_origin, -v), metres; per-chunk offset must be restored',
              'ue_frame': '(u, -v, elevation - z_origin) * 100 cm; restore manifest actor_location_cm',
              'ground_uv': 'U=u/600, V=(300-v)/600; PNG top row is north side'}
    save(OUT / 'corridor.json', result)
    return result


def local_xy(x, y, c):
    dx, dy = x-c['origin_utm_m'][0], y-c['origin_utm_m'][1]
    a, b = c['along_utm'], c['left_utm']
    return dx*a[0]+dy*a[1], dx*b[0]+dy*b[1]


def footprints(archive, c):
    import shapefile
    import zipfile
    # Stream extract only the shapefile components, validating paths before writing.
    dest = archive.parent / 'extracted'
    dest.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if Path(item.filename).suffix.lower() in ('.shp','.shx','.dbf','.prj','.cpg'):
                target = dest / Path(item.filename).name
                if not target.exists():
                    import shutil
                    with z.open(item) as src, target.open('wb') as out:
                        shutil.copyfileobj(src, out, 1024*1024)
    shp = next(dest.glob('*.shp'))
    reader = shapefile.Reader(str(shp))
    crs = shp.with_suffix('.prj').read_text()
    t = Transformer.from_crs(crs, 2958, always_xy=True)
    inv = Transformer.from_crs(2958, crs, always_xy=True)
    box = np.array([inv.transform(*p) for p in c['corners_utm_m']])
    bbox = [*box.min(0), *box.max(0)]
    roi = Polygon(c['corners_utm_m'])
    polys, records = [], []
    fields = [x[0] for x in reader.fields[1:]]
    for sr in reader.iterShapeRecords(bbox=bbox):
        geom = transform(lambda x,y,z=None: t.transform(x,y), shape(sr.shape.__geo_interface__))
        if not geom.is_valid:
            geom = shapely.make_valid(geom)
        if geom.is_empty or not geom.intersects(roi) or geom.area < .2:
            continue
        bid = int(sr.shape.oid) + 1
        polys.append(geom)
        records.append({'building_id': bid, 'source_record_zero_based': int(sr.shape.oid),
                        'attributes': dict(zip(fields, list(sr.record))),
                        'area_m2': float(geom.area), 'bounds_utm': list(geom.bounds),
                        'geometry': shapely.to_geojson(geom)})
    reader.close()
    save(OUT/'buildings.json', {'source': str(archive), 'source_prj': crs, 'fields': fields,
                              'identity': '1-based source shapefile record; separate massing parts remain separate',
                              'records': records})
    return np.array(polys, dtype=object), np.array([r['building_id'] for r in records], np.int32)


def assign(x, y, polys, ids, tree):
    p = shapely.points(x, y)
    bids = np.zeros(len(p), np.int32)
    hit = tree.query(p, predicate='intersects')
    if hit.size:
        # Smallest polygon wins an overlap, deterministic source ID breaks ties.
        order = np.lexsort((ids[hit[1]], shapely.area(polys[hit[1]])))
        h = hit[:, order]
        _, first = np.unique(h[0], return_index=True)
        bids[h[0,first]] = ids[h[1,first]]
    return bids


def point_chunks(path, dtype=POINT, size=150000):
    with path.open('rb') as f:
        while True:
            p = np.fromfile(f, dtype, size)
            if not len(p):
                break
            yield p


def refine_assignment():
    stats=json.loads((OUT/'crop_stats.json').read_text())
    if 'building_assigned_within_1m' in stats:return
    c=json.loads((OUT/'corridor.json').read_text())
    records=json.loads((OUT/'buildings.json').read_text())['records']
    polys=np.array([shapely.from_geojson(r['geometry']) for r in records],object)
    ids=np.array([r['building_id'] for r in records],np.int32)
    tree=shapely.STRtree(polys)
    matched=0;hist=np.zeros(6,np.int64);bins=[0,.5,1,2,5,10,10000]
    path=OUT/'crop_points.bin'
    with path.with_suffix('.refined').open('wb') as f:
        for p in point_chunks(path):
            ii=np.flatnonzero((p['cls']==6)&(p['bid']==0))
            u=p['u'][ii].astype(np.float64);v=p['v'][ii].astype(np.float64)
            x=c['origin_utm_m'][0]+u*c['along_utm'][0]+v*c['left_utm'][0]
            y=c['origin_utm_m'][1]+u*c['along_utm'][1]+v*c['left_utm'][1]
            pts=shapely.points(x,y);nearest=tree.nearest(pts)
            distance=shapely.distance(pts,polys[nearest])
            hist+=np.histogram(distance,bins)[0]
            ok=distance<=1.0
            p['bid'][ii[ok]]=ids[nearest[ok]];matched+=int(ok.sum())
            p.tofile(f)
    path.with_suffix('.refined').replace(path)
    stats['building_assigned_exact']=stats['building_assigned']
    stats['building_assigned_within_1m']=matched
    stats['building_assigned']+=matched;stats['building_unassigned']-=matched
    stats['assignment_tolerance']='Exact PIP first, nearest footprint within 1 m for overhang/alignment; farther points retain unknown ID 0.'
    stats['original_unassigned_distance_histogram']={'bins_m':bins,'counts':hist.tolist()}
    save(OUT/'crop_stats.json',stats)
    print('footprint overhang matches',matched,'still unassigned',stats['building_unassigned'],flush=True)


def shortlist(p, rng, polys, tree, c, roof_height):
    p = p[np.isin(p['cls'],[3,4,5,6])]
    if not len(p):
        return np.empty(0,SAMPLE)
    # One point per 0.5 m 3D voxel retains vertical edges while reducing roof overlap.
    vox = np.stack([np.floor(p[k]/.5).astype(np.int32) for k in ['u','v','z']],1)
    _, keep = np.unique(vox,axis=0,return_index=True)
    p = p[keep]
    cell=np.clip(p['u'].astype(int),0,599)*600+np.clip((p['v']+300).astype(int),0,599)
    roof = (p['cls']==6)&(p['z']>=roof_height[cell]-.5)
    u,v=p['u'].astype(np.float64),p['v'].astype(np.float64)
    e = c['origin_utm_m'][0]+u*c['along_utm'][0]+v*c['left_utm'][0]
    n = c['origin_utm_m'][1]+u*c['along_utm'][1]+v*c['left_utm'][1]
    nearest = tree.nearest(shapely.points(e,n))
    edge = shapely.distance(shapely.points(e,n),shapely.boundary(polys[nearest])) < 1.0
    weight = (1+roof*2+edge*2) * np.where(np.abs(p['v'])<100,1.5,1.0)
    out = np.empty(len(p),SAMPLE)
    for k in POINT.names:
        out[k] = p[k]
    out['roof'],out['edge'] = roof,edge
    out['priority'] = -np.log(np.maximum(rng.random(len(p)),1e-12))/weight
    return out


def normalise(value, lo, hi):
    return .12+.78*np.clip((value.astype(np.float32)-lo)/max(1,hi-lo),0,1)


def bake_quads(doc, blob):
    attrs = doc['meshes'][0]['primitives'][0]['attributes']
    result = bytearray(blob)
    def acc(k,nc):
        a = doc['accessors'][attrs[k]]
        return np.frombuffer(result,'<f4',a['count']*nc,doc['bufferViews'][a['bufferView']]['byteOffset']).reshape(-1,4,nc)
    p,uv,r = acc('POSITION',3),acc('TEXCOORD_0',2),acc('TEXCOORD_1',2)
    centre = p.mean(1)
    p[:] = centre[:,None,:]
    p[:,:,0] += uv[:,:,0]*r[:,:,0]/100
    p[:,:,2] -= uv[:,:,1]*r[:,:,0]/100
    a = doc['accessors'][attrs['POSITION']]
    a['min'], a['max'] = p.reshape(-1,3).min(0).tolist(),p.reshape(-1,3).max(0).tolist()
    return result


def write_mesh(p, name, z_origin, limits, converter, origin=None, building_radius=.43):
    # Feed the existing converter a small SH0 PLY, then bake its lean quad positions.
    fields = list(converter.REQUIRED)
    cols = np.zeros((len(p),len(fields)), '<f4')
    def setcol(k,v):
        cols[:,fields.index(k)] = v
    setcol('x',p['u']); setcol('y',-(p['z']-z_origin)); setcol('z',p['v'])
    setcol('opacity',8); setcol('rot_0',1)
    radius = np.where(p['cls']==6,building_radius,.60)
    for k in range(3):
        setcol(f'scale_{k}',np.log(radius/2))
        setcol(f'f_dc_{k}',(normalise(p['intensity'],*limits)-.5)/converter.C0)
    header = ('ply\nformat binary_little_endian 1.0\nelement vertex '+str(len(p))+'\n'+
              ''.join('property float '+k+'\n' for k in fields)+'end_header\n').encode()
    doc,blob,side = converter.convert(header+cols.tobytes(),len(p),17,name,src='Toronto crop_points.bin',lean=True,origin=origin)
    blob = bake_quads(doc,blob)
    mesh = OUT/'meshes'/name
    mesh.parent.mkdir(exist_ok=True)
    mesh.with_suffix('.bin').write_bytes(blob)
    save(mesh.with_suffix('.gltf'),doc)
    side['static_facing'] = 'glTF +Y, UE +Z; corners already baked, no billboard WPO at rest'
    side['bounds_m'] = {'min':doc['accessors'][0]['min'],'max':doc['accessors'][0]['max']}
    side['radius_scale_hint'] = 1.0
    save(mesh.with_suffix('.splatmesh.json'),side)
    off=side['offset_m']
    return {'name':name,'gltf':'meshes/'+name+'.gltf','splats':len(p),'offset_gltf_m':off,
            'actor_location_cm':[off[0]*100,off[2]*100,off[1]*100],
            'bounds_local_uvz_m':[[float(p[k].min()) for k in ['u','v','z']], [float(p[k].max()) for k in ['u','v','z']]],
            'bytes':len(blob)+mesh.with_suffix('.gltf').stat().st_size+mesh.with_suffix('.splatmesh.json').stat().st_size}


def build():
    from scipy.ndimage import distance_transform_edt
    refine_assignment()
    c=json.loads((OUT/'corridor.json').read_text())
    buildings=json.loads((OUT/'buildings.json').read_text())['records']
    polys=np.array([shapely.from_geojson(r['geometry']) for r in buildings],dtype=object)
    tree=shapely.STRtree(polys)
    rng=np.random.default_rng(1729)
    pool=np.empty(0,SAMPLE)
    hist=np.zeros(65536,np.int64)
    roof_height=np.full(600*600,-np.inf,np.float32)
    for p in point_chunks(OUT/'crop_points.bin'):
        hist += np.bincount(p['intensity'],minlength=65536)
        b=p[p['cls']==6]
        cell=np.clip(b['u'].astype(int),0,599)*600+np.clip((b['v']+300).astype(int),0,599)
        np.maximum.at(roof_height,cell,b['z'])
    count=np.zeros(4096*4096,np.uint32)
    intensity=np.zeros(len(count),np.float32)
    height=np.zeros(len(count),np.float32)
    candidates=0
    for p in point_chunks(OUT/'crop_points.bin'):
        q=shortlist(p,rng,polys,tree,c,roof_height)
        candidates+=len(q)
        pool=np.concatenate([pool,q])
        if len(pool)>900000:
            pool=pool[np.argpartition(pool['priority'],899999)[:900000]]
        ground=np.isin(p['cls'],[2,11])
        g=p[ground]
        ix=np.clip((g['u']/600*4096).astype(int),0,4095)
        iy=np.clip(((300-g['v'])/600*4096).astype(int),0,4095)
        pix=iy*4096+ix
        np.add.at(count,pix,1); np.add.at(intensity,pix,g['intensity']); np.add.at(height,pix,g['z'])
        memory()
    # Remove cross-chunk voxel duplicates, retaining the best weighted sample.
    pool.sort(order='priority')
    voxel=np.stack([np.floor(pool[k]/.5).astype(np.int32) for k in ['u','v','z']],1)
    _,unique=np.unique(voxel,axis=0,return_index=True)
    pool=pool[unique]
    if len(pool)>800000:
        pool=pool[np.argpartition(pool['priority'],799999)[:800000]]
    pool.sort(order=['bid','u','v','z'])
    pool.tofile(OUT/'selected_splats.bin')
    limits=[int(np.searchsorted(np.cumsum(hist),hist.sum()*f)) for f in [.02,.98]]
    np.save(OUT/'intensity_histogram.npy',hist)
    observed=count>0
    intensity/=np.maximum(count,1); height/=np.maximum(count,1)
    z_origin=float(np.median(height[observed]))
    coverage=float(observed.mean())
    Image.fromarray(observed.reshape(4096,4096).astype(np.uint8)*255).save(OUT/'ground_observed_mask.png')
    # Nearest fill is explicitly marked by the coverage mask, including under roofs.
    del count, polys, tree, p, q, g
    gc.collect()
    nearest=distance_transform_edt(~observed.reshape(4096,4096),return_distances=False,return_indices=True)
    flat=nearest[0].astype(np.int64)*4096+nearest[1]
    del nearest
    intensity=intensity[flat]
    height=height[flat]
    del flat
    Image.fromarray((normalise(intensity,*limits)*255).astype(np.uint8)).save(OUT/'ground_intensity_4096.png')
    np.save(OUT/'ground_height_metres.npy',height)
    hmin,hmax=float(height.min()),float(height.max())
    Image.fromarray(np.round((height-hmin)/(hmax-hmin)*65535).astype(np.uint16)).save(OUT/'ground_height_16bit.png')
    save(OUT/'ground.json',{'size':[4096,4096],'metres_per_pixel':600/4096,'classes':[2,11],
         'raw_observed_fraction':coverage,'fill':'nearest observed ground pixel; mask 255=measured, 0=filled',
         'height_png_decode':'min_m + value/65535 * (max_m-min_m)','min_m':hmin,'max_m':hmax,
         'height_npy':'float32 lidar elevation metres; source vertical datum from LAS CRS',
         'intensity_percentiles_2_98':limits,'grey_mapping':'0.12 + 0.78 * clamp((I-p2)/(p98-p2))',
         'uv':c['ground_uv'],'z_origin_m':z_origin})
    finish_ground_texture()
    del intensity,height,observed
    gc.collect()
    converter=module('ply_to_splatmesh')
    entries=[]
    for bid in np.unique(pool['bid']):
        pts=pool[pool['bid']==bid]
        if bid:
            groups=[(f'B{bid:07d}',pts,'building')]
        else:
            cells=(pts['u']//50).astype(int)*12+np.clip(((pts['v']+300)//50).astype(int),0,11)
            groups=[]
            for cell in np.unique(cells):
                for vegetation in [True,False]:
                    m=(cells==cell)&((pts['cls']!=6)==vegetation)
                    if m.any():
                        kind='trees' if vegetation else 'unassigned_building'
                        groups.append((f'{kind}_{cell:03d}',pts[m],kind))
        for base,pp,kind in groups:
            # Split very large buildings; every part keeps the same logical dissolve group.
            for part,start in enumerate(range(0,len(pp),16000)):
                e=write_mesh(pp[start:start+16000],f'{base}_{part:02d}',z_origin,limits,converter)
                e.update(building_id=int(bid),dissolve_group=base,kind=kind)
                entries.append(e)
        if bid and len(entries)%25==0:
            print(f'converted {len(entries)} meshes',flush=True)
        memory()
    manifest={'corridor':'corridor.json','z_origin_m':z_origin,'splats':len(pool),'candidates_after_voxel':candidates,
       'roof_splats':int(pool['roof'].sum()),'edge_splats':int(pool['edge'].sum()),
       'classes':{str(int(k)):int(v) for k,v in zip(*np.unique(pool['cls'],return_counts=True))},
       'chunk_policy':'Source massing record per building, max 16000 splats/part. Trees and unassigned buildings in separate 50 m cells.',
       'placement':'Use actor_location_cm; do not place all meshes at zero. UE local axes=(u,-v,z-z_origin).',
       'material':'Lean unlit vertex colour, baked +Z quads. No billboard WPO; reconstruct centre from UV0/radius before event displacement.',
       'identity_caveat':'A source massing record is a building part, not necessarily a whole architectural building; group manually at job sites.',
       'mesh_bytes':sum(e['bytes'] for e in entries),'ue_asset_bytes_estimate':[len(pool)*50,len(pool)*140],
       'memory':memory(),'meshes':entries}
    save(OUT/'manifest.json',manifest)
    print('build complete',len(pool),'splats',len(entries),'meshes',memory(),flush=True)


def finish_ground_texture():
    from scipy.ndimage import maximum_filter
    texture=np.asarray(Image.open(OUT/'ground_intensity_4096.png')).copy()
    observed=np.asarray(Image.open(OUT/'ground_observed_mask.png'))>0
    unsupported=~maximum_filter(observed,size=9)
    neutral=int(np.median(texture[observed]))
    texture[unsupported]=neutral
    Image.fromarray(texture).save(OUT/'ground_intensity_4096.png')
    meta=json.loads((OUT/'ground.json').read_text())
    meta.update(intensity_fill='Nearest measured pixel within a 9x9 pixel neighbourhood; farther gaps use median observed grey. Height remains nearest-filled.',
                neutral_grey_u8=neutral,neutral_fill_fraction=float(unsupported.mean()),
                fill='Mask 255=measured, 0=filled. See intensity_fill for colour; height is nearest measured ground.')
    save(OUT/'ground.json',meta)


def preview():
    renderer=module('splat_preview')
    renderer.W,renderer.H=1200,1200
    m=json.loads((OUT/'manifest.json').read_text())
    positions=[]; radii=[]; colours=[]
    # Existing loader takes first vertex; undo our baked first-corner offset to recover centres.
    for e in m['meshes']:
        p,r,col,_=renderer.load(str(OUT/e['gltf']))
        p[:,0]+=r; p[:,2]-=r
        p+=np.array(e['offset_gltf_m'])
        positions.append(p.astype(np.float32));radii.append(r.astype(np.float32));colours.append(col.copy())
    p=np.concatenate(positions);r=np.concatenate(radii);col=np.concatenate(colours)
    del positions,radii,colours
    dest=OUT/'previews';dest.mkdir(exist_ok=True)
    flat=p.copy();flat[:,1]=0
    eye=np.array([300.,600.,0.]);target=np.array([300.,0.,0.])
    image=renderer.render(flat,r,col,eye,renderer.look(eye,target),fov_deg=2*math.degrees(math.atan(300/600)),rmax=4,bg=(0,0,0))
    Image.fromarray(image).save(dest/'top_down_splats.png')
    white=col.copy();white[:,:3]=1
    alpha=renderer.render(flat,r,white,eye,renderer.look(eye,target),fov_deg=2*math.degrees(math.atan(300/600)),rmax=4,bg=(0,0,0))[:,:,0]/255.
    ground_preview=np.asarray(Image.open(OUT/'ground_intensity_4096.png').resize((1200,1200)))
    combined=np.clip(image+ground_preview[:,:,None]*(1-alpha[:,:,None]),0,255).astype(np.uint8)
    Image.fromarray(combined).save(dest/'top_down_city.png')
    del white,alpha,ground_preview,combined,flat
    renderer.W,renderer.H=1280,720
    ground=np.load(OUT/'ground_height_metres.npy',mmap_mode='r')
    views=[]
    for name,u,direction in [('street_east',70,1),('street_west',530,-1)]:
        h=float(ground[2048,int(u/600*4096)])-m['z_origin_m']
        eye=np.array([float(u),h+1.7,0.])
        target=eye+np.array([direction*90.,12.,-15.])
        image=renderer.render(p,r,col,eye,renderer.look(eye,target),fov_deg=75,rmax=12)
        Image.fromarray(image).save(dest/(name+'.png'))
        views.append({'file':name+'.png','eye_gltf_m':eye.tolist(),'target_gltf_m':target.tolist()})
    Image.open(OUT/'ground_intensity_4096.png').resize((1200,1200)).save(dest/'ground_texture.png')
    save(dest/'views.json',{'top_down':'Orthographic plan simulated by flattening height before perspective rendering; full 600 m square.',
          'street_views':views,'limitation':'splat_preview.py weighted OIT, Gaussian camera-facing discs. These are data-coverage previews, not baked-quad UE renders. No facade infill or ground in splat views.',
          'memory':memory()})
    print('previews complete',memory(),flush=True)


def verify():
    m=json.loads((OUT/'manifest.json').read_text())
    total=0
    for entry in m['meshes']:
        path=OUT/entry['gltf'];doc=json.loads(path.read_text())
        blob=path.with_suffix('.bin').read_bytes()
        attrs=doc['meshes'][0]['primitives'][0]['attributes']
        assert set(attrs)=={'POSITION','TEXCOORD_0','TEXCOORD_1','COLOR_0'}
        a=doc['accessors'][attrs['POSITION']];v=doc['bufferViews'][a['bufferView']]
        p=np.frombuffer(blob,'<f4',a['count']*3,v['byteOffset']).reshape(-1,4,3)
        assert np.isfinite(p).all() and len(p)==entry['splats']<=16000
        assert np.max(np.ptp(p[:,:,1],axis=1))<1e-5
        assert np.min(np.ptp(p[:,:,0],axis=1))>.8
        assert len(blob)==doc['buffers'][0]['byteLength']
        centres=p.mean(1)+entry['offset_gltf_m']
        restored=np.stack([centres[:,0],-centres[:,2],centres[:,1]+m['z_origin_m']],1)
        assert np.allclose([restored.min(0),restored.max(0)],entry['bounds_local_uvz_m'],rtol=0,atol=.001),'placement roundtrip'
        total+=len(p)
    assert total==m['splats']<=800000
    ground=json.loads((OUT/'ground.json').read_text())
    mask=np.asarray(Image.open(OUT/'ground_observed_mask.png'))
    assert mask.shape==(4096,4096) and set(np.unique(mask))=={0,255}
    assert abs(float((mask>0).mean())-ground['raw_observed_fraction'])<1e-12
    heights=np.load(OUT/'ground_height_metres.npy',mmap_mode='r')
    assert heights.shape==(4096,4096) and heights.dtype==np.float32
    assert np.isfinite(heights).all() and float(heights.min())==ground['min_m'] and float(heights.max())==ground['max_m']
    del mask,heights
    for name in ['top_down_city','top_down_splats','street_east','street_west','ground_texture']:
        with Image.open(OUT/'previews'/(name+'.png')) as im:
            im.verify()
    inventory=[{'path':str(p.relative_to(OUT)),'bytes':p.stat().st_size} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='verification.json']
    save(OUT/'verification.json',{'splats':total,'meshes':len(m['meshes']),'checks':'lean attributes, finite nondegenerate baked quads, <=16k per mesh, <=800k total, buffers, placement roundtrip <=1mm, ground coverage/height bounds and preview PNGs valid',
                                'inventory':inventory,'memory':memory()})
    print('verification OK',total,len(m['meshes']),memory())


def selftest():
    converter=module('ply_to_splatmesh');converter.selftest()
    module('splat_preview').selftest()
    c=corridor()
    a=np.array(c['origin_utm_m']);along=np.array(c['along_utm']);left=np.array(c['left_utm'])
    assert abs(np.dot(along,left))<1e-10
    assert np.allclose(local_xy(*(a+along*123+left*45),c),(123,45))
    polys=np.array([shapely.box(0,0,10,10),shapely.box(2,2,4,4)],object)
    assert assign([3,9,20],[3,9,20],polys,np.array([1,2]),shapely.STRtree(polys)).tolist()==[2,1,0]
    p=np.zeros(3,POINT);p['u']=[1,2,3];p['v']=[2,3,4];p['z']=[75,76,77];p['cls']=6;p['intensity']=100
    # Test through converter without writing a production mesh.
    rows=np.zeros((3,len(converter.REQUIRED)),'<f4')
    for k,val in [('x',p['u']),('y',-p['z']),('z',p['v']),('rot_0',1),('opacity',8)]:
        rows[:,list(converter.REQUIRED).index(k)]=val
    for k in range(3):rows[:,list(converter.REQUIRED).index(f'scale_{k}')]=math.log(.2)
    head=('ply\nformat binary_little_endian 1.0\nelement vertex 3\n'+''.join('property float '+k+'\n' for k in converter.REQUIRED)+'end_header\n').encode()
    doc,blob,side=converter.convert(head+rows.tobytes(),3,1,'test',lean=True)
    baked=bake_quads(doc,blob)
    a=doc['accessors'][0];v=doc['bufferViews'][a['bufferView']]
    q=np.frombuffer(baked,'<f4',36,v['byteOffset']).reshape(3,4,3)
    assert np.allclose(np.ptp(q[:,:,1],axis=1),0)
    assert np.allclose(np.ptp(q[:,:,0],axis=1),.8)
    restored=q.mean(1)+side['offset_m']
    assert np.allclose(restored,np.stack([p['u'],p['z'],-p['v']],1))
    assert np.cross(q[0,1]-q[0,0],q[0,2]-q[0,0])[1]>0
    print('city selftest OK',memory())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['corridor','build','preview','verify','selftest'])
    args=parser.parse_args()
    globals()[args.stage]()
