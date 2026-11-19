import math
import struct
import unittest
from unittest.mock import patch
import ply_to_splatmesh as convert
import dream_sky
import build_splat_world_lean as material

class DreamVisualTest(unittest.TestCase):
    def test_sky_replaces_photo_only_after_new_shader_compiles(self):
        calls=[]
        info=dict(expressions=[dict(id='photo',x=-300,y=0,**{'class':'MaterialExpressionTextureSampleParameter2D'})],
                  material_outputs=[dict(property='Emissive Color',from_node='photo')],comments=[])
        def call(name,**args):
            calls.append((name,args))
            if name=='material_get_info':return info
            if name=='material_add_node':return dict(node_id='node'+str(len(calls)))
            return {}
        with patch.object(material,'call',call),patch.object(material.h,'call',return_value={'ok':True}):material.sky()
        compiled=next(i for i,(name,_) in enumerate(calls) if name=='material_compile')
        deleted=next(i for i,(name,_) in enumerate(calls) if name=='material_delete_node')
        self.assertGreater(deleted,compiled)
        self.assertTrue(all(args.get('material_path',material.SKY)==material.SKY for _,args in calls))

    def test_sky_compile_failure_restores_photo_connection(self):
        calls=[];compiles=0
        info=dict(expressions=[dict(id='photo',x=-300,y=0,**{'class':'MaterialExpressionTextureSampleParameter2D'})],
                  material_outputs=[dict(property='Emissive Color',from_node='photo')],comments=[])
        def call(name,**args):
            nonlocal compiles
            calls.append((name,args))
            if name=='material_get_info':return info
            if name=='material_add_node':return dict(node_id='node'+str(len(calls)))
            if name=='material_compile':
                compiles+=1
                if compiles==1:raise RuntimeError('test compiler rejection')
            return {}
        with patch.object(material,'call',call),patch.object(material.h,'call',return_value={'ok':True}):
            with self.assertRaisesRegex(RuntimeError,'test compiler rejection'):material.sky()
        self.assertEqual(compiles,2)
        self.assertFalse(any(name=='material_delete_node' for name,_ in calls))
        self.assertEqual([args['from_node'] for name,args in calls if name=='material_connect_nodes' and args.get('to_property')=='emissive_color'][-1],'photo')

    def test_fixed_frame_survives_density_changes_and_preserves_true_colour(self):
        names=list(convert.REQUIRED);rows=[]
        for i in range(12):
            row={key:0. for key in names}
            row.update(x=i*.5,y=-i*.1,z=-i*.2,opacity=8.,rot_0=1.)
            for k in range(3):row['scale_'+str(k)]=math.log(.03);row['f_dc_'+str(k)]=(float((k+1)/4)-.5)/convert.C0
            rows.append([row[key] for key in names])
        header=('ply\nformat binary_little_endian 1.0\nelement vertex 12\n'+''.join('property float '+k+'\n' for k in names)+'end_header\n').encode()
        data=header+struct.pack('<'+str(12*len(names))+'f',*(v for row in rows for v in row))
        origin=[1.25,-3.5,2.75]
        doc,blob,side=convert.convert(data,12,1,'test',lean=True,origin=origin)
        self.assertEqual(side['offset_m'],origin);self.assertEqual(side['splats'],12)
        self.assertEqual(convert.convert(data,5,1,'test',lean=True,origin=origin)[2]['offset_m'],origin)
        attrs=doc['meshes'][0]['primitives'][0]['attributes']
        self.assertEqual(set(attrs),{'POSITION','TEXCOORD_0','TEXCOORD_1','COLOR_0'})
        acc=doc['accessors'][attrs['COLOR_0']];view=doc['bufferViews'][acc['bufferView']]
        rgb=struct.unpack_from('<3f',blob,view['byteOffset'])
        for actual,expected in zip(rgb,[.25,.5,.75]):self.assertAlmostEqual(actual,expected,places=6)

    def test_sky_is_dark_seamless_slow_and_has_no_texture_dependency(self):
        self.assertNotIn('Texture',dream_sky.SKY_CODE)
        classes=[spec[1] for spec in dream_sky.specs(lambda *args:{})]
        self.assertEqual(classes,['CameraVectorWS','Time','Custom'])
        for z in (-1,-.5,0,.5,1):
            direction=(1,.4,z);a=dream_sky.colour(direction);b=dream_sky.colour(direction,1/30)
            self.assertTrue(all(0<v<.06 for v in a))
            self.assertLess(max(abs(x-y) for x,y in zip(a,b)),.0001)
        a=dream_sky.colour((-1,1e-8,.3));b=dream_sky.colour((-1,-1e-8,.3))
        self.assertLess(max(abs(x-y) for x,y in zip(a,b)),1e-7)

if __name__=='__main__':unittest.main()
