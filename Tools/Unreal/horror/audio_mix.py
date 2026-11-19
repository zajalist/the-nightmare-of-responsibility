"""Audio lane mix architecture (idempotent, edits in place):
  - SoundClasses under SC_Master: SC_SFX, SC_Ambience, SC_UI (existing), SC_Dialogue and SC_Music (new)
  - Submixes: SM_Bedroom (small-room reverb, dry 1.0 / wet 0.22) for SFX, Ambience and Dialogue; SM_Music for the
    user's tracks (dry, no reverb)
  - SMX_StoryDuck: SFX to 50%, Ambience to 35% (0.3 s in, 1.5 s out). Stingers and story moments push and pop it.
  - SMX_MusicUnderDialogue: passive on SC_Dialogue, SC_Music to 45% while any dialogue plays
  - ATT_SFX_Room: occlusion on (the hallway and the outside sit behind walls and the door)
  - Long loops stream (load on demand) instead of sitting in memory
  $env:FOA_AREAS='Audio'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/audio_mix.py"""
import unreal

EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
MIX = '/Game/FoA/Audio/Mix'


def get_or_create(name, cls, factory):
    a = unreal.load_asset(f'{MIX}/{name}')
    return a if a else AT.create_asset(name, MIX, cls, factory)


def save(a):
    EAL.save_asset(a.get_path_name().split('.')[0], only_if_is_dirty=False)


