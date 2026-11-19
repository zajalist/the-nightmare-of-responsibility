"""Offline contract: explicit Interchange stack and exact paths retain existing references."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

class Properties:
    def __init__(self):self.values={}
    def set_editor_property(self,key,value):self.values[key]=value
    def get_editor_property(self,key):return self.values.setdefault(key,Properties())

class Overrides(Properties):
    def add_pipeline(self,pipeline):self.pipeline=pipeline

def function(filename,name):
    tree=ast.parse(Path(__file__).with_name(filename).read_text())
    return compile(ast.Module(body=[next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)],type_ignores=[]),filename,'exec')

class ImportContract(unittest.TestCase):
    def test_dream_and_city_import_exact_path_with_lean_pipeline(self):
        for filename,name in [('import_l2_city.py','tasks'),('import_l2_dream.py','task')]:
            with self.subTest(filename=filename):
                imported=[]
                fake=SimpleNamespace(AssetImportTask=Properties,InterchangeGenericAssetsPipeline=Properties,
                    InterchangePipelineStackOverride=Overrides,
                    AssetToolsHelpers=SimpleNamespace(get_asset_tools=lambda:SimpleNamespace(import_asset_tasks=imported.extend)))
                env=dict(unreal=fake,Path=Path);exec(function(filename,name),env)
                env[name](['P:/source/SM_Test.gltf'] if name=='tasks' else 'P:/source/SM_Test.gltf','/Game/Test')
                self.assertEqual(len(imported),1);task=imported[0]
                self.assertEqual(task.values['destination_path'],'/Game/Test/SM_Test/StaticMeshes')
                self.assertTrue(task.values['replace_existing'])
                stack=task.values['options'];self.assertIsInstance(stack,Overrides)
                pipeline=stack.pipeline
                self.assertFalse(pipeline.values['material_pipeline'].values['import_materials'])
                self.assertFalse(pipeline.values['mesh_pipeline'].values['build_nanite'])
                self.assertEqual(pipeline.values['mesh_pipeline'].values['distance_field_resolution_scale'],0)
                self.assertTrue(pipeline.values['common_meshes_properties'].values['use_full_precision_u_vs'])

if __name__=='__main__':unittest.main()
