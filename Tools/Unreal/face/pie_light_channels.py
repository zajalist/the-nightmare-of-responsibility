"""PIE component dump (face lane, read-only): the lighting channels of every primitive on the live player pawn and of
every light on the phone(s), to prove the class change reached the spawned pawn.
  FOA_DRIVER=Tools/Unreal/face/pie_light_channels.py bash Tools/Unreal/face/face_burst.sh channels_<tag> dump
Output: Saved/FaceShots/<run>/shots.json (pawn, components, phone_lights)."""
import json
import os
import time
from pathlib import Path

import unreal

RUN = os.environ.get('FOA_RUN', 'channels')
OUT = Path('P:/FoA/Saved/FaceShots') / RUN
OUT.mkdir(parents=True, exist_ok=True)
S = dict(t0=time.time(), h=None)
chans = lambda c: [int(c.get_editor_property('lighting_channels').get_editor_property(f'channel{i}')) for i in range(3)]


def tick(dt):
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    p = unreal.GameplayStatics.get_player_character(w, 0) if w else None
    if not p and time.time() - S['t0'] < 20:
        return
    unreal.unregister_slate_post_tick_callback(S['h'])
    out = dict(pawn=p.get_name() if p else None, components={}, phone_lights={})
    if p:
        for c in p.get_components_by_class(unreal.PrimitiveComponent):
            out['components'][c.get_name()] = chans(c)
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if w else []:
        if 'Phone' in a.get_class().get_name():
            for c in a.get_components_by_class(unreal.LightComponent):
                out['phone_lights'][f'{a.get_name()}.{c.get_name()}'] = chans(c)
    (OUT / 'shots.json').write_text(json.dumps(dict(reason='done', error=None, shots=[], **out), indent=1))
    unreal.log(f'[face] {RUN} dumped')


S['h'] = unreal.register_slate_post_tick_callback(tick)
