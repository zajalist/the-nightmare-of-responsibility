"""Offline city streaming plan and native graphs for the existing sector actor.

No editor access on import. The active city path stays unchanged until every
new map/mesh has been imported, validated and visually checked by the coordinator.
"""
from collections import defaultdict
import json
from math import hypot
from pathlib import Path
import build_drive as b

BP='/Game/FoA/Level2/City/Expanded/BP_City2Sector'
MASTER='/Game/FoA/Level2/Maps/L_L2_CityStream'
MAP_ROOT='/Game/FoA/Level2/Maps/CityDense'
ASSET_ROOT='/Game/FoA/Level2/City/Dense/Meshes'
SOURCE=Path('P:/FoA-Assets/level2/toronto/processed/queen_600m_streamed')
CELL_CM=5000.;SIDE=12
LOAD_CM=9000.;UNLOAD_CM=11500.;TICK_SECONDS=.25
POLL_MOVEMENT_GUARD_CM=2000*TICK_SECONDS
ENTRY=(9000.,-250.,0.)
GPU_BYTES_PER_SPLAT=192
GPU_GEOMETRY_CEILING=360*1024*1024
MASTER_ACTORS_PER_PASS=64


def cell_centre(x,y):return ((x+.5)*CELL_CM,-30000+(y+.5)*CELL_CM,0.)
def package(x,y):return f'{MAP_ROOT}/L_CityDense_S{x}_{y}'
def box_distance(camera,centre):
    return hypot(max(0,abs(camera[0]-centre[0])-CELL_CM/2),max(0,abs(camera[1]-centre[1])-CELL_CM/2))
def wanted(distance,was_loaded):return distance<(UNLOAD_CM if was_loaded else LOAD_CM)


def plan(manifest):
    groups=defaultdict(list)
    near=[m for m in manifest['meshes'] if m.get('lod','near')=='near']
    far=list(manifest.get('overview',[]))+[m for m in manifest['meshes'] if m.get('lod')=='far']
    assert len({m['name'] for m in near+far})==len(near+far),'Duplicate mesh names'
    for row in near:
        xy=tuple(row.get('cell_xy',divmod(int(row['cell']),SIDE)))
        assert len(xy)==2 and all(0<=n<SIDE for n in xy),xy
        assert tuple(row['sector'])==xy,'Manifest must use one50m cell per sector'
        groups[xy].append(row)
    assert len(groups)==SIDE*SIDE,('Every city cell needs near coverage',len(groups))
    assert far,'Coarse splats are required while near sectors load'
    sectors=[dict(cell=[x,y],centre=cell_centre(x,y),package=package(x,y),meshes=groups[x,y],
                  splats=sum(m['splats'] for m in groups[x,y])) for x,y in sorted(groups)]
    far_points=sum(m['splats'] for m in far)
    import numpy as np
    peaks={};xs=np.arange(0,60001,100);ys=np.arange(-30000,30001,100)
    # Inflate by the maximum distance to the nearest1m sample. AABB distance is
    # 1-Lipschitz, so this bounds every continuous camera position, not just samples.
    allowance=100/2**.5
    for name,radius in (('load',LOAD_CM),('retained',UNLOAD_CM)):
        points=np.zeros((len(xs),len(ys)),np.int64);counts=np.zeros_like(points)
        for sector in sectors:
            cx,cy,_=sector['centre']
            dx=np.maximum(abs(xs-cx)-CELL_CM/2,0)[:,None]
            dy=np.maximum(abs(ys-cy)-CELL_CM/2,0)[None,:]
            eligible=dx*dx+dy*dy<(radius+allowance+POLL_MOVEMENT_GUARD_CM)**2
            points+=eligible*sector['splats'];counts+=eligible
        ix,iy=np.unravel_index(points.argmax(),points.shape)
        peaks[name]=dict(points=int(points[ix,iy]),sectors=int(counts[ix,iy]),camera=[int(xs[ix]),int(ys[iy])])
    estimate=(peaks['retained']['points']+far_points)*GPU_BYTES_PER_SPLAT
    assert estimate<=GPU_GEOMETRY_CEILING,('Geometry residency budget exceeded',estimate,peaks)
    return dict(master=MASTER,sectors=sectors,overview=far,load_cm=LOAD_CM,unload_cm=UNLOAD_CM,
                tick_seconds=TICK_SECONDS,peaks=peaks,far_splats=far_points,
                estimated_peak_wanted_gpu_geometry_bytes=estimate,
                budget_guard_cm=allowance+POLL_MOVEMENT_GUARD_CM,
                estimate_scope='Wanted geometry only,192 bytes/point vertex/index allowance. Pending unload/GC resources, process RAM and packaged size require native measurement.')


