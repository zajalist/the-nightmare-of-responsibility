"""Evaluate unbound transient rigs only. User sequence, channels and live hierarchy stay untouched."""
import unreal,json,re
from pathlib import Path
seq=unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence();assert seq.get_name()=='LS_WakeUp_ManualPose'
live=unreal.ControlRigSequencerLibrary.get_control_rigs(seq)[0].control_rig;lh=live.get_hierarchy()
bp=unreal.load_asset('/Game/Characters/Mannequins/Rigs/CR_Mannequin_Body')
def values(h):return {str(k.name):h.get_control_value(k).export_text() for k in h.get_controls()}
before=values(lh)
def tf(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
def snapshot(h):
    return {str(k.name):tf(h.get_global_transform(k)) for k in h.get_all_keys() if (k.type==unreal.RigElementType.BONE and any(x in str(k.name) for x in ('hand','thumb','index','middle','ring','pinky','pelvis'))) or str(k.name) in ('fingers_l_space','fingers_r_space','hips_ctrl')}
result={}
for case in ('baseline','hips_translate','hips_rotate','index_rotate','neutral','relaxed'):
    r=bp.create_control_rig();assert r!=live
    r.request_init();r.execute('Forwards Solve')
    h=r.get_hierarchy()
    if case!='neutral':h.copy_hierarchy(lh)
    for k in h.get_controls():
        if 'Auto Interpolate' in str(k.name):h.set_control_value(k,unreal.RigHierarchy.make_control_value_from_bool(False))
    assert r.execute('Forwards Solve')
    if case=='relaxed':
        curls={'index':(10,20,8),'middle':(15,25,10),'ring':(18,28,12),'pinky':(20,30,15),'thumb':(6,8,5)}
        for key in h.get_controls():
            hit=re.fullmatch(r'(thumb|index|middle|ring|pinky)_(metacarpal|0[123]|curl)_([lr])_ctrl',str(key.name))
            if not hit:continue
            f,j,s=hit.groups();deg=curls[f][int(j)-1] if j.startswith('0') else 0
            v=unreal.EulerTransform(rotation=unreal.Rotator(yaw=-deg))
            h.set_control_value(key,unreal.RigHierarchy.make_control_value_from_euler_transform(v))
        assert r.execute('Forwards Solve')
    elif case not in ('baseline','neutral'):
        key=unreal.RigElementKey(name='index_01_l_ctrl' if case=='index_rotate' else 'hips_ctrl',type=unreal.RigElementType.CONTROL)
        tr=h.get_local_transform(key)
        if case=='hips_translate':tr.translation=tr.translation+unreal.Vector(10,0,0)
        else:tr.rotation=unreal.MathLibrary.multiply_quat_quat(tr.rotation,unreal.Rotator(roll=20 if case=='index_rotate' else 15).quaternion())
        h.set_local_transform(key,tr,False,True)
        assert r.execute('Forwards Solve')
    result[case]={'rig':r.get_path_name(),'pose':snapshot(h),'values':values(h),'local_bones':{str(k.name):tf(h.get_local_transform(k)) for k in h.get_bones()}}
assert before==values(lh),'The live rig changed during isolated proof'
result['live_untouched']=True
Path('P:/FoA/Saved/Integration/finger_transient_test.json').write_text(json.dumps(result,indent=1));print('FINGER_TRANSIENT_TEST',list(result))
