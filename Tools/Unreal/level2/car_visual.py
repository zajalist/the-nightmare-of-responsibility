"""Offline original sedan mesh, following drive_visuals.py's embedded glTF pattern.

One mesh, two legacy slot names: 0=M_L2Flat, 1=MI_L2Dark. No textures.
car_visual_setup assigns the shared lit master's paint and trim instances.
Authoring coordinates: metres, +X front, Z up; glTF stores (X,Z,-Y).
Integration (separately authorized): import SM_L2Sedan.gltf, put on Car.Body at
location/rotation zero, scale one, NoCollision; clear/hide the old Roof cube.
Wheel contact Z=0, footprint about4.47m x2.04m including mirrors, height1.47m.
This is an original procedural visual, no third-party asset/licence dependency.
"""
import base64
import json
import math
from pathlib import Path
import struct

MATERIALS=('/Game/FoA/Level2/Drive/M_L2Flat','/Game/FoA/Level2/Drive/MI_L2Dark')


def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def gltf(v):return (v[0],v[2],-v[1])


class Mesh:
    def __init__(self):
        self.parts=[dict(positions=[],normals=[],indices=[]) for _ in MATERIALS]
        self.features={}

    def face(self,points,material=0,outward=None):
        points=list(points)
        n=cross(sub(points[1],points[0]),sub(points[2],points[0]))
        if outward and dot(n,outward)<0:
            points.reverse();n=tuple(-x for x in n)
        length=math.sqrt(dot(n,n));assert length>1e-9
        n=gltf(tuple(x/length for x in n));part=self.parts[material]
        start=len(part['positions'])
        part['positions'].extend(gltf(p) for p in points)
        part['normals'].extend([n]*len(points))
        for i in range(1,len(points)-1):part['indices'].extend((start,start+i,start+i+1))

    def box(self,center,size,material=0):
        x,y,z=center;a,b,c=(v/2 for v in size)
        for axis in range(3):
            other=[i for i in range(3) if i!=axis]
            for sign in (-1,1):
                points=[]
                for u,v in ((-1,-1),(1,-1),(1,1),(-1,1)):
                    p=[x,y,z];p[axis]+=sign*(a,b,c)[axis]
                    p[other[0]]+=u*(a,b,c)[other[0]];p[other[1]]+=v*(a,b,c)[other[1]]
                    points.append(p)
                normal=[0,0,0];normal[axis]=sign;self.face(points,material,normal)

    def window(self,corners,u0=.07,u1=.93,v0=.09,v1=.89,outward=(0,0,1)):
        # Bilinear inset keeps glass clear of pillars and roof, without new geometry assets.
        def at(u,v):
            return tuple((1-v)*((1-u)*corners[0][i]+u*corners[1][i])+
                         v*((1-u)*corners[3][i]+u*corners[2][i])+.006*outward[i] for i in range(3))
        self.face([at(u,v) for u,v in ((u0,v0),(u1,v0),(u1,v1),(u0,v1))],1,outward)

    def wheel(self,x,side):
        self.features.setdefault('wheel_centres',[]).append((x,.84*side,.32))
        # Tire with bevelled sidewalls; circumference visible from the overhead camera.
        segments=20
        rings=[(.74,.26),(.77,.32),(.92,.32),(.95,.26)]
        for (y0,r0),(y1,r1) in zip(rings,rings[1:]):
            for i in range(segments):
                a,b=(math.tau*j/segments for j in (i,i+1))
                pts=[(x+r0*math.cos(a),side*y0,.32+r0*math.sin(a)),
                     (x+r0*math.cos(b),side*y0,.32+r0*math.sin(b)),
                     (x+r1*math.cos(b),side*y1,.32+r1*math.sin(b)),
                     (x+r1*math.cos(a),side*y1,.32+r1*math.sin(a))]
                self.face(pts,1,(math.cos((a+b)/2),0,math.sin((a+b)/2)))
        for radius,y,mat in ((.26,.95,1),(.16,.953,0),(.065,.956,1)):
            self.face([(x+radius*math.cos(math.tau*i/segments),side*y,.32+radius*math.sin(math.tau*i/segments))
                       for i in range(segments)],mat,(0,side,0))