def write_plan():
    manifest=json.loads((SOURCE/'manifest.json').read_text())
    assert manifest.get('complete') is True and manifest.get('completed_cells')==SIDE*SIDE,'Wait for the complete dense export'
    result=plan(manifest)
    out=Path('P:/FoA/Saved/Integration/city_streaming');out.mkdir(parents=True,exist_ok=True)
    (out/'plan.json').write_text(json.dumps(result,indent=2))
    return result


def setup():
    info=b.call('blueprint_get_info',path=BP)
    have={v['name'] for v in info['variables']}
    b.call('blueprint_add_variable',path=BP,variable_name='SectorPackage',variable_type='string',
           instance_editable=True,update_existing=True,category='City streaming')
    for name,typ,value in [('LoadRadius','real',str(LOAD_CM)),('UnloadRadius','real',str(UNLOAD_CM)),
        ('SectorHalfExtent','vector','2500,2500,0'),('DesiredLoaded','bool','false'),('Ready','bool','false'),
        ('BootstrapPending','bool','false'),('BootstrapPoint','vector','9000,-250,0')]:
        if name not in have:b.call('blueprint_add_variable',path=BP,variable_name=name,variable_type=typ,
                                  default_value=value,instance_editable=True,category='City streaming')
    for name in ('UpdateSector','ReleaseSector'):
        if name not in info['functions']:b.call('blueprint_add_function',path=BP,function_name=name)


def update():
    g=b.G(BP,'UpdateSector')
    camera=g.f('/Script/Engine.PlayerCameraManager:GetCameraLocation',self=g.f(b.GS+'GetPlayerCameraManager',PlayerIndex=0))
    arrived=g.math('Less_DoubleDouble',A=g.math('Vector_Distance2D',V1=camera,V2=g.getv('BootstrapPoint')),B=2000)
    g.setv('BootstrapPending',g.math('BooleanAND',A=g.getv('BootstrapPending'),B=g.math('Not_PreBool',A=arrived)))
    focus=g.math('SelectVector',A=g.getv('BootstrapPoint'),B=camera,bPickA=g.getv('BootstrapPending'))
    delta=g.math('Subtract_VectorVector',A=focus,B=g.f(b.A+'K2_GetActorLocation'))
    xy=g.math('BreakVector',InVec=delta);extent=g.math('BreakVector',InVec=g.getv('SectorHalfExtent'))
    distances=[g.math('FMax',A=0,B=g.math('Subtract_DoubleDouble',A=g.math('Abs',A=(xy[0],axis)),B=(extent[0],axis))) for axis in ('X','Y')]
    distance=g.math('VSize',A=g.math('MakeVector',X=distances[0],Y=distances[1],Z=0))
    limit=g.math('SelectFloat',A=g.getv('UnloadRadius'),B=g.getv('LoadRadius'),bPickA=g.getv('DesiredLoaded'))
    g.setv('DesiredLoaded',g.math('Less_DoubleDouble',A=distance,B=limit))
    stream=g.getv('Stream');valid=g.branch(g.f(b.SL+'IsValid',Object=stream));g.side(valid)
    g.do('/Script/Engine.LevelStreaming:SetShouldBeVisible',self=stream,bInShouldBeVisible=g.getv('DesiredLoaded'))
    g.do('/Script/Engine.LevelStreaming:SetShouldBeLoaded',self=stream,bInShouldBeLoaded=g.getv('DesiredLoaded'))
    g.setv('Ready',g.math('BooleanOR',A=g.math('Not_PreBool',A=g.getv('DesiredLoaded')),
                        B=g.f('/Script/Engine.LevelStreaming:IsLevelVisible',self=stream)))
    unloaded=g.math('BooleanAND',A=g.math('Not_PreBool',A=g.getv('DesiredLoaded')),
                    B=g.math('Not_PreBool',A=g.f('/Script/Engine.LevelStreaming:IsLevelLoaded',self=stream)))
    forget=g.branch(unloaded);g.side(forget)
    g.do('/Script/Engine.LevelStreaming:SetIsRequestingUnloadAndRemoval',self=stream,bInIsRequestingUnloadAndRemoval=True)
    g.setv('Stream','')
    g.side(valid,False)
    g.setv('Ready',g.math('Not_PreBool',A=g.getv('DesiredLoaded')))
    needed=g.branch(g.getv('DesiredLoaded'));g.side(needed)
    loaded=g.do('/Script/Engine.LevelStreamingDynamic:LoadLevelInstance',LevelName=g.getv('SectorPackage'),Location='0,0,0',Rotation='0,0,0')
    g.setv('Stream',loaded);g.finish()


