"""Voice-only sources for the music (the user, 2026-11-10: "remove beat from all audios, only vocals", wordless only).
  P:/FoA-Assets/audio/_tools/sep-venv/Scripts/python.exe -I Tools/Audio/vocal_stems.py <key>=<source file> ...
For each source: Demucs htdemucs (two stems) keeps the vocal stem, written as 48 kHz float to
P:/FoA-Assets/audio/music/work/src_<key>.wav (what make_music.py reads); then faster-whisper (small, offline, language
detected) transcribes the stem with word timestamps, and every span with sung or spoken words is listed in
P:/FoA-Assets/audio/music/stems/<key>.json together with the wordless spans between them (padded 0.4 s around each word).
A segment counts as words when whisper is confident in it (avg log-probability over -1.0, no-speech probability under
0.6) and it has at least one word of two or more letters that isn't a bare vowel or a hum ("ah", "oh", "mm", "hmm").
Local and free; the models download once into the venv's cache."""
import json
import os
import re
import site
import subprocess
import sys

sys.path.append(site.getusersitepackages())
if sys.platform == 'win32':  # heavy offline work at BelowNormal so the shared PC stays responsive
    import ctypes
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
import torch  # noqa: E402
from demucs.apply import apply_model  # noqa: E402
from demucs.pretrained import get_model  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402
import torchaudio  # noqa: E402

WORK = 'P:/FoA-Assets/audio/music/work'
STEMS = 'P:/FoA-Assets/audio/music/stems'
HUM = re.compile(r'^(a+h*|o+h*|u+h*|e+h*|m+|h?m+|h+m+|la+|na+|ha+|ya+|ay+|oo+|ah+a*|[^\w]*)$', re.I)
DEV = 'cuda' if torch.cuda.is_available() else 'cpu'


def separate(model, path):
    tmp = f'{STEMS}/_decode.wav'  # ffmpeg decodes (torchaudio.load needs torchcodec); soundfile reads the PCM
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-ar', str(model.samplerate), '-ac', '2', '-c:a', 'pcm_f32le', tmp],
                   check=True)
    wav = torch.from_numpy(sf.read(tmp, dtype='float32', always_2d=True)[0].T.copy())
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / (ref.std() + 1e-8)
    with torch.no_grad():
        out = apply_model(model, wav[None], device=DEV, split=True, overlap=0.25, progress=False)[0]
    voc = out[model.sources.index('vocals')] * (ref.std() + 1e-8) + ref.mean()
    voc = torchaudio.functional.resample(voc, model.samplerate, 48000)
    return voc.T.numpy()


def words(asr, path, lang=None):
    v = torch.from_numpy(sf.read(path, dtype='float32', always_2d=True)[0].mean(1).copy())
    audio = torchaudio.functional.resample(v, 48000, 16000).numpy()  # whisper takes 16 kHz mono (no PyAV decode)
    segs, info = asr.transcribe(audio, beam_size=5, language=lang, word_timestamps=True, vad_filter=False, condition_on_previous_text=False)
    spans, text = [], []
    for s in segs:
        ws = [w for w in (s.words or []) if len(re.sub(r'[\W\d_]', '', w.word)) >= 2 and not HUM.match(w.word.strip())]
        if s.avg_logprob > -1.0 and s.no_speech_prob < 0.6 and ws:
            spans += [(max(0.0, w.start - 0.4), w.end + 0.4) for w in ws]
            text.append(s.text.strip())
    merged = []
    for a, b in sorted(spans):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged, info.language, text


def main():
    os.makedirs(STEMS, exist_ok=True)
    model = None if '--asr-only' in sys.argv else get_model('htdemucs').to(DEV).eval()
    asr = WhisperModel('small', device=DEV, compute_type='float16' if DEV == 'cuda' else 'int8')
    asr_only = '--asr-only' in sys.argv
    for arg in [a for a in sys.argv[1:] if a != '--asr-only']:
        key, path = arg.split('=', 1)
        key, _, force = key.partition('@')  # key@ar: transcribe as that language (detection calls sung Arabic 'en')
        if asr_only:
            voc = sf.read(f'{WORK}/src_{key}.wav', dtype='float32', always_2d=True)[0]
        else:
            voc = separate(model, path)
            sf.write(f'{WORK}/src_{key}.wav', voc.astype(np.float32), 48000, subtype='FLOAT')
        dur = len(voc) / 48000
        spans, lang, text = words(asr, f'{WORK}/src_{key}.wav', force or None)
        free, t = [], 0.0
        for a, b in spans + [[dur, dur]]:
            if a - t >= 2.0:
                free.append([round(t, 2), round(a, 2)])
            t = max(t, b)
        rec = dict(source=path, seconds=round(dur, 2), language=lang, worded=[[round(a, 2), round(b, 2)] for a, b in spans],
                   wordless=free, wordless_seconds=round(sum(b - a for a, b in free), 1), text=text[:40])
        json.dump(rec, open(f'{STEMS}/{key}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(key, f'{dur:.1f} s', lang, 'worded', len(spans), 'spans, wordless', rec['wordless_seconds'], 's', flush=True)


main()
