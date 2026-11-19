"""Set BP_FoAPlayer's phone-hold class defaults (CDO) and save: FOA_HANDROT='pitch,yaw,roll' and/or
FOA_READ='x,y,z', FOA_LOW='x,y,z', FOA_ELBOW='x,y,z' (camera-space / actor-space offsets, cm).
  $env:FOA_AREAS='Characters'; python Tools/Unreal/ue_remote.py Tools/Unreal/player/set_phone_defaults.py FOA_HANDROT=0,0,0"""
import os
import unreal
bp = unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
cdo = unreal.get_default_object(bp.generated_class())
if os.environ.get('FOA_HANDROT'):
    p, y, r = (float(v) for v in os.environ['FOA_HANDROT'].split(','))
    cdo.set_editor_property('PhoneHandRot', unreal.Rotator(roll=r, pitch=p, yaw=y))
for env, prop in (('FOA_READ', 'PhoneReadOffset'), ('FOA_LOW', 'PhoneLowOffset'), ('FOA_ELBOW', 'PhoneElbowOffset')):
    if os.environ.get(env):
        cdo.set_editor_property(prop, unreal.Vector(*(float(v) for v in os.environ[env].split(','))))
unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
print('PHONE_DEFAULTS', {k: str(cdo.get_editor_property(k)) for k in ('PhoneHandRot', 'PhoneReadOffset', 'PhoneLowOffset', 'PhoneElbowOffset')})
