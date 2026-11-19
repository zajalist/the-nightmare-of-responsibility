"""Targeted search data/reference update. Run only after native graph compile and outside PIE.
Preserves every existing interaction row, including custom rows from other lanes.
"""
import json, sys, os
from pathlib import Path
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/gameplay')
from data_rows import SEARCH_ROWS

assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
actors={a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
probe_only=os.environ.get('FOA_SEARCH_PROBE')=='1'
director=next(a for a in actors.values() if a.get_class().get_name()=='BP_BeatDirector_C')
for var,label in [('SearchWardrobe','Wardrobe'),('SearchDesk','Desk'),('SearchBed','Bed'),('SearchShirt','Shirt_T7')]:
    if not probe_only:director.set_editor_property(var,actors[label])

def bounds(actor):
    corners=[]
    for c in actor.get_components_by_class(unreal.StaticMeshComponent):
        if not c.get_editor_property('static_mesh'):continue
        o,e,_=unreal.SystemLibrary.get_component_bounds(c)
        corners.extend([o-e,o+e])
    assert corners,actor
    return [min(getattr(p,k) for p in corners) for k in ('x','y','z')],[max(getattr(p,k) for p in corners) for k in ('x','y','z')]

lo,hi=bounds(actors['Bed']);slo,shi=bounds(actors['Shirt_T7']);home=actors['Shirt_T7'].get_actor_location()
# The bed's long axis points away from the nearest wall. Use its room-facing end and keep the full shirt clear.
axis=0 if hi[0]-lo[0]>hi[1]-lo[1] else 1
side=1 if abs(hi[axis])<abs(lo[axis]) else -1
target=[(lo[i]+hi[i])/2 for i in range(3)]
target[axis]=(hi[axis] if side>0 else lo[axis])+side*((shi[axis]-slo[axis])/2+12)
spot=unreal.Vector(home.x+target[0]-(slo[0]+shi[0])/2,home.y+target[1]-(slo[1]+shi[1])/2,home.z-slo[2]+1)
# The chest occupies the foot end. Keep the full garment clear of every solid prop,
# then use the room-facing bedside corner when the first candidate is obstructed.
def obstruction(candidate):
    delta=[getattr(candidate,k)-getattr(home,k) for k in ('x','y','z')]
    a=[slo[i]+delta[i] for i in range(3)];b=[shi[i]+delta[i] for i in range(3)]
    for actor in actors.values():
        if actor==actors['Shirt_T7']:continue
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            if not component.get_editor_property('static_mesh'):continue
            if component.get_collision_enabled()==unreal.CollisionEnabled.NO_COLLISION:continue
            o,e,_=unreal.SystemLibrary.get_component_bounds(component)
            c=[o.x-e.x,o.y-e.y,o.z-e.z];d=[o.x+e.x,o.y+e.y,o.z+e.z]
            if d[2]<=8:continue  # Floor, rug and shallow sand are support surfaces.
            if all(a[i]<d[i] and b[i]>c[i] for i in range(3)):return actor.get_actor_label()
    return None
if obstruction(spot):
    lateral=1-axis
    target[lateral]=hi[lateral]+(shi[lateral]-slo[lateral])/2+20
    for retreat in (0,40,80,120):
        clear_target=list(target);clear_target[axis]+=side*retreat
        spot=unreal.Vector(home.x+clear_target[0]-(slo[0]+shi[0])/2,home.y+clear_target[1]-(slo[1]+shi[1])/2,home.z-slo[2]+1)
        if obstruction(spot) is None:break
assert obstruction(spot) is None,('No clear shirt pickup position',obstruction(spot))
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(spot.x,spot.y,12),unreal.Vector(spot.x,spot.y,-5),
    unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[],unreal.DrawDebugTrace.NONE,True)
hit=hit[1] if isinstance(hit,tuple) else hit
if hit and hit.to_tuple()[0]:spot.z+=hit.to_tuple()[5].z
if not probe_only:director.set_editor_property('ClothingShirtSpot',spot)
Path('P:/FoA/Saved/Integration/clothing_clear_spot.json').write_text(json.dumps(dict(
    actor=director.get_path_name(),spot=list(spot.to_tuple()),obstruction=obstruction(spot)),indent=1))
def configure_tables():
    bed=actors['Bed']
    properties=[str(n) for n in unreal.BlueprintEditorLibrary.list_member_variable_names(unreal.load_asset('/Game/FoA/Gameplay/BP_Interactable'),False)]
    print('BASE_VARS',properties)
    for prop in properties:
        if prop.lower()=='autouseitem':
            bed.set_editor_property(prop,unreal.Name('Hanger'))

    dt=unreal.load_asset('/Game/FoA/Gameplay/DT_Interactions')
    raw=unreal.DataTableFunctionLibrary.export_data_table_to_json_string(dt)
    existing=json.loads(raw)
    backup=Path('P:/FoA/Saved/Integration/clothing_interactions_before.json')
    if not backup.exists():backup.write_text(raw,encoding='utf-8')
    rows=[dict(r,Name=f'Search_{i:02d}_{r["Interactable"]}_{r["State"]}_{r["Verb"]}_{r["Item"]}') for i,r in enumerate(SEARCH_ROWS)]
    kept=[r for r in existing if not str(r['Name']).startswith('Search_')]
    assert unreal.DataTableFunctionLibrary.fill_data_table_from_json_string(dt,json.dumps(rows+kept)), 'Table import failed'
    assert unreal.EditorAssetLibrary.save_loaded_asset(dt,False)
    gi=unreal.load_asset('/Game/FoA/Gameplay/GI_FoA')
    assert gi
    cdo=unreal.get_default_object(gi.generated_class());notes=dict(cdo.get_editor_property('NotebookLines'))
    notes.update({unreal.Name(k):unreal.Text(v) for k,v in {
        'Knows.ClothingThread':'Thread in the wardrobe, goes to the desk.',
        'Knows.ClothingTrail':'Button under the papers. Marks to the bed.',
        'Knows.ClothingSnag':"Shirt's under the bed. Use the hanger."}.items()})
    cdo.set_editor_property('NotebookLines',notes);assert unreal.EditorAssetLibrary.save_loaded_asset(gi,False)
    beat=unreal.load_asset('/Game/FoA/Gameplay/Beats/DA_Beat_T7');assert beat
    beat.set_editor_property('Objective',unreal.Text('Find the missing shirt.'));assert unreal.EditorAssetLibrary.save_loaded_asset(beat,False)
    print('SEARCH_CONFIG',json.dumps(dict(bed_bounds=[lo,hi],shirt_bounds=[slo,shi],shirt_home=home.to_tuple(),shirt_spot=spot.to_tuple(),priority_rows=len(rows),preserved_rows=len(kept))))

if probe_only or os.environ.get('FOA_SEARCH_SPOT_ONLY')=='1':
    print('SEARCH_SPOT',spot.to_tuple())
else:
    configure_tables()
