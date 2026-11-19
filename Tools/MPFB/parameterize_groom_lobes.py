"""Expose existing lobe constants with identical defaults for controlled transient comparison."""
import sys,json,datetime,shutil
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h
P='/Game/FoA/Characters/Teen/Hair/M_FoA_TeenStrands';owner='character_hair_material'
def call(cmd,**kw):
    r=h.call(cmd,kw,owner=owner);assert r.get('ok'),r;return r.get('data',{})
assert not call('editor_get_state')['pie_running']
token=h.lease_acquire(owner,['asset:'+P],ttl_s=45,wait_s=3)
try:
    backup=Path('Saved/Backups/hair_lobes')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
    shutil.copy2('Content/FoA/Characters/Teen/Hair/M_FoA_TeenStrands.uasset',backup/'M_FoA_TeenStrands.uasset')
    before=call('material_get_info',path=P);values={}
    for prop,name in [('Roughness','HairRoughness'),('Specular','HairSpecular')]:
        output=next(o for o in before['material_outputs'] if o['property']==prop)
        old=next(e for e in before['expressions'] if e['id']==output['from_node'])
        if old.get('parameter_name')==name:values[name]=old['default_value'];continue
        assert old['class']=='MaterialExpressionConstant'
        value=call('object_get_property',path=P+'.M_FoA_TeenStrands:'+old['id'],names=['R'])['properties']['R']
        value=float(value);values[name]=value
        node=call('material_add_node',material_path=P,expression_class='MaterialExpressionScalarParameter',node_pos=[old['x'],old['y']],properties={'ParameterName':name,'DefaultValue':value})['node_id']
        call('material_connect_nodes',material_path=P,from_node=node,from_output_index=0,to_property=prop.lower())
        call('material_delete_node',material_path=P,node_id=old['id'])
    call('material_validate',material_path=P);compiled=call('material_compile',material_path=P)
    call('asset_save',asset_paths=[P])
    after=call('material_get_info',path=P)
    for name,value in values.items():assert abs(next(e['default_value'] for e in after['expressions'] if e.get('parameter_name')==name)-value)<1e-7
    Path('Saved/Integration/cinematic_audit/hair_lobe_parameterization.json').write_text(json.dumps(dict(backup=str(backup),values=values,compile=compiled,after=after),indent=2))
    print('Same-default hair parameters saved',values)
finally:h.release(owner,token)
