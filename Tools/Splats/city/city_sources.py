"""Approved anonymous downloads and the installed standalone LASzip DLL, no editor calls.

COPC hierarchy selects compressed nodes over HTTP; a sparse-on-disk LAZ image lets
LASzip seek to those nodes using the original chunk table. Missing nodes are never read.
"""
import ctypes as ct
import json
import os
from pathlib import Path
import struct
import sys
import urllib.request

sys.dont_write_bytecode = True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import toronto_city as city
import numpy as np

DLL=Path('C:/Program Files/Epic Games/UE_5.8/Engine/Plugins/Enterprise/LidarPointCloud/Source/ThirdParty/LasZip/Win64/laszip.dll')
MASSING='https://opendata.toronto.ca/city.planning/3d-massing/2025/3DMassingShapefile_2025_WGS84.zip'


def download_massing():
    path=city.ROOT/'raw/massing/2025_20261110/3DMassingShapefile_2025_WGS84.zip'
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(MASSING,timeout=90) as src, path.with_suffix('.partial').open('wb') as dst:
            expected=int(src.headers['Content-Length'])
            total=0
            while data:=src.read(1024*1024):
                total+=len(data);dst.write(data)
            assert total==expected
        path.with_suffix('.partial').replace(path)
    city.save(path.parent/'source.json',{'url':MASSING,'bytes':path.stat().st_size,'licence':'OGL-Toronto 1.0'})
    print('massing downloaded',path.stat().st_size,flush=True)
    return path


def fetch_tile(north,c,east=6290,tag='20261110'):
    url=city.URL.format(north=north).replace('E6290_',f'E{east}_')
    folder=city.ROOT/f'raw/lidar/E{east}_N{north}_{tag}'
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/'corridor_ranges.copc.laz'
    manifest=folder/'ranges.json'
    if manifest.exists():
        return path,json.loads(manifest.read_text())
    ranges=[]
    def get(offset,size):
        req=urllib.request.Request(url,headers={'Range':f'bytes={offset}-{offset+size-1}'})
        with urllib.request.urlopen(req,timeout=90) as response:
            if response.status!=206:
                raise ValueError('Server did not honour byte range')
            result=response.read(size+1)
            assert len(result)==size,(offset,size,len(result))
            total=int(response.headers['Content-Range'].split('/')[-1])
        ranges.append([int(offset),int(size)])
        return result,total
    header,total=get(0,375)
    assert header[:4]==b'LASF' and header[104]&63==6
    point_offset=struct.unpack_from('<I',header,96)[0]
    head,_=get(0,point_offset+8)
    pos=struct.unpack_from('<H',header,94)[0]
    info=None;wkt=None
    while pos<point_offset:
        userid=head[pos+2:pos+18].rstrip(b'\0');rid,size=struct.unpack_from('<HH',head,pos+18)
        body=head[pos+54:pos+54+size]
        if userid==b'copc' and rid==1:info=body
        if userid==b'LASF_Projection' and rid==2112:wkt=body.rstrip(b'\0').decode('utf-8')
        pos+=54+size
    assert info is not None,'COPC info VLR missing'
    centre=np.array(struct.unpack_from('<3d',info));half=struct.unpack_from('<d',info,24)[0]
    root_offset,root_size=struct.unpack_from('<QQ',info,40)
    nodes=[]; pages=[]
    def walk(offset,size):
        data,_=get(offset,size);pages.append((offset,data))
        assert len(data)%32==0
        for level,x,y,z,off,length,count in struct.iter_unpack('<iiiiQii',data):
            if count==-1:walk(off,length)
            elif count>0:nodes.append({'level':level,'key':[x,y,z],'offset':off,'bytes':length,'count':count})
    walk(root_offset,root_size)
    nodes.sort(key=lambda n:n['offset'])
    corners=np.array(c['corners_utm_m']);lo,hi=corners.min(0),corners.max(0)
    index=0;selected=[]
    for node in nodes:
        width=2*half/2**node['level']
        nlo=centre-half+np.array(node['key'])*width;nhi=nlo+width
        node['start_point']=index;index+=node['count']
        if np.all(nhi[:2]>=lo) and np.all(nlo[:2]<=hi):
            node['bounds']=[nlo.tolist(),nhi.tolist()]
            selected.append(node)
    point_count=struct.unpack_from('<Q',header,247)[0]
    assert index==point_count,(index,point_count)
    table_offset=struct.unpack_from('<Q',head,point_offset)[0]
    # Chunk table and EVLR tail are small; cap allocation before accepting the source.
    assert 0<table_offset<total and total-table_offset<32*1024*1024
    tail,_=get(table_offset,total-table_offset)
    with path.with_suffix('.partial').open('w+b') as f:
        # Mark the range image sparse so unfetched bytes do not consume allocated disk.
        import msvcrt
        returned=ct.c_ulong()
        ct.windll.kernel32.DeviceIoControl(ct.c_void_p(msvcrt.get_osfhandle(f.fileno())),0x900c4,None,0,None,0,ct.byref(returned),None)
        f.truncate(total);f.seek(0);f.write(head)
        f.seek(table_offset);f.write(tail)
        for offset,data in pages:f.seek(offset);f.write(data)
        for i,node in enumerate(selected):
            data,_=get(node['offset'],node['bytes'])
            f.seek(node['offset']);f.write(data)
            if i%25==0:print(f'N{north}: {i+1}/{len(selected)} COPC nodes, {sum(r[1] for r in ranges)/1e6:.1f} MB transferred',flush=True)
    path.with_suffix('.partial').replace(path)
    meta={'url':url,'source_bytes':total,'source_points':point_count,'selected_nodes':selected,
          'all_node_count':len(nodes),'selected_node_points':sum(n['count'] for n in selected),
          'http_ranges':ranges,'transferred_bytes':sum(r[1] for r in ranges),
          'scales':list(struct.unpack_from('<3d',header,131)),'offsets':list(struct.unpack_from('<3d',header,155)),
          'source_wkt':wkt,'warning':'INCOMPLETE sparse range image: only nodes listed in selected_nodes may be read. Not a full LAZ tile.',
          'decoder':str(DLL),'memory':city.memory()}
    city.save(manifest,meta)
    return path,meta


