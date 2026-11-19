"""The pale skullcap on the player's crown (fight camera, all presets) is the groom's own shading, not a scalp or LOD gap:
the crown strands lie flat toward the window light, and even HairColor 0.0007 transmits (TT) and 0.03 specular reflects
(R) a near-white cap under that light. Diagnosis runs 11-18: Saved/Perf/runs/*atmo_hairprobe2..7 (Face hidden keeps
the cap; HairColor 0 + low specular removes it; specular 0, roughness 1, voxelization off, sky off do not).
Fix: MI_Teen_Strands HairColor 0 (black, no transmission) and HairSpecular 0.06 (0.03 read flat in close-ups); zero GPU cost, the style (short01)
and the groom are untouched.
  python Tools/Unreal/hair_crown_fix.py          # apply
  python Tools/Unreal/hair_crown_fix.py revert   # back to HairColor (0.014, 0.011, 0.008), HairSpecular 0.16"""
import datetime
import shutil
import sys
from pathlib import Path

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h  # noqa: E402

MI = '/Game/FoA/Characters/Teen/Hair/MI_Teen_Strands'
OWNER = 'atmosphere'
VALUES = {'apply': {'HairColor': [0.0, 0.0, 0.0, 1.0], 'HairSpecular': 0.06},
          'revert': {'HairColor': [0.014, 0.011, 0.008, 1.0], 'HairSpecular': 0.16}}[sys.argv[1] if len(sys.argv) > 1 else 'apply']


def call(cmd, **kw):
    r = h.call(cmd, kw, owner=OWNER)
    assert r.get('ok'), (cmd, r)
    return r.get('data', {})


token = h.lease_acquire(OWNER, ['asset:' + MI], ttl_s=90, wait_s=240)
try:
    disk = Path('P:/FoA/Content/FoA/Characters/Teen/Hair/MI_Teen_Strands.uasset')
    backup = Path('P:/FoA/Saved/Backups/hair_crown') / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    shutil.copy2(disk, backup / disk.name)
    for name, value in VALUES.items():
        call('material_set_param', instance_path=MI, param_name=name, value=value)
    call('asset_save', asset_paths=[MI])
    print('saved', MI, VALUES, 'backup', backup, 'mtime', datetime.datetime.fromtimestamp(disk.stat().st_mtime))
finally:
    h.release(OWNER, token)
