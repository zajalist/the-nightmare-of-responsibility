"""Expanded Toronto city. python -I city2.py crop|ground|meshes|audit|selftest.
Idle priority, one 50 m cell at a time. Keeps the first city's world origin.
"""
import array
import collections
import json
import math
import os
from pathlib import Path
import sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import toronto_city as base
import city_sources as source
import numpy as np
import shapely
from PIL import Image,ImageDraw,ImageFilter

base.PROC.nice(base.psutil.IDLE_PRIORITY_CLASS)
OUT=base.ROOT/'processed/queen_1600m'
base.OUT=OUT
U0,V0=-100.,-600.
NX,NY=32,24
Z0=90.04000091552734
SUN={'pitch':-45.,'yaw':-45.,'shadow_local_uv_direction':[1.,1.]}


def save(name,obj):base.save(OUT/name,obj)
def read(name):return json.loads((OUT/name).read_text())


def geometry():
    c=base.corridor()
    a=np.array(c['origin_utm_m']);u=np.array(c['along_utm']);v=np.array(c['left_utm'])
    c.update(length_m=1600,width_m=1200,local_bounds_m=[[-100,-600],[1500,600]],
             corners_utm_m=[(a+x*u+y*v).tolist() for x,y in [(-100,-600),(1500,-600),(1500,600),(-100,600)]],
             local_frame='Original Queen frame retained: u along Queen from Spadina, v north/left, z CGVD2013 metres',
             z_origin_m=Z0,ground_uv='Each 400 m ground tile: U east, V south; individual bounds in manifest')
    save('corridor.json',c)
    clamp={'world_units':'UE centimetres, unchanged queen_600m origin',
       'data_rect_cm':{'min':[-10000,-60000],'max':[150000,60000]},
       'camera_clamp_rect_cm':{'min':[6000,-44000],'max':[134000,44000]},
       'margin_m':160,'skirt_rect_cm':{'min':[-30000,-80000],'max':[170000,80000]},
       'camera':{'height_cm':5000,'horizontal_fov_deg':90,'reference_resolution':[1920,1080],
                 'ground_footprint_at_90_m':[100,56.25],'pitch_range_degrees':[55,90],
                 'max_ground_corner_radius_m':146,'yaw':'any; clamp actual camera XY, not the car or boom pivot'},
       'streaming':{'sector_size_m':200,'load_margin_m':120,'distance_cull_cm':18000},
       'drive_integration':'Clamp actual smoothed camera world X/Y each tick. Maximum vertical height 5000 cm above ground, horizontal FOV90, aspect16:9, pitch55..90. Existing BP_L2Car/rails unchanged.',
       'sun_rotation_degrees':SUN,'ground_plane_z_cm':(89.41-Z0)*100}
    save('drive_clamp.json',clamp)
    return c


def building_data():
    records=read('buildings.json')['records']
    polys=np.array([shapely.from_geojson(r['geometry']) for r in records],object)
    ids=np.array([r['building_id'] for r in records],np.int32)
    return records,polys,ids,shapely.STRtree(polys)


