"""Apply the matched-light approved hair instance; preserve groom/pose contracts."""
import json,sys,os,subprocess,datetime,shutil
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h
root='/Game/FoA/Characters/Teen/Hair';mi=root+'/MI_Teen_Strands'
owner='character_hair_material'
assets=[mi,root+'/GR_Teen_Scalp','/Game/FoA/Characters/Player/BP_FoAPlayer','/Game/FoA/Cinematics/LS_WakeUp']
def call(cmd,**kw):
    r=h.call(cmd,kw,owner=owner);assert r.get('ok'),r;return r.get('data',{})
assert not call('editor_get_state')['pie_running']
token=h.lease_acquire(owner,['asset:'+p for p in assets],ttl_s=90,wait_s=3)
try:
    folder=Path('Saved/Backups/dark_groom')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');folder.mkdir(parents=True)
    for p in assets:
        disk=Path('Content'+p.removeprefix('/Game')+'.uasset')
        if disk.exists():shutil.copy2(disk,folder/disk.name)
    if not Path('Content/FoA/Characters/Teen/Hair/MI_Teen_Strands.uasset').exists():
        call('material_create_instance',parent_material_path=root+'/M_FoA_TeenStrands',package_path=root,name='MI_Teen_Strands')
    for name,value in {'HairColor':[.004,.003,.002,1],'HairRoughness':.85,'HairSpecular':.08}.items():
        call('material_set_param',instance_path=mi,param_name=name,value=value)
    call('asset_save',asset_paths=[mi])
    env=dict(os.environ,FOA_AGENT=owner,FOA_AREAS=','.join('asset:'+p for p in assets))
    subprocess.run([sys.executable,'Tools/Unreal/ue_remote.py','Tools/MPFB/ue_assign_dark_groom.py'],env=env,check=True)
finally:h.release(owner,token)
