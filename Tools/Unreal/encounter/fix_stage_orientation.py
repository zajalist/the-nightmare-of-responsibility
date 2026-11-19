"""Repair the saved encounter's upside-down root without rebuilding or moving user furniture."""
import json
import sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h

ROOT='/Game/FoA/Maps/L_Tutorial_Bedroom.L_Tutorial_Bedroom:PersistentLevel.BP_Encounter_C_0.DefaultSceneRoot'

def main():
    owner=h.agent_id() or 'main:presentation'
    assert not h.call('editor_get_state')['data']['pie_running'], 'User PIE active'
    lease=h.lease_acquire(owner,['world:/Game/FoA/Maps/L_Tutorial_Bedroom'],ttl_s=30,wait_s=3)
    def c(cmd,**params):
        r=h.call(cmd,params,owner=owner,lease=lease); assert r.get('ok'),r
        d=r.get('data',{});assert d.get('ok',True),d
        return d
    try:
        assert not c('editor_get_state')['pie_running']
        before=c('object_get_property',path=ROOT,names=['RelativeLocation','RelativeRotation'])
        c('object_set_property',path=ROOT,properties={'RelativeRotation':'(Pitch=0,Yaw=180,Roll=0)'})
        after=c('object_get_property',path=ROOT,names=['RelativeLocation','RelativeRotation'])
        assert before['properties']['RelativeLocation']==after['properties']['RelativeLocation']
        assert after['properties']['RelativeRotation']=='(Pitch=0.000000,Yaw=180.000000,Roll=0.000000)',after
        c('level_save')
        Path('Saved/PresentationReview/stage_orientation_fixed.json').write_text(json.dumps({'before':before,'after':after},indent=1))
        print('Saved encounter upright at original location; runtime staging still requires review')
    finally:h.release(owner,lease)

if __name__=='__main__':main()
