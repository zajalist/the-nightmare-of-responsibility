"""Exercise the real import loop without an editor or native assets."""
import ast
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch


class StreamedImportTest(unittest.TestCase):
    def run_import(self, elapsed):
        source=Path(__file__).parents[1]/'import_l2_city.py'
        function=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='streamed')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'queen_600m_streamed';folder.mkdir()
            entries=[dict(name=f'Mesh{i}',gltf=f'Mesh{i}.gltf',asset_path=f'/Game/Dense/Mesh{i}',
                          material='/Game/Ground',kind='ground',lod='near',splats=10,radius_cm_max=87.5) for i in range(3)]
            (folder/'manifest.json').write_text(json.dumps(dict(complete=True,completed_cells=144,meshes=entries,overview=[])))
            disk=root/'asset.uasset';disk.write_bytes(b'asset')
            def path(value):
                if str(value).startswith('P:/FoA/Content'):return disk
                if str(value).startswith('P:/FoA/Saved'):return root/'receipts'
                return Path(value)
            events=[];settings={'enabled':True,'use_full_precision_u_vs':False}
            props=MagicMock()
            props.get_editor_property.side_effect=lambda key:settings.get(key,True)
            props.set_editor_property.side_effect=lambda key,value:settings.update({key:value})
            mesh=MagicMock();mesh.get_editor_property.return_value.to_tuple.return_value=(0,0,0)
            def triangles(lod):
                self.assertFalse(settings['enabled']);self.assertTrue(settings['use_full_precision_u_vs'])
                self.assertIn(('nanite_build',True),events)
                return 20
            mesh.get_num_triangles.side_effect=triangles
            smes=MagicMock();smes.get_nanite_settings.return_value=props;smes.get_lod_build_settings.return_value=props
            smes.set_nanite_settings.side_effect=lambda mesh,ns,build:events.append(('nanite_build',build))
            smes.get_num_uv_channels.return_value=2
            unreal=MagicMock();unreal.get_editor_subsystem.return_value.get_game_world.return_value=None
            unreal.load_asset.return_value=mesh
            eal=MagicMock();eal.does_asset_exist.return_value=False;eal.save_loaded_asset.return_value=True
            ticks=iter([0.,*elapsed,99.])
            namespace=dict(json=json,os=os,Path=path,SRC=str(root/'queen_600m'),DST='/Game/City',
                           time=types.SimpleNamespace(monotonic=lambda:next(ticks)),unreal=unreal,SMES=smes,EAL=eal,
                           tasks=lambda files,dest:events.append(('import',files)),print=lambda *a:None)
            exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),namespace)
            with patch.dict(os.environ,FOA_CITY_FROM='0',FOA_CITY_N='3'):
                namespace['streamed']()
            receipt=json.loads((root/'receipts/0000.json').read_text())
            self.assertEqual(len(receipt),sum(e[0]=='import' for e in events))
            self.assertTrue(all(r['bounds_padding_cm']==50 and r['full_precision_uvs'] for r in receipt))
            return receipt

    def test_nanite_build_and_precision_precede_triangle_verification(self):
        self.assertEqual([r['index'] for r in self.run_import([1.,2.,3.])],[0,1,2])

    def test_time_budget_saves_receipt_before_stopping_next_import(self):
        self.assertEqual([r['index'] for r in self.run_import([41.,42.])],[0])


if __name__=='__main__':unittest.main()
