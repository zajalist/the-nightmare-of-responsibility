"""Offline Kokoro syllable bank. Run with python -I; only compact WAVs ship."""
import json
from pathlib import Path
import site
import sys

sys.path.append(site.getusersitepackages())
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path('P:/FoA-Assets/audio/character-voices-kokoro-v1')
OUT = ROOT / 'phrases'
PROFILES = (
    ('Player', 'am_puck', 'am_michael', .72, 1.12),
    ('Adviser', 'af_heart', 'af_bella', .68, .96),
    ('Manager', 'am_fenrir', 'am_michael', .70, 1.20),
    ('Receptionist', 'bf_emma', 'af_nicole', .72, 1.03),
    ('Interviewer', 'bm_george', 'bm_fable', .66, .90),
)
# Explicit fictional phonemes prevent a language model from adding English words.
PHRASES = (
    'vˈɛnə ʃomˈɑɹi? nˈɛlu vˈɑʃə?',
    'ɹˈovaɪ nɛʃˈimə? tˈɛlə vˈʊn?',
    'nɛvˈiɹə. ʃˈomə vɛlˈʊn, dˈɑɹə.',
    'təlˈumə vˈɛʃi, noɹˈɑvə.',
    'kˈɛʃ! nəvˈoɹə tˈɑlɛm! vˈiʃu nˈɑɹə.',
    'dˈovə. ɹɛʃˈimə, kˈɑlu vˈɛnɛʃ.',
)


def finish(samples, sr):
    x = np.asarray(samples, dtype=np.float64)
    assert x.ndim == 1 and len(x) and np.isfinite(x).all()
    active = np.flatnonzero(np.abs(x) > .003)
    assert len(active), 'Silent speech synthesis'
    margin = int(.025 * sr)
    x = x[max(0, active[0]-margin):min(len(x), active[-1]+margin)]
    x -= np.mean(x)
    fade = min(int(.012*sr), len(x)//4)
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    x *= .63 / max(np.max(np.abs(x)), 1e-8)
    assert .6 < len(x)/sr < 8 and abs(x[0]) < 1e-6 and abs(x[-1]) < 1e-6
    return x


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    model = Kokoro(str(ROOT/'kokoro-v1.0.onnx'), str(ROOT/'voices-v1.0.bin'))
    records = []
    audition = []
    for character, first, second, weight, speed in PROFILES:
        style = model.get_voice_style(first)*weight + model.get_voice_style(second)*(1-weight)
        for index, phrase in enumerate(PHRASES):
            filename = f'S_Voice_{character}_{index:02d}.wav'
            destination = OUT/filename
            if not destination.exists():
                tokens = model.tokenizer.tokenize(phrase)
                # Installed kokoro-onnx sends int32 speed to this float-input export.
                inputs = {'input_ids': np.array([[0, *tokens, 0]], dtype=np.int64),
                          'style': np.array(style[len(tokens)], dtype=np.float32),
                          'speed': np.array([speed], dtype=np.float32)}
                x, sr = model.sess.run(None, inputs)[0], 24000
                sf.write(destination, finish(x, sr), sr, subtype='PCM_16')
            x, sr = sf.read(destination)
            assert sf.info(destination).channels == 1 and np.max(np.abs(x)) < .64
            records.append(dict(file=filename, character=character, sources=[first, second],
                blend=weight, speed=speed, phonemes=phrase, emotion=index//2, variant=index%2,
                seconds=round(len(x)/sr,3)))
            if index == 0:
                audition.extend([x, np.zeros(int(.6*sr))])
            print(filename, round(len(x)/sr, 2), flush=True)
    (OUT/'manifest.json').write_text(json.dumps(records, indent=2), encoding='utf8')
    preview = Path('P:/FoA/Saved/CharacterVoice')
    preview.mkdir(parents=True, exist_ok=True)
    sf.write(preview/'five_character_audition.wav', np.concatenate(audition), sr, subtype='PCM_16')
    (OUT/'SOURCES.txt').write_text(
        'Original fictional phonemes and blended character profiles authored for The Nightmare of Responsibility.\n'
        'Generated locally with Kokoro-82M v1.0 (hexgrad), Apache-2.0 weights and bundled voice styles.\n'
        'Model and voice license: https://huggingface.co/hexgrad/Kokoro-82M\n'
        'Voice inventory: https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md\n'
        'Only American/British styles used; no additional CC-BY sources listed for those styles.\n'
        'Runtime: kokoro-onnx, MIT, https://github.com/thewh1teagle/kokoro-onnx\n'
        'Model source: https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1\n'
        'No voice cloning, reference recording, English dialogue, musical notes, paid API or network inference.\n'
        'Processing: trim silence, 12ms boundary taper, peak -4dBFS, mono PCM16.\n', encoding='utf8')
    print('PASS', len(records), 'phrases', sum((OUT/r['file']).stat().st_size for r in records), 'bytes')


if __name__ == '__main__':
    main()
