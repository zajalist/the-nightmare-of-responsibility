"""NumPy build adapter for the existing converter's SH0 lean path; no repo converter edits."""
import array
import math
import numpy as np


def install(conv):
    def build(cols,sh_names,kept,rng,origin=None):
        assert not sh_names,'City adapter only supports SH0 lean input'
        get=lambda key:np.asarray(cols[key],np.float64)[kept]
        centres=np.stack([get('x'),-get('y'),-get('z')],1)
        lo=centres.min(0);hi=centres.max(0);off=np.array([(lo[0]+hi[0])/2,lo[1],(lo[2]+hi[2])/2])
        if origin is not None:
            off=np.asarray(origin,dtype=float)
            if off.shape!=(3,) or not np.isfinite(off).all():raise ValueError('origin must contain three finite coordinates')
        n=len(centres);p=np.repeat((centres-off)[:,None,:],4,axis=1)
        corners=np.asarray(conv.CORNER_UV).reshape(4,2)
        p[:,:,:2]+=corners[None,:,:]*conv.NUDGE_M
        scales=get('scale_0')+get('scale_1')+get('scale_2')
        radius=200*np.exp(scales/3);alpha=1/(1+np.exp(-get('opacity')))
        seed=np.fromiter((rng.random() for _ in range(n)),float,count=n)
        rs=np.repeat(np.stack([radius,seed],1),4,axis=0)
        colour=np.repeat(np.stack([*[np.clip(.5+conv.C0*get(f'f_dc_{k}'),0,1) for k in range(3)],alpha],1),4,axis=0)
        values={'POSITION':p,'TEXCOORD_0':np.tile(corners,(n,1)),'TEXCOORD_1':rs,'COLOR_0':colour}
        arrays={k:array.array('f') for k in conv.CHANNELS}
        for k,value in values.items():arrays[k].frombytes(np.asarray(value,dtype='<f4').tobytes())
        idx=array.array('I');idx.frombytes((np.arange(n,dtype=np.uint32)[:,None]*4+np.array([0,1,2,0,2,3],np.uint32)).tobytes())
        return arrays,idx,{'centers_min':(lo-off).tolist(),'centers_max':(hi-off).tolist(),'offset':off.tolist(),
            'footprint':float(np.sum(alpha*np.exp(scales*2/3))),'radii':sorted(radius.tolist())}
    conv.build=build


def selftest(conv):
    fields=list(conv.REQUIRED);rng=np.random.default_rng(31);rows=np.zeros((511,len(fields)),'<f4')
    for key,value in [('x',rng.uniform(-100,100,511)),('y',rng.uniform(-40,1,511)),('z',rng.uniform(-600,600,511)),('opacity',8),('rot_0',1)]:rows[:,fields.index(key)]=value
    for k in range(3):
        rows[:,fields.index(f'f_dc_{k}')]=rng.uniform(-1,1,511)
        rows[:,fields.index(f'scale_{k}')]=rng.uniform(-4,-1,511)
    header=('ply\nformat binary_little_endian 1.0\nelement vertex 511\n'+''.join('property float '+f+'\n' for f in fields)+'end_header\n').encode()
    data=header+rows.tobytes();old=conv.build
    expected=conv.convert(data,511,8,'check',lean=True)
    try:
        install(conv);actual=conv.convert(data,511,8,'check',lean=True)
    finally:conv.build=old
    for a,b in zip(expected[0]['accessors'],actual[0]['accessors']):
        va=expected[0]['bufferViews'][a['bufferView']];vb=actual[0]['bufferViews'][b['bufferView']]
        dtype='<u4' if a['componentType']==5125 else '<f4'
        x=np.frombuffer(expected[1][va['byteOffset']:va['byteOffset']+va['byteLength']],dtype)
        y=np.frombuffer(actual[1][vb['byteOffset']:vb['byteOffset']+vb['byteLength']],dtype)
        assert np.allclose(x,y,rtol=1e-6,atol=1e-5),(a,np.max(abs(x-y)))
    assert expected[2]['offset_m']==actual[2]['offset_m']
    assert expected[2]['radius_scale_hint']==actual[2]['radius_scale_hint']
    print('city2 vectorized lean adapter matches original converter',flush=True)
