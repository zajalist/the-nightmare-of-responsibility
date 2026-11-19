"""Blender-only: six ceramic shards from the already licensed Poly Haven pot."""
import bpy,bmesh,math,json
from pathlib import Path
OUT=Path('P:/FoA-Assets/procedural/vase_fragments');OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath='P:/FoA-Assets/polyhaven/models/potted_plant_02/potted_plant_02_1k.gltf')
source=next(o for o in bpy.context.scene.objects if o.name=='potted_plant_02_pot')
manifest=[]
for i in range(6):
 mesh=source.data.copy();obj=bpy.data.objects.new('SM_VaseShard_'+str(i+1),mesh);bpy.context.collection.objects.link(obj)
 bm=bmesh.new();bm.from_mesh(mesh)
 remove=[]
 for face in bm.faces:
  p=source.matrix_world@face.calc_center_median()
  sector=int(((math.atan2(p.y,p.x)+math.pi+.09*math.sin(p.z*38))%(2*math.pi))/(2*math.pi/6))
  if sector!=i:remove.append(face)
 bmesh.ops.delete(bm,geom=remove,context='FACES')
 loose=[v for v in bm.verts if not v.link_faces]
 if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
 # Fill only the fresh fracture boundary; the original pot's UVs remain intact.
 boundary=[e for e in bm.edges if e.is_boundary]
 if boundary:
  filled=bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
  for face in filled.get('faces',[]):face.material_index=0
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 for v in mesh.vertices:v.co=source.matrix_world@v.co
 # Bake the slender vase proportions into each shard, matching the intact component scale.
 for v in mesh.vertices:v.co.x*=.45;v.co.y*=.45;v.co.z*=.95
 center=sum((v.co for v in mesh.vertices),start=__import__('mathutils').Vector())/len(mesh.vertices)
 for v in mesh.vertices:v.co-=center
 obj.location=(0,0,0)
 # Reuse the existing UE material instead of importing new textures/material assets.
 mesh.materials.clear()
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 path=OUT/(obj.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},
  use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z')
 manifest.append({'name':obj.name,'file':str(path),'center_cm':[float(v*100) for v in center],
  'vertices':len(mesh.vertices),'triangles':len(mesh.polygons)})
 bpy.data.objects.remove(obj,do_unlink=True)
(OUT/'fragments.json').write_text(json.dumps(manifest,indent=1))
(OUT/'SOURCES.txt').write_text('Derived from Poly Haven potted_plant_02, CC0. Existing local source: P:/FoA-Assets/polyhaven/models/potted_plant_02/potted_plant_02_1k.gltf. Six procedural fracture sectors preserve the original surface UVs; existing UE ceramic material is reused.\n')
print('SHARDS',json.dumps(manifest))
