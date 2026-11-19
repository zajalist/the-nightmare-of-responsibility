"""Geometry, winding and embedded-buffer checks without Unreal or third-party packages."""
import base64
import ast
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import car_visual as c


class SedanTest(unittest.TestCase):
    def test_paint_reuses_lit_master_without_changing_marker_materials(self):
        tree=ast.parse(Path(__file__).with_name('drive_visuals.py').read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='car_materials')
        call=Mock();env=dict(call=call,D=SimpleNamespace(ROOT='/Game/FoA/Level2/Drive'))
        exec(compile(ast.Module(body=[function],type_ignores=[]),'materials','exec'),env)
        env['car_materials']()
        created=[row.kwargs for row in call.call_args_list if row.args[0]=='material_create_instance']
        self.assertEqual({row['name'] for row in created},{'MI_L2CarPaint','MI_L2CarTrim'})
        self.assertTrue(all(row['parent_material_path']=='/Game/FoA/Materials/M_Greybox' for row in created))
        params=[row.kwargs for row in call.call_args_list if row.args[0]=='material_set_param']
        self.assertEqual(len(params),8)
        self.assertTrue(all(row['instance_path'].startswith('/Game/FoA/Level2/Drive/MI_L2Car') for row in params))
        self.assertEqual([row['value'] for row in params if row['param_name']=='Emissive'],[0.,0.])

    def test_geometry_is_small_finite_and_faces_match_normals(self):
        mesh=c.sedan()
        self.assertEqual(len(mesh.parts),2)
        self.assertLess(sum(len(p['indices'])//3 for p in mesh.parts),1500)
        for part in mesh.parts:
            self.assertLess(max(part['indices']),len(part['positions']))
            for p,n in zip(part['positions'],part['normals']):
                self.assertTrue(all(math.isfinite(v) for v in p+n))
                self.assertAlmostEqual(c.dot(n,n),1)
            for start in range(0,len(part['indices']),3):
                a,b,d=[part['positions'][i] for i in part['indices'][start:start+3]]
                normal=part['normals'][part['indices'][start]]
                self.assertGreater(c.dot(c.cross(c.sub(b,a),c.sub(d,a)),normal),1e-8)

    def test_footprint_contacts_and_sedan_features(self):
        mesh=c.sedan();vertices=[v for p in mesh.parts for v in p['positions']]
        self.assertAlmostEqual(min(p[1] for p in vertices),0)
        self.assertAlmostEqual(max(p[1] for p in vertices),1.47)
        self.assertLess(max(p[0] for p in vertices)-min(p[0] for p in vertices),4.5)
        self.assertEqual(len(mesh.features['wheel_centres']),4)
        self.assertEqual(mesh.features['windows'],6)
        self.assertEqual(mesh.features['headlights'],2)

    def test_gltf_is_one_mesh_two_reusable_slots_and_valid_buffers(self):
        doc=c.document(c.sedan());blob=base64.b64decode(doc['buffers'][0]['uri'].split(',')[1])
        self.assertEqual(len(doc['meshes']),1);self.assertEqual(len(doc['meshes'][0]['primitives']),2)
        self.assertEqual(len(blob),doc['buffers'][0]['byteLength'])
        self.assertNotIn('textures',doc)
        for view in doc['bufferViews']:
            self.assertEqual(view['byteOffset']%4,0)
            self.assertLessEqual(view['byteOffset']+view['byteLength'],len(blob))
        self.assertEqual(tuple(m['extras']['unreal_material'] for m in doc['materials']),c.MATERIALS)

    def test_setup_respects_slot_names_and_clears_prototype_roof(self):
        tree=ast.parse(Path(__file__).with_name('car_visual_setup.py').read_text())
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('assign_materials','apply_to_components')]
        paths=('/Game/FoA/Level2/Drive/MI_L2CarPaint','/Game/FoA/Level2/Drive/MI_L2CarTrim')
        materials={p:SimpleNamespace(get_path_name=lambda p=p:p) for p in paths}
        fake=SimpleNamespace(load_asset=materials.get,Vector=lambda *v:v,Rotator=lambda *v:v)
        env=dict(unreal=fake,MATERIALS=paths)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'setup','exec'),env)
        slots=[SimpleNamespace(get_editor_property=lambda _,name=name:name) for name in ('MI_L2Dark','M_L2Flat')]
        mesh=Mock();mesh.get_editor_property.return_value=slots
        body,roof=Mock(),Mock()
        env['apply_to_components']({'Body':body,'Roof':roof},mesh)
        body.set_static_mesh.assert_called_once_with(mesh)
        body.set_editor_property.assert_any_call('relative_scale3d',(1,1,1))
        body.set_editor_property.assert_any_call('relative_location',(0,0,0))
        body.set_material.assert_any_call(0,materials[paths[1]])
        body.set_material.assert_any_call(1,materials[paths[0]])
        body.set_editor_property.assert_any_call('cast_shadow',True)
        roof.set_static_mesh.assert_called_once_with(None)
        roof.set_editor_property.assert_any_call('hidden_in_game',True)
        body.set_collision_profile_name.assert_called_once_with('NoCollision')


if __name__=='__main__':unittest.main()
