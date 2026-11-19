"""Editor leases for the shared Unreal editor: lanes on different AREAS work at the same time; EXCLUSIVE runs alone.
  python Tools/Unreal/editor_lock.py acquire <lane> --areas VFX,Level [--ttl 600] [--wait 1800]   # blocks until granted
  python Tools/Unreal/editor_lock.py acquire <lane>                                    # no areas = EXCLUSIVE (old lock)
  python Tools/Unreal/editor_lock.py acquire <lane> --assets /Game/FoA/UI/WBP_Menu     # finer than an area
  python Tools/Unreal/editor_lock.py acquire <lane> --actors Bed,DeskLamp --actors-new TMP_<lane>_  # level actors
  python Tools/Unreal/editor_lock.py save_level <lane>                                 # queues, saves, releases
  python Tools/Unreal/editor_lock.py force-release <owner>                             # coordinator: orphaned leases
  python Tools/Unreal/editor_lock.py release <lane>                                    # everything <lane> holds
  python Tools/Unreal/editor_lock.py renew <lane>                                      # heartbeat for long holds
  python Tools/Unreal/editor_lock.py status
Areas (case-insensitive): VFX UI Characters Gameplay PostProcess Audio Materials Cinematics = /Game/FoA/<Area> and what
belongs to it; Level = bulk work on arbitrary actors in the open map (prefer --actors / --actors-new); EXCLUSIVE = everything (PIE, level_save,
asset deletes and GC-heavy runs, restarts, DLL swaps). Requests whose areas intersect another holder's queue FIFO;
EXCLUSIVE waits for every holder to finish and everyone after it waits for it.
The holds are Hayba leases (owner = the lane), kept in the editor's lease table: they need no file and die with the
editor. A hold lapses after its ttl (max 900 s) unless renewed; ue_remote.py renews on every run. While the editor is
down or restarting, acquire waits for it to come back. The old file lock (Saved/FoA_editor.lock) only still counts for
the coordinator's main:MAINTENANCE holds, and is cleared otherwise."""
import json
import os
import sys
import time

import hayba_call as hc  # same folder

USE_HAYBA = True  # selftest turns it off: it must never take leases in the live editor

MAP = "/Game/FoA/Maps/L_Tutorial_Bedroom"
AREAS = {
    "vfx": "asset:/Game/FoA/VFX",
    "ui": "asset:/Game/FoA/UI",
    "characters": "asset:/Game/FoA/Characters",
    "gameplay": "asset:/Game/FoA/Gameplay",
    "postprocess": "asset:/Game/FoA/PostProcess",
    "audio": "asset:/Game/FoA/Audio",
    "materials": "asset:/Game/FoA/Materials",
    "cinematics": "asset:/Game/FoA/Cinematics",
    "level": "world:" + MAP,
    "exclusive": "global",
}

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Saved")
LOCK = os.path.join(ROOT, "FoA_editor.lock")
QUEUE = os.path.join(ROOT, "FoA_editor.queue")
TOKENS = os.path.join(ROOT, "FoA_leases")  # <owner>.txt: tokens of holds taken from the CLI, for release()
STALE_TICKET_S = 30
POLL_S = 2


def actor_keys(labels=(), new_prefixes=()):
    """Actors in the open map: one key per label, and one per spawn prefix (TMP_<lane>_*, a lane's own prefix).
    Different actors never conflict; the Level area (the whole map) conflicts with all of them."""
    return ([f"actor:{MAP}.{label.strip()}" for label in labels if label.strip()]
            + [f"actor:{MAP}.new:{prefix.strip().rstrip('*')}" for prefix in new_prefixes if prefix.strip()])


def area_keys(areas):
    """Area names, /Game paths or actor: keys -> Hayba lease keys. Unknown names are an error, not a silent no-op."""
    keys = []
    for a in areas:
        a = a.strip()
        if not a:
            continue
        if a.startswith("actor:"):
            keys.append(a)
        elif a.lower() in AREAS:
            keys.append(AREAS[a.lower()])
        elif a.startswith(("/", "asset:", "world:")) or a in ("global", "pie"):
            keys.append(hc.asset_resource(a))
        else:
            sys.exit(f"unknown area '{a}'; use one of {', '.join(sorted(AREAS))} or a /Game path")
    return sorted(set(keys)) or ["global"]


# ---- the old file lock: fallback without Hayba, and what legacy holders still write ----