def crop():
    c=geometry();archive=source.download_massing()
    polys,ids=base.footprints(archive,c);tree=shapely.STRtree(polys)
    (OUT/'cells').mkdir(exist_ok=True)
    total=collections.Counter();tiles=[];assigned=near=unknown=0
    for east in [6290,6300]:
        for north in [48330,48340,48350]:
            done=OUT/f'crop_E{east}_N{north}.json'
            if done.exists():
                tiles.append(json.loads(done.read_text()));continue
            path,meta=source.fetch_tile(north,c,east,tag='city2')
            counts=collections.Counter();dropped=0;matching=[0,0,0]
            # Each tile writes separate cell fragments; retries never append duplicate points.
            fragments=OUT/'cells'/f'E{east}_N{north}'
            fragments.mkdir(exist_ok=True)
            handles={}
            try:
                for xyz,intensity,cls,withheld in source.read_nodes(path,meta):
                    u,v=base.local_xy(xyz[:,0],xyz[:,1],c)
                    mask=(u>=U0)&(u<U0+1600)&(v>=V0)&(v<V0+1200)
                    counts.update(dict(zip(*[a.tolist() for a in np.unique(cls[mask],return_counts=True)])))
                    reject=np.isin(cls,[7,18])|(xyz[:,2]<-60)|withheld
                    dropped+=int((mask&reject).sum());mask&=~reject
                    p=np.zeros(int(mask.sum()),base.POINT)
                    for k,d in [('u',u),('v',v),('z',xyz[:,2]),('intensity',intensity),('cls',cls)]:p[k]=d[mask]
                    bi=np.flatnonzero(p['cls']==6)
                    xy=xyz[mask,:2][bi]
                    bid=base.assign(xy[:,0],xy[:,1],polys,ids,tree)
                    matching[0]+=int((bid>0).sum())
                    missing=np.flatnonzero(bid==0)
                    if len(missing):
                        pts=shapely.points(xy[missing]);nn=tree.nearest(pts)
                        close=shapely.distance(pts,polys[nn])<=1
                        bid[missing[close]]=ids[nn[close]];matching[1]+=int(close.sum())
                    matching[2]+=int((bid==0).sum());p['bid'][bi]=bid
                    cells=np.floor((p['u']-U0)/50).astype(int)*NY+np.floor((p['v']-V0)/50).astype(int)
                    for cell in np.unique(cells):
                        if int(cell) not in handles:handles[int(cell)]=(fragments/f'{cell:03}.bin').open('wb')
                        p[cells==cell].tofile(handles[int(cell)])
                    base.memory()
            finally:
                for f in handles.values():f.close()
            result={'east':east,'north':north,'classes':dict(counts),'dropped':dropped,'matches_exact_near_unknown':matching,
                    'transferred_bytes':meta['transferred_bytes'],'source_bytes':meta['source_bytes'],'memory':base.memory()}
            base.save(done,result);tiles.append(result)
            print('tile complete',east,north,result,flush=True)
    for t in tiles:
        total.update({int(k):v for k,v in t['classes'].items()})
        assigned+=t['matches_exact_near_unknown'][0];near+=t['matches_exact_near_unknown'][1];unknown+=t['matches_exact_near_unknown'][2]
    save('crop_stats.json',{'tiles':tiles,'classes':dict(total),'exact_building_matches':assigned,'within_1m':near,
         'unknown_building_points':unknown,'memory':base.memory()})


def cell_points(cell):
    files=sorted((OUT/'cells').glob(f'*/{cell:03}.bin'))
    if not files:return np.empty(0,base.POINT)
    sizes=sum(f.stat().st_size for f in files)
    assert sizes<30_000_000,'Unexpectedly large cell; stream it before processing'
    return np.concatenate([np.fromfile(f,base.POINT) for f in files])


def identities(records,polys,ids):
    tree=shapely.STRtree(polys)
    pairs=tree.query(shapely.buffer(polys,1.0),predicate='intersects')
    adjacent=[set() for _ in ids]
    for a,b in pairs.T:
        if a!=b:adjacent[a].add(int(b));adjacent[b].add(int(a))
    palette=np.linspace(.23,.85,63)
    grey=np.full(len(ids),np.nan)
    order=sorted(range(len(ids)),key=lambda i:(-len(adjacent[i]),int(ids[i])))
    for i in order:
        height=max(0,float(records[i]['attributes'].get('AVG_HEIGHT') or 0))
        hashed=((int(ids[i])*2654435761)&0xffffffff)/2**32
        desired=.32+.28*min(height/100,1)+(hashed-.5)*.3
        taken=np.array([grey[j] for j in adjacent[i] if np.isfinite(grey[j])])
        distance=np.min(abs(palette[:,None]-taken),axis=1) if len(taken) else np.ones(len(palette))
        candidates=np.flatnonzero(distance>=.075)
        if not len(candidates):candidates=np.flatnonzero(distance==distance.max())
        pick=candidates[np.argmin(abs(palette[candidates]-desired))]
        grey[i]=palette[pick]
    edges=[(a,b) for a in range(len(ids)) for b in adjacent[a] if a<b]
    gap=min(abs(grey[a]-grey[b]) for a,b in edges)
    assert gap>.001,'Adjacent buildings must have different base greys'
    save('building_identity.json',{'neighbour_definition':'Footprints overlap or are <=1 metre apart',
        'adjacency_pairs':len(edges),'minimum_adjacent_base_grey_difference':float(gap),
        'values':{str(int(b)):float(g) for b,g in zip(ids,grey)},'sun':SUN})
    return grey