class NativePoint(ct.Structure):
    _fields_=[('x',ct.c_int32),('y',ct.c_int32),('z',ct.c_int32),('intensity',ct.c_uint16),
              ('returns',ct.c_uint8),('classification',ct.c_uint8),('scan_angle_rank',ct.c_int8),
              ('user_data',ct.c_uint8),('source_id',ct.c_uint16),('extended_scan_angle',ct.c_int16),
              ('extended_flags',ct.c_uint8),('extended_classification',ct.c_uint8),
              ('extended_returns',ct.c_uint8),('dummy',ct.c_uint8*7),('gps_time',ct.c_double)]


def read_nodes(path,meta):
    dll=ct.CDLL(str(DLL))
    handle=ct.c_void_p();point=ct.POINTER(NativePoint)();compressed=ct.c_int32()
    def check(result):
        if result:
            error=ct.c_char_p();dll.laszip_get_error(handle,ct.byref(error))
            raise RuntimeError(error.value.decode(errors='replace'))
    check(dll.laszip_create(ct.byref(handle)))
    try:
        check(dll.laszip_open_reader(handle,str(path).encode(),ct.byref(compressed)))
        check(dll.laszip_get_point_pointer(handle,ct.byref(point)))
        assert NativePoint.extended_classification.offset==23 and NativePoint.gps_time.offset==32
        read=dll.laszip_read_point
        p=point.contents
        for ni,node in enumerate(meta['selected_nodes']):
            check(dll.laszip_seek_point(handle,ct.c_int64(node['start_point'])))
            for start in range(0,node['count'],100000):
                count=min(100000,node['count']-start)
                raw=np.empty((count,6),np.int32)
                for i in range(count):
                    check(read(handle))
                    raw[i]=(p.x,p.y,p.z,p.intensity,p.extended_classification,(p.extended_flags>>4)&4)
                xyz=raw[:,:3].astype(np.float64)*meta['scales']+meta['offsets']
                if 'bounds' in node:
                    assert np.all(xyz>=np.array(node['bounds'][0])-.02) and np.all(xyz<=np.array(node['bounds'][1])+.02), 'COPC seek decoded wrong node'
                yield xyz,raw[:,3],raw[:,4],raw[:,5].astype(bool)
            if ni%25==0:print(f'decoded {ni+1}/{len(meta["selected_nodes"])} nodes',flush=True)
        check(dll.laszip_close_reader(handle))
    finally:
        dll.laszip_destroy(handle)


