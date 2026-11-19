"""Restore the InteractionContact notify on the five interaction montages (main's grant 2026-11-09, story lane, this fix
only). BP_Interactable commits a montage row only at OnPendingContact, which only AN_FoA_InteractionContact calls; a
montage rebuild (build_montages.py clears every notify track) dropped it, so every montage row animated and cancelled.
Runs the gameplay lane's own marker phase (contact_notify_assets.py: one wanted marker per montage, segments and length
unchanged, adds the track only when missing), saves, then reads the events back. The Audio track is not touched.
Backs the five .uasset files up first.   python Tools/Unreal/flow/apply_contact_markers.py"""
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h  # noqa: E402

OWNER = 'story'
M = '/Game/FoA/Characters/Player/Montages/'
NAMES = ['AM_FoA_PickUp_Floor', 'AM_FoA_PickUp_Table', 'AM_FoA_OpenDrawer', 'AM_FoA_TryLockedHandle', 'AM_FoA_KneelScrewdriver']
MONTAGES = [M + n for n in NAMES]
BACKUP = Path('P:/FoA/Saved/StoryShots/montage_backup')
READ = Path('P:/FoA/Saved/StoryShots/montage_notifies.json')
os.environ['HAYBA_AGENT_ID'] = OWNER


def call(name, token, **args):
    r = h.call(name, args, owner=OWNER, lease=token, timeout=60)
    assert r.get('ok'), r
    d = r.get('data', {})
    assert d.get('ok', True) and not d.get('failed'), d
    return d


assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
BACKUP.mkdir(parents=True, exist_ok=True)
for n in NAMES:
    shutil.copy2(f'P:/FoA/Content/FoA/Characters/Player/Montages/{n}.uasset', BACKUP / f'{n}.uasset')
markers = Path('P:/FoA/Saved/Integration/contact_notify_markers.json')
if markers.exists():
    shutil.copy2(markers, BACKUP / 'contact_notify_markers_before.json')
token = h.lease_acquire(OWNER, ['asset:' + p for p in MONTAGES], ttl_s=120, wait_s=180, label='story contact markers')
os.environ['FOA_LEASE'] = token
try:
    out = call('python_exec_file', token, path='P:/FoA/Tools/Unreal/gameplay/contact_notify_assets.py',
               env={'FOA_CONTACT_PHASE': 'markers'}, resources=['asset:' + p for p in MONTAGES])
    print('markers', str(out.get('output', ''))[:600])
    # asset_save skips them as 'not dirty' (notify edits do not dirty the package): save them unconditionally
    call('python_exec_file', token, path='P:/FoA/Tools/Unreal/flow/save_contact_montages.py', env={},
         resources=['asset:' + p for p in MONTAGES])
    call('python_exec_file', token, path='P:/FoA/Tools/Unreal/flow/read_montage_notifies.py', env={}, resources=[])
    events = json.loads(READ.read_text())
    contact = {n: [e for e in events[n]['events'] if e[0] == 'AN_FoA_InteractionContact_C'] for n in NAMES}
    for n in NAMES:
        assert len(contact[n]) == 1, (n, contact[n])
    print('contact per montage', {n: contact[n][0][2] for n in NAMES})
    for n in NAMES:  # the saved package on disk must carry the notify class
        assert b'AN_FoA_InteractionContact' in Path(f'P:/FoA/Content/FoA/Characters/Player/Montages/{n}.uasset').read_bytes(), n
    print('on disk: InteractionContact in all five')
finally:
    h.release(OWNER, token)
    os.environ.pop('FOA_LEASE', None)
