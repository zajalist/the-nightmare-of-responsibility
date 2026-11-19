"""MRQ render of LS_WakeUp in chunks, each inside its own EXCLUSIVE hold of 58 s at most (editor-rules: PIE and renders
only in a PIE window, 60 s or less). Offline driver, run from P:/FoA:
  python Tools/Unreal/cine/render_chunks.py 0-150 150-300 ... [--samples 1] [--res 960x540] [--warmup 4] [--out DIR]
  python Tools/Unreal/cine/render_chunks.py --auto 0-1092 --holds 6 ...   each hold renders until it is cancelled at 58 s,
                                                                         the next resumes at the last frame written
Per chunk: editor_lock acquire cine (EXCLUSIVE, waits for the window), ue_remote render_ls.py (queues the PIE render),
watch Saved/Logs/FoA.log for "[cine] render done", cancel the render if it would overrun, release. Prints seconds per
chunk so the next chunk size can be chosen. Frames land as LS_WakeUp.NNNN.png (absolute sequence frame numbers)."""
import os
import subprocess
import sys
import time

ROOT = "P:/FoA"
LOG = ROOT + "/Saved/Logs/FoA.log"
LIMIT_S = 58.0
PY = sys.executable


def run(args, env=None, timeout=None):
    return subprocess.run([PY] + args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)


def log_size():
    return os.path.getsize(LOG)


def log_since(pos):
    with open(LOG, encoding="utf-8", errors="replace") as fh:
        fh.seek(pos)
        return fh.read()


def chunk(rng, samples, out, res, warmup, fps="30"):
    # No FOA_AREAS / FOA_EXCLUSIVE: inside our own EXCLUSIVE hold ue_remote then reuses it instead of queueing a second
    env = {k: v for k, v in os.environ.items() if k not in ("FOA_AREAS", "FOA_ACTORS", "FOA_ACTORS_NEW", "FOA_EXCLUSIVE")}
    env.update(HAYBA_AGENT_ID="cine", FOA_AGENT="cine", MSYS_NO_PATHCONV="1")
    r = run(["Tools/Unreal/editor_lock.py", "acquire", "cine", "--ttl", "120"], env)
    t0 = time.time()
    print(rng, "acquired", r.stdout.strip()[-120:], flush=True)
    pos = log_size()
    ok, cancelled = False, False
    try:
        r = run(["Tools/Unreal/ue_remote.py", "Tools/Unreal/cine/render_ls.py", "FOA_RANGE=" + rng, "FOA_SAMPLES=" + samples,
                 "FOA_OUT=" + out, "FOA_RES=" + res, "FOA_WARMUP=" + warmup] +
                (["FOA_FPS=" + fps] if fps != "30" else []), env, timeout=40)
        print(r.stdout.strip()[-300:], r.stderr.strip()[-300:], flush=True)
        while time.time() - t0 < LIMIT_S:
            if "[cine] render done" in log_since(pos):
                ok = True
                break
            time.sleep(1.0)
        if not ok:  # overrun: stop the render so the hold ends on time
            run(["Tools/Unreal/ue_remote.py", "Tools/Unreal/cine/render_cancel.py"], env, timeout=30)
            cancelled = True
    finally:
        run(["Tools/Unreal/editor_lock.py", "release", "cine"], env)
    done = log_since(pos)
    tail = done[done.find("[cine] render done"):][:120] if ok else ""
    print("%s %s in %.1f s %s" % (rng, "done" if ok else ("CANCELLED" if cancelled else "failed"), time.time() - t0, tail), flush=True)
    return ok


def main():
    args = sys.argv[1:]
    samples = args[args.index("--samples") + 1] if "--samples" in args else "1"
    out = args[args.index("--out") + 1] if "--out" in args else ROOT + "/Saved/Cinematics/wakeup_v3_frames"
    res = args[args.index("--res") + 1] if "--res" in args else "1920x1080"
    warmup = args[args.index("--warmup") + 1] if "--warmup" in args else "8"
    fps = args[args.index("--fps") + 1] if "--fps" in args else "30"
    k = 30 // int(fps)  # ranges are display frames (30 fps); file numbers are output frames
    if "--auto" in args:
        a, b = [int(x) for x in args[args.index("--auto") + 1].split("-")]
        for _ in range(int(args[args.index("--holds") + 1]) if "--holds" in args else 6):
            have = [int(f.split(".")[1]) for f in os.listdir(out) if f.startswith("LS_WakeUp.")] if os.path.isdir(out) else []
            start = (max([x for x in have if a <= x * k < b], default=a // k - 1) + 1) * k
            if start >= b:
                print("all frames %d-%d present" % (a, b - 1))
                return
            start = max(a, start - k)  # the last frame may have been cut mid-write by the cancel: redo it
            chunk("%d-%d" % (start, b), samples, out, res, warmup, fps)
        return
    ranges = [a for a in args if "-" in a and a[0].isdigit()]
    for rng in ranges:
        if not chunk(rng, samples, out, res, warmup):
            sys.exit(1)


if __name__ == "__main__":
    main()