def local_geom(poly,c):
    return base.transform(lambda x,y,z=None:base.local_xy(np.asarray(x),np.asarray(y),c),poly)


def draw_polygon(draw,geom,origin,size,fill,shift=(0,0)):
    parts=list(geom.geoms) if geom.geom_type=='MultiPolygon' else [geom]
    for g in parts:
        if g.geom_type!='Polygon':continue
        coords=[((x+shift[0]-origin[0])/400*size,(origin[1]+400-y-shift[1])/400*size) for x,y in g.exterior.coords]
        draw.polygon(coords,fill=fill)


def ground():
    from scipy.ndimage import distance_transform_edt,maximum_filter
    c=read('corridor.json');records,polys,ids,_=building_data()
    identities(records,polys,ids)
    local=[local_geom(p,c) for p in polys]
    (OUT/'ground').mkdir(exist_ok=True)
    tiles=[]
    for tx in range(4):
        for ty in range(3):
            origin=(U0+tx*400,V0+ty*400);size=2048
            count=np.zeros(size*size,np.uint16);intensity=np.zeros(size*size,np.float32)
            for x in range(tx*8,tx*8+8):
                for y in range(ty*8,ty*8+8):
                    p=cell_points(x*NY+y);p=p[np.isin(p['cls'],[2,11])]
                    ix=np.clip(((p['u']-origin[0])/400*size).astype(int),0,size-1)
                    iy=np.clip(((origin[1]+400-p['v'])/400*size).astype(int),0,size-1)
                    pixel=iy*size+ix;np.add.at(count,pixel,1);np.add.at(intensity,pixel,p['intensity'])
            observed=(count>0).reshape(size,size)
            intensity=(intensity/np.maximum(count,1)).reshape(size,size)
            nn=distance_transform_edt(~observed,return_distances=False,return_indices=True)
            intensity=intensity[nn[0],nn[1]];del nn,count
            intensity[~maximum_filter(observed,size=9)]=np.median(intensity[observed])
            grey=.22+.55*np.clip((intensity-2805)/(63298-2805),0,1)
            ao=Image.new('L',(size,size));shadow=Image.new('L',(size,size))
            ad,sd=ImageDraw.Draw(ao),ImageDraw.Draw(shadow)
            for rec,geom in zip(records,local):
                if not geom.intersects(shapely.box(origin[0]-250,origin[1]-250,origin[0]+400,origin[1]+400)):continue
                h=min(180,max(3,float(rec['attributes'].get('AVG_HEIGHT') or 8)))
                draw_polygon(ad,geom,origin,size,255)
                # Swept projection fills the shadow between footprint and translated roof.
                swept=shapely.convex_hull(shapely.union(geom,base.transform(lambda x,y,z=None:(np.asarray(x)+h/math.sqrt(2),np.asarray(y)+h/math.sqrt(2)),geom)))
                draw_polygon(sd,swept,origin,size,255)
            factor=1-.20*np.asarray(ao.filter(ImageFilter.GaussianBlur(8)))/255-.28*np.asarray(shadow.filter(ImageFilter.GaussianBlur(4)))/255
            grey=np.clip(grey*factor,.08,.9)
            name=f'T_City2_Ground_{tx}_{ty}'
            Image.fromarray((grey*255).astype(np.uint8)).save(OUT/'ground'/(name+'.png'))
            tiles.append({'name':name,'file':'ground/'+name+'.png','local_bounds_m':[list(origin),[origin[0]+400,origin[1]+400]],
                          'actor_location_cm':[(origin[0]+200)*100,-(origin[1]+200)*100,(89.35-Z0)*100],
                          'observed_fraction':float(observed.mean())})
            print('ground',tx,ty,base.memory(),flush=True)
    save('ground_manifest.json',{'tiles':tiles,'metres_per_pixel':400/2048,'sun':SUN,'ground_is_flat_for_existing_drive':True})
    mosaic=Image.new('L',(1024,768))
    for t in tiles:
        tx,ty=map(int,t['name'].split('_')[-2:]);mosaic.paste(Image.open(OUT/t['file']).resize((256,256)),(tx*256,(2-ty)*256))
    skirt=Image.fromarray(np.pad(np.asarray(mosaic),128,mode='edge')).filter(ImageFilter.GaussianBlur(16))
    skirt.save(OUT/'ground/T_City2_Skirt.png')
    mosaic.save(OUT/'ground_overview.png')