def read():
    try:
        with open(LOCK, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def stale(held):
    return held is not None and time.time() - held.get("t", 0) > held.get("ttl", 1200)


def _file_owner(held):
    return held.get("owner", "").split(":")[0] if held else ""


def _live_tickets():
    """Ticket names in queue order, dropping ones whose waiter stopped refreshing them."""
    names = []
    for name in sorted(os.listdir(QUEUE)):
        path = os.path.join(QUEUE, name)
        try:
            if time.time() - os.path.getmtime(path) > STALE_TICKET_S:
                os.remove(path)
                continue
        except OSError:
            continue
        names.append(name)
    return names


def acquire_file(owner, wait_s=1800, ttl=600, front=False):
    """The old exclusive lock: returns once `owner` holds it; re-entrant (refreshes the timestamp)."""
    os.makedirs(QUEUE, exist_ok=True)
    held = read()
    if _file_owner(held) == owner and not stale(held):
        held.update(t=time.time(), ttl=ttl)
        with open(LOCK, "w", encoding="utf-8") as fh:
            json.dump(held, fh)
        return
    now = time.time_ns()  # fronts sort first, then by arrival; the pid is zero-padded so it never decides the order
    ticket = f"{0 if front else now:020d}_{now:020d}_{os.getpid():08d}_{owner}"
    ticket_path = os.path.join(QUEUE, ticket)
    deadline = time.time() + wait_s
    try:
        while True:
            with open(ticket_path, "w", encoding="utf-8") as fh:  # (re)write = heartbeat
                fh.write(owner)
            held = read()
            if stale(held):
                try:
                    os.remove(LOCK)
                except OSError:
                    pass
            tickets = _live_tickets()
            if tickets and tickets[0] == ticket:
                try:
                    fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    with os.fdopen(fd, "w") as fh:
                        json.dump({"owner": owner, "pid": os.getpid(), "t": time.time(), "ttl": ttl}, fh)
                    return
                except FileExistsError:
                    pass
            if time.time() > deadline:
                sys.exit(f"editor busy: held by {read()}; gave up after {wait_s}s")
            time.sleep(POLL_S)
    finally:
        try:
            os.remove(ticket_path)
        except OSError:
            pass


def release_file(owner):
    held = read()
    if _file_owner(held) == owner:
        os.remove(LOCK)
        return True
    return False


# ---- Hayba leases ----

def _soft(fn, default):
    """Run Hayba calls; an unreachable editor (or a Hayba without leases) returns `default`."""
    if not USE_HAYBA:
        return default
    try:
        return fn()
    except (OSError, RuntimeError, ValueError) as e:
        print(f"editor_lock: Hayba leases unavailable ({e})", file=sys.stderr)
        return default


def hayba_leases(owner):
    """[(token, [lease key, ...]), ...] that `owner` holds in Hayba now."""
    return _soft(lambda: hc.leases_of(owner), [])


EXCLUSIVE_WINDOW = (10, 3)  # EXCLUSIVE (PIE, deletes) may only start in the first 3 minutes of every 10


def in_exclusive_window(t=None):
    period, open_min = EXCLUSIVE_WINDOW
    return (time.localtime(t).tm_min % period) < open_min


def _wait_exclusive_window(owner, keys, deadline):
    """A waiting EXCLUSIVE blocks every later request, so 15 lanes stall behind each PIE burst. Batching them into
    windows keeps the other 7 minutes free-flowing. The coordinator (main*) is exempt."""
    if "global" not in keys or owner.startswith("main"):
        return
    if USE_HAYBA and any(r.lower() == "global" for _, res in _soft(lambda: hc.leases_of(owner), []) for r in res):
        return  # already holds EXCLUSIVE (granted in a window): later calls of the same burst must not wait
    told = False
    while not in_exclusive_window():
        if time.time() > deadline:
            sys.exit("editor busy: EXCLUSIVE only starts in the first 3 minutes of every 10 (PIE window); gave up")
        if not told:
            print(f"editor_lock: {owner} EXCLUSIVE waits for the next PIE window (minutes :x0-:x2)", file=sys.stderr)
            told = True
        time.sleep(5)


def _maintenance_blocks(owner):
    # main-* helpers (e.g. main-cleanup) work inside the coordinator's window without owning, and so never release, it
    if owner == "main" or owner.startswith("main-"):
        return False
    held = read()
    return bool(held) and not stale(held) and held.get("owner", "").startswith("main:MAINTENANCE")


def _wait_maintenance(owner, deadline, wait_s):
    """The coordinator's maintenance hold (editor restarts, the user playtesting) blocks every lane's lease."""
    while _maintenance_blocks(owner):
        if time.time() > deadline:
            sys.exit(f"editor busy: {read().get('owner')} (maintenance); gave up after {wait_s}s")
        time.sleep(POLL_S)


def user_playing():
    """PIE runs and no lane holds EXCLUSIVE (the only way a lane may run PIE), so the PIE is the user's playtest.
    11-10 17:20: a lane granted EXCLUSIVE in the user's session restarted and then ended his PIE ("don't let ai do
    stuff in the play"). No lane gets any lease while this is true."""
    def check():
        if not hc.call("editor_get_state", timeout=20).get("data", {}).get("pie_running"):
            return False
        leases = hc.call("lease_status", timeout=20).get("data", {}).get("leases", [])
        return not any(str(r).lower() == "global" or (isinstance(r, dict) and r.get("resource") == "global")
                       for l in leases for r in l.get("resources", []))
    return _soft(check, False)


def _wait_user_play(owner, deadline, wait_s):
    if owner == "main" or owner.startswith("main-"):
        return
    told = False
    while user_playing():
        if time.time() > deadline:
            sys.exit(f"editor busy: the user is playtesting; gave up after {wait_s}s")
        if not told:
            print(f"editor_lock: {owner} waits: the user is playtesting (PIE without a lane's EXCLUSIVE)", file=sys.stderr)
            told = True
        time.sleep(10)


def acquire(owner, wait_s=1800, ttl=600, front=False, areas=None):
    """Block until `owner` holds `areas` (default EXCLUSIVE). Returns the new lease token, or None when the hold was
    already there (renewed) or Hayba is down and the file lock was taken instead."""
    keys = sorted(k.lower() for k in area_keys(areas or ["EXCLUSIVE"]))  # compared sorted with held leases below
    deadline = time.time() + wait_s
    _wait_maintenance(owner, deadline, wait_s)
    if USE_HAYBA and _hayba_up():
        _retire_file_lock(owner)
    _wait_exclusive_window(owner, keys, deadline)
    _wait_maintenance(owner, deadline, wait_s)  # a hold placed while this request waited for the window wins too
    if not USE_HAYBA:
        acquire_file(owner, max(1, deadline - time.time()), ttl, front)
        return None
    told = False
    while True:
        try:
            mine = hc.leases_of(owner)
            held = {r.lower() for _, res in mine for r in res}
            # Already covered by what this owner holds: renew, never queue again. A second request from a holder
            # would queue behind any EXCLUSIVE waiter, which itself waits for the holder: a deadlock.
            if "global" in held or set(keys) <= held:
                hc.renew_all(owner, ttl)
                return None
            _wait_maintenance(owner, deadline, wait_s)  # last check right before the lease is granted
            _wait_user_play(owner, deadline, wait_s)
            token = hc.lease_acquire(owner, keys, ttl_s=ttl, wait_s=max(1, deadline - time.time()),
                                     label=f"{owner}: {', '.join(areas or ['EXCLUSIVE'])}")
            os.makedirs(TOKENS, exist_ok=True)
            with open(os.path.join(TOKENS, owner + ".txt"), "a", encoding="utf-8") as fh:
                print(token, file=fh)
            return token
        except hc.QueueTimeout as e:
            sys.exit(f"editor busy: {e}")
        except ConnectionRefusedError:
            # Nothing listens on Hayba's port: the editor is down or restarting. There is nothing to lock then, and
            # an old-file-lock queue formed while it was down kept lanes serial after it came back: wait for Hayba.
            if time.time() > deadline:
                sys.exit(f"editor not running: Hayba never answered within {wait_s:.0f}s")
            if not told:
                print("editor_lock: editor not running; waiting for it to come back", file=sys.stderr)
                told = True
            time.sleep(5)
        except (OSError, RuntimeError, ValueError) as e:
            # The port answers but the game thread is busy (a long run, PIE start) or the connection cap is full:
            # keep waiting for Hayba, never fall back to the file lock while it is reachable.
            if time.time() > deadline:
                sys.exit(f"editor busy: Hayba did not answer lease calls for {wait_s:.0f}s ({e})")
            if not told:
                print(f"editor_lock: editor busy ({e}); still waiting for the lease", file=sys.stderr)
                told = True
            time.sleep(5)


def _hayba_up():
    """True when something listens on Hayba's port (busy or not); False only when the editor is down."""
    try:
        hc.connect(timeout=5).close()
        return True
    except ConnectionRefusedError:
        return False
    except OSError:
        return True  # reset or timeout: the editor is there, just busy or at its connection cap


def _retire_file_lock(owner):
    """With Hayba up, the old file lock and its ticket queue mean nothing: drop them (maintenance holds excepted)."""
    held = read()
    if held and not held.get("owner", "").startswith("main:MAINTENANCE") and _file_owner(held) != owner:
        try:
            os.remove(LOCK)
        except OSError:
            pass
    if os.path.isdir(QUEUE):
        for name in os.listdir(QUEUE):
            try:
                os.remove(os.path.join(QUEUE, name))
            except OSError:
                pass


def release(owner):
    path = os.path.join(TOKENS, owner + ".txt")
    tokens = open(path, encoding="utf-8").read().split() if os.path.exists(path) else []
    released = _soft(lambda: sum(hc.release(owner, t) for t in tokens) + hc.release_all(owner), 0) > 0
    if _soft(lambda: hc.leases_of(owner), []):  # a token we never learned (or lost): find it by owner
        released = force_release(owner) > 0 or released
    if os.path.exists(path):
        os.remove(path)
    return release_file(owner) or released


def force_release(owner):
    """Release every Hayba lease `owner` holds, without its tokens (coordinator admin, and release()'s fallback).
    This Hayba redacts tokens in replies; they are 'lease-<salt>-<seq>', so learn salt and seq from a queue ticket
    and try each seq as `owner`. The table's owner check makes every other owner's lease a no-op.
    shortcut: a scan over this editor session's seqs; drop it with the Hayba build that returns lease ids."""
    def run():
        hc.call("lease_acquire", {"resources": ["asset:/__hayba_probe"], "ttl_s": 5, "label": "probe"},
                owner="hayba-probe-a", retries=hc.RETRIES)
        data = hc.call("lease_acquire", {"resources": ["asset:/__hayba_probe"], "ttl_s": 5, "label": "probe"},
                       owner="hayba-probe-b", retries=hc.RETRIES).get("data", {})
        ticket = data.get("ticket", "")
        if not ticket.startswith("q-"):
            raise RuntimeError("could not learn the lease salt")
        hc.call("lease_release", {"token": ticket}, owner="hayba-probe-b", retries=hc.RETRIES)
        salt, seq = ticket[2:].rsplit("-", 1)
        left = len(hc.leases_of(owner))
        done = 0
        for n in range(int(seq) - 1, -1, -1):
            if done >= left:
                break
            done += hc._ok(hc.call("lease_release", {"token": f"lease-{salt}-{n}"}, owner=owner, retries=hc.RETRIES))
        return done
    return _soft(run, 0)


def forget(owner, token):
    """Drop a token ue_remote released itself from the owner's CLI token list."""
    path = os.path.join(TOKENS, owner + ".txt")
    if os.path.exists(path):
        rest = [t for t in open(path, encoding="utf-8").read().split() if t != token]
        with open(path, "w", encoding="utf-8") as fh:
            for t in rest:
                print(t, file=fh)


def status_lines():
    held = read()
    lines = []
    if held:
        lines.append(f"old lock: {held.get('owner')} for {time.time() - held.get('t', 0):.0f}s"
                     + (" (abandoned)" if stale(held) else ""))
    if os.path.isdir(QUEUE):
        waiting = [t.split("_", 3)[3] for t in _live_tickets() if t.count("_") >= 3]
        if waiting:
            lines.append("old queue: " + ", ".join(waiting))
    data = _soft(lambda: hc.call("lease_status", retries=hc.RETRIES).get("data", {}), None)
    if data is None:
        lines.append("Hayba leases: no answer (editor busy in a long command, restarting, or closed)")
        return lines
    names = {v: k for k, v in AREAS.items()}
    for lease in data.get("leases", []):
        res = ", ".join(names.get(r.get("resource", ""), r.get("resource", "")) for r in lease.get("resources", []))
        lines.append(f"{lease.get('owner')}: {res} (held {lease.get('held_s', 0):.0f}s, {lease.get('expires_in_s', 0):.0f}s left)")
    for w in data.get("waiters", []):
        res = ", ".join(names.get(r.get("resource", ""), r.get("resource", "")) for r in w.get("resources", []))
        lines.append(f"waiting: {w.get('owner')} for {res} ({w.get('waited_s', 0):.0f}s)")
    if not data.get("leases") and not data.get("waiters") and not held:
        lines.append("free")
    return lines


def selftest():
    global LOCK, QUEUE, USE_HAYBA
    real = (LOCK, QUEUE, USE_HAYBA)
    LOCK, QUEUE, USE_HAYBA = LOCK + ".selftest", QUEUE + ".selftest", False
    global TOKENS
    TOKENS = TOKENS + ".selftest"
    assert area_keys(["vfx", "Level"]) == ["asset:/Game/FoA/VFX", "world:/Game/FoA/Maps/L_Tutorial_Bedroom"]
    assert area_keys([]) == ["global"] and area_keys(["/Game/FoA/UI/W.W"]) == ["asset:/Game/FoA/UI/W"]
    try:
        acquire("a", wait_s=1, ttl=60)                    # no Hayba: falls back to the file lock
        acquire("a", wait_s=1, ttl=60)                    # re-entrant for the same owner
        assert read()["owner"] == "a"
        assert not release("b") and read()["owner"] == "a"  # others can't release it
        # FIFO: an older live ticket blocks a newer waiter even when the lock is free
        assert release("a")
        older = os.path.join(QUEUE, f"{1:020d}_1_00000001_older")
        open(older, "w").close()
        try:
            acquire_file("b", wait_s=1, ttl=60)
            raise AssertionError("newer waiter jumped the queue")
        except SystemExit:
            pass
        os.utime(older, (time.time() - 100, time.time() - 100))  # a dead waiter's ticket goes stale
        acquire_file("b", wait_s=5, ttl=60)
        assert read()["owner"] == "b" and release("b")
        with open(LOCK, "w", encoding="utf-8") as fh:      # an abandoned hold is taken over
            json.dump({"owner": "a", "t": time.time() - 100, "ttl": 10}, fh)
        acquire("c", wait_s=5, ttl=60)
        assert read()["owner"] == "c" and release("c") and read() is None
    finally:
        if os.path.exists(LOCK):
            os.remove(LOCK)
        if os.path.isdir(QUEUE):
            for n in os.listdir(QUEUE):
                os.remove(os.path.join(QUEUE, n))
            os.rmdir(QUEUE)
        LOCK, QUEUE, USE_HAYBA = real
    print("editor_lock selftest ok")


if __name__ == "__main__":
    args = sys.argv[1:]
    opt = lambda name, default: float(args[args.index(name) + 1]) if name in args else default  # noqa: E731
    lst = lambda name: args[args.index(name) + 1].split(",") if name in args else []  # noqa: E731
    if not args or args[0] == "status":
        print("\n".join(status_lines()))
    elif args[0] == "acquire":
        wanted = lst("--areas") + lst("--assets") + actor_keys(lst("--actors"), lst("--actors-new"))
        token = acquire(args[1], opt("--wait", 1800), opt("--ttl", 600), "--front" in args, wanted or None)
        held = hayba_leases(args[1])
        print("acquired", args[1], "->", "; ".join(", ".join(r) for _, r in held) if held else "old exclusive lock")
    elif args[0] == "release":
        print("released" if release(args[1]) else "not held by " + args[1])
    elif args[0] == "save_level":
        # Queues for the Level key: waits for every actor holder and any EXCLUSIVE (PIE) holder, never for asset lanes.
        token = acquire(args[1], opt("--wait", 1800), 120, areas=["Level"])
        try:
            resp = hc.call("level_save", {}, timeout=600, owner=args[1])
            print("level_save:", "ok" if hc._ok(resp) else resp.get("error"))
        finally:
            if token:
                _soft(lambda: hc.release(args[1], token), None)
                forget(args[1], token)
            else:
                release(args[1])
    elif args[0] == "force-release":
        print("force-released", force_release(args[1]), "lease(s) of", args[1])
    elif args[0] == "renew":
        _soft(lambda: hc.renew_all(args[1], opt("--ttl", 600)), None)
        print("renewed", args[1])
    elif args[0] == "selftest":
        selftest()
    else:
        sys.exit(__doc__)