def run():
    import collections
    c=city.corridor();archive=download_massing()
    polys,ids=city.footprints(archive,c);tree=city.shapely.STRtree(polys)
    before,after=collections.Counter(),collections.Counter()
    stats={'tiles':[],'dropped_noise':0,'dropped_below_minus60':0,'withheld':0,
           'building_assigned':0,'building_unassigned':0,'polygons':len(polys),
           'method':'COPC range-selected nodes, standalone installed LASzip, 100000-point chunks',
           'point_dtype':city.POINT.descr}
    output=city.OUT/'crop_points.bin'
    with output.with_suffix('.partial').open('wb') as f:
        for north in [48330,48340]:
            path,meta=fetch_tile(north,c)
            tile={'source_points':meta['source_points'],'decoded_points':0,'corridor_points':0,'ranges_file':str(path.parent/'ranges.json')}
            for xyz,intensity,cls,withheld in read_nodes(path,meta):
                tile['decoded_points']+=len(xyz)
                u,v=city.local_xy(xyz[:,0],xyz[:,1],c)
                mask=(u>=0)&(u<600)&(v>=-300)&(v<300)
                tile['corridor_points']+=int(mask.sum())
                before.update(dict(zip(*[a.tolist() for a in np.unique(cls[mask],return_counts=True)])))
                stats['dropped_noise']+=int((mask&np.isin(cls,[7,18])).sum())
                stats['dropped_below_minus60']+=int((mask&(xyz[:,2]<-60)).sum())
                stats['withheld']+=int((mask&withheld).sum())
                mask &= ~np.isin(cls,[7,18])&(xyz[:,2]>=-60)&~withheld
                after.update(dict(zip(*[a.tolist() for a in np.unique(cls[mask],return_counts=True)])))
                arr=np.zeros(int(mask.sum()),city.POINT)
                for key,data in [('u',u),('v',v),('z',xyz[:,2]),('intensity',intensity),('cls',cls)]:arr[key]=data[mask]
                building=arr['cls']==6
                arr['bid'][building]=city.assign(xyz[mask,0][building],xyz[mask,1][building],polys,ids,tree)
                stats['building_assigned']+=int((arr['bid']>0).sum())
                stats['building_unassigned']+=int((building&(arr['bid']==0)).sum())
                arr.tofile(f);city.memory()
            stats['tiles'].append(tile)
    output.with_suffix('.partial').replace(output)
    stats['classes_before_filter']={str(k):v for k,v in sorted(before.items())}
    stats['classes_retained']={str(k):v for k,v in sorted(after.items())}
    stats['retained_points']=sum(after.values());stats['memory']=city.memory()
    city.save(city.OUT/'crop_stats.json',stats)
    print(json.dumps(stats),flush=True)


def selftest():
    """Check native ABI and first/last points of every downloaded COPC node."""
    assert NativePoint.intensity.offset==12 and NativePoint.extended_flags.offset==22
    result=[]
    for folder in sorted((city.ROOT/'raw/lidar').glob('E*_20261110')):
        path=folder/'corridor_ranges.copc.laz'
        if not (folder/'ranges.json').exists():continue
        meta=json.loads((folder/'ranges.json').read_text())
        with path.open('rb') as f:header=f.read(1000)
        # COPC mandates the info record as the first VLR after the LAS 1.4 header.
        assert header[377:393].rstrip(b'\0')==b'copc'
        centre=np.array(struct.unpack_from('<3d',header,429));half=struct.unpack_from('<d',header,453)[0]
        sample=dict(meta);sample['selected_nodes']=[]
        for node in meta['selected_nodes']:
            width=2*half/2**node['level'];lo=centre-half+np.array(node['key'])*width
            bounds=[lo.tolist(),(lo+width).tolist()]
            for point_index in [node['start_point'],node['start_point']+node['count']-1]:
                sample['selected_nodes'].append(dict(node,start_point=point_index,count=1,bounds=bounds))
        read_count=sum(len(xyz) for xyz,*_ in read_nodes(path,sample))
        assert read_count==2*len(meta['selected_nodes'])
        result.append({'tile':folder.name,'nodes_checked':len(meta['selected_nodes']),'boundary_points_checked':read_count})
    assert len(result)==2,'Both downloaded tiles must be checked'
    city.save(city.OUT/'source_verification.json',{'checks':result,'memory':city.memory()})
    print('native source selftest OK',result,city.memory())


if __name__=='__main__':
    selftest() if '--selftest' in sys.argv else run()
