"""Hand the editor lock to lanes in a fixed order, one after another (coordinator tool).

  python Tools/Unreal/handoff.py sandvfx ui review

Whenever the lock is free, writes it in the next lane's name (ttl 1200 s). That lane runs its ue_remote calls as
FOA_AGENT=<lane> (they see the lock as already theirs) and releases with `editor_lock.py release <lane>`.
Lanes that win the lock through the normal queue in between simply go first; the order then continues.
"""
import json, os, sys, time
LOCK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Saved", "FoA_editor.lock")
order = sys.argv[1:]
while order:
    if os.path.exists(LOCK):
        time.sleep(0.1)
        continue
    nxt = order[0]
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        continue
    with os.fdopen(fd, "w") as fh:
        json.dump({"owner": f"{nxt}:handed-by-main", "pid": os.getpid(), "t": time.time(), "ttl": 1200.0}, fh)
    print(time.strftime("%H:%M:%S"), "handed to", nxt, flush=True)
    order.pop(0)
    time.sleep(2)
print(time.strftime("%H:%M:%S"), "handoff list done", flush=True)
