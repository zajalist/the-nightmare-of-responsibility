"""Offline density upgrade for the LIVE original600m city, retaining asset IDs and placed pivots.

Existing selected points remain; add measured lidar returns with facade priority.
No synthesized buildings, terrain/collision edits, downloads, or material changes.
python -I Tools/Splats/city/prepare_city_density.py
"""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import toronto_city as base
import city2_fast
import numpy as np

SOURCE=base.ROOT/'processed/queen_600m'
OUTPUT=base.ROOT/'processed/queen_600m_dense'
TARGET=1_800_000
VOXEL=.32
RADIUS=.34

def voxel_keys(points,width=VOXEL):
    xyz=np.stack([np.floor(points[k]/width).astype('<i4') for k in ('u','v','z')],1)
    return np.ascontiguousarray(xyz).view('V12').reshape(-1)

def enrich(old,raw,wanted,seed):
    """Keep all old samples, append unique measured voxels, favour lower facade returns."""
    keys=voxel_keys(raw);_,first=np.unique(keys,return_index=True)
    raw=raw[first];keys=keys[first]
    raw=raw[~np.isin(keys,voxel_keys(old))]
    room=max(0,wanted-len(old))
    if room<len(raw):
        roof=float(np.percentile(raw['z'],90))
        weight=np.where(raw['z']<roof-1.5,4.,1.)
        priority=np.random.default_rng(seed).exponential(size=len(raw))/weight
        raw=raw[np.argpartition(priority,room)[:room]] if room else raw[:0]
    previous=np.empty(len(old),base.POINT)
    for key in base.POINT.names:previous[key]=old[key]
    out=np.concatenate([previous,raw.astype(base.POINT)])
    out.sort(order=['u','v','z'])
    return out

