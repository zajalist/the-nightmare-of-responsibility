"""Call Hayba's editor commands directly over TCP (127.0.0.1:52342), without the MCP server. Stdlib only.

  python Tools/Unreal/hayba_call.py <command> ['<json params>']      # prints the JSON response
  python Tools/Unreal/hayba_call.py <command> @params.json           # params from a file (easier from PowerShell)
  python Tools/Unreal/hayba_call.py --batch calls.jsonl              # one {"cmd": ..., "params": {...}} per line
  python Tools/Unreal/hayba_call.py --batch calls.jsonl --keep-going # don't stop at the first failed call

Examples:
  python Tools/Unreal/hayba_call.py ping
  python Tools/Unreal/hayba_call.py material_get_info '{"path": "/Game/FoA/Materials/M_Glass"}'

Command names are the plugin's (the MCP tool names without the mcp__hayba-toolkit__ prefix for the C++-backed tools).
It never takes the editor lock: hold it yourself as for any other editor work. The envelope carries
owner=$HAYBA_AGENT_ID (else $FOA_AGENT; Hayba's lease owner). $env:FOA_EDITOR='B' targets editor B (P:/FoA-B);
HAYBA_PORT overrides the port and, when set, lease=$FOA_LEASE. Exit code 1 when any call fails.
Also importable: `from hayba_call import call; call("ping")`.
"""
import itertools
import random
import json
import os
import socket
import struct
import sys
import time

HOST = os.environ.get("HAYBA_HOST", "127.0.0.1")
EDITORS = {"A": r"P:\FoA", "B": r"P:\FoA-B"}  # FOA_EDITOR picks one; A is the editor that saves to disk


def editor_root():
    return EDITORS.get(os.environ.get("FOA_EDITOR", "A").strip().upper() or "A", EDITORS["A"])


def _alive(pid):
    """True while process `pid` runs. (Never os.kill(pid, 0) on Windows: 0 is CTRL_C_EVENT there, not a probe.)"""
    import ctypes
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    try:
        code = ctypes.c_ulong()
        return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259  # STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _editor_port():
    """HAYBA_PORT wins; else the port in the FOA_EDITOR project's live Hayba heartbeat; else 52342."""
    if os.environ.get("HAYBA_PORT"):
        return int(os.environ["HAYBA_PORT"])
    folder = os.path.join(editor_root(), "Saved", "HaybaMCP", "instances")
    try:
        beats = sorted((os.path.join(folder, n) for n in os.listdir(folder) if n.endswith(".json")),
                       key=os.path.getmtime, reverse=True)
    except OSError:
        beats = []
    for path in beats:
        try:
            with open(path, encoding="utf-8") as fh:
                beat = json.load(fh)
            if _alive(int(beat["pid"])):
                return int(beat["port"])
        except (OSError, ValueError, KeyError):
            continue
    return 52342 if editor_root() == EDITORS["A"] else 52343


PORT = _editor_port()
_ids = itertools.count(1)


def _recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Hayba closed the connection")
        buf += chunk
    return buf


def connect(timeout=120.0):
    sock = socket.create_connection((HOST, PORT), timeout=10)
    sock.settimeout(timeout)
    return sock


def send(sock, cmd, params=None, owner=None, lease=None):
    """One framed request/response on an open connection (4-byte big-endian length + UTF-8 JSON)."""
    msg = {"id": f"hc_{os.getpid()}_{next(_ids)}", "cmd": cmd, "params": params or {}}
    owner = owner or agent_id()
    lease = lease or os.environ.get("FOA_LEASE")
    if owner:
        msg["owner"] = owner
    if lease:
        msg["lease"] = lease
    if os.environ.get("HAYBA_AUTH"):
        msg["auth"] = os.environ["HAYBA_AUTH"]
    body = json.dumps(msg).encode("utf-8")
    sock.sendall(struct.pack(">I", len(body)) + body)
    (length,) = struct.unpack(">I", _recv_exact(sock, 4))
    return json.loads(_recv_exact(sock, length).decode("utf-8"))


def agent_id():
    """The lease owner: HAYBA_AGENT_ID (what Hayba's own MCP client sends), else FOA_AGENT."""
    return os.environ.get("HAYBA_AGENT_ID") or os.environ.get("FOA_AGENT")