def sedan():
    m=Mesh()
    sections=[(-2.20,.72,.68),(-2.03,.87,.88),(-1.35,.89,.96),
              (.85,.88,.96),(1.87,.83,.83),(2.20,.72,.69)]
    rings=[]
    for x,w,top in sections:
        rings.append([(x,y,z) for y,z in ((-.8*w,.25),(.8*w,.25),(w,.37),(w,top-.10),
                                        (.8*w,top),(-.8*w,top),(-w,top-.10),(-w,.37))])
    m.face(rings[0],0,(-1,0,0));m.face(rings[-1],0,(1,0,0))
    for a,b in zip(rings,rings[1:]):
        for i in range(8):
            j=(i+1)%8;pts=[a[i],b[i],b[j],a[j]]
            radial=(0,sum(p[1] for p in pts)/4,sum(p[2] for p in pts)/4-.60)
            m.face(pts,0,radial)
    # Three-box sedan: short rear deck, raked greenhouse, longer bonnet.
    rear=[(-1.25,-.78,.965),(-1.25,.78,.965),(-.80,.67,1.47),(-.80,-.67,1.47)]
    front=[(.85,.78,.965),(.85,-.78,.965),(.30,-.67,1.47),(.30,.67,1.47)]
    m.face(rear,0,(-1,0,0));m.window(rear,outward=(-1,0,0))
    m.face(front,0,(1,0,0));m.window(front,outward=(1,0,0))
    m.face([rear[3],rear[2],front[3],front[2]],0,(0,0,1))
    for side in (-1,1):
        corners=[(-1.25,side*.78,.965),(.85,side*.78,.965),(.30,side*.67,1.47),(-.80,side*.67,1.47)]
        m.face(corners,0,(0,side,0))
        for u0,u1 in ((.06,.46),(.51,.94)):m.window(corners,u0,u1,outward=(0,side,0))
        for x in (-1.38,1.34):m.wheel(x,side)
        m.box((.57,side*.925,1.02),(.24,.17,.12))
        m.box((.58,side*1.012,1.02),(.15,.012,.075),1)
        # Fine rub strip and handles; bright body remains legible over black asphalt.
        m.box((-.04,side*.888,.66),(2.9,.012,.025),1)
        for x in (-.87,.18):m.box((x,side*.794,.91),(.16,.02,.025),1)
    for x in (-2.22,2.22):m.box((x,0,.43),(.04,1.43,.09),1)
    m.box((2.204,0,.61),(.02,1.2,.14),1)
    for side in (-1,1):
        m.box((2.22,side*.48,.64),(.035,.27,.11),0)
        m.box((1.99,side*.62,.81),(.27,.23,.015),0)
        m.box((-2.204,side*.48,.62),(.025,.30,.12),1)
        m.box((-2.222,side*.48,.65),(.012,.23,.025),0)
    m.box((-2.226,0,.56),(.012,.29,.10),0)
    m.features.update(windows=6,headlights=2,material_paths=MATERIALS)
    return m


def document(mesh):
    blob=bytearray();views=[];accessors=[];primitives=[]
    def add(values,kind,component,fmt,target):
        while len(blob)%4:blob.append(0)
        offset=len(blob);flat=[n for row in values for n in row] if kind=='VEC3' else values
        packed=struct.pack('<'+fmt*len(flat),*flat);blob.extend(packed)
        views.append(dict(buffer=0,byteOffset=offset,byteLength=len(packed),target=target))
        accessor=dict(bufferView=len(views)-1,componentType=component,count=len(values),type=kind)
        if kind=='VEC3':
            accessor.update(min=[min(row[i] for row in values) for i in range(3)],max=[max(row[i] for row in values) for i in range(3)])
        accessors.append(accessor);return len(accessors)-1
    for slot,part in enumerate(mesh.parts):
        position=add(part['positions'],'VEC3',5126,'f',34962)
        normal=add(part['normals'],'VEC3',5126,'f',34962)
        indices=add(part['indices'],'SCALAR',5123,'H',34963)
        primitives.append(dict(attributes={'POSITION':position,'NORMAL':normal},indices=indices,material=slot))
    return dict(asset={'version':'2.0','generator':'FoA original procedural sedan'},scene=0,scenes=[{'nodes':[0]}],
        nodes=[{'mesh':0,'name':'SM_L2Sedan'}],meshes=[{'name':'SM_L2Sedan','primitives':primitives}],
        materials=[{'name':path.rsplit('/',1)[1],'pbrMetallicRoughness':{'baseColorFactor':[c,c,c,1],'metallicFactor':0,'roughnessFactor':.65},
                    'extras':{'unreal_material':path}} for path,c in zip(MATERIALS,(.9,.009))],
        buffers=[{'byteLength':len(blob),'uri':'data:application/octet-stream;base64,'+base64.b64encode(blob).decode()}],
        bufferViews=views,accessors=accessors,extras=mesh.features)


def generate(output=None):
    mesh=sedan();doc=document(mesh)
    output=Path(output or 'P:/FoA/Saved/Codex/l2_drive/generated/SM_L2Sedan.gltf')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(doc,separators=(',',':')),encoding='utf-8')
    print(output,dict(vertices=sum(len(p['positions']) for p in mesh.parts),
                      triangles=sum(len(p['indices'])//3 for p in mesh.parts),bytes=output.stat().st_size))
    return output


if __name__=='__main__':generate()
