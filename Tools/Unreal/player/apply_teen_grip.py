"""Apply the measured grip transform through Hayba and verify its save."""
import json,sys
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
d=json.load(open('P:/FoA/Saved/AnimShots/teen_grip_calibration.json'))
v='(Rotation=(X=%s,Y=%s,Z=%s,W=%s),Translation=(X=%s,Y=%s,Z=%s),Scale3D=(X=%s,Y=%s,Z=%s))'%tuple(d['rotation']+d['location']+d['scale'])
p='/Game/FoA/Characters/Player/BP_FoAPlayer'
t=h.lease_acquire('anim',['asset:/Game/FoA/Characters/Player'],ttl_s=30)
try:
    r=h.call('object_set_property',dict(path=p+'.Default__BP_FoAPlayer_C',properties=dict(ToolGripOffset=v)),owner='anim')
    assert r.get('ok'),r
    r=h.call('asset_save',dict(asset_paths=[p]),owner='anim');assert r.get('data',{}).get('verified'),r
    print('Applied measured Teen grip',d)
finally:h.release('anim',t)