def release():
    g=b.G(BP,'ReleaseSector');g.do(b.A+'SetActorTickEnabled',bEnabled=False)
    g.setv('Ready',False);g.setv('DesiredLoaded',False)
    stream=g.getv('Stream');valid=g.branch(g.f(b.SL+'IsValid',Object=stream));g.side(valid)
    g.do('/Script/Engine.LevelStreaming:SetShouldBeVisible',self=stream,bInShouldBeVisible=False)
    g.do('/Script/Engine.LevelStreaming:SetShouldBeLoaded',self=stream,bInShouldBeLoaded=False)
    g.do('/Script/Engine.LevelStreaming:SetIsRequestingUnloadAndRemoval',self=stream,bInIsRequestingUnloadAndRemoval=True)
    g.setv('Stream','')
    g.finish()


def events():
    nodes,_=b.inspect(BP,'EventGraph');batch=b.Batch(BP,'EventGraph')
    intervals=[n for n in nodes if n.get('title','').replace(' ','').split('\n')[0]=='SetActorTickInterval']
    assert len(intervals)==1,'Expected existing sector BeginPlay interval'
    batch.pin(intervals[0]['node_id'],'TickInterval',str(TICK_SECONDS))
    if not any(n.get('title','').replace(' ','').split('\n')[0]=='ReleaseSector' for n in nodes):
        assert not any('EndPlay' in n.get('title','').replace(' ','') for n in nodes),'Inspect existing EndPlay before editing'
        batch.ops.append(dict(op='add_event',ref='sector_end',event_name='ReceiveEndPlay',x=0,y=800))
        batch.fn('sector_release',b.cls(BP)+':ReleaseSector',400,800);batch.chain('sector_end','sector_release')
        batch.comment('Release streamed geometry',['sector_end','sector_release'])
    batch.run()


def threshold_ready():
    import build_threshold as t
    g=b.G(t.BP,'CheckCitySectors')
    actors=g.do(b.GS+'GetAllActorsOfClass',ActorClass=b.cls(BP));array=(actors[0],'OutActors')
    g.setv('CitySectorCount',0);g.setv('CityReady',True)
    loop=g.ref();g.node(loop,'macro',0,0,macro_name='ForEachLoop');g.put(loop,'Array',array)
    g.link(g.tail,'then',loop,'Exec');g.tail=loop;g._side='LoopBody'
    sector=g.cast((loop,'Array Element'),b.cls(BP),'BP City 2Sector')
    # Land also runs after a road retry. Re-arm entry prefetch here before
    # reading Ready; otherwise previously unloaded, unwanted sectors all report
    # Ready while the camera is back in the dream. Only Land calls this helper,
    # so ordinary driving continues to track the camera without re-arming.
    prewarm=g.ref();g.set(prewarm,'BootstrapPending',0,0,b.cls(BP))
    g.put(prewarm,'self',sector);g.put(prewarm,'BootstrapPending',True)
    g.chain(g.tail,prewarm);g.tail=prewarm
    g.do(b.cls(BP)+':UpdateSector',self=sector)
    g.setv('CitySectorCount',g.math('Add_IntInt',A=g.getv('CitySectorCount'),B=1))
    g.setv('CityReady',g.math('BooleanAND',A=g.getv('CityReady'),B=g.getv('Ready',sector,BP)))
    g.tail=loop;g._side='Completed'
    complete=g.math('EqualEqual_IntInt',A=g.getv('CitySectorCount'),B=SIDE*SIDE)
    g.setv('CityReady',g.math('BooleanAND',A=g.getv('CityReady'),B=complete))
    g.finish()


if __name__=='__main__':
    result=write_plan()
    print(json.dumps({k:v for k,v in result.items() if k not in ('sectors','overview')},indent=2))
