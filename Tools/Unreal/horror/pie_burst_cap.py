"""Audio lane: minimal PIE test of the sand-burst cap (SCON_SandBurst: max 2, StopOldest, 0.15 s retrigger guard).
Fires a sound 10 times in 1 s near the player, three ways, 3 s apart, logging each fire with its epoch:
  A  S_Sand_Burst (MetaSound preset) with PlaySoundAtLocation
  B  SFX_Sand_Burst_02 (raw SoundWave) with PlaySoundAtLocation
  C  S_Sand_Burst with PlaySound2D
Pair it with sample_audio.sh (audio_active_sounds on the PIE world, new instance ids) to count audible copies per window.
  python Tools/Unreal/integration/run_read.py Tools/Unreal/horror/pie_burst_cap.py FOA_RUN=<name>  (inside a PIE burst)
Writes Saved/HorrorShots/<name>_timeline.json. Reads PIE actors; plays sounds only."""
import json
import os
import time

import unreal

RUN = os.environ.get('FOA_RUN', 'cap')
OUT = f'P:/FoA/Saved/HorrorShots/{RUN}_timeline.json'
PRESET = '/Game/FoA/Audio/MetaSounds/Sand/S_Sand_Burst'
WAVE = '/Game/FoA/Audio/SFX/Sand/SFX_Sand_Burst_02'
PLAN = [('A', PRESET, '3d', 1.0), ('B', WAVE, '3d', 4.5), ('C', PRESET, '2d', 8.0)]  # (label, sound, mode, start s)
S = {'t0': time.time(), 'fired': {}, 'log': [], 'h': None, 'done': False, 'dumped': set()}


def log(kind, **kw):
    e = dict(t=round(time.time() - S['t0'], 3), epoch=round(time.time(), 3), kind=kind, **kw)
    S['log'].append(e)


def finish():
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(S['log'], fh, indent=1)


def tick(_dt):
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not w:
        log('pie_gone')
        return finish()
    el = time.time() - S['t0']
    pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
    at = pawn.get_actor_location() + unreal.Vector(120, 0, 0) if pawn else unreal.Vector(0, 0, 100)
    for label, path, mode, start in PLAN:
        n = S['fired'].get(label, 0)
        if n < 10 and el >= start + n * 0.1:  # ten fires, 0.1 s apart (half fall inside the 0.15 s guard)
            snd = unreal.load_asset(path)
            if mode == '3d':
                unreal.GameplayStatics.play_sound_at_location(w, snd, at, unreal.Rotator(0, 0, 0))
            else:
                unreal.GameplayStatics.play_sound2d(w, snd)
            S['fired'][label] = n + 1
            log('fire', label=label, n=n + 1)
    for label, path, mode, start in PLAN:  # the audio device's own view, 0.3 s and 1.0 s after the tenth fire
        for lag in (0.3, 1.0):
            key = f'{label}{lag}'
            if el >= start + 0.9 + lag and key not in S['dumped']:
                S['dumped'].add(key)
                unreal.log(f'[horror-cap] dump {key}')
                unreal.SystemLibrary.execute_console_command(w, 'au.DumpActiveSounds')
                log('dump', key=key)
    if el > 12.0:
        log('end')
        finish()


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('burst cap test scheduled ->', OUT)