def call(cmd, params=None, timeout=120.0, retries=0, **envelope):
    """One request on a fresh connection. With `retries`, a dropped connection is retried for up to ~retries*8 s:
    Hayba closes clients beyond its connection cap, and that means "busy", not "down". A refused connection (no editor
    listening) is raised at once. Only for idempotent calls such as the lease ones below."""
    give_up = time.time() + retries * 8
    attempt = 0
    while True:
        try:
            with connect(timeout) as sock:
                return send(sock, cmd, params, **envelope)
        except ConnectionRefusedError:
            raise
        except (ConnectionError, socket.timeout):
            attempt += 1
            if not retries or time.time() > give_up:
                raise
            time.sleep(min(0.5 * attempt, 3))


def _ok(resp):
    return bool(resp.get("ok", resp.get("success", False)))


# ---- leases (Hayba's lease table, ADR-0010): what editor_lock.py and ue_remote.py build on ----

def asset_resource(path):
    """A lease key from what a lane declares: '/Game/A/B.B' or '/Game/A' -> 'asset:/Game/A/B' / 'asset:/Game/A'
    (keys compare exactly, so lanes must declare the same granularity: the folder they own is the convention);
    'level' -> the current map's 'world:' key; 'global', 'pie' and 'world:...' pass through."""
    path = path.strip()
    if path in ("global", "pie") or path.startswith(("world:", "wp-region:", "actor:")):
        return path
    if path == "level":
        return "world:" + (call("lease_status", retries=RETRIES).get("data", {}).get("current_world") or "/Game/FoA/Maps/L_Tutorial_Bedroom")
    if path.startswith("asset:"):
        path = path[6:]
    return "asset:" + path.split(".", 1)[0].rstrip("/")


RETRIES = 8


class QueueTimeout(Exception):
    """lease_acquire gave up: still queued behind other holders after wait_s."""

# Leases use one short connection per call: Hayba drops a connection that sends nothing for ~5 s, so a lease here is
# never bound to a connection; it lives until released or its TTL lapses (renew_all on activity).

def _redacted(token):
    return not token or token.startswith("[REDACTED")


def _lease_param(lease):
    return {"lease_id" if lease.startswith("ls_") else "token": lease}


def _probe_tokens(owner, resources):
    """This Hayba build redacts every reply field named "token", so a granted lease's token never reaches us.
    Tokens are 'lease-<salt>-<seq>' and queue tickets 'q-<salt>-<seq>' from the same counter: a probe that must queue
    behind the lease we just got reveals the salt and the next seq, and our lease is one of the few seqs before it.
    shortcut: guesses up to 6 candidates (release tries each; the owner check makes a wrong guess a no-op);
    drop this once the installed Hayba returns unredacted lease ids (origin/main's lease_id)."""
    probe = owner + "~probe"
    resp = call("lease_acquire", {"resources": list(resources), "mode": "exclusive", "ttl_s": 5,
                                  "bind_connection": False, "label": "token probe"}, owner=probe, retries=RETRIES)
    data = resp.get("data", {})
    ticket = data.get("ticket", "")
    if data.get("status") != "queued" or not ticket.startswith("q-"):
        return []
    call("lease_release", {"token": ticket}, owner=probe, retries=RETRIES)
    salt, seq = ticket[2:].rsplit("-", 1)
    return [f"lease-{salt}-{n}" for n in range(int(seq) - 1, max(int(seq) - 7, -1), -1)]