def main():
    master = unreal.load_asset(f'{MIX}/SC_Master')
    # submixes
    fx = unreal.SoundSubmixEffectFactory()
    fx.set_editor_property('sound_effect_submix_preset_class', unreal.SubmixEffectReverbPreset)
    rvb = get_or_create('RVB_Bedroom', unreal.SubmixEffectReverbPreset, fx)
    s = rvb.get_editor_property('settings')
    for k, v in (('density', 0.6), ('diffusion', 0.7), ('decay_time', 0.55), ('late_delay', 0.01), ('reflections_delay', 0.004),
                 ('late_gain', 0.0), ('gain', 0.0), ('reflections_gain', 0.0), ('air_absorption_gain_hf', 0.9),
                 ('gain_hf', 0.85), ('wet_level', 0.22), ('dry_level', 1.0)):
        try:
            s.set_editor_property(k, v)
        except Exception as e:  # field names drift between engine versions; report rather than fail the whole run
            print('reverb field', k, e)
    rvb.set_editor_property('settings', s)
    save(rvb)
    room = get_or_create('SM_Bedroom', unreal.SoundSubmix, unreal.SoundSubmixFactory())
    room.set_editor_property('submix_effect_chain', [rvb])
    save(room)
    music = get_or_create('SM_Music', unreal.SoundSubmix, unreal.SoundSubmixFactory())
    save(music)
    # classes
    for name, sub in (('SC_SFX', room), ('SC_Ambience', room), ('SC_Dialogue', room), ('SC_Music', music), ('SC_UI', None)):
        sc = get_or_create(name, unreal.SoundClass, unreal.SoundClassFactory())
        sc.set_editor_property('parent_class', master)
        if sub:
            props = sc.get_editor_property('properties')
            props.set_editor_property('default_submix', sub)
            sc.set_editor_property('properties', props)
        save(sc)
    kids = [unreal.load_asset(f'{MIX}/{n}') for n in ('SC_SFX', 'SC_Ambience', 'SC_UI', 'SC_Dialogue', 'SC_Music')]
    master.set_editor_property('child_classes', kids)
    save(master)
    # ducking for stingers and story moments
    duck = get_or_create('SMX_StoryDuck', unreal.SoundMix, unreal.SoundMixFactory())
    adj = []
    for cls, vol in (('SC_SFX', 0.5), ('SC_Ambience', 0.35)):
        a = unreal.SoundClassAdjuster()
        a.set_editor_property('sound_class_object', unreal.load_asset(f'{MIX}/{cls}'))
        a.set_editor_property('volume_adjuster', vol)
        a.set_editor_property('apply_to_children', True)
        adj.append(a)
    duck.set_editor_property('sound_class_effects', adj)
    duck.set_editor_property('fade_in_time', 0.3)
    duck.set_editor_property('fade_out_time', 1.5)
    duck.set_editor_property('duration', -1.0)
    save(duck)
    # music under voice: any SC_Dialogue sound pulls SC_Music to 45 % while it plays (a passive modifier on the class,
    # so no Blueprint has to push or pop it; the battle's lines will duck the fight music once they are voiced)
    vo = get_or_create('SMX_MusicUnderDialogue', unreal.SoundMix, unreal.SoundMixFactory())
    a = unreal.SoundClassAdjuster()
    a.set_editor_property('sound_class_object', unreal.load_asset(f'{MIX}/SC_Music'))
    a.set_editor_property('volume_adjuster', 0.45)
    vo.set_editor_property('sound_class_effects', [a])
    vo.set_editor_property('fade_in_time', 0.25)
    vo.set_editor_property('fade_out_time', 1.0)
    save(vo)
    dlg = unreal.load_asset(f'{MIX}/SC_Dialogue')
    pm = unreal.PassiveSoundMixModifier()
    pm.set_editor_property('sound_mix', vo)
    pm.set_editor_property('min_volume_threshold', 0.0)
    pm.set_editor_property('max_volume_threshold', 10.0)
    dlg.set_editor_property('passive_sound_mix_modifiers', [pm])
    save(dlg)
    # concurrency caps ("SFX go wild" without pile-ups): a group limit per family, the oldest voice gives way
    # SCON_SandBurst: QA B3 heard five bursts and five shifts land together; a cluster must read as one big burst
    # SCON_Creaks: QA B3 heard three settling creaks at once; one at a time, 2 s apart, and the new one waits (no cut tails)
    for name, count, retrigger in (('SCON_Footsteps', 4, 0.0), ('SCON_OneShot', 8, 0.0), ('SCON_Story', 2, 0.0),
                                   ('SCON_Loop', 6, 0.0), ('SCON_SandBurst', 2, 0.15), ('SCON_Creaks', 1, 2.0)):
        con = get_or_create(name, unreal.SoundConcurrency, unreal.SoundConcurrencyFactory())
        cs = con.get_editor_property('concurrency')
        cs.set_editor_property('max_count', count)
        # UE 5.8's factory turns "Enable MaxCount Platform Scaling" on with Platform Max Count 16, and then MaxCount is
        # ignored (FSoundConcurrencySettings::GetMaxCount): set the platform default too, and turn scaling off
        pm = cs.get_editor_property('platform_max_count')
        pm.set_editor_property('default', count)
        cs.set_editor_property('platform_max_count', pm)
        cs.set_editor_property('enable_max_count_platform_scaling', False)
        cs.set_editor_property('retrigger_time', retrigger)
        cs.set_editor_property('limit_to_owner', False)
        cs.set_editor_property('resolution_rule', unreal.MaxConcurrentResolutionRule.PREVENT_NEW if name == 'SCON_Creaks'
                               else unreal.MaxConcurrentResolutionRule.STOP_OLDEST)
        con.set_editor_property('concurrency', cs)
        save(con)
    # occlusion on the room attenuation
    att = unreal.load_asset(f'{MIX}/ATT_SFX_Room')
    st = att.get_editor_property('attenuation')
    for k, v in (('enable_occlusion', True), ('occlusion_low_pass_filter_frequency', 2500.0), ('occlusion_volume_attenuation', 0.6),
                 ('occlusion_interpolation_time', 0.3), ('use_complex_collision_for_occlusion', False)):
        try:
            st.set_editor_property(k, v)
        except Exception as e:
            print('attenuation field', k, e)
    att.set_editor_property('attenuation', st)
    save(att)
    # stream the long loops
    n = 0
    for p in EAL.list_assets('/Game/FoA/Audio/SFX', recursive=True, include_folder=False):
        if '_Loop_' not in p:
            continue
        w = unreal.load_asset(p)
        if not isinstance(w, unreal.SoundWave) or w.get_editor_property('duration') < 8:
            continue
        w.set_editor_property('loading_behavior', unreal.SoundWaveLoadingBehavior.LOAD_ON_DEMAND)
        save(w)
        n += 1
    for name in ('SCON_Footsteps', 'SCON_OneShot', 'SCON_Story', 'SCON_Loop', 'SCON_SandBurst', 'SCON_Creaks'):  # read back
        c = unreal.load_asset(f'{MIX}/{name}').get_editor_property('concurrency')
        print(name, 'effective max', c.get_editor_property('platform_max_count').get_editor_property('default')
              if c.get_editor_property('enable_max_count_platform_scaling') else c.get_editor_property('max_count'),
              'scaling', c.get_editor_property('enable_max_count_platform_scaling'),
              'rule', c.get_editor_property('resolution_rule'), 'retrigger', c.get_editor_property('retrigger_time'))
    print('mix built: classes', [k.get_name() for k in kids], 'submixes SM_Bedroom SM_Music, duck SMX_StoryDuck, streamed loops', n)


main()
