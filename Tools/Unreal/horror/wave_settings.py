"""Audio lane: SoundWave settings for every wave under /Game/FoA/Audio/SFX (idempotent, saves only what changes):
  - *_Loop_* waves loop; loops of 8 s or more stream (load on demand) with compression quality 40
  - SoundClass by category: Ambience -> SC_Ambience, UI -> SC_UI, UI_FrontEnd left alone (the UI lane's presets set it),
    everything else -> SC_SFX
  $env:FOA_AREAS='Audio'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/wave_settings.py"""
import unreal

EAL = unreal.EditorAssetLibrary
MIX = '/Game/FoA/Audio/Mix/'


def main():
    cls = {k: unreal.load_asset(MIX + 'SC_' + k) for k in ('SFX', 'Ambience', 'UI')}
    con = {k: unreal.load_asset(MIX + 'SCON_' + k) for k in ('Footsteps', 'OneShot', 'Story', 'Loop', 'SandBurst')}
    changed = 0
    for p in EAL.list_assets('/Game/FoA/Audio/SFX', recursive=True, include_folder=False):
        cat = p.split('/')[5]
        if cat == 'UI_FrontEnd':
            continue
        w = unreal.load_asset(p)
        if not isinstance(w, unreal.SoundWave):
            continue
        want = {'sound_class_object': cls['Ambience' if cat == 'Ambience' else 'UI' if cat == 'UI' else 'SFX']}
        # direct wave plays (other lanes' PlaySound or sequencer tracks on a raw SoundWave) still get a concurrency cap;
        # no attenuation on the waves themselves: LS_WakeUp's audio track plays some of them unattached
        fam = 'Loop' if '_Loop_' in p else {'Footsteps': 'Footsteps', 'Foley': 'Footsteps', 'Creaks': 'Footsteps',
                                            'Story': 'Story', 'Dream': 'Story', 'Horror': 'Story'}.get(cat, 'OneShot')
        if '_Sand_Burst_' in p or '_Sand_Shift_' in p:
            fam = 'SandBurst'
        want['concurrency_set'] = [con[fam]]
        if '_Loop_' in p:
            want['looping'] = True
            if w.get_editor_property('duration') >= 8:
                want['loading_behavior'] = unreal.SoundWaveLoadingBehavior.LOAD_ON_DEMAND
                want['compression_quality'] = 40
        dirty = False
        for k, v in want.items():
            cur = w.get_editor_property(k)
            if (list(cur) if k == 'concurrency_set' else cur) != v:
                w.set_editor_property(k, v)
                dirty = True
        if dirty:
            EAL.save_asset(p.split('.')[0], only_if_is_dirty=False)
            changed += 1
    EAL.save_directory('/Game/FoA/Audio/SFX', only_if_is_dirty=True, recursive=True)  # fresh Hayba imports are unsaved
    # music (make_music.py): SC_Music (routes to the dry SM_Music), each _Loop file is exactly one loop, all streamed
    music = 0
    if EAL.does_directory_exist('/Game/FoA/Audio/Music'):
        for p in EAL.list_assets('/Game/FoA/Audio/Music', recursive=False, include_folder=False):
            w = unreal.load_asset(p)
            if not isinstance(w, unreal.SoundWave):
                continue
            for k, v in (('sound_class_object', unreal.load_asset(MIX + 'SC_Music')), ('looping', w.get_name().endswith('_Loop')),
                         ('loading_behavior', unreal.SoundWaveLoadingBehavior.LOAD_ON_DEMAND)):
                w.set_editor_property(k, v)
            EAL.save_asset(p.split('.')[0], only_if_is_dirty=False)
            music += 1
    print('wave settings changed', changed, 'music', music)


main()