def lease_acquire(owner, resources, ttl_s=600, wait_s=1800, label=""):
    """Block until `owner` holds an exclusive lease on `resources`; returns its token ("a;b;c" candidates when this
    Hayba redacts tokens: pass it to release()). Conflicts queue in Hayba, FIFO among conflicting requests, so an
    exclusive waiter drains the rest; the editor itself never waits."""
    params = {"resources": list(resources), "mode": "exclusive", "ttl_s": min(float(ttl_s), 900.0),
              "bind_connection": False, "label": label or owner,
              # A grant lives 30 s until we confirm it with a renew below, so a lease granted to a waiter that died
              # in the queue lapses at once instead of after its full TTL (older Hayba builds ignore this).
              "confirm_within_s": 30}
    deadline = time.time() + wait_s
    ticket = None
    resp = call("lease_acquire", params, owner=owner, retries=RETRIES)
    while True:
        if not _ok(resp):
            raise RuntimeError(f"lease_acquire failed: {resp.get('error')}")
        data = resp.get("data", {})
        if data.get("status") == "granted":
            token = data.get("lease_id") or data.get("token", "")
            if not _redacted(token):
                call("lease_renew", {**_lease_param(token), "ttl_s": params["ttl_s"]}, owner=owner, retries=RETRIES)
                return token
            if ticket:  # granted from the queue: same seq as its ticket
                return "lease-" + ticket[2:]
            return ";".join(_probe_tokens(owner, resources))
        ticket = data.get("ticket", "")
        if time.time() > deadline:
            call("lease_release", {"token": ticket}, owner=owner, retries=RETRIES)
            raise QueueTimeout(f"lease on {resources} still queued behind {data.get('holder_owner')} after {wait_s:.0f}s")
        # Poll every 5-9 s (Hayba drops a ticket not polled for 30 s); polls are cheap: answered on the TCP thread.
        time.sleep(5 + random.random() * 4)
        resp = call("lease_acquire", {"ticket": ticket}, owner=owner, retries=RETRIES)
        if not _ok(resp):  # the ticket lapsed (the editor was busy for >30 s): queue again from the back
            ticket = None
            resp = call("lease_acquire", params, owner=owner, retries=RETRIES)


def leases_of(owner):
    """[(token, [resource, ...]), ...] held by `owner`."""
    out = []
    for lease in call("lease_status", owner=owner, retries=RETRIES).get("data", {}).get("leases", []):
        token = lease.get("lease_id") or lease.get("token", "")
        if lease.get("mine") and not _redacted(token):
            out.append((token, [r.get("resource") for r in lease.get("resources", [])]))
    return out


def renew_all(owner, ttl_s=600):
    for token, _ in leases_of(owner):
        call("lease_renew", {**_lease_param(token), "ttl_s": min(float(ttl_s), 900.0)}, owner=owner, retries=RETRIES)


def release(owner, token):
    """Release a token from lease_acquire (or one of its ';'-separated candidates). True when one was released."""
    return any(_ok(call("lease_release", _lease_param(t), owner=owner, retries=RETRIES))
               for t in (token or "").split(";") if t and not _redacted(t))


def release_all(owner):
    """Release every lease `owner` holds and cancel every ticket it still has queued."""
    data = call("lease_status", owner=owner, retries=RETRIES).get("data", {})
    tickets = [w["ticket"] for w in data.get("waiters", []) if w.get("owner") == owner and w.get("ticket")]
    for ticket in tickets:
        call("lease_release", {"token": ticket}, owner=owner, retries=RETRIES)
    return len(tickets) + sum(release(owner, token) for token, _ in leases_of(owner))


def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        sys.exit(__doc__)
    try:
        if argv[0] == "--batch":
            keep_going = "--keep-going" in argv
            failed = False
            with open(argv[1], encoding="utf-8") as fh, connect() as sock:
                for n, line in enumerate(fh, 1):
                    if not line.strip() or line.lstrip().startswith("#"):
                        continue
                    item = json.loads(line)
                    resp = send(sock, item["cmd"], item.get("params"))
                    print(json.dumps({"line": n, "cmd": item["cmd"], "response": resp}), flush=True)
                    if not _ok(resp):
                        failed = True
                        if not keep_going:
                            break
            return 1 if failed else 0
        raw = argv[1] if len(argv) > 1 else "{}"
        if raw.startswith("@"):
            with open(raw[1:], encoding="utf-8") as fh:
                raw = fh.read()
        params = json.loads(raw)
        resp = call(argv[0], params)
        print(json.dumps(resp, indent=2))
        return 0 if _ok(resp) else 1
    except (ConnectionError, OSError) as e:
        print(json.dumps({"ok": False, "error": f"Hayba not reachable on {HOST}:{PORT}: {e}"}))
        return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
