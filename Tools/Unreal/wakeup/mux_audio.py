"""Adds LS_WakeUp's soundtrack to a silent PIE recording (this machine has no loopback capture device).
  python Tools/Unreal/wakeup/mux_audio.py Saved/Devlog/wakeup_v1.mp4 [offset_s]
  python Tools/Unreal/wakeup/mux_audio.py Saved/Cinematics/wakeup_v3.mp4 --v3   (an MRQ render: frame 0 is 0 s, v3 cues)
The cues come from wake_cues.py and Saved/WakeUp/placement.json, the WAVs from P:/FoA-Assets/audio/SFX. Without an
offset, the sequence start is found from where the opening black ends (the eyes open at 2.4 s). Rewrites the MP4 in place."""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wake_cues  # noqa: E402

SRC = "P:/FoA-Assets/audio/SFX/"
T = wake_cues.T


def first_black(mp4):
    """Sequence start in the recording: the end of the first long black (the UI's cut to black flows straight into
    LS_WakeUp's own black, whose fade opens at T pov = 2.4 s)."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", mp4, "-vf", "blackdetect=d=1.5:pix_th=0.06", "-an", "-f", "null",
                          "-"], capture_output=True, text=True).stderr
    ends = re.findall(r"black_end:([\d.]+)", out)
    assert ends, "no black interval found; pass the offset by hand"
    return float(ends[0]) - T["pov"]


def main():
    v3 = "--v3" in sys.argv
    argv = [a for a in sys.argv if a != "--v3"]
    mp4 = argv[1]
    off = float(argv[2]) if len(argv) > 2 else (0.0 if v3 else first_black(mp4))
    P = json.load(open("P:/FoA/Saved/WakeUp/placement.json", encoding="utf-8"))
    if v3:
        cues = wake_cues.cues_v3(P["grab_t"])
    else:
        cues = [c + (None,) for c in wake_cues.cues(T, P["grab_t"], wake_cues.times(P["edge_len"])["stand"])]
    args, chains = ["ffmpeg", "-y", "-loglevel", "error", "-i", mp4], []
    n = 0
    for path, t0, t1, vol, loop, fo in cues:
        wav = SRC + path + ".wav"
        if not os.path.exists(wav):
            print("missing", wav)
            continue
        args += (["-stream_loop", "-1"] if loop else []) + ["-i", wav]
        n += 1
        trim = f"atrim=0:{t1 - t0:.3f}," if t1 is not None else ""
        ms = int((off + t0) * 1000)
        fade = f"afade=t=out:st={fo[0] - t0:.3f}:d={fo[1] - fo[0]:.3f}," if fo else ""
        chains.append(f"[{n}:a]{trim}{fade}adelay={ms}|{ms},volume={vol}[a{n}]")
    graph = ";".join(chains) + ";" + "".join(f"[a{i}]" for i in range(1, n + 1)) + \
        f"amix=inputs={n}:normalize=0:duration=longest[mix]"
    tmp = mp4.replace(".mp4", "_mux.mp4")
    subprocess.run(args + ["-filter_complex", graph, "-map", "0:v", "-map", "[mix]", "-c:v", "copy", "-c:a", "aac",
                           "-b:a", "192k", "-shortest", tmp], check=True)
    os.replace(tmp, mp4)
    print("muxed %d cues at offset %.2fs -> %s" % (n, off, mp4))


if __name__ == "__main__":
    main()
