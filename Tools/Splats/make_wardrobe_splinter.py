"""A 5.4 cm tapered wood splinter; existing cabinet atlas/material reused."""
import bpy,json
from pathlib import Path
OUT=Path('P:/FoA-Assets/procedural/wardrobe_splinter');OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
verts=[]
for x,width,z,thickness in [(2.7,.50,.02,.14),(-.8,.27,.18,.18),(-2.7,.035,.72,.06)]:
    verts += [(x,-width,z),(x,width,z),(x,width,z+thickness),(x,-width,z+thickness)]
faces=[(3,2,1,0),(8,9,10,11)]
for r in range(2):
    for i in range(4):
        a=r*4+i;b=r*4+(i+1)%4;c=b+4;d=a+4
        faces += [(a,b,c),(a,c,d)]
mesh=bpy.data.meshes.new('SM_WardrobeSplinter');mesh.from_pydata([(x*.01,y*.01,z*.01) for x,y,z in verts],[],faces)
obj=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(obj)
uv=mesh.uv_layers.new(name='UVMap')
for poly in mesh.polygons:
    for loop in poly.loop_indices:
        v=mesh.vertices[mesh.loops[loop].vertex_index].co
        # A plain exposed wood region of the existing cabinet atlas, not its carved trim.
        uv.data[loop].uv=(.75+(v.x/.054+.5)*.11,.56+(v.y/.01+.5)*.07)
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
path=OUT/(obj.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},
    use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z')
(OUT/'SOURCES.txt').write_text('Original procedural 5.4 cm tapered splinter geometry authored for FoA. Reuses the existing Poly Haven GothicCabinet_01 CC0 material and UV atlas; no texture or material copies.\n')
(OUT/'mesh.json').write_text(json.dumps({'file':str(path),'vertices':len(verts),'triangles':20,'length_cm':5.4},indent=1))
