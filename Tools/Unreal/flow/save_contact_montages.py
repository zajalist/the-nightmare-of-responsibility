"""Story lane: force-save the five interaction montages (AnimationLibrary notify edits do not mark the package dirty,
so Hayba asset_save skips them as 'not dirty'). Run under their asset leases by apply_contact_markers.py."""
import unreal

M = '/Game/FoA/Characters/Player/Montages/'
for n in ('AM_FoA_PickUp_Floor', 'AM_FoA_PickUp_Table', 'AM_FoA_OpenDrawer', 'AM_FoA_TryLockedHandle', 'AM_FoA_KneelScrewdriver'):
    m = unreal.load_asset(M + n)
    assert any(e.get_editor_property('notify') and e.get_editor_property('notify').get_class().get_name() == 'AN_FoA_InteractionContact_C'
               for e in unreal.AnimationLibrary.get_animation_notify_events(m)), n
    assert unreal.EditorAssetLibrary.save_asset(M + n, only_if_is_dirty=False), n
print('montages saved with InteractionContact')
