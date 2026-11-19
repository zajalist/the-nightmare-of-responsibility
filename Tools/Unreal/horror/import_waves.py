"""Audio lane: import WAVs from P:/FoA-Assets/audio/SFX/<Category>/<Name>.wav into /Game/FoA/Audio/SFX/<Category>/
(and MUS_<Name> from P:/FoA-Assets/audio/music/processed/ into /Game/FoA/Audio/Music/) through Hayba asset_import (staged in %TEMP%/hayba-asset-connectors/horror/waves), skipping assets that exist.
  python Tools/Unreal/horror/import_waves.py SFX_Creaks_Settle_01 SFX_Ambience_RainOnGlass_Loop_01 ...
Then run wave_settings.py in the editor for class, looping and streaming (asset_import leaves them unsaved defaults)."""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h  # noqa: E402

SRC = 'P:/FoA-Assets/audio/SFX'
STAGE = os.path.join(tempfile.gettempdir(), 'hayba-asset-connectors', 'horror', 'waves')


def main(names):
    os.makedirs(STAGE, exist_ok=True)
    for n in names:
        if n.startswith('MUS_'):
            src, game = f'P:/FoA-Assets/audio/music/processed/{n}.wav', '/Game/FoA/Audio/Music'
        else:
            cat = n.split('_')[1]
            src, game = f'{SRC}/{cat}/{n}.wav', f'/Game/FoA/Audio/SFX/{cat}'
        if not os.path.exists(src):
            print('NO SOURCE', src)
            continue
        if os.path.exists(game.replace('/Game/', 'P:/FoA/Content/') + f'/{n}.uasset'):
            print('exists', n)
            continue
        dst = os.path.join(STAGE, n + '.wav')
        shutil.copyfile(src, dst)
        r = h.call('asset_import', {'source_file': dst.replace('\\', '/'), 'destination_path': game,
                                    'asset_type': 'sound_wave'})
        d = r.get('data') or {}
        print(n, d.get('code') or r.get('error'))


if __name__ == '__main__':
    main(sys.argv[1:])
