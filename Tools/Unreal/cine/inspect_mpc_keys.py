"""Read-only: key times of LS_WakeUp's MPC parameter tracks in display and tick units."""
import unreal

seq = unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp')
for t in seq.get_tracks():
    if 'Parameter' not in t.get_class().get_name():
        continue
    for s in t.get_sections():
        print('SEC', t.get_display_name(), s.get_class().get_name(), s.get_start_frame(), s.get_end_frame())
        for c in s.get_all_channels():
            ks = c.get_keys()
            print(' ', c.channel_name, c.get_class().get_name(),
                  [(k.get_time(unreal.MovieSceneTimeUnit.DISPLAY_RATE).frame_number.value,
                    k.get_time(unreal.MovieSceneTimeUnit.TICK_RESOLUTION).frame_number.value, round(k.get_value(), 3)) for k in ks])