def thin(p,cell):
    p=p[np.isin(p['cls'],[2,3,4,5,6,11])]
    output=[]
    for building in [True,False]:
        q=p[(p['cls']==6)==building]
        if not len(q):continue
        width=.32 if building else .65
        xyz=np.stack([np.floor(q[k]/width).astype(np.int32) for k in ['u','v','z']],1)
        _,i=np.unique(xyz,axis=0,return_index=True);q=q[i]
        cap=22000 if building else 6000
        if len(q)>cap:
            rng=np.random.default_rng(1000+cell+building)
            weight=np.ones(len(q))
            if building:
                xy=np.stack([np.floor(q[k]/.5).astype(np.int32) for k in ['u','v']],1)
                _,group=np.unique(xy,axis=0,return_inverse=True)
                roof=np.full(group.max()+1,-np.inf);np.maximum.at(roof,group,q['z'])
                weight+=3*(q['z']>=roof[group]-.5)
            priority=rng.exponential(size=len(q))/weight
            q=q[np.argpartition(priority,cap-1)[:cap]]
        output.append(q)
    return np.concatenate(output) if output else np.empty(0,base.POINT)


def attach_ids(doc,blob,ids):
    # Two exact half-float integers preserve source IDs without full-precision UV buffers.
    ids=np.asarray(ids,np.int32);assert np.all((ids>=0)&(ids<1024*1024))
    uv=np.repeat(np.stack([ids%1024,ids//1024],1).astype('<f4'),4,axis=0)
    assert np.all(uv.astype(np.float16).astype(np.float32)==uv)
    vi=len(doc['bufferViews']);ai=len(doc['accessors'])
    doc['bufferViews'].append({'buffer':0,'byteOffset':len(blob),'byteLength':uv.nbytes,'target':34962})
    doc['accessors'].append({'bufferView':vi,'componentType':5126,'count':len(uv),'type':'VEC2'})
    doc['meshes'][0]['primitives'][0]['attributes']['TEXCOORD_2']=ai
    blob=bytes(blob)+uv.tobytes();doc['buffers'][0]['byteLength']=len(blob)
    return blob


def render_height(height):
    return np.where(height<=25,height,25+15*(1-np.exp(-np.maximum(height-25,0)/50)))


def meshes():
    c=read('corridor.json');records,polys,ids,tree=building_data()
    identity=read('building_identity.json')['values'];index={int(b):i for i,b in enumerate(ids)}
    conv=base.module('ply_to_splatmesh')
    import city2_fast
    city2_fast.selftest(conv);city2_fast.install(conv)
    entries=[];counts=[];overview=collections.defaultdict(list)
    (OUT/'meshes').mkdir(exist_ok=True)
    for cell in range(NX*NY):
        name=f'SM_City2_C{cell:03}_0'
        if all((OUT/'meshes'/(name+suffix)).exists() for suffix in ['.gltf','.bin','.splatmesh.json']):
            doc=read('meshes/'+name+'.gltf');side=read('meshes/'+name+'.splatmesh.json')
            assert (OUT/'meshes'/(name+'.bin')).stat().st_size==doc['buffers'][0]['byteLength']
            renderer=base.module('splat_preview');pos,rad,col,_=renderer.load(str(OUT/'meshes'/(name+'.gltf')))
            pos[:,0]+=rad;pos[:,2]-=rad;pos+=np.asarray(side['offset_m'])
            q=np.zeros(len(pos),base.POINT);q['u']=pos[:,0];q['v']=-pos[:,2];q['z']=pos[:,1]+Z0
            x,y=divmod(cell,NY);sector=[x//4,y//4];building=rad>(.3 if doc.get('extras',{}).get('city2_coverage_tuned') else .2)
            counts.append({'cell':cell,'splats':len(q),'buildings':int(building.sum()),'ground':int((~building).sum()),'sector':sector})
            take=np.linspace(0,len(q)-1,min(180,len(q)),dtype=int);overview[tuple(sector)].append((q[take].copy(),col[take,0].copy()))
            off=side['offset_m'];entries.append({'name':name,'gltf':'meshes/'+name+'.gltf','splats':len(q),'cell':cell,'sector':sector,
                'actor_location_cm':[off[0]*100,off[2]*100,off[1]*100],'offset_gltf_m':off,
                'bounds_gltf_m':[doc['accessors'][0]['min'],doc['accessors'][0]['max']],
                'bounds_uv_m':[[float(q['u'].min()),float(q['v'].min())],[float(q['u'].max()),float(q['v'].max())]]})
            if cell%24==0:print('resumed mesh column',x,flush=True)
            continue
        p=thin(cell_points(cell),cell)
        if not len(p):continue
        p.sort(order=['bid','u','v','z'])
        x,y=divmod(cell,NY);sector=[x//4,y//4]
        tx,ty=x//8,y//8
        ground_image=np.asarray(Image.open(OUT/f'ground/T_City2_Ground_{tx}_{ty}.png'))
        ix=np.clip(((p['u']-(U0+tx*400))/400*2048).astype(int),0,2047)
        iy=np.clip((((V0+ty*400)+400-p['v'])/400*2048).astype(int),0,2047)
        colour=ground_image[iy,ix].astype(np.float32)/255
        building=p['cls']==6
        u,v=p['u'].astype(float),p['v'].astype(float)
        e=c['origin_utm_m'][0]+u*c['along_utm'][0]+v*c['left_utm'][0]
        n=c['origin_utm_m'][1]+u*c['along_utm'][1]+v*c['left_utm'][1]
        points=shapely.points(e,n);nearest=tree.nearest(points)
        chosen=np.array([index.get(int(b),int(nn)) for b,nn in zip(p['bid'],nearest)])
        distance=shapely.distance(points,shapely.boundary(polys[chosen]))
        for bid in np.unique(p['bid'][building]):
            mask=building&(p['bid']==bid)
            colour[mask]=identity.get(str(bid),.42)+.025*(np.clip((p['intensity'][mask].astype(float)-2805)/60493,0,1)-.5)
        colour[building&(distance<.75)]*=.48
        height=p['z'][building]-89.41
        # A fixed 50m perspective camera cannot see real Toronto tower roofs above it.
        height=render_height(height)
        p['z'][building]=89.41+height
        p['z'][~building]=89.41
        radii=np.where(building,.24,.18)
        take=np.linspace(0,len(p)-1,min(180,len(p)),dtype=int)
        overview[tuple(sector)].append((p[take].copy(),colour[take].copy()))
        counts.append({'cell':cell,'splats':len(p),'buildings':int(building.sum()),'ground':int((~building).sum()),'sector':sector})
        for part,start in enumerate(range(0,len(p),28000)):
            q=p[start:start+28000];grey=colour[start:start+28000];radius=radii[start:start+28000]
            name=f'SM_City2_C{cell:03}_{part}'
            if all((OUT/'meshes'/(name+suffix)).exists() for suffix in ['.gltf','.bin','.splatmesh.json']):
                doc=read('meshes/'+name+'.gltf');side=read('meshes/'+name+'.splatmesh.json')
                assert side['splats']==len(q) and (OUT/'meshes'/(name+'.bin')).stat().st_size==doc['buffers'][0]['byteLength']
                off=side['offset_m']
                entries.append({'name':name,'gltf':'meshes/'+name+'.gltf','splats':len(q),'cell':cell,'sector':sector,
                    'actor_location_cm':[off[0]*100,off[2]*100,off[1]*100],'offset_gltf_m':off,
                    'bounds_gltf_m':[doc['accessors'][0]['min'],doc['accessors'][0]['max']],
                    'bounds_uv_m':[[float(q['u'].min()),float(q['v'].min())],[float(q['u'].max()),float(q['v'].max())]]})
                continue
            fields=list(conv.REQUIRED);rows=np.zeros((len(q),len(fields)),'<f4')
            def col(k,val):rows[:,fields.index(k)]=val
            col('x',q['u']);col('y',-(q['z']-Z0));col('z',q['v']);col('rot_0',1);col('opacity',8)
            for k in range(3):col(f'f_dc_{k}',(grey-.5)/conv.C0);col(f'scale_{k}',np.log(radius/2))
            header=('ply\nformat binary_little_endian 1.0\nelement vertex '+str(len(q))+'\n'+''.join('property float '+f+'\n' for f in fields)+'end_header\n').encode()
            doc,blob,side=conv.convert(header+rows.tobytes(),len(q),cell,name,src='GTA 2023 city2 50m cell',lean=True)
            blob=attach_ids(doc,base.bake_quads(doc,blob),q['bid'])
            (OUT/'meshes'/(name+'.bin')).write_bytes(blob);save('meshes/'+name+'.gltf',doc)
            unique,first,num=np.unique(q['bid'],return_index=True,return_counts=True)
            side.update(static_facing='+UE Z; no billboard expansion',building_id_encoding='UV2.x + 1024*UV2.y; exact half floats; ID 0 ground or unassigned',building_ranges=[{'building_id':int(b),'first':int(i),'count':int(j)} for b,i,j in zip(unique,first,num)],radius_scale_hint=1)
            save('meshes/'+name+'.splatmesh.json',side)
            off=side['offset_m']
            entries.append({'name':name,'gltf':'meshes/'+name+'.gltf','splats':len(q),'cell':cell,'sector':sector,
              'actor_location_cm':[off[0]*100,off[2]*100,off[1]*100],'offset_gltf_m':off,
              'bounds_gltf_m':[doc['accessors'][0]['min'],doc['accessors'][0]['max']],
              'bounds_uv_m':[[float(q['u'].min()),float(q['v'].min())],[float(q['u'].max()),float(q['v'].max())]]})
        if cell%24==0:print('mesh column',x,'splats so far',sum(e['splats'] for e in entries),base.memory(),flush=True)
    lod=[]
    for sector,parts in overview.items():
        q=np.concatenate([v[0] for v in parts]);grey=np.concatenate([v[1] for v in parts])
        name=f'SM_City2_Overview_{sector[0]}_{sector[1]}'
        fields=list(conv.REQUIRED);rows=np.zeros((len(q),len(fields)),'<f4')
        for key,value in [('x',q['u']),('y',-(q['z']-Z0)),('z',q['v']),('rot_0',1),('opacity',8)]:rows[:,fields.index(key)]=value
        for k in range(3):
            rows[:,fields.index(f'f_dc_{k}')]=(grey-.5)/conv.C0
            rows[:,fields.index(f'scale_{k}')]=np.log(1.8/2)
        header=('ply\nformat binary_little_endian 1.0\nelement vertex '+str(len(q))+'\n'+''.join('property float '+f+'\n' for f in fields)+'end_header\n').encode()
        doc,blob,side=conv.convert(header+rows.tobytes(),len(q),0,name,src='City2 distant overview',lean=True)
        (OUT/'meshes'/(name+'.bin')).write_bytes(base.bake_quads(doc,blob));save('meshes/'+name+'.gltf',doc)
        off=side['offset_m'];lod.append({'name':name,'gltf':'meshes/'+name+'.gltf','splats':len(q),'sector':sector,
            'actor_location_cm':[off[0]*100,off[2]*100,off[1]*100]})
    save('manifest.json',{'meshes':entries,'overview':lod,'cells':counts,'splats':sum(e['splats'] for e in entries),
         'z_origin_m':Z0,'sectors':sorted({tuple(e['sector']) for e in entries}),'memory':base.memory(),
         'render_height':'Source height h above 89.41m: h<=25 unchanged; above25 rendered as 25+15*(1-exp(-(h-25)/50)), below40m. Raw elevations remain intact. Shadows and grey height bias use original massing heights.',
         'material':'Existing /Game/FoA/Level2/M_SplatCity_Lean, unchanged. Identity/edges in vertex colour.',
         'identity':'Per-splat source IDs in UV2.x + 1024*UV2.y, also building_ranges in sidecars. A 50m chunk may contain multiple buildings; shader ID support enables individual dissolves later.'})


def audit():
    m=read('manifest.json');counts=np.zeros((NX,NY),np.int64)
    if not m.get('coverage_tuned'):
        for e in m['meshes']:
            doc=read(e['gltf']);path=OUT/Path(e['gltf']).with_suffix('.bin');blob=bytearray(path.read_bytes())
            if doc.get('extras',{}).get('city2_coverage_tuned'):continue
            attrs=doc['meshes'][0]['primitives'][0]['attributes'];a=doc['accessors'][attrs['TEXCOORD_1']]
            radius=np.frombuffer(blob,'<f4',a['count']*2,doc['bufferViews'][a['bufferView']]['byteOffset']).reshape(-1,2)
            radius[:,0]=np.where(radius[:,0]>20,36.,24.)
            blob=base.bake_quads(doc,blob);path.write_bytes(blob)
            doc.setdefault('extras',{})['city2_coverage_tuned']=True;save(e['gltf'],doc)
            e['bounds_gltf_m']=[doc['accessors'][attrs['POSITION']]['min'],doc['accessors'][attrs['POSITION']]['max']]
        m['coverage_tuned']={'building_radius_m':.36,'ground_radius_m':.24,'reason':'Denser coverage with the existing Gaussian dither material'}
        save('manifest.json',m)
    for e in m['cells']:counts[divmod(e['cell'],NY)]=e['splats']
    max9=max(int(counts[x:x+4,y:y+4].sum()) for x in range(NX-3) for y in range(NY-3))
    assert max9<=1_500_000
    tilted=max(int(counts[x:x+7,y:y+7].sum()) for x in range(NX-6) for y in range(NY-6))
    assert tilted<=1_500_000
    views=[('spadina',155,0),('university',800,0),('play_corner',60,440)]
    result=[]
    for name,u,v in views:
        selected=[e for e in m['meshes'] if e['bounds_uv_m'][0][0]<=u+50 and e['bounds_uv_m'][1][0]>=u-50 and e['bounds_uv_m'][0][1]<=v+50 and e['bounds_uv_m'][1][1]>=v-50]
        result.append({'name':name,'camera_xy_cm':[u*100,-v*100],'conservative_visible_splats':sum(e['splats'] for e in selected),'meshes':len(selected)})
    for e in m['meshes']:
        doc=read(e['gltf']);blob=OUT/Path(e['gltf']).with_suffix('.bin')
        assert blob.stat().st_size==doc['buffers'][0]['byteLength']
        assert set(doc['meshes'][0]['primitives'][0]['attributes'])=={'POSITION','TEXCOORD_0','TEXCOORD_1','TEXCOORD_2','COLOR_0'}
        side_path=Path(e['gltf']).with_suffix('.splatmesh.json');side=read(side_path)
        cell=m['cells'][e['cell']]
        side['radius_cm']={'min':24. if cell['ground'] else 36.,'median':36. if cell['buildings']>=cell['ground'] else 24.,'max':36. if cell['buildings'] else 24.}
        side['channels']['POSITION']='Baked horizontal quad corners in glTF metres, relative to offset_m'
        side['channels']['TEXCOORD_2']='Source building ID packed as low/high 10-bit integers; ID = x + 1024*y'
        save(side_path,side)
    import csv
    with (OUT/'output_sizes.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['relative_path','bytes'])
        for folder in ['meshes','ground','previews']:
            for path in sorted((OUT/folder).glob('*')):
                if path.is_file():writer.writerow([path.relative_to(OUT).as_posix(),path.stat().st_size])
    save('audit.json',{'splats':m['splats'],'meshes':len(m['meshes']),'max_visible_100m_square_conservative':max9,
         'max_tilted_55_to_90_conservative':tilted,'tilted_method':'All splats in any 7x7 cells, covering a radius146m around the camera for all yaw at height50m, FOV90, aspect16:9, pitch55..90. Below-ground returns are occluded by the opaque ground plane.',
         'method':'Conservative cell bound: all splats in any 4x4 50m cells, including cell-boundary and quad-radius padding around a 100x100m ground footprint; native proof frustum counts are measured separately.',
         'proof_views':result,'memory':base.memory(),'mesh_binary_bytes':sum(p.stat().st_size for p in (OUT/'meshes').glob('*.bin'))})
    handoff=read('drive_clamp.json')
    handoff['city_map']='/Game/FoA/Level2/Maps/L_L2_CityTest2'
    handoff['streaming_map_packages']=[f'/Game/FoA/Level2/Maps/City2/L_City2_S{x}_{y}' for x,y in m['sectors']]
    handoff['cook_note']='Include these maps in the cook; streamed by full package name. Packaged build not verified.'
    base.save(Path('P:/FoA/Saved/Codex/l2_city_camera_bounds.json'),handoff)
    print(read('audit.json'),flush=True)


def selftest():
    c=geometry();assert np.all(np.array(c['corners_utm_m'])[:,0]>629000) and np.all(np.array(c['corners_utm_m'])[:,0]<631000)
    clamp=read('drive_clamp.json');lo=clamp['camera_clamp_rect_cm']['min'];hi=clamp['camera_clamp_rect_cm']['max']
    assert lo==[6000,-44000] and hi==[134000,44000]
    for pitch in [55,60,70,75,90]:
        angle=math.radians(pitch)
        for vertical in [-.5625,.5625]:
            scale=50/(math.sin(angle)-vertical*math.cos(angle))
            radius=math.hypot(scale,scale*(math.cos(angle)+vertical*math.sin(angle)))
            assert radius<146<160
    for x in [lo[0],hi[0]]:
        for y in [lo[1],hi[1]]:
            assert x-5000>=-10000 and x+5000<=150000 and y-5000>=-60000 and y+5000<=60000
    p=np.zeros(10,base.POINT);p['u']=1;p['v']=2;p['z']=90;p['cls']=6
    assert len(thin(p,0))==1
    doc={'bufferViews':[],'accessors':[],'buffers':[{}],'meshes':[{'primitives':[{'attributes':{}}]}]}
    blob=attach_ids(doc,b'',np.array([0,1023,1024,1048575]))
    uv=np.frombuffer(blob,'<f4').reshape(-1,2)[::4]
    assert np.array_equal(uv[:,0]+1024*uv[:,1],[0,1023,1024,1048575])
    heights=render_height(np.array([0.,10.,25.,100.,400.]))
    assert np.array_equal(heights[:3],[0,10,25]) and np.all(np.diff(heights)>0) and heights[-1]<40
    import city2_fast
    city2_fast.selftest(base.module('ply_to_splatmesh'))
    print('city2 selftest OK',base.memory())


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('stage',choices=['crop','ground','meshes','audit','selftest'])
    stage=ap.parse_args().stage;save('worker_'+stage+'.json',{'pid':os.getpid(),'priority':'Idle'})
    globals()[stage]()