def main():
    baseline=json.loads((SOURCE/'manifest.json').read_text())
    selected=np.fromfile(SOURCE/'selected_splats.bin',base.SAMPLE)
    raw=np.memmap(SOURCE/'crop_points.bin',dtype=base.POINT,mode='r')
    buildings=raw[raw['cls']==6].copy();buildings.sort(order=['bid','u','v','z'])
    groups={}
    for entry in baseline['meshes']:groups.setdefault(entry['dissolve_group'],[]).append(entry)
    hist=np.load(SOURCE/'intensity_histogram.npy');sums=np.cumsum(hist)
    limits=[int(np.searchsorted(sums,sums[-1]*f)) for f in (.02,.98)]
    converter=base.module('ply_to_splatmesh');city2_fast.install(converter)
    OUTPUT.mkdir(exist_ok=True);base.OUT=OUTPUT
    ratio=TARGET/baseline['splats'];entries=[];added=0
    for number,(group,old_entries) in enumerate(groups.items()):
        bid=old_entries[0]['building_id']
        if bid:
            old=selected[selected['bid']==bid]
            lo,hi=np.searchsorted(buildings['bid'],bid,side='left'),np.searchsorted(buildings['bid'],bid,side='right')
            candidates=buildings[lo:hi]
        else:
            cell=int(group.rsplit('_',1)[1]);old=selected[selected['bid']==0]
            raw0=buildings[buildings['bid']==0]
            def cell_of(p):return (p['u']//50).astype(int)*12+np.clip(((p['v']+300)//50).astype(int),0,11)
            old=old[cell_of(old)==cell];candidates=raw0[cell_of(raw0)==cell]
        assert len(old)==sum(e['splats'] for e in old_entries),(group,len(old))
        old.sort(order=['u','v','z'])
        points=enrich(old,candidates,max(len(old),round(len(old)*ratio)),1000+number)
        added+=len(points)-len(old)
        # Split around the original parts' u boundaries; each existing actor keeps its exact pivot.
        cuts=[float(e['bounds_local_uvz_m'][1][0]) for e in old_entries[:-1]]
        assignment=np.searchsorted(cuts,points['u'],side='left')
        for part,e in enumerate(old_entries):
            p=points[assignment==part]
            if not len(p):raise AssertionError(('Empty existing part',e['name']))
            entry=base.write_mesh(p,e['name'],baseline['z_origin_m'],limits,converter,
                                  origin=e['offset_gltf_m'],building_radius=RADIUS)
            for key in ('building_id','dissolve_group','kind'):entry[key]=e[key]
            assert entry['offset_gltf_m']==e['offset_gltf_m'],e['name']
            assert entry['actor_location_cm']==e['actor_location_cm'],e['name']
            entry['previous_splats']=e['splats'];entries.append(entry)
        if number%30==0:print('density groups',number,'/',len(groups),'added',added,flush=True)
    manifest=dict(baseline,meshes=entries,splats=sum(e['splats'] for e in entries))
    manifest['density_upgrade']=dict(previous_splats=baseline['splats'],genuine_building_returns=len(buildings),
        voxel_m=VOXEL,radius_m=RADIUS,added_points=added,preserve_all_previous_samples=True,
        preserve_asset_names_and_actor_locations=True,source=str(SOURCE/'crop_points.bin'),
        estimated_gpu_geometry_bytes=manifest['splats']*184)
    manifest['mesh_bytes']=sum(e['bytes'] for e in entries)
    base.save(OUTPUT/'manifest.json',manifest)
    print(json.dumps(manifest['density_upgrade']),flush=True)

# Streamed version keeps the original imported map/assets intact until native proof.
STREAMED=SOURCE.with_name('queen_600m_streamed')
CELL=50.;GRID=12;GROUND_STEP=.5;FACADE_MIN_STEP=.35
BUILDING_BUDGET=40000;MEASURED_BUDGET=10000


def clip_segment(a,b,bounds):
    lo,hi=0.,1.;dx,dy=b[0]-a[0],b[1]-a[1]
    for p,q in ((-dx,a[0]-bounds[0]),(dx,bounds[2]-a[0]),(-dy,a[1]-bounds[1]),(dy,bounds[3]-a[1])):
        if abs(p)<1e-12:
            if q<0:return None
        elif p<0:lo=max(lo,q/p)
        else:hi=min(hi,q/p)
        if lo>=hi:return None
    return (a[0]+lo*dx,a[1]+lo*dy,a[0]+hi*dx,a[1]+hi*dy)


def wall_cells():
    import shapely
    from shapely.geometry import LineString,Polygon
    frame=json.loads((SOURCE/'corridor.json').read_text())
    records=json.loads((SOURCE/'buildings.json').read_text())['records']
    cells=[[] for _ in range(GRID*GRID)];parts=[];polygons=[]
    for rec in records:
        g=json.loads(rec['geometry']);polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
        height=max(4.,float(rec['attributes'].get('AVG_HEIGHT') or 4))
        for polygon in polys:
            rings=[]
            for ring in polygon:
                a=np.asarray(ring,float)-np.asarray(frame['origin_utm_m'])
                rings.append(np.stack((a@np.asarray(frame['along_utm']),-a@np.asarray(frame['left_utm'])),1))
            polygons.append(Polygon(rings[0],rings[1:]))
            for xy in rings:
                parts.extend((a,b,height,int(rec['building_id'])) for a,b in zip(xy,xy[1:]))
    # Adjacent massing records include thousands of buried party walls. Spending
    # the close-detail budget there would starve the accessible street facades.
    union=shapely.union_all(shapely.make_valid(polygons));shapely.prepare(union)
    for start,end,height,bid in parts:
        if np.linalg.norm(end-start)<.15:continue
        length=float(np.linalg.norm(end-start));pieces=max(1,int(np.ceil(length)))
        direction=(end-start)/length;normal=np.asarray((-direction[1],direction[0]))*.08
        mid=start+(end-start)*((np.arange(pieces)+.5)/pieces)[:,None]
        left=shapely.contains_xy(union,mid[:,0]+normal[0],mid[:,1]+normal[1])
        right=shapely.contains_xy(union,mid[:,0]-normal[0],mid[:,1]-normal[1])
        # One side outside the combined footprint identifies accessible exterior.
        visible=np.flatnonzero(left!=right)
        if not len(visible):continue
        spans=np.split(visible,np.flatnonzero(np.diff(visible)>1)+1)
        original_start=start.copy();original_end=end.copy()
        for span in spans:
            start=original_start+(original_end-original_start)*float(span[0])/pieces
            end=original_start+(original_end-original_start)*float(span[-1]+1)/pieces
            xmin,xmax=sorted((start[0],end[0]));ymin,ymax=sorted((start[1],end[1]))
            for cx in range(max(0,int(xmin//CELL)),min(GRID-1,int(xmax//CELL))+1):
                for cy in range(max(0,int((ymin+300)//CELL)),min(GRID-1,int((ymax+300)//CELL))+1):
                    segment=clip_segment(start,end,(cx*CELL,cy*CELL-300,(cx+1)*CELL,(cy+1)*CELL-300))
                    if segment:
                        cells[cx*GRID+cy].append((*segment,0.,min(12.,height),bid))
                        if height>12:cells[cx*GRID+cy].append((*segment,12.,height,bid))
    return cells


def facade_grid(segments,budget):
    import math
    assert budget>=len(segments),('Each exposed segment needs at least one splat',len(segments),budget)
    area=sum(math.hypot(r[2]-r[0],r[3]-r[1])*(r[5]-r[4]) for r in segments)
    step=max(FACADE_MIN_STEP,math.sqrt(area/max(1,budget)))
    def count(s):return sum(max(1,math.ceil(math.hypot(r[2]-r[0],r[3]-r[1])/s))*max(1,math.ceil((r[5]-r[4])/s)) for r in segments)
    while count(step)>budget:step*=1.01
    return step,count(step)


def stream_plan():
    walls=wall_cells();counts=np.zeros(GRID*GRID,np.int64)
    for raw in base.point_chunks(SOURCE/'crop_points.bin'):
        raw=raw[raw['cls']==6]
        x=np.clip((raw['u']//CELL).astype(int),0,GRID-1);y=np.clip(((300-raw['v'])//CELL).astype(int),0,GRID-1)
        counts+=np.bincount(x*GRID+y,minlength=GRID*GRID)
    rows=[]
    for index,segments in enumerate(walls):
        cx,cy=divmod(index,GRID);measured=min(int(counts[index]),MEASURED_BUDGET)
        lower=[r for r in segments if r[4]==0];upper=[r for r in segments if r[4]>0]
        budget=BUILDING_BUDGET-measured
        spacing,lower_count=facade_grid(lower,int(budget*.8) if upper else budget)
        upper_spacing,upper_count=facade_grid(upper,budget-lower_count)
        facades=lower_count+upper_count
        rows.append(dict(cell=index,cell_xy=[cx,cy],sector=[cx,cy],centre_cm=[(cx+.5)*5000,(cy+.5)*5000-30000,-63],
            measured_candidates=int(counts[index]),measured_budget=measured,facade_splats=facades,
            facade_spacing_m=spacing,upper_spacing_m=upper_spacing,lower_facade_splats=lower_count,upper_facade_splats=upper_count,
            facade_radius_m=spacing*1.75,ground_splats=10000,
            near_splats=measured+facades+10000,far_splats=2000))
    old=json.loads((OUTPUT/'manifest.json').read_text());size=0
    for e in old['meshes']:
        f=Path('P:/FoA/Content/FoA/Level2/City/Meshes')/e['name']/'StaticMeshes'/(e['name']+'.uasset')
        if f.exists():size+=f.stat().st_size
    ratio=size/old['splats'];weights=np.asarray([r['near_splats'] for r in rows]);centres=np.asarray([r['centre_cm'][:2] for r in rows])/100
    worst={}
    for radius in (90,115):
        maximum=(0,None)
        for x in range(0,601,25):
            for y in range(-300,301,25):
                delta=np.maximum(np.abs(centres-(x,y))-25,0);distance=np.sqrt((delta*delta).sum(1))
                n=int(weights[distance<=radius].sum())
                if n>maximum[0]:maximum=(n,[x,y])
        worst[str(radius)]=dict(splats=maximum[0],camera_m=maximum[1])
    result=dict(cells=rows,sectors=[r['sector'] for r in rows],z_origin_m=90.04000091552734,
        cell_size_m=50,sector_size_m=50,near_blend_m=[60,80],load_m=90,unload_m=115,poll_seconds=.25,
        near_splats=int(weights.sum()),far_splats=288000,worst_residency=worst,
        native_bytes_per_splat=ratio,estimated_native_asset_bytes=int((weights.sum()+288000)*ratio),
        estimated_resident_geometry_bytes=(worst['115']['splats']+288000)*184,
        provenance={'measured':'NRCan GTA2023 lidar, existing crop_points.bin; selected genuine returns',
          'facades':'Original procedural grids on exposed City of Toronto2025 massing footprint edges and AVG_HEIGHT; lower12m prioritized; scan-intensity-derived greys with authored window bands; NOT measured facade geometry or imagery',
          'ground':'Original regular0.5m splat grid sampling the existing approved Toronto ground intensity texture; NOT measured point locations'})
    STREAMED.mkdir(exist_ok=True);base.save(STREAMED/'density_plan.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('cells','sectors','provenance')},indent=2),flush=True)
    return result,walls


def write_stream_mesh(points,radii,colours,name,cell,kind,lod):
    import array
    converter=base.module('ply_to_splatmesh');n=len(points)
    cx,cy=divmod(cell,GRID);origin=np.asarray([(cx+.5)*50,-.63,(cy+.5)*50-300],float)
    centre=points-origin
    corners=np.asarray(((-1,-1),(1,-1),(1,1),(-1,1)),np.float32)
    position=np.repeat(centre[:,None,:],4,axis=1)
    position[:,:,0]+=corners[None,:,0]*radii[:,None]
    position[:,:,2]-=corners[None,:,1]*radii[:,None]
    seed=((np.arange(n,dtype=np.uint32)*73+cell*151)%997)/997.
    values={'POSITION':position,'TEXCOORD_0':np.tile(corners,(n,1)),
            'TEXCOORD_1':np.repeat(np.stack((radii*100,seed),1),4,axis=0),
            'COLOR_0':np.repeat(np.column_stack((colours,colours,colours,np.ones(n))),4,axis=0)}
    attrs={}
    for key,value in values.items():
        a=array.array('f');a.frombytes(np.asarray(value,'<f4').tobytes());attrs[key]=a
    idx=array.array('I');idx.frombytes((np.arange(n,dtype=np.uint32)[:,None]*4+np.asarray((0,1,2,0,2,3),np.uint32)).tobytes())
    doc,blob=converter.gltf_doc(attrs,idx,name)
    folder=STREAMED/'meshes';folder.mkdir(exist_ok=True)
    (folder/(name+'.bin')).write_bytes(blob);base.save(folder/(name+'.gltf'),doc)
    return dict(name=name,gltf='meshes/'+name+'.gltf',splats=n,cell=cell,cell_xy=[cx,cy],sector=[cx,cy],kind=kind,lod=lod,
        actor_location_cm=[float(origin[0]*100),float(origin[2]*100),float(origin[1]*100)],offset_gltf_m=origin.tolist(),
        material='/Game/FoA/Level2/City/M_City_Ground' if kind=='ground' else '/Game/FoA/Level2/M_SplatCity_Lean',
        asset_path='/Game/FoA/Level2/City/Dense/Meshes/'+name+'/StaticMeshes/'+name,bytes=len(blob),
        radius_cm_max=float(radii.max()*100),bounds_gltf_m=[doc['accessors'][0]['min'],doc['accessors'][0]['max']],
        cpd={'3':-63,'4':-2 if kind=='ground' else 0,'5':1 if lod=='near' else 2})


def facade_samples(segments,lower_step,upper_step):
    import math
    points=[];radii=[];windows=[]
    for ax,ay,bx,by,z0,z1,bid in segments:
        step=lower_step if z0==0 else upper_step;length=math.hypot(bx-ax,by-ay)
        n=max(1,math.ceil(length/step));nz=max(1,math.ceil((z1-z0)/step))
        t=(np.arange(n)+.5)/n;z=z0+(np.arange(nz)+.5)/nz*(z1-z0)-.63
        pts=np.column_stack((np.repeat(ax+(bx-ax)*t,nz),np.tile(z,n),np.repeat(ay+(by-ay)*t,nz)))
        points.append(pts);radii.extend([step*1.75]*len(pts))
        horizontal=(pts[:,0]*(bx-ax)/length+pts[:,2]*(by-ay)/length)/(2.8+.1*(bid%4))
        vertical=(pts[:,1]+.63)/(3.2+.1*(bid%3))
        windows.extend(((horizontal%1>.19)&(horizontal%1<.78)&(vertical%1>.21)&(vertical%1<.79)).tolist())
    return (np.concatenate(points) if points else np.empty((0,3))),np.asarray(radii),np.asarray(windows)


def stream_build(start=0,count=144):
    import math,gc
    from scipy.spatial import cKDTree
    from PIL import Image
    plan,walls=stream_plan();raw=np.memmap(SOURCE/'crop_points.bin',dtype=base.POINT,mode='r')
    texture=np.asarray(Image.open(SOURCE/'ground_intensity_4096.png'))
    hist=np.load(SOURCE/'intensity_histogram.npy');sums=np.cumsum(hist);limits=[int(np.searchsorted(sums,sums[-1]*f)) for f in (.02,.98)]
    # Per-cell raw slice is bounded; no city-sized selected-point copy.
    for cell in range(start,min(start+count,144)):
        row=plan['cells'][cell];cx,cy=row['cell_xy'];x0=cx*50;y0=cy*50-300
        part=STREAMED/f'cell_{cell:03}.json'
        if part.exists():
            existing=json.loads(part.read_text())
            if existing.get('format_version')==2 and all((STREAMED/e['gltf']).exists() for e in existing['meshes']):continue
        pick=(raw['cls']==6)&(raw['u']>=x0)&(raw['u']<x0+50)&(-raw['v']>=y0)&(-raw['v']<y0+50)
        r=raw[pick].copy();xyz=np.column_stack((r['u'],r['z']-plan['z_origin_m'],-r['v']))
        rawcolour=base.normalise(r['intensity'],*limits)
        tree=cKDTree(xyz) if len(xyz) else None
        count_raw=min(len(xyz),row['measured_budget'])
        chosen=np.linspace(0,len(xyz)-1,count_raw,dtype=int) if count_raw else np.empty(0,int)
        measured=xyz[chosen];measured_colour=rawcolour[chosen]
        spacing=row['facade_spacing_m']
        facade,facade_radii,window_masks=facade_samples(walls[cell],spacing,row['upper_spacing_m'])
        assert len(facade)==row['facade_splats']
        def paint_facade(points,window):
            if len(points) and tree:
                distance,nearest=tree.query(points,k=1,workers=1)
                colour=np.where(distance<8,rawcolour[nearest],np.median(rawcolour))
            else:colour=np.full(len(points),.4)
            return (.2+.7*colour)*np.where(window,.58,1.)
        building=np.concatenate((measured,facade))
        building_colour=np.concatenate((measured_colour,paint_facade(facade,window_masks)))
        building_radius=np.concatenate((np.full(len(measured),.42),facade_radii))
        # Far facade grids are re-sampled regularly. Striding a flattened grid
        # would create diagonal sparse rows and visible holes at the LOD seam.
        fm=min(225,len(measured));far_budget=1375-fm
        lower=[r for r in walls[cell] if r[4]==0];upper=[r for r in walls[cell] if r[4]>0]
        fs,fn=facade_grid(lower,int(far_budget*.8) if upper else far_budget)
        fu,_=facade_grid(upper,far_budget-fn)
        fp,fr,fw=facade_samples(walls[cell],fs,fu)
        fi=np.linspace(0,len(measured)-1,fm,dtype=int) if fm else np.empty(0,int)
        far_building=np.concatenate((measured[fi],fp))
        far_colour=np.concatenate((measured_colour[fi],paint_facade(fp,fw)))
        far_radius=np.concatenate((np.full(fm,.42*math.sqrt(max(len(measured),1)/max(fm,1))),fr))
        xy=(np.arange(100)+.5)*.5;gx,gy=np.meshgrid(x0+xy,y0+xy,indexing='ij')
        ground=np.column_stack((gx.ravel(),np.full(10000,-.63),gy.ravel()))
        tx=np.clip((ground[:,0]/600*(texture.shape[1]-1)).round().astype(int),0,texture.shape[1]-1)
        ty=np.clip(((ground[:,2]+300)/600*(texture.shape[0]-1)).round().astype(int),0,texture.shape[0]-1)
        ground_colour=texture[ty,tx].astype(float)/255
        entries=[]
        for kind,points,radius,colors in (('building',building,building_radius,building_colour),('ground',ground,np.full(10000,.875),ground_colour)):
            for lod in ('near','far'):
                if lod=='near':p,rad,col=points,radius,colors
                elif kind=='building':p,rad,col=far_building,far_radius,far_colour
                else:
                    chosen=np.asarray([x*100+y for x in range(2,100,4) for y in range(2,100,4)])
                    p,rad,col=points[chosen],radius[chosen]*4,colors[chosen]
                if not len(p):continue
                for chunk,lo in enumerate(range(0,len(p),16000)):
                    name=f'SM_CityDense_C{cell:03}_{kind}_{lod}_{chunk}'
                    entries.append(write_stream_mesh(p[lo:lo+16000],rad[lo:lo+16000],col[lo:lo+16000],name,cell,kind,lod))
        receipt=dict(format_version=2,cell=cell,measured_splats=len(measured),procedural_facade_splats=len(facade),procedural_ground_splats=10000,
            facade_spacing_m=spacing,facade_radius_m=row['facade_radius_m'],meshes=entries)
        base.save(part,receipt)
        print('streamed cell',cell,'near',len(building)+10000,'facade spacing',round(spacing,3),flush=True)
        del r,xyz,tree,building,facade;gc.collect()
    receipts=[json.loads(p.read_text()) for p in sorted(STREAMED.glob('cell_*.json'))]
    entries=[e for row in receipts for e in row['meshes']]
    manifest=dict(plan,meshes=[e for e in entries if e['lod']=='near'],overview=[e for e in entries if e['lod']=='far'],
                  complete=len(receipts)==144,completed_cells=len(receipts),actual_near_splats=sum(e['splats'] for e in entries if e['lod']=='near'),
                  actual_far_splats=sum(e['splats'] for e in entries if e['lod']=='far'),source_mesh_bytes=sum(e['bytes'] for e in entries))
    base.save(STREAMED/'manifest.json',manifest)
    print('STREAMED MANIFEST',len(receipts),'cells',manifest['actual_near_splats'],'near',manifest['actual_far_splats'],'far',flush=True)


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='stream_audit':stream_plan()
    elif len(sys.argv)>1 and sys.argv[1]=='stream_build':stream_build(*map(int,sys.argv[2:]))
    else:main()

