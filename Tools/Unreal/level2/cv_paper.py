"""Offline A4 CV for the existing ItemInspect turntable. No editor calls.

python Tools/Unreal/level2/cv_paper.py
UE axes: printed front faces -X, width Y, height Z; 21 x29.7cm.
Content matches build_journey.confirm Phase2; intentionally blank later sections.
Font: existing Darker Grotesque (SIL OFL, P:/FoA-Assets/fonts/DarkerGrotesque/OFL.txt).
"""
import base64
import json
from pathlib import Path
import struct

from PIL import Image, ImageDraw, ImageFont
import numpy as np

OUT=Path('P:/FoA/Saved/Codex/l2_cv_paper/generated')
ASSET='/Game/FoA/Level2/Journey/Paper/SM_L2CVPaper'
FONT=Path('P:/FoA-Assets/fonts/DarkerGrotesque')
TEXT=('Curriculum vitae','Experience','I have no job experience.','Skills','Availability')


def texture():
    # Warm neutral paper stays within the locked monochrome art direction.
    rng=np.random.default_rng(18)
    values=np.clip(230+rng.normal(0,.65,(2172,1536)),227,233).astype('uint8')
    image=Image.fromarray(values).convert('RGB');draw=ImageDraw.Draw(image)
    rows=((TEXT[0],150,155,'ExtraBold'),(TEXT[1],530,112,'SemiBold'),
          (TEXT[2],680,104,'Medium'),(TEXT[3],1060,112,'SemiBold'),
          (TEXT[4],1570,112,'SemiBold'))
    for line,y,size,weight in rows:
        font=ImageFont.truetype(str(FONT/f'DarkerGrotesque-{weight}.ttf'),size)
        assert draw.textbbox((160,y),line,font=font)[2]<1376,(line,'overflow')
        draw.text((160,y),line,font=font,fill=(27,27,27))
    return image


def geometry():
    """Smooth curved faces and a closed 0.12mm edge, separate printed/back slots."""
    parts=[dict(p=[],n=[],uv=[],i=[]) for _ in range(2)]
    def point(u,v,side):
        # Metres; faint bow and upper-right corner lift, not a crumpled prop.
        x=.00025*(2*u-1)**2+.0012*u**6*v**8+side*.00006
        return (x,.21*(u-.5),.297*(v-.5))
    def face(coords,slot,outward):
        p=parts[slot];positions=[point(*c) for c in coords]
        a,b,c=positions[:3]
        ab=[b[k]-a[k] for k in range(3)];ac=[c[k]-a[k] for k in range(3)]
        n=np.cross(ab,ac);n=n/np.linalg.norm(n)
        if np.dot(n,outward)<0:
            coords=list(reversed(coords));positions.reverse();n=-n
        start=len(p['p'])
        p['p'].extend((x,z,-y) for x,y,z in positions)
        p['n'].extend([(float(n[0]),float(n[2]),float(-n[1]))]*4)
        p['uv'].extend((u,1-v) for u,v,side in coords)
        p['i'].extend((start,start+1,start+2,start,start+2,start+3))
    nx,ny=8,12
    for side in (-1,1):
        for j in range(ny):
            for i in range(nx):
                face([(i/nx,j/ny,side),((i+1)/nx,j/ny,side),
                      ((i+1)/nx,(j+1)/ny,side),(i/nx,(j+1)/ny,side)],
                     0 if side==-1 else 1,(side,0,0))
    for edge in range(4):
        count=nx if edge<2 else ny
        for i in range(count):
            a,b=i/count,(i+1)/count
            if edge<2:
                v=float(edge);coords=[(a,v,-1),(b,v,-1),(b,v,1),(a,v,1)];normal=(0,0,2*edge-1)
            else:
                u=float(edge-2);coords=[(u,a,-1),(u,b,-1),(u,b,1),(u,a,1)];normal=(0,2*(edge-2)-1,0)
            face(coords,1,normal)
    return parts


def document(parts):
    blob=bytearray();views=[];accessors=[];primitives=[]
    def add(values,kind,component,fmt,target):
        while len(blob)%4:blob.append(0)
        flat=[n for row in values for n in row] if kind!='SCALAR' else values
        packed=struct.pack('<'+fmt*len(flat),*flat);offset=len(blob);blob.extend(packed)
        views.append(dict(buffer=0,byteOffset=offset,byteLength=len(packed),target=target))
        a=dict(bufferView=len(views)-1,componentType=component,count=len(values),type=kind)
        if kind=='VEC3':a.update(min=np.min(values,axis=0).tolist(),max=np.max(values,axis=0).tolist())
        accessors.append(a);return len(accessors)-1
    for slot,p in enumerate(parts):
        attrs={key:add(p[name],kind,5126,'f',34962) for key,name,kind in
               [('POSITION','p','VEC3'),('NORMAL','n','VEC3'),('TEXCOORD_0','uv','VEC2')]}
        primitives.append(dict(attributes=attrs,indices=add(p['i'],'SCALAR',5123,'H',34963),material=slot))
    return dict(asset={'version':'2.0','generator':'FoA original A4 paper'},scene=0,scenes=[{'nodes':[0]}],
        nodes=[{'mesh':0,'name':'SM_L2CVPaper'}],meshes=[{'name':'SM_L2CVPaper','primitives':primitives}],
        materials=[dict(name='M_L2CVPrint',pbrMetallicRoughness=dict(baseColorTexture={'index':0},metallicFactor=0,roughnessFactor=.95)),
                   dict(name='M_L2CVPaperBack',pbrMetallicRoughness=dict(baseColorFactor=[.79,.79,.79,1],metallicFactor=0,roughnessFactor=.95))],
        images=[{'uri':'T_L2CVPaper.png'}],textures=[{'source':0,'sampler':0}],
        samplers=[{'magFilter':9729,'minFilter':9987,'wrapS':33071,'wrapT':33071}],
        buffers=[{'byteLength':len(blob),'uri':'data:application/octet-stream;base64,'+base64.b64encode(blob).decode()}],
        bufferViews=views,accessors=accessors)


def generate():
    OUT.mkdir(parents=True,exist_ok=True)
    image=texture();image.save(OUT/'T_L2CVPaper.png')
    parts=geometry();doc=document(parts)
    (OUT/'SM_L2CVPaper.gltf').write_text(json.dumps(doc,separators=(',',':')))
    receipt=dict(asset=ASSET,dimensions_cm=[21,29.7],thickness_mm=.12,front_normal='-X',
        text=TEXT,source='Tools/Unreal/level2/build_journey.py:confirm Phase2',
        font_license=str(FONT/'OFL.txt'),triangles=sum(len(p['i'])//3 for p in parts),native_verified=False)
    (OUT/'manifest.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt))
    return doc


if __name__=='__main__':generate()
