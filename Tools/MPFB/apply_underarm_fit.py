"""Polo-only validated reimport; protect accepted body/head/manual sleep and backup mesh."""
import sys,os,json,datetime,shutil,hashlib,subprocess
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h
owner='character_underarm';p='/Game/FoA/Characters/Teen/Mesh/SK_Teen_Polo'
variant=os.environ.get('FOA_UNDERARM_VARIANT','weights')
assert variant in ('weights','wedge')
report_root=Path('Saved/Integration/cinematic_audit/underarm_'+variant+'_candidate')
validation=json.loads((report_root/'fbx_validation.json').read_text());assert validation['central_chest_unchanged']
assert not h.call('editor_get_state')['data']['pie_running']
token=h.lease_acquire(owner,['asset:'+p,'asset:/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body_Skeleton'],ttl_s=60,wait_s=3)
protected=['Content/FoA/Characters/Teen/Mesh/SK_Teen_Body.uasset','Content/FoA/Characters/Teen/Mesh/SK_Teen_Head.uasset','Content/FoA/Cinematics/LS_WakeUp_ManualPose.uasset','Content/FoA/Cinematics/WakeUp/AS_FoA_Wake_Lying.uasset','Content/FoA/Cinematics/WakeUp/AS_FoA_Wake_EdgeReach.uasset']
hashes=lambda:{q:hashlib.sha256(Path(q).read_bytes()).hexdigest() for q in protected}
try:
    before=hashes();backup=Path('Saved/Backups/polo_underarm')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
    shutil.copy2('Content/FoA/Characters/Teen/Mesh/SK_Teen_Polo.uasset',backup/'SK_Teen_Polo.uasset')
    env=dict(os.environ,FOA_AGENT=owner,FOA_AREAS='asset:'+p+',asset:/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body_Skeleton')
    source='P:/FoA-Assets/character/mpfb/export/teen_underarm'+('_wedge' if variant=='wedge' else '')+'/SK_Teen_Polo.fbx'
    subprocess.run([sys.executable,'Tools/Unreal/ue_remote.py','Tools/MPFB/ue_reimport_cm.py','FOA_PIECE=Polo','FOA_SOURCE='+source,'FOA_PRESERVE_REFERENCE=1'],env=env,check=True)
    assert hashes()==before,'Protected asset changed'
    receipt=json.loads(Path('Saved/CharacterShots/mpfb/SK_Teen_Polo_cm.json').read_text());assert receipt['reference_delta']==0,receipt
    (report_root/'reimport.json').write_text(json.dumps(dict(backup=str(backup),protected=before,imported=receipt),indent=2))
finally:h.release(owner,token)
