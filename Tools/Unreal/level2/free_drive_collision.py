"""One solid dark city backing/collision mesh from the licensed building footprints.

Offline only. Metres here, same surveyed frame as the rendered city. No downloads.
"""
import json
from pathlib import Path
from car_visual import Mesh,document
from drive_data import SOURCE

OUT=Path('P:/FoA-Assets/level2/toronto/processed/free_drive_collision')


def local(point,frame):
    delta=[point[i]-frame['origin_utm_m'][i] for i in range(2)]
    return (sum(delta[i]*frame['along_utm'][i] for i in range(2)),
            -sum(delta[i]*frame['left_utm'][i] for i in range(2)))


def build():
    frame=json.loads(Path(SOURCE,'corridor.json').read_text())
    records=json.loads(Path(SOURCE,'buildings.json').read_text())['records']
    mesh=Mesh();segments=0
    for record in records:
        geometry=json.loads(record['geometry'])
        assert geometry['type'] in ('Polygon','MultiPolygon')
        polygons=geometry['coordinates'] if geometry['type']=='MultiPolygon' else [geometry['coordinates']]
        height=max(4.,float(record['attributes'].get('AVG_HEIGHT') or 4))
        for polygon in polygons:
            for ring in polygon:
                assert ring[0]==ring[-1],'Footprint ring must be closed'
                for a,b in zip(ring,ring[1:]):
                    x,y=local(a,frame);u,v=local(b,frame)
                    if (x-u)**2+(y-v)**2<1e-10:continue
                    wall=[(x,y,-1.63),(u,v,-1.63),(u,v,height),(x,y,height)]
                    mesh.face(wall);mesh.face(reversed(wall))
                    segments+=1
    # Boundaries coincide with the available city, beyond the streets' usable space.
    length,width=frame['length_m'],frame['width_m']
    for centre,size in [((0,0,3),(1,width,8)),((length,0,3),(1,width,8)),
                        ((length/2,-width/2,3),(length,1,8)),((length/2,width/2,3),(length,1,8))]:
        mesh.box(centre,size,1)
    assert segments>6000 and all(len(p['positions'])<65536 for p in mesh.parts)
    doc=document(mesh)
    doc['asset']['generator']='FoA city footprint collision'
    doc['nodes'][0]['name']=doc['meshes'][0]['name']='SM_L2CityCollision'
    doc['extras']={'source':'City of Toronto 3D Massing 2025, existing approved source',
                   'building_count':len(records),'wall_segments':segments,'frame':frame}
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/'SM_L2CityCollision.gltf';path.write_text(json.dumps(doc,separators=(',',':')))
    (OUT/'SOURCES.txt').write_text('Derived from the existing City of Toronto 3D Massing 2025 building footprints.\nSource and approved licence: ../queen_600m/buildings.json and project Level 2 source manifest.\nDark solid backing and collision; original surveyed frame retained.\n')
    print(path,dict(buildings=len(records),walls=segments,triangles=sum(len(p['indices'])//3 for p in mesh.parts)))
    return path


if __name__=='__main__':
    frame=json.loads(Path(SOURCE,'corridor.json').read_text())
    assert local(frame['origin_utm_m'],frame)==(0,0)
    p=[frame['origin_utm_m'][i]+10*frame['along_utm'][i] for i in range(2)]
    x,y=local(p,frame);assert abs(x-10)<1e-6 and abs(y)<1e-6
    build()
