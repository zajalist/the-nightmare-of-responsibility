"""Audio lane: MetaSound presets of the shared random one-shot templates, created or updated in place.
  $env:FOA_AREAS='Audio'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/audio_presets.py FOA_ONLY=S_Creaks_Settle,...
Each preset only sets the template's `Waves` list (and `Loop` for loops); the template does the randomisation: a random
take that never repeats the previous one, about +-1 semitone pitch and 0.85-1.0 volume (MANIFEST.md). The preset also
gets its SoundClass and attenuation. The table lives in audio_table.py so the wiring lists and this builder share it."""
import os
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib  # noqa: E402

import audio_table as T  # noqa: E402

importlib.reload(T)  # the editor's interpreter keeps modules between runs

EAL = unreal.EditorAssetLibrary
MS = '/Game/FoA/Audio/MetaSounds'
WAVES = '/Game/FoA/Audio/SFX'


def literal_objects(objs):
    r = unreal.get_engine_subsystem(unreal.MetaSoundBuilderSubsystem).create_object_array_meta_sound_literal(objs)
    return r[0] if isinstance(r, tuple) else r


def literal_bool(v):
    r = unreal.get_engine_subsystem(unreal.MetaSoundBuilderSubsystem).create_bool_meta_sound_literal(v)
    return r[0] if isinstance(r, tuple) else r


def build(name, spec):
    cat = name.split('_')[1]
    path = f'{MS}/{cat}/{name}'
    waves = []
    for w in spec['waves']:
        wcat = w.split('_')[1]
        a = unreal.load_asset(f'{WAVES}/{wcat}/{w}')
        if not a:
            print('MISSING WAVE', w)
            continue
        waves.append(a)
    if not waves:
        print('SKIP (no waves)', name)
        return
    stereo = any(w.get_editor_property('num_channels') > 1 for w in waves)
    template = unreal.load_asset(f"{MS}/S_RandomOneShot_{'Stereo' if stereo else 'Mono'}")
    ed = unreal.get_editor_subsystem(unreal.MetaSoundEditorSubsystem)
    existing = unreal.load_asset(path)
    if existing:
        r = ed.find_or_begin_building(existing)
        builder = r[0] if isinstance(r, tuple) else r
    else:
        r = unreal.get_engine_subsystem(unreal.MetaSoundBuilderSubsystem).create_source_preset_builder(name, template)
        builder = r[0] if isinstance(r, tuple) else r
    builder.set_graph_input_default('Waves', literal_objects(waves))
    if '_Loop_' in name:
        builder.set_graph_input_default('Loop', literal_bool(True))
    if not existing:
        ed.build_to_asset(builder, 'horror', name, f'{MS}/{cat}', None)
    asset = unreal.load_asset(path)
    asset.set_editor_property('sound_class_object', unreal.load_asset(T.CLASS[spec.get('cls', 'SFX')]))
    fam = 'Loop' if '_Loop_' in name else {'Footsteps': 'Footsteps', 'Foley': 'Footsteps', 'Creaks': 'Footsteps',
                                             'Story': 'Story', 'Dream': 'Story'}.get(cat, 'OneShot')
    fam = {'S_Sand_Burst': 'SandBurst', 'S_Sand_Shift': 'SandBurst', 'S_Creaks_Settle': 'Creaks'}.get(name, fam)
    asset.set_editor_property('concurrency_set', [unreal.load_asset(f'/Game/FoA/Audio/Mix/SCON_{fam}')])
    att = spec.get('att')
    asset.set_editor_property('attenuation_settings', unreal.load_asset(T.ATT[att]) if att else None)
    EAL.save_asset(path, only_if_is_dirty=False)
    print('preset', path, len(waves), 'waves', 'stereo' if stereo else 'mono', 'loop' if '_Loop_' in name else '',
          spec.get('cls', 'SFX'), att or '2D')


def main():
    only = [s for s in os.environ.get('FOA_ONLY', '').split(',') if s]
    for name, spec in T.PRESETS.items():
        if only and name not in only:
            continue
        build(name, spec)


main()
