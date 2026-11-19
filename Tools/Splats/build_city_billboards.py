"""One-node correction for the city's baked horizontal splat quads.

Run --selftest offline, or apply only during a coordinator-granted editor window.
No mesh, map, shared dynamics function, MPC, coverage or colour changes.
"""
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path('P:/FoA')
CITY='/Game/FoA/Level2/M_SplatCity_Lean'
CORNER='MaterialExpressionCustom_4'
DYNAMICS='MaterialExpressionMaterialFunctionCall_0'
REST='MaterialExpressionCustom_2'
UV='MaterialExpressionTextureCoordinate_0'
RS='MaterialExpressionTextureCoordinate_1'
INPUTS=('Dynamics','Facing','UV','RS')
BAKED_CODE='return float3(UV.x, -UV.y, 0) * RS.x;'
FACING_CODE='''// Rotate each baked city quad around its unchanged splat centre.
float3 R = ResolvedView.ViewToTranslatedWorld[0].xyz;
float3 U = ResolvedView.ViewToTranslatedWorld[1].xyz;
return (R * UV.x + U * UV.y) * RS.x;'''
OFFSET_CODE='''// The imported vertex already includes a horizontal corner.
// Dynamics receives Facing, so breathing and meteor shrink use the same basis.
return Dynamics + Facing - float3(UV.x, -UV.y, 0) * RS.x;'''


def norm(name):return ''.join(c.lower() for c in name if c.isalnum())
def inputs(node):return {n['name']:n for n in node.get('inputs',[])}
def terminal(info):
    return next(n for n in info['material_outputs'] if norm(n['property'])=='worldpositionoffset')
def correction(info):
    found=[n for n in info['expressions'] if n['class']=='MaterialExpressionCustom' and set(inputs(n))==set(INPUTS)]
    assert len(found)<=1,('Duplicate city facing corrections',found)
    return found[0] if found else None


def preflight(info):
    nodes={n['id']:n for n in info['expressions']}
    assert set(inputs(nodes[CORNER]))=={'UV','RS'},'City corner contract changed'
    assert set(inputs(nodes[REST]))=={'WP','UV','RS'},'City rest contract changed'
    ports={norm(k):v for k,v in inputs(nodes[DYNAMICS]).items()}
    assert ports['restv3']['from_node']==REST and ports['corneroffsetv3']['from_node']==CORNER,ports
    old=correction(info)
    assert terminal(info).get('from_node') in {DYNAMICS,old['id'] if old else None},'Unexpected city WPO writer'
    return old


def restore_baked(call,node=None):
    call('material_set_node',material_path=CITY,node_id=CORNER,properties={'Code':BAKED_CODE})
    call('material_connect_nodes',material_path=CITY,from_node=DYNAMICS,from_output_index=0,to_property='world_position_offset')
    if node:call('material_delete_node',material_path=CITY,node_id=node)
    call('material_compile',material_path=CITY)


def apply(call):
    """Native adapter also used by the canonical dynamics builder on future reruns."""
    before=call('material_get_info',path=CITY);old=preflight(before)
    node=old['id'] if old else None
    try:
        call('material_set_node',material_path=CITY,node_id=CORNER,properties={'Code':FACING_CODE})
        props=dict(Description='City facing correction',OutputType='CMOT_Float3',Code=OFFSET_CODE,
                   Inputs=[dict(InputName=n) for n in INPUTS])
        if node:call('material_set_node',material_path=CITY,node_id=node,properties=props)
        else:node=call('material_add_node',material_path=CITY,expression_class='MaterialExpressionCustom',
                       node_pos=[1200,1100],properties=props)['node_id']
        for source,pin in ((DYNAMICS,'Dynamics'),(CORNER,'Facing'),(UV,'UV'),(RS,'RS')):
            call('material_connect_nodes',material_path=CITY,from_node=source,from_output_index=0,to_node=node,to_input=pin)
        call('material_connect_nodes',material_path=CITY,from_node=node,from_output_index=0,to_property='world_position_offset')
        after=call('material_get_info',path=CITY);preflight(after)
        assert terminal(after)['from_node']==node
        assert inputs(next(n for n in after['expressions'] if n['id']==node))['Dynamics']['from_node']==DYNAMICS
        # Existing opacity/colour and all other terminal connections stay byte-for-byte equivalent.
        assert [n for n in before['material_outputs'] if norm(n['property'])!='worldpositionoffset']==[
            n for n in after['material_outputs'] if norm(n['property'])!='worldpositionoffset']
        return dict(node=node,new_node=old is None,before=before,after=after)
    except Exception:
        # Restore the existing valid graph if a native schema/connectivity check fails.
        if old is None:
            restore_baked(call,node)
        raise


