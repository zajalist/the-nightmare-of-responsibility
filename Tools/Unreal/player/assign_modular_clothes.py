"""Assign fitted individual garments and their original UV atlas, retaining the existing MH leader chain."""
import json
from pathlib import Path
import sys
sys.path.insert(0,"P:/FoA/Tools/Unreal")
import hayba_call as hc

P="/Game/FoA/Characters/Player/BP_FoAPlayer"
FOLDER="/Game/FoA/Characters/Player/Clothing"
OWNER="codex-character-modular"
TOKEN=None
def call(name,**params):
    result=hc.call(name,params,owner=OWNER,lease=TOKEN)
    assert result.get('ok'),result
    data=result.get('data',{});assert data.get('ok',True),data
    return data
def props(path,names):return call('object_get_property',path=path,names=names)['properties']
def main():
    global TOKEN
    assert not call('editor_get_state')['pie_running']
    TOKEN=hc.lease_acquire(OWNER,['asset:'+P,'asset:'+FOLDER],ttl_s=120,wait_s=20)
    try:
        before=props(P+'.BP_FoAPlayer_C:Body_GEN_VARIABLE',['SkeletalMeshAsset','AnimClass'])
        report=json.loads(Path('P:/FoA/Saved/CharacterShots/modular/staged.json').read_text())
        assigned={}
        for garment in ('Shirt','Trousers','Tie','Socks'):
            path=FOLDER+'/SK_FoA_'+garment
            materials=[]
            for name in report[garment]['material_names']:
                instance=('MI_Socks_Dark' if garment=='Socks' else 'MI_Suit_Cloth' if name=='uniform_1001' else
                          'MI_Suit_ButtonGreen' if name in ('Button_1062-Button','blinn6SG') else 'MI_Suit_ButtonDark')
                materials.append({'MaterialInterface':FOLDER+'/'+instance,
                                  'MaterialSlotName':name,'ImportedMaterialSlotName':name})
            assert materials
            call('object_set_property',path=path,properties={'Materials':materials})
            actual=props(path,['Materials','Skeleton'])
            assert 'metahuman_base_skel' in actual['Skeleton']
            assert ('MI_Socks_Dark' if garment=='Socks' else 'MI_Suit_Cloth') in actual['Materials']
            call('asset_save',asset_paths=[path])
            component=P+'.BP_FoAPlayer_C:'+garment+'_GEN_VARIABLE'
            call('object_set_property',path=component,properties={'SkeletalMeshAsset':path,'bVisible':False})
            assigned[garment]=props(component,['SkeletalMeshAsset'])['SkeletalMeshAsset']
            assert path in assigned[garment]
        compiled=call('blueprint_compile',path=P)
        assert compiled['error_count']==0 and compiled['warning_count']==0,compiled
        assert props(P+'.BP_FoAPlayer_C:Body_GEN_VARIABLE',['SkeletalMeshAsset','AnimClass'])==before
        call('asset_save',asset_paths=[P])
        Path('P:/FoA/Saved/CharacterShots/modular_applied.json').write_text(json.dumps(
            {'assigned':assigned,'body_preserved':before,'compile':compiled,'coverage_runtime_pending':True},indent=2))
        print('PASS four separate fitted garments assigned with reference atlas/normal and original MH body/ABP preserved')
    finally:hc.release(OWNER,TOKEN)
if __name__=='__main__':main()