def selftest():
    from itertools import product
    def add(*vectors):return tuple(sum(v[i] for v in vectors) for i in range(3))
    def mul(v,s):return tuple(x*s for x in v)
    def subtract(a,b):return add(a,mul(b,-1))
    def dot(a,b):return sum(x*y for x,y in zip(a,b))
    centre=(9000.,-250.,1700.);radius=43.
    views=(((1,0,0),(0,-1,0)),((0,1,0),(0,0,1)),((.6,.8,0),(-.48,.36,.8)))
    checks=0
    for right,up in views:
        for q,breath in product((0.,.25,.65,1.),(-.036,0.,.036)):
            coefficient=1+breath*(1-q)-q*.65
            motion=(7*(1-q)+18*q,-3*(1-q)-22*q,(5-centre[2])*q*q)
            vertices=[]
            for x,y in product((-1.,1.),repeat=2):
                baked=(x*radius,-y*radius,0.)
                facing=mul(add(mul(right,x),mul(up,y)),radius)
                dynamics=add(motion,mul(facing,breath*(1-q)-q*.65))
                original=add(centre,baked)
                corrected=add(original,dynamics,facing,mul(baked,-1))
                expected=add(centre,motion,mul(facing,coefficient))
                assert max(abs(a-b) for a,b in zip(corrected,expected))<1e-9
                assert subtract(original,baked)==centre
                vertices.append(corrected);checks+=1
                if right==(1,0,0):assert max(abs(a-b) for a,b in zip(corrected,add(original,dynamics)))<1e-9
            mean=tuple(sum(v[i] for v in vertices)/4 for i in range(3))
            assert max(abs(a-b) for a,b in zip(mean,add(centre,motion)))<1e-9
            assert coefficient>=.35-1e-12
            e1,e2=subtract(vertices[2],vertices[0]),subtract(vertices[1],vertices[0])
            projected_area=abs(dot(e1,right)*dot(e2,up)-dot(e1,up)*dot(e2,right))
            assert abs(projected_area-(2*radius*coefficient)**2)<1e-7
    # At street height, old horizontal quads have zero vertical projected extent;
    # the corrected quad retains a full circular footprint without centre displacement.
    right,up=views[1];e1,e2=(2*radius,0,0),(0,-2*radius,0)
    assert dot(e1,right)*dot(e2,up)-dot(e1,up)*dot(e2,right)==0
    print('City billboard math passed:',checks,'corners; top-down identity, street/tilted footprint, stable centres, breathing and meteor collapse/reform')


def main():
    if sys.argv[1:] == ['--selftest']:return selftest()
    assert sys.argv[1:]==['apply'],'Use apply or --selftest'
    sys.path.insert(0,str(ROOT/'Tools/Unreal'))
    import editor_lock
    import hayba_call as h
    owner=os.environ.get('FOA_AGENT','main-level2-city-facing')
    os.environ['FOA_AGENT']=os.environ['HAYBA_AGENT_ID']=owner
    def call(command,**args):
        r=h.call(command,args,timeout=90);assert r.get('ok'),r
        d=r.get('data',{});assert d.get('ok',True) and not d.get('has_errors'),d
        return d
    editor_lock.acquire(owner,wait_s=5,ttl=180,areas=[CITY])
    try:
        assert not call('editor_get_state')['pie_running']
        source=ROOT/'Content/FoA/Level2/M_SplatCity_Lean.uasset'
        backup=ROOT/'Saved/Backups/level-integration-20261111/CityBillboard'/source.name
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(source,backup)
        result=apply(call)
        try:
            valid=call('material_validate',material_path=CITY);assert not valid.get('problems'),valid
            compiled=call('material_compile',material_path=CITY)
            assert compiled.get('saved') and not compiled.get('errors') and not compiled.get('shader_compile_timed_out'),compiled
        except Exception:
            if result['new_node']:restore_baked(call,result['node'])
            raise
        out=ROOT/'Saved/Integration/city_billboards';out.mkdir(parents=True,exist_ok=True)
        (out/'apply.json').write_text(json.dumps(dict(result,compile=compiled),indent=2))
        print(json.dumps(dict(asset=CITY,node=result['node'],new_node=result['new_node'],compiled=compiled)))
    finally:editor_lock.release(owner)


if __name__=='__main__':main()
