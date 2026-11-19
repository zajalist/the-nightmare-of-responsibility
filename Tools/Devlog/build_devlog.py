"""Build or refresh the FoA devlog archive in P:/FoA-Devlog from observable sources only.

    python Tools/Devlog/build_devlog.py

Reads (never modifies): the Hayba tool-call log, the UE editor logs, Content/ file times, Hayba's scene map,
screenshots the lanes save, the screen recordings, git history and the FoA-Assets manifests.
It never reads agent transcripts. Re-runs are incremental: new events are merged into each day's timeline.json,
new stills and clips are added, and nothing is ever deleted.
Writes: <day>/stills, <day>/clips, <day>/timeline.json, showcase/ (graph captures, comment-group crops, widget
renders, GIFs), _index.json, _scene/ snapshots and index.html.
Optional inputs: <day>/notes.json = {"<lane-slug>": "what the lane reported"}, shown on that lane's card, and
showcase/notes.json = {"<AssetName>": "one-line description"}, shown on that asset's card.

    python Tools/Devlog/build_devlog.py --capture
also drives the editor: whole-graph PNGs of every authored material, material function and Blueprint through
FoAGraphTools, one asset at a time via ue_remote.py (see ue_capture.py). Read-only on assets. Off by default: the
coordinator paused editor captures until its single-writer lock protocol is in place.
"""
import datetime as dt
import glob
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter

import numpy as np
from PIL import Image
from scipy import ndimage

FOA, ASSETS, OUT = "P:/FoA", "P:/FoA-Assets", "P:/FoA-Devlog"
HAYBA_LOG = f"{FOA}/Saved/hayba-execution.log"
UE_LOGS = f"{FOA}/Saved/Logs/FoA*.log"
SCENE_MAP = f"{FOA}/Saved/hayba-cognitive-map.json"
SCAN_DIRS = [f"{FOA}/Content/FoA", f"{FOA}/Plugins/FoAGraphTools"]
RECORDINGS = f"{OUT}/recordings/editor_*.mp4"
SHOT_SOURCES = [  # (folder, lane to force or None to infer from the folder and file name)
    *[(p.replace("\\", "/"), "ui" if p.endswith("UIShots") else None) for p in sorted(glob.glob(f"{FOA}/Saved/*Shots"))],
    (f"{FOA}/Saved/Screenshots", None),
    (f"{ASSETS}/blender/previews", None),
    (f"{ASSETS}/character/turnaround", "character"),
    (f"{ASSETS}/storyboard/frames", "concept"),
    (f"{ASSETS}/storyboard/moods", "concept"),
]
CONCEPT_LINKS = [
    ("Storyboard", "https://claude.ai/artifact/PLRgtmHY7UusSvT4R8B5Rr"),
    ("Concept board", "https://claude.ai/artifact/9AHdPVWkh8ar5ZV7FSbnJg"),
    ("Moodboard", "https://claude.ai/artifact/CRuYFYM17KMhEprHLZ9GQH"),
]
GAP_S, MAX_BURST_S = 120, 600  # a burst ends after 2 min of quiet, or after 10 min so clips stay short
CLIP_SPEED, SHORT_CLIP_SPEED = 20, 4
# shortcut: crop measured from the 2026-11-05 editor layout (viewport left of the Outliner/Hayba panel, above the
# dock); re-measure on a recording frame if the user re-docks panels.
VIEWPORT_CROP = "crop=1264:830:4:158"
EDITOR_REF = f"{OUT}/_ref/editor_layout.png"  # a desktop frame with the editor in front, same layout as VIEWPORT_CROP
EDITOR_PATCHES = [(0, 80, 760, 40), (1280, 125, 620, 30), (1282, 380, 90, 350)]  # (x, y, w, h): main toolbar,
# Outliner tab row, Hayba icon column (catches mid-screen overlays such as the task switcher)
X264 = ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]

# (slug, name, brief, keywords). Order matters: the first lane whose keyword appears in a name wins.
LANES = [
    ("fonts", "Fonts", "Import the game's typefaces as UE font faces and composite fonts.",
     ["/fonts/", "font", "typography", "typespecimen"]),
    ("ui", "UI", "Build the game's UMG widgets in the monochrome style.", ["/ui/", "wbp_", "ui_"]),
    ("light-shafts", "Light shafts", "Light shafts falling into the bedroom, from a light-shaft material and line texture.",
     ["lightshaft", "light_shaft", "godray", "t_lines", "light_lines", "shaftshots"]),
    ("sand-vfx", "Gaussian-splat sand VFX", "Black-sand effects made from Gaussian-splat meshes and materials, not Niagara.",
     ["/vfx/", "splat", "sandfall", "sandimpact", "vfxlab", "sandmound"]),
    ("trims", "Mitered trims", "Mitered room trim: baseboards, crown molding, casings, sills and muntins.",
     ["trim", "casing", "baseboard", "crownmolding", "crown_molding", "muntin", "sm_sill", "framebar"]),
    ("fireplace", "Fireplace", "Dress the chimney breast on the west wall: hearth, firebox, soot and mantel.",
     ["hearth", "fireplace", "chimney", "mantel", "soot", "firebox", "ember"]),
    ("door-bedding", "Door + bedding", "The bedroom door in the east wall, and the Lux3D bedding on the bed.",
     ["/door/", "door_", "bedding", "pillow", "blanket", "duvet"]),
    ("post-process", "Dream post-process", "PP_DreamMono and MPC_Dream: everything black and white, with a slight hue drift.",
     ["pp_dream", "mpc_dream", "postprocess", "post_process", "pp_", "ppshots"]),
    ("animations", "Animations", "Animation setup for the character.",
     ["/anim", "abp_", "anim_", "_anim", "montage", "/ual", "ual1", "ual2", "retarget", "rtg_"]),
    ("character", "Lux3D character", "The player character, generated with Lux3D.",
     ["/character", "turnaround", "skm_"]),
    ("wall-art", "Wall art and decals", "Wall art and decals.",
     ["decal", "wallart", "wall_art", "picture_frame", "poster", "painting", "/art/", "artwork", "wa_shot", "wa_cam"]),
    ("carpet-props", "Carpet and props", "The rug and set-dressing props, each one resting on a surface.",
     ["rug", "carpet", "/props/", "nightstand", "dressing"]),
    ("box-projected", "Box-projected surfaces", "World-aligned (box-projected) materials for the room's surfaces.",
     ["worldaligned", "world_aligned", "boxproj", "box_proj", "triplanar", "surf_"]),
    ("graph-tools", "FoAGraphTools plugin", "An FoA editor plugin for graph tooling.",
     ["foagraphtools", "graphtools", "graph_tools"]),
    ("sfx", "SFX", "Sound effects and ambience, CC0 or generated (see the audio MANIFEST).",
     ["/audio/", "/sfx/", "/sound", "sound_wave", ".wav", "metasound", "soundcue"]),
    ("concept", "Concept", "The storyboard, concept board and moodboard.", ["storyboard", "/moods/", "moodboard"]),
]
LANE_NAME = {s: n for s, n, _, _ in LANES} | {"editor": "Unattributed editor work", "timelapse": "Timelapse"}
LANE_BRIEF = {s: b for s, _, b, _ in LANES} | {
    "editor": "Changes the archive could not attribute to a lane from asset or actor names."}
CHANGE_VERBS = {"create", "add", "set", "delete", "connect", "disconnect", "import", "duplicate", "spawn", "transform",
                "apply", "compile", "save", "mutate", "build", "remove", "move", "rename", "reparent", "replace",
                "bind", "copy", "run"}

UE_TS = re.compile(r"^\[(\d{4})\.(\d\d)\.(\d\d)-(\d\d)\.(\d\d)\.(\d\d):(\d{3})\]")
UE_PATTERNS = [
    ("save", re.compile(r'Cmd: OBJ SAVEPACKAGE PACKAGE="([^"]+)"')),
    ("spawn", re.compile(r"Actor Factory spawned Class \S+ as actor: \S+ \S+:PersistentLevel\.(\S+)")),
    ("import", re.compile(r"FactoryCreateFile: .*\(\S+ \S+ (.+)\)\s*$")),
    ("crash", re.compile(r"LogWindows: Error: (=== Critical error: ===)")),
]
HIGHLIGHT_LANES = {"light-shafts", "post-process", "ui"}  # the big visual changes: shafts, dream PP, title screen
POST_CRASH_S = 1200  # bursts starting within 20 min after an editor crash are the recovery and stability work


# ---------- parsing ----------

def parse_hayba_line(line):
    """One TSV row of hayba-execution.log: utc, tool, args hash, ms, ok|err, message."""
    p = line.rstrip("\r\n").split("\t", 5)
    if len(p) < 5 or not re.match(r"\d{4}-\d\d-\d\dT[\d:.]+Z$", p[0]):
        return None
    return {"utc": p[0], "src": "hayba", "kind": p[1], "args_hash": p[2],
            "ms": int(p[3]) if p[3].isdigit() else None, "status": p[4], "msg": p[5].strip() if len(p) > 5 else ""}


def parse_ue_line(line):
    m = UE_TS.match(line)
    if not m:
        return None
    for kind, rx in UE_PATTERNS:
        k = rx.search(line)
        if k:
            y, mo, d, h, mi, s, ms = m.groups()
            target = {"import": os.path.basename(k.group(1)), "crash": "Unreal Editor crashed"}.get(kind, k.group(1))
            return {"utc": f"{y}-{mo}-{d}T{h}:{mi}:{s}.{ms}Z", "src": "ue", "kind": kind, "target": target,
                    "status": "ok"}
    return None


def to_local(utc):
    return dt.datetime.fromisoformat(utc).astimezone()


def iso_utc(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def is_change(tool):
    return bool(CHANGE_VERBS & set(tool.split("_")))


def lane_of(text):
    t = text.lower()
    return next((slug for slug, _, _, kws in LANES if any(k in t for k in kws)), None)


def group_bursts(events):
    out = []
    for e in sorted(events, key=lambda e: e["utc"]):
        t = to_local(e["utc"])
        if out and (t - out[-1][1]).total_seconds() <= GAP_S and (t - out[-1][0]).total_seconds() <= MAX_BURST_S:
            out[-1][2].append(e)
            out[-1][1] = t
        else:
            out.append([t, t, [e]])
    return [b[2] for b in out]


def selftest():
    e = parse_hayba_line("2026-11-05T21:22:11.725Z\tpython_run\tAB12\t11\terr\tpython_run policy_blocked "
                         "[HCR-TIME-001]: matched 'try statement'\n")
    assert e["kind"] == "python_run" and e["status"] == "err" and e["ms"] == 11 and "HCR-TIME-001" in e["msg"], e
    e = parse_hayba_line("2026-11-05T21:06:38.759Z\tping\tBF21\t2\tok\t\n")
    assert e["status"] == "ok" and e["msg"] == "" and e["utc"] == "2026-11-05T21:06:38.759Z", e
    assert parse_hayba_line("") is None and parse_hayba_line("not\ta\tlog\tline\tok") is None
    u = parse_ue_line('[2026.11.05-20.52.12:299][535]Cmd: OBJ SAVEPACKAGE PACKAGE="/Game/FoA/Maps/L_Tutorial_Bedroom" '
                      'FILE="P:/x.umap" SILENT=true')
    assert u == {"utc": "2026-11-05T20:52:12.299Z", "src": "ue", "kind": "save",
                 "target": "/Game/FoA/Maps/L_Tutorial_Bedroom", "status": "ok"}, u
    u = parse_ue_line("[2026.11.05-21.29.19:863][866]LogActorFactory: Actor Factory spawned Class /Script/Engine."
                      "CameraActor as actor: CameraActor /Game/FoA/Maps/L.L:PersistentLevel.CameraActor_0")
    assert u["kind"] == "spawn" and u["target"] == "CameraActor_0", u
    u = parse_ue_line("[2026.11.05-21.24.08:158][468]LogFactory: FactoryCreateFile: Texture with TextureFactory "
                      "(0 0 C:/Temp/hayba-asset-connectors/foa/tex/T_plastered_wall_Albedo.jpg)")
    assert u["kind"] == "import" and u["target"] == "T_plastered_wall_Albedo.jpg", u
    assert parse_ue_line("[2026.11.05-21.22.27:280][229]Cmd: SELECT NONE") is None
    u = parse_ue_line("[2026.11.05-22.25.14:583][662]LogWindows: Error: === Critical error: ===")
    assert u["kind"] == "crash" and u["utc"] == "2026-11-05T22:25:14.583Z", u
    assert to_local("2026-11-05T21:06:38.759Z").utcoffset() is not None
    assert [len(b) for b in group_bursts([{"utc": f"2026-11-05T21:{m:02d}:00.000Z"} for m in (0, 1, 2, 10)])] == [3, 1]
    minutes = [{"utc": f"2026-11-05T{20 + m // 60}:{m % 60:02d}:00.000Z"} for m in range(25)]
    assert [len(b) for b in group_bursts(minutes)] == [11, 11, 3]
    assert lane_of("/Game/FoA/UI/Fonts/F_FoA_UI") == "fonts" and lane_of("/Game/FoA/UI/Widgets/WBP_SandButton") == "ui"
    assert lane_of("desk_lamp_arm_01") is None and lane_of("/Game/FoA/Materials/M_WorldAligned") == "box-projected"
    assert lane_of("/Game/FoA/Characters/Player/Source/UAL1/A") == "animations" and lane_of("PPShots/v1_Wide") == "post-process"
    assert unversioned("Title_option_A_r1b") == "Title_option_A" and unversioned("v2_ThirdPerson") == "ThirdPerson"
    assert unversioned("MF_BoxProjectUV_v0") == "MF_BoxProjectUV" and unversioned("sand_0012") == "sand"
    grid = np.full((600, 900, 3), 104, np.uint8)
    grid[100:400, 50:500] = (150, 140, 160)  # a tinted comment bubble on the graph grid
    grid[200:260, 100:300] = (45, 45, 45)    # a node inside it
    assert comment_groups_in(grid) == [(50, 100, 450, 300)], comment_groups_in(grid)
    assert lane_of("/Game/FoA/Props/hanging_picture_frame_03/T") == "wall-art" and lane_of("Door_overall.png") == "door-bedding"
    assert is_change("material_set_param") and is_change("actor_transform") and not is_change("get_setting")
    assert not is_change("material_get_info") and not is_change("editor_capture_viewport")


# ---------- sources ----------

def read_lines(path):
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        return fh.readlines()


def hayba_events():
    return [e for e in map(parse_hayba_line, read_lines(HAYBA_LOG))] if os.path.exists(HAYBA_LOG) else []


def ue_events():
    return [e for p in glob.glob(UE_LOGS) for e in map(parse_ue_line, read_lines(p))]


def file_events():
    for root in SCAN_DIRS:
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in ("Binaries", "Intermediate")]
            for f in fns:
                rel = os.path.relpath(os.path.join(dp, f), FOA).replace("\\", "/")
                target = "/Game/" + rel[len("Content/"):].rsplit(".", 1)[0] if rel.startswith("Content/") else rel
                yield {"utc": iso_utc(os.path.getmtime(os.path.join(dp, f))), "src": "file", "kind": "asset_file",
                       "target": target, "status": "ok"}


def scene_events():
    """Snapshot Hayba's scene map whenever it changes, then diff consecutive snapshots into actor events."""
    snapdir = f"{OUT}/_scene"
    os.makedirs(snapdir, exist_ok=True)
    if os.path.exists(SCENE_MAP):
        name = f"{snapdir}/{dt.datetime.fromtimestamp(os.path.getmtime(SCENE_MAP)):%Y%m%d_%H%M%S}.json"
        if not os.path.exists(name):
            try:
                actors = json.load(open(SCENE_MAP, encoding="utf-8")).get("actors", [])
            except ValueError:  # Hayba is mid-write; the next run picks it up
                actors = None
            if actors is not None:
                snap = {a["id"]: {"label": a.get("label", a["id"]), "class": a.get("class", ""),
                                  "loc": [round(v, 1) for v in a.get("location", [0, 0, 0])]} for a in actors}
                with open(name, "w", encoding="utf-8") as fh:
                    json.dump(snap, fh, indent=0)
    events, labels, prev = [], {}, None
    for p in sorted(glob.glob(f"{snapdir}/*.json")):
        cur = json.load(open(p, encoding="utf-8"))
        utc = iso_utc(dt.datetime.strptime(os.path.basename(p)[:15], "%Y%m%d_%H%M%S").timestamp())
        if prev is not None:
            diff = [("actor_added", cur[i]) for i in cur.keys() - prev.keys()]
            diff += [("actor_removed", prev[i]) for i in prev.keys() - cur.keys()]
            diff += [("actor_moved", cur[i]) for i in cur.keys() & prev.keys()
                     if max(abs(a - b) for a, b in zip(cur[i]["loc"], prev[i]["loc"])) > 1]
            events += [{"utc": utc, "src": "scene", "kind": k, "target": a["label"], "status": "ok"} for k, a in diff]
        labels.update({i: v["label"] for i, v in cur.items()})
        prev = cur
    return events, labels


def git_commits():
    r = subprocess.run(["git", "-C", FOA, "log", "--date=iso-strict-local", "--format=%h%x09%ad%x09%s"],
                       capture_output=True, text=True, encoding="utf-8")
    return [dict(zip(("hash", "time", "subject"), ln.split("\t", 2))) for ln in r.stdout.splitlines() if ln.count("\t") >= 2]


def toolchain():
    tc = {"lux3d": [], "splats": [], "polyhaven": None, "audio": None}
    state = f"{ASSETS}/lux3d/_state.json"
    if os.path.exists(state):
        for key, v in json.load(open(state, encoding="utf-8")).items():
            exts = sorted({os.path.splitext(f)[1].lstrip(".") for f in v.get("files", [])} - {"zip"})
            tc["lux3d"].append({"key": key, "item": v.get("item", key), "task": v.get("task"),
                                "status": v.get("status"), "outputs": exts})
    tc["splats"] = sorted(os.path.basename(p).split(".")[0] for p in glob.glob(f"{ASSETS}/splatmesh/*.splatmesh.json"))
    ph = f"{ASSETS}/polyhaven/MANIFEST.md"
    if os.path.exists(ph):
        tc["polyhaven"] = len({m for ln in read_lines(ph) if ln.startswith("|")
                               for m in re.findall(r"polyhaven\.com/a/([\w-]+)", ln)})
    au = f"{ASSETS}/audio/MANIFEST.md"
    if os.path.exists(au):
        tc["audio"] = sum(1 for ln in read_lines(au) if ln.startswith("| `"))
    return tc


def source_status(segs):
    rows = []
    for name, path in [("Hayba tool-call log", HAYBA_LOG), ("Hayba scene map", SCENE_MAP),
                       ("UE editor logs", f"{FOA}/Saved/Logs"), ("Hayba MCP state", f"{FOA}/Saved/HaybaMCP"),
                       ("Lux3D state", f"{ASSETS}/lux3d/_state.json"), ("Lux3D prompts", f"{FOA}/docs/lux3d-bedroom-prompts.md"),
                       ("Poly Haven manifest", f"{ASSETS}/polyhaven/MANIFEST.md"),
                       ("Audio manifest", f"{ASSETS}/audio/MANIFEST.md"), ("Splat meshes", f"{ASSETS}/splatmesh"),
                       ("FoAGraphTools plugin", f"{FOA}/Plugins/FoAGraphTools")] + [(f"Shots: {r}", r) for r, _ in SHOT_SOURCES]:
        rows.append((name, path, "found" if os.path.exists(path) else "missing"))
    done = sum(1 for _, _, d in segs if d)
    rows.append(("Screen recordings", RECORDINGS, f"{done} finished, {len(segs) - done} in progress or unreadable"
                 if segs else "missing"))
    return rows


# ---------- archive ----------

def ekey(e):
    return e["utc"], e["src"], e["kind"], e.get("target") or e.get("args_hash", "")


def load_json(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_if_changed(path, text):
    if not os.path.exists(path) or open(path, encoding="utf-8").read() != text:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)


def summarize(evs, labels, day):
    t0, t1 = to_local(evs[0]["utc"]), to_local(evs[-1]["utc"])
    hay = [e for e in evs if e["src"] == "hayba"]
    tools = Counter(e["kind"] for e in hay)
    assets = sorted({e["target"] for e in evs if e["kind"] in ("save", "asset_file")})
    imports = sorted({e["target"] for e in evs if e["kind"] == "import"})
    actors = sorted({labels.get(e["target"], e["target"]) for e in evs if e["kind"] == "spawn" or e["src"] == "scene"})
    lanes = Counter(filter(None, map(lane_of, assets + imports + actors + [e["kind"] for e in hay])))
    errs = Counter(re.sub(r"'[^']*'", "'…'", e["msg"])[:90] for e in hay if e["status"] == "err")
    crashes = sum(e["kind"] == "crash" for e in evs)
    parts = ["the editor crashed"] if crashes else []
    if hay:
        parts.append(f"{len(hay)} Hayba calls (" + ", ".join(f"{k} ×{v}" for k, v in tools.most_common(3)) + ")")
    if assets:
        names = shorts(assets)
        parts.append(f"{len(assets)} assets saved: " + ", ".join(names[:4]) + (" …" if len(names) > 4 else ""))
    if imports:
        parts.append(f"{len(imports)} files imported")
    if actors:
        parts.append("actors: " + ", ".join(actors[:5]) + (" …" if len(actors) > 5 else ""))
    return {"id": f"b{t0:%H%M%S}", "start": t0.isoformat(timespec="seconds"), "end": t1.isoformat(timespec="seconds"),
            "lane": (lanes.most_common(1) or [("editor", 0)])[0][0], "lanes": [k for k, _ in lanes.most_common()],
            "label": "; ".join(parts),
            "changes": any(e["src"] != "hayba" or (e["status"] == "ok" and is_change(e["kind"])) for e in evs),
            "calls": len(hay), "errors": sum(errs.values()), "crashes": crashes, "tools": dict(tools.most_common()),
            "error_kinds": dict(errs.most_common()), "assets": assets, "imports": imports, "actors": actors,
            "clips": [], "frames": [], "events": [e for e in evs if e["src"] != "scene"]}


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def unique(path):
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(path):
        path, n = f"{base}-{n}{ext}", n + 1
    return path


def rel(path):
    return os.path.relpath(path, OUT).replace("\\", "/")


def collect_stills(index):
    added = 0
    for root, forced in SHOT_SOURCES:
        for p in sorted(glob.glob(f"{root}/**/*", recursive=True)):
            if (not p.lower().endswith((".png", ".jpg", ".jpeg")) or time.time() - os.path.getmtime(p) < 5
                    or "/review/" in p.replace("\\", "/")):
                continue  # non-images, files a lane may still be writing, and review graph captures (showcase only)
            digest = sha1(p)
            if digest in index["stills"]:
                continue
            t = dt.datetime.fromtimestamp(os.path.getmtime(p))
            lane = forced or lane_of(f"{os.path.basename(root)}/{os.path.relpath(p, root)}") or "editor"
            stem, ext = os.path.splitext(os.path.basename(p))
            what = re.sub(r"[^A-Za-z0-9-]+", "-", stem).strip("-")
            dest = unique(f"{OUT}/{t:%Y-%m-%d}/stills/{t:%H%M}_{lane}_{what}{ext.lower()}")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(p, dest)
            index["stills"][digest] = {"rel": rel(dest), "src": p.replace("\\", "/"), "t": t.isoformat(timespec="seconds"),
                                       "lane": lane}
            added += 1
    return added


def probe_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip()) or None
    except ValueError:
        return None  # still being recorded (no moov atom yet) or unreadable


def segments():
    segs = []
    for p in sorted(glob.glob(RECORDINGS)):
        m = re.search(r"editor_(\d{8}_\d{6})\.mp4$", p)
        if m:
            segs.append((p.replace("\\", "/"), dt.datetime.strptime(m.group(1), "%Y%m%d_%H%M%S").astimezone(),
                         probe_duration(p)))
    return segs


def ffmpeg_out(index, key, dest, args, meta):
    """Render one derived media file once; the index key (not the file name) makes re-runs skip it."""
    if key in index["media"]:
        return 0
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    base, ext = os.path.splitext(dest)
    tmp = f"{base}.part{ext}"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args), tmp],
                       capture_output=True, text=True)
    if r.returncode or not os.path.exists(tmp):
        print(f"  ffmpeg failed for {key}: {r.stderr.strip()[-300:]}")
        if os.path.exists(tmp):
            os.remove(tmp)  # our own partial output, never source media
        return 0
    os.replace(tmp, dest)
    index["media"][key] = {"rel": rel(dest)} | meta
    return 1


_EDITOR_REF = []


def editor_in_front(seg, offset_s):
    """The recording is the whole desktop. Use only moments where the editor's own toolbar and Outliner tab row are on
    top, so other windows (terminals with agent chat, image viewers) never end up in clips or stills."""
    if not _EDITOR_REF:
        _EDITOR_REF.append(np.asarray(Image.open(EDITOR_REF).convert("RGB")).astype(np.int16)
                           if os.path.exists(EDITOR_REF) else None)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{offset_s:.2f}", "-i", seg, "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    if _EDITOR_REF[0] is None or len(raw) != 1920 * 1080 * 3:
        return False
    f = np.frombuffer(raw, np.uint8).reshape(1080, 1920, 3).astype(np.int16)
    # Measured on the 16:44 segment: editor in front differs by < 1.5, any covering window by > 14.
    return all(np.abs(f[y:y + h, x:x + w] - _EDITOR_REF[0][y:y + h, x:x + w]).mean() < 6 for x, y, w, h in EDITOR_PATCHES)


def cut_media(index, days, segs):
    made = 0
    sec = dt.timedelta(seconds=1)
    for seg, s0, dur in segs:
        if not dur:
            continue
        s1, segkey = s0 + dur * sec, os.path.basename(seg)
        for day, bursts in days.items():
            for b in bursts:
                b0, b1 = dt.datetime.fromisoformat(b["start"]), dt.datetime.fromisoformat(b["end"])
                a, z = max(b0 - 10 * sec, s0), min(b1 + 10 * sec, s1)
                key, lane, bid = f"{day}/{b['id']}@{segkey}", b["lane"], b["id"]
                if not b["changes"] or z <= a or key in index["media"] or key in index["skipped"]:
                    continue
                # Keep the longest stretch where every 10 s sample shows the editor in front; its ends are the
                # before/after frames. shortcut: a window flashing up between two samples can slip through.
                off0 = (a - s0).total_seconds()
                vis = [editor_in_front(seg, off0 + i * 10) for i in range(int((z - a).total_seconds() // 10) + 1)]
                runs = [(i, j) for i in range(len(vis)) for j in range(i, len(vis)) if all(vis[i:j + 1])]
                i, j = max(runs, key=lambda r: r[1] - r[0], default=(0, -1))
                if (j - i) * 10 < 30:
                    index["skipped"][key] = "editor not in front for 30 s of the burst"
                    continue
                off, length = off0 + i * 10, (j - i) * 10
                a, z = s0 + off * sec, s0 + (off + length) * sec
                speed = SHORT_CLIP_SPEED if length <= 120 or b.get("highlight") else CLIP_SPEED
                meta = {"lane": lane, "burst": f"{day}/{bid}"}
                made += ffmpeg_out(index, key, f"{OUT}/{day}/clips/{a:%H%M}_{lane}_{bid}-{speed}x.mp4",
                                   ["-ss", f"{off:.2f}", "-t", f"{length:.2f}", "-i", seg,
                                    "-vf", f"{VIEWPORT_CROP},setpts=PTS/{speed}", "-r", 30, *X264],
                                   meta | {"kind": "clip", "t": a.isoformat(timespec="seconds")})
                for which, t in (("before", a), ("after", z)):
                    made += ffmpeg_out(index, f"{key}@{which}", f"{OUT}/{day}/stills/{t:%H%M}_{lane}_{bid}-{which}.png",
                                       ["-ss", f"{(t - s0).total_seconds():.2f}", "-i", seg, "-frames:v", 1,
                                        "-vf", VIEWPORT_CROP], meta | {"kind": which, "t": t.isoformat(timespec="seconds")})
    return made


# ---------- showcase: graphs, widgets, GIFs ----------

SHOWCASE = f"{OUT}/showcase"
KINDS = {"M": "Material", "MF": "Material function", "ABP": "Anim Blueprint", "BP": "Blueprint", "WBP": "Widget Blueprint"}
IMPORTED = re.compile(r"/(Lux3D|Props|Procedural|Source|_GraphToolsTest)/|/SM_[^/]+/Materials/")  # imported, not authored
VERSION = re.compile(r"(?:^|_)(?:v\d+[a-z]?|r\d+[a-z]?|before|after|\d{2,4})(?=_|$)", re.I)
REVIEW_SHOTS = f"{FOA}/Saved/GraphShots/review"
TURNTABLES = f"{ASSETS}/character/v3/turntables/*.mp4"
GIF_PALETTE = ("split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];"
               "[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle")


def unversioned(stem):
    return VERSION.sub("", stem).strip("_") or stem


def slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")


def graph_assets():
    """Authored graph assets under /Game/FoA, found offline by naming convention (the lane rules enforce the prefixes)."""
    out, root = {}, f"{FOA}/Content/FoA"
    for dp, _, fns in os.walk(root):
        for f in fns:
            m = re.match(r"(MF|M|ABP|WBP|BP)_.+\.uasset$", f)
            path = "/Game/FoA/" + os.path.relpath(os.path.join(dp, f[:-7]), root).replace("\\", "/")
            if m and not IMPORTED.search(path):
                out[f[:-7]] = {"path": path, "kind": m.group(1), "mtime": os.path.getmtime(os.path.join(dp, f))}
    return out


def comment_groups_in(rgb):
    """Comment bubbles in a FoAGraphTools capture: large tinted rectangles brighter than the grey grid, with the holes
    left by their nodes filled. Returns [] for anything that is not a graph capture (editor-window shots are dark)."""
    lum = rgb.astype(np.int16).mean(axis=2)
    bg = np.bincount(lum.astype(np.int32).ravel()).argmax()
    if not 90 <= bg <= 130:
        return []
    m = (lum > bg + 25) & (lum < 235)
    m = ndimage.binary_opening(m, structure=np.ones((9, 9)))  # drop wires and text
    m = ndimage.binary_fill_holes(ndimage.binary_closing(m, structure=np.ones((15, 15))))
    lab, _ = ndimage.label(m)
    boxes = []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        y, x, h, w = sl[0].start, sl[1].start, sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if w >= 240 and h >= 140 and (lab[sl] == i).mean() > 0.85:
            boxes.append((int(x), int(y), int(w), int(h)))
    return sorted(boxes, key=lambda b: (b[1] // 200, b[0]))


def is_graph_capture(path):
    lum = np.asarray(Image.open(path).convert("RGB")).astype(np.int16).mean(axis=2)
    return 90 <= np.bincount(lum.astype(np.int32).ravel()).argmax() <= 130


def ingest_graph_shots(index, assets):
    """FoAGraphTools captures saved by lanes (GraphShots, GraphShots/review) join the matching asset's history."""
    added = 0
    for p in sorted(glob.glob(f"{FOA}/Saved/GraphShots/*.png") + glob.glob(f"{REVIEW_SHOTS}/**/*.png", recursive=True)):
        stem = os.path.splitext(os.path.basename(p))[0]
        name = next((n for n in sorted(assets, key=len, reverse=True)
                     if unversioned(stem) == n or stem.startswith(n + "_") or stem.startswith(n + "-")), None)
        if not name or time.time() - os.path.getmtime(p) < 5:
            continue
        digest = sha1(p)
        if digest in index["showcase"]:
            continue
        index["showcase"][digest] = None
        if not is_graph_capture(p):
            continue  # an editor-window screenshot, not a clean whole-graph render
        t = dt.datetime.fromtimestamp(os.path.getmtime(p))
        graph = stem[len(name):].strip("_-") if stem.startswith(name) else ""
        graph = "" if VERSION.fullmatch("_" + graph) else graph
        dest = unique(f"{SHOWCASE}/graphs/{name}/{slug(graph) or 'graph'}_{t:%Y%m%d-%H%M}.png")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(p, dest)
        index["showcase"][digest] = rel(dest)
        added += 1
    return added


def ingest_widget_renders(index, assets):
    """Designer renders of Widget Blueprints (Hayba ui_render_widget_to_png and the UI lane's shots)."""
    def key(s):
        return re.sub(r"[^a-z0-9]", "", s.lower()).removeprefix("wbp")
    wbps = {key(n): n for n, a in assets.items() if a["kind"] == "WBP"}
    added = 0
    for folder in (f"{FOA}/Saved/Screenshots/Hayba", f"{FOA}/Saved/UIShots", f"{FOA}/Saved/GraphShots"):
        for p in sorted(glob.glob(f"{folder}/*.png")):
            stem = os.path.splitext(os.path.basename(p))[0]
            match = max((w for w in wbps if key(unversioned(stem)).startswith(w)), key=len, default=None)
            if not match or time.time() - os.path.getmtime(p) < 5:
                continue
            digest = sha1(p)
            if digest in index["showcase"]:
                continue
            t = dt.datetime.fromtimestamp(os.path.getmtime(p))
            dest = unique(f"{SHOWCASE}/widgets/{wbps[match]}/{t:%Y%m%d-%H%M}_{slug(stem)}.png")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(p, dest)
            index["showcase"][digest] = rel(dest)
            added += 1
    return added


def versions(folder):
    """{label: [png, ...]} oldest first, for files named <label>_<YYYYmmdd-HHMM>.png."""
    out = {}
    for p in sorted(glob.glob(f"{folder}/*.png"), key=os.path.getmtime):
        stem = os.path.splitext(os.path.basename(p))[0]
        out.setdefault(re.sub(r"_\d{8}-\d{4}(-\d+)?$", "", stem), []).append(p)
    return out


def make_crops(index, png):
    """Comment-group crops of one capture, at 1:1 (downscaled only past 1920 px) so they read in a video."""
    key = rel(png)
    if key not in index["crops"]:
        im = Image.open(png).convert("RGB")
        base = os.path.splitext(png.replace("/graphs/", "/crops/"))[0]
        out = []
        for i, (x, y, w, h) in enumerate(comment_groups_in(np.asarray(im)), 1):
            c = im.crop((max(x - 24, 0), max(y - 24, 0), min(x + w + 24, im.width), min(y + h + 24, im.height)))
            if c.width > 1920:
                c = c.resize((1920, round(c.height * 1920 / c.width)), Image.LANCZOS)
            dest = f"{base}_g{i}.png"
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            c.save(dest)
            out.append(rel(dest))
        index["crops"][key] = out
    return index["crops"][key]


def ffmpeg_gif(inputs, dest, vf):
    tmp = dest[:-4] + ".part.gif"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-vf", f"{vf},{GIF_PALETTE}",
                        "-loop", "0", tmp], capture_output=True, text=True)
    if r.returncode or not os.path.exists(tmp):
        print(f"  gif failed {os.path.basename(dest)}: {r.stderr.strip()[-200:]}")
        if os.path.exists(tmp):
            os.remove(tmp)  # our own partial output
        return False
    os.replace(tmp, dest)
    return True


def gif_from_stills(files, dest, width, hold_s):
    """Frames padded onto one canvas (the newest frame's aspect), each held hold_s, the last held 3x as long."""
    frames = [Image.open(f).convert("RGB") for f in files]
    w = min(width, max(f.width for f in frames)) // 2 * 2
    h = min(round(w * frames[-1].height / frames[-1].width), round(w * 1.25)) // 2 * 2
    with tempfile.TemporaryDirectory() as tmp:
        for i, f in enumerate(frames + [frames[-1]] * 2):
            f = f.copy()
            f.thumbnail((w, h), Image.LANCZOS)
            canvas = Image.new("RGB", (w, h), (17, 17, 17))
            canvas.paste(f, ((w - f.width) // 2, (h - f.height) // 2))
            canvas.save(f"{tmp}/f{i:03d}.png")
        return ffmpeg_gif(["-framerate", f"{1 / hold_s:.4f}", "-i", f"{tmp}/f%03d.png"], dest, "fps=15")


def make_gifs(index):
    """Each GIF is rebuilt only when its inputs change (signature in the index). Returns how many were (re)built."""
    jobs = []  # (name, kind, title, inputs, builder)
    for mp4 in sorted(glob.glob(TURNTABLES)):
        stem = os.path.splitext(os.path.basename(mp4))[0]
        w = 560 if "grid" in stem else 420
        jobs.append((f"turntable_{slug(stem)}", "turntable", f"Character {stem.replace('_', ' ')}", [mp4],
                     lambda d, m=mp4, w=w: ffmpeg_gif(["-i", m], d, f"fps=15,scale={w}:-2:flags=lanczos")))
    for m in sorted(index["media"].values(), key=lambda m: m["rel"]):
        if m["kind"] == "clip":
            src = f"{OUT}/{m['rel']}"
            jobs.append((f"editor_{slug(os.path.splitext(os.path.basename(src))[0])}", "editor",
                         f"Editor timelapse {m['t'][11:16]} ({LANE_NAME.get(m['lane'], m['lane'])})", [src],
                         lambda d, s=src, t="5", vf="fps=15,scale=480:-2:flags=lanczos": ffmpeg_gif(["-t", t, "-i", s], d, vf)))
    groups = {}
    for folder in glob.glob(f"{FOA}/Saved/*Shots") + glob.glob(f"{FOA}/Saved/Screenshots/*"):
        if folder.endswith("UIShots") or not os.path.isdir(folder):
            continue  # UIShots duplicates Screenshots/Hayba
        for p in glob.glob(f"{folder}/*.png"):
            stem = os.path.splitext(os.path.basename(p))[0]
            if VERSION.search(stem):
                groups.setdefault(f"{os.path.basename(folder)}/{unversioned(stem)}", []).append(p)
    for key, files in sorted(groups.items()):
        files = list({sha1(f): f for f in sorted(files, key=os.path.getmtime)}.values())
        if len(files) < 3:
            continue
        motion = len(files) >= 8 and all(re.search(r"_\d{2,4}$", os.path.splitext(f)[0]) for f in files)
        folder, label = key.split("/", 1)
        jobs.append((("motion_" if motion else "iter_") + slug(key), "motion" if motion else "iteration",
                     f"{label} ({folder}): {len(files)} {'frames' if motion else 'iterations'}", files,
                     lambda d, f=files, m=motion: gif_from_stills(f[-16:], d, 720, 1 / 15 if m else 0.8)))
    for d in sorted(glob.glob(f"{SHOWCASE}/graphs/*")):
        for label, files in versions(d).items():
            if len(files) >= 3:
                name = os.path.basename(d)
                jobs.append((f"build_{slug(name)}_{slug(label)}", "graph-build",
                             f"{name} {label}: the graph over {len(files)} captures", files,
                             lambda dst, f=files: gif_from_stills(f[-16:], dst, 960, 0.8)))
    built = 0
    for name, kind, title, inputs, build in jobs:
        dest = f"{SHOWCASE}/gifs/{name}.gif"
        sig = hashlib.sha1(repr([GIF_PALETTE, build.__defaults__] + [(os.path.basename(i), os.path.getmtime(i))
                                for i in inputs]).encode()).hexdigest()  # settings in the signature: changing them rebuilds
        old = index["gifs"].get(rel(dest))
        if old and old["sig"] == sig and os.path.exists(dest):
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if build(dest):
            index["gifs"][rel(dest)] = {"kind": kind, "title": title, "sig": sig, "frames": len(inputs)}
            built += 1
    return built


# ---------- editor captures (only with --capture) ----------

def editor_lock(action, assets=()):
    """Concurrent editor leases: hold only the assets being captured. Never acquire without --assets, which would be
    an EXCLUSIVE hold that stalls every lane."""
    args = ["--assets", ",".join(assets), "--ttl", "600"] if action == "acquire" else []
    assert action != "acquire" or assets, "a devlog hold must name its assets"
    r = subprocess.run([sys.executable, f"{FOA}/Tools/Unreal/editor_lock.py", action, "devlog", *args], cwd=FOA,
                       env=os.environ | {"HAYBA_AGENT_ID": "devlog", "FOA_AGENT": "devlog"}, capture_output=True,
                       text=True, timeout=2000)
    return r.returncode == 0


def ue_capture(close="", asset="", graph="", png="", meta=""):
    """One ue_remote.py run of ue_capture.py inside our own lock hold (ue_remote reuses it because FOA_AGENT matches)."""
    r = subprocess.run([sys.executable, f"{FOA}/Tools/Unreal/ue_remote.py", f"{FOA}/Tools/Devlog/ue_capture.py",
                        f"FOA_CLOSE={close}", f"FOA_ASSET={asset}", f"FOA_GRAPH={graph}", f"FOA_PNG={png}",
                        f"FOA_META={meta}"], cwd=FOA, env=os.environ | {"FOA_AGENT": "devlog", "HAYBA_AGENT_ID": "devlog"},
                       capture_output=True, text=True, timeout=300)
    ok = r.returncode == 0 and (not asset or '"loaded": true' in r.stdout)
    if not ok:
        print(f"  ue_capture failed for {asset or close} {graph}: {(r.stdout + r.stderr).strip()[-300:]}")
    return ok


def wait_for(path, seconds):
    deadline = time.time() + seconds
    while not os.path.exists(path) and time.time() < deadline:
        time.sleep(0.5)
    return os.path.exists(path)


# Coordinator's rule: 3-5 assets per lock hold, each hold under 5 minutes; release between holds.
BATCH_ASSETS, BATCH_START_S, HOLDS_PER_RUN = 5, 180, 3  # no new asset starts after 3 min, so a hold stays under 5


def capture_asset(name, a):
    """Capture one asset's graph(s), waiting for each PNG, then close its editor. The caller holds the lock.
    Returns the number of PNGs written, or None when the editor failed (stop all captures)."""
    meta = f"{SHOWCASE}/_meta/{name}.json"
    stamp = f"{dt.datetime.now():%Y%m%d-%H%M}"
    graphs = [""]
    if a["kind"] in ("BP", "WBP", "ABP"):
        if not ue_capture(asset=a["path"], meta=meta):
            return None
        graphs = sorted((g for g in dict.fromkeys(load_json(meta, {}).get("graphs", [])) if g != "Transition"),
                        key=lambda g: g not in ("EventGraph", "AnimGraph"))[:8]
    made = 0
    for g in graphs:
        png = f"{SHOWCASE}/graphs/{name}/{slug(g) or 'graph'}_{stamp}.png"
        if not ue_capture(asset=a["path"], graph=g, png=png, meta="" if g else meta):
            made = None
            break
        made += wait_for(png, 20)
    ue_capture(close=a["path"])  # close the editor we opened before moving on
    return made


def capture_graphs(index, assets):
    """Leased batches: each hold leases only its 3-5 asset paths, captures them, closes their editors and releases.
    Skips assets whose newest capture (ours or the review lane's) is newer than their .uasset."""
    def newest(name):
        return max([os.path.getmtime(p) for ps in versions(f"{SHOWCASE}/graphs/{name}").values() for p in ps]
                   + [index["captured"].get(name, 0)])
    todo = [n for n, a in sorted(assets.items(), key=lambda kv: (kv[1]["kind"], kv[0])) if newest(n) < a["mtime"]]
    made = 0
    for _ in range(HOLDS_PER_RUN):
        if not todo:
            break
        batch, todo = todo[:BATCH_ASSETS], todo[BATCH_ASSETS:]
        if not editor_lock("acquire", [assets[n]["path"] for n in batch]):  # lease only these assets
            print("  could not get the editor lock; stopping captures")
            break
        t0, failed = time.time(), False
        try:
            while batch:
                if time.time() - t0 > BATCH_START_S:
                    todo = batch + todo  # not started: back to the front for the next hold
                    break
                name = batch.pop(0)
                n = capture_asset(name, assets[name])
                if n is None:
                    failed = True
                    break
                made += n
                index["captured"][name] = time.time()
                print(f"  captured {name}: {n} PNG(s)", flush=True)
        finally:
            editor_lock("release")
        if failed:
            print("  stopping captures after an editor failure")
            break
    return made


# ---------- page ----------

E = html.escape


def hm(iso):
    return iso[11:16]


def fig(r, caption, fid):
    return (f'<figure id="{E(fid)}"><a href="{E(r)}"><img src="{E(r)}" loading="lazy" alt="{E(caption)}"></a>'
            f"<figcaption>{E(caption)}</figcaption></figure>")


def vid(r, caption, fid, poster=None):
    p = f' poster="{E(poster)}"' if poster else ""
    return (f'<figure id="{E(fid)}"><video controls preload="none"{p} src="{E(r)}"></video>'
            f'<figcaption><a href="{E(r)}">{E(caption)}</a></figcaption></figure>')


def vo(text):
    return f'<p class="vo">{E(text)}</p>'


def stem_id(r):
    return "m-" + os.path.splitext(os.path.basename(r))[0]


def short(a):
    m = re.search(r"/Lux3D/([^/]+)/", a)  # Lux3D imports all share generic names like "textured"
    return f"Lux3D {m.group(1)}" if m else a.rsplit("/", 1)[-1]


def shorts(paths):
    return list(dict.fromkeys(map(short, paths)))


def render_showcase(assets, index):
    notes = load_json(f"{SHOWCASE}/notes.json", {})
    order = {"M": 0, "MF": 1, "ABP": 2, "BP": 3, "WBP": 4}
    cards, pending, n_groups, n_captured = [], [], 0, 0
    for name, a in sorted(assets.items(), key=lambda kv: (order[kv[1]["kind"]], kv[0])):
        if a["kind"] == "WBP":
            continue  # widgets get their own section
        vers = versions(f"{SHOWCASE}/graphs/{name}")
        lane = LANE_NAME.get(lane_of(a["path"]) or "", "")
        if not vers:
            pending.append(f"<tr><td>{E(name)}</td><td>{KINDS[a['kind']]}</td><td>{E(a['path'])}</td><td>{E(lane)}</td></tr>")
            continue
        n_captured += 1
        meta = load_json(f"{SHOWCASE}/_meta/{name}.json", {})
        main = next((g for g in ("graph", "AnimGraph", "EventGraph") if g in vers), next(iter(vers)))
        latest = vers[main][-1]
        crops = make_crops(index, latest)
        n_groups += len(crops)
        org = [f"{meta['nodes']} nodes"] if meta.get("nodes") is not None else []
        org.append(f"{len(crops)} titled comment groups" if crops else "no comment groups")
        org += [f"{k}: {', '.join(meta[k])}" for k in ("functions", "inputs", "outputs") if meta.get(k)]
        if len(vers) > 1:
            org.append(f"graphs captured: {', '.join(vers)}")
        if sum(map(len, vers.values())) > 1:
            org.append(f"{sum(map(len, vers.values()))} captures over time")
        folder = a["path"].rsplit("/", 1)[0].removeprefix("/Game/FoA/")
        desc = notes.get(name) or (meta.get("description") or "").split(". ")[0] or f"{KINDS[a['kind']]} in {folder}."
        extra = [fig(rel(v[-1]), f"{name} {g}", f"a-{name}-{slug(g)}") for g, v in vers.items() if g != main]
        builds = [g for g in index["gifs"] if g.startswith(f"showcase/gifs/build_{slug(name)}_")]
        cards.append(
            f'<div class="lane asset" id="a-{E(name)}"><a href="{E(rel(latest))}"><img class="graph" src="{E(rel(latest))}" '
            f'loading="lazy" alt="{E(name)} graph"></a><h4>{E(name)}</h4><p class=meta>{KINDS[a["kind"]]} · '
            f'{E(a["path"])}{" · " + E(lane) if lane else ""}</p><p>{E(desc)}</p><p class=meta>{E("; ".join(org))}</p>'
            + (f'<div class="grid">{"".join(fig(c, f"comment group {i}", "c-" + slug(c)) for i, c in enumerate(crops, 1))}'
               f'{"".join(extra)}</div>' if crops or extra else "")
            + "".join(f'<figure><img src="{E(g)}" loading="lazy" alt="{E(index["gifs"][g]["title"])}"><figcaption>'
                      f'{E(index["gifs"][g]["title"])}</figcaption></figure>' for g in builds) + "</div>")

    widgets, no_render = [], []
    for name in sorted(n for n, a in assets.items() if a["kind"] == "WBP"):
        renders = sorted(glob.glob(f"{SHOWCASE}/widgets/{name}/*.png"))
        graph = [p for ps in versions(f"{SHOWCASE}/graphs/{name}").values() for p in ps][-1:]
        if not renders and not graph:
            no_render.append(name)
            continue
        hero = renders[-1] if renders else graph[0]
        older = [fig(rel(r), os.path.basename(r)[:13], "w-" + slug(rel(r))) for r in renders[-9:-1]]
        widgets.append(
            f'<div class="lane asset" id="w-{E(name)}"><a href="{E(rel(hero))}"><img class="graph" src="{E(rel(hero))}" '
            f'loading="lazy" alt="{E(name)}"></a><h4>{E(name)}</h4><p class=meta>Widget Blueprint · {E(assets[name]["path"])}'
            f' · {len(renders)} designer renders{" · event graph captured" if graph else ""}</p>'
            + (f"<p>{E(notes[name])}</p>" if name in notes else "")
            + (f'<div class="grid">{"".join(older)}{fig(rel(graph[0]), "event graph", "w-" + name + "-graph") if graph and renders else ""}</div>'
               if older or (graph and renders) else "") + "</div>")

    kinds = [("turntable", "Character turntables"), ("editor", "Editor timelapse moments"),
             ("graph-build", "Graphs building up"), ("iteration", "Iterations"), ("motion", "Motion captures")]
    gif_html = ""
    for kind, title in kinds:
        items = sorted((r, g) for r, g in index["gifs"].items() if g["kind"] == kind)
        if items:
            gif_html += f"<h4>{title}</h4><div class='grid wide'>" + "".join(
                f'<figure id="gif-{E(slug(os.path.basename(r)[:-4]))}"><img src="{E(r)}" loading="lazy" alt="{E(g["title"])}">'
                f'<figcaption>{E(g["title"])}</figcaption></figure>' for r, g in items) + "</div>"
    count = Counter(a["kind"] for a in assets.values())
    beat = (f"Built in the editor so far: {count['M']} materials, {count['MF']} material functions, {count['WBP']} widget "
            f"blueprints and {count['ABP'] + count['BP']} blueprints. {n_captured} graphs are captured whole at 1:1, with "
            f"{n_groups} titled comment groups between them, so every node label stays readable.")
    return ('<section id="built"><h2>Built in the editor</h2><p>Every authored material, material function, Blueprint and '
            "widget under /Game/FoA, captured straight from the editor with the FoAGraphTools plugin. Crops zoom into "
            "the titled comment groups.</p>" + vo(beat)
            + "<h3>Graphs</h3>" + ("".join(cards) or "<p class=meta>No graph captures yet.</p>")
            + (f"<details><summary class=meta>{len(pending)} graphs not captured yet</summary><div class=tablewrap><table>"
               f"<tr><th>Asset</th><th>Kind</th><th>Path</th><th>Lane</th></tr>{''.join(pending)}</table></div></details>"
               if pending else "")
            + "<h3>Widgets</h3>" + "".join(widgets)
            + (f"<p class=meta>No render yet: {E(', '.join(no_render))}</p>" if no_render else "")
            + "<h3>GIFs</h3>" + (gif_html or "<p class=meta>No GIFs yet.</p>") + "</section>")


def render(days, index, commits, tc, sources, showcase=""):
    all_bursts = [b for bs in days.values() for b in bs]
    hay_tools = Counter()
    for b in all_bursts:
        hay_tools.update(b["tools"])
    total_calls, total_err = sum(b["calls"] for b in all_bursts), sum(b["errors"] for b in all_bursts)
    out = [PAGE_HEAD.replace("{updated}", E(dt.datetime.now().strftime("%Y-%m-%d %H:%M")))]
    out.append('<nav><a href="#concept">Concept</a><a href="#toolchain">Toolchain</a><a href="#built">Built in the editor</a>'
               + "".join(f'<a href="#day-{d}">Day {i + 1} · {d}</a>' for i, d in enumerate(days)) + "</nav>")

    out.append('<section id="concept"><h2>Concept work</h2><p>The story and the look were set before the build:</p><ul>'
               + "".join(f'<li><a href="{u}">{E(n)}</a></li>' for n, u in CONCEPT_LINKS)
               + f"<li>Canva storyboard frames and mood frames: <span class=mono>{ASSETS}/storyboard</span> "
                 "(copied into each day's stills under the <i>concept</i> lane)</li></ul>"
               + vo("Before any geometry existed, the film was boarded: a storyboard, a concept board and a moodboard "
                    "locked a fully monochrome look, black sand, and splat-mesh effects instead of Niagara.") + "</section>")

    lux = tc["lux3d"]
    glb = sum("glb" in x["outputs"] for x in lux)
    ply = sum("ply" in x["outputs"] for x in lux)
    out.append('<section id="toolchain"><h2>Toolchain</h2>')
    out.append(f'<div class="lane"><h4>Hayba (editor MCP toolkit)</h4><p>Every agent edit to the open editor goes through '
               f'Hayba, which logs each tool call to <span class=mono>Saved/hayba-execution.log</span> and streams it live '
               f'in its Tool Stream panel.</p><p class=meta>{total_calls} calls logged · {len(hay_tools)} distinct tools · '
               f'{total_err} errors · top: {E(", ".join(f"{k} ×{v}" for k, v in hay_tools.most_common(6)))}</p>'
               + vo(f"The agents drive the open editor through Hayba, with Python over remote execution for imports. "
                    f"Hayba has logged {total_calls} tool calls across "
                    f"{len(hay_tools)} different tools; the most used was "
                    f"{hay_tools.most_common(1)[0][0] if hay_tools else 'none'}.") + "</div>")
    rows = "".join(f"<tr><td>{E(str(x['item']))}</td><td>{E(str(x['task']))}</td><td>{E(str(x['status']))}</td>"
                   f"<td>{E(', '.join(x['outputs']))}</td></tr>" for x in lux)
    out.append(f'<div class="lane"><h4>Lux3D (Aholo/Manycore 3D generation)</h4><p>{len(lux)} generation tasks on file: '
               f'{glb} textured meshes (GLB), {ply} Gaussian splats (PLY). Prompts and task IDs: '
               f'<a href="file:///{FOA}/docs/lux3d-bedroom-prompts.md">docs/lux3d-bedroom-prompts.md</a>.</p>'
               f'<div class=tablewrap><table><tr><th>Item</th><th>Task ID</th><th>Status</th><th>Outputs</th></tr>{rows}'
               f'</table></div>'
               + vo(f"Lux3D generated {len(lux)} assets for the bedroom and its nightmares: {glb} textured meshes and "
                    f"{ply} Gaussian splats, each traceable to a task ID.") + "</div>")
    out.append(f'<div class="lane"><h4>Splat meshes</h4><p>Lux3D splats converted to splat-mesh glTFs by '
               f'<span class=mono>Tools/Splats</span>: {E(", ".join(tc["splats"]) or "none yet")}.</p>'
               + vo(f"No Niagara for the hero effects. {len(tc['splats'])} Lux3D splats were baked into splat meshes, "
                    "so the sand renders as geometry with materials.") + "</div>")
    out.append(f'<div class="lane"><h4>Poly Haven and audio</h4><p>{tc["polyhaven"] or 0} CC0 Poly Haven assets in '
               f'<span class=mono>FoA-Assets/polyhaven/MANIFEST.md</span>; {tc["audio"] or 0} audio files in '
               f'<span class=mono>FoA-Assets/audio/MANIFEST.md</span>, each with its source and license recorded.</p>'
               + vo(f"Real-world furniture and surfaces came from Poly Haven, {tc['polyhaven'] or 0} CC0 assets, and the "
                    f"sound from {tc['audio'] or 0} CC0 or generated audio files.") + "</div>")
    out.append('<div class="lane"><h4>Agent lanes</h4><p>Parallel AI agent lanes share one open Unreal editor, each '
               'with its own actors, assets and folders, under the shared rules in '
               '<span class=mono>docs/agents/editor-rules.md</span>. Lane attribution on this page is inferred from asset '
               'paths and names.</p><div class=tablewrap><table><tr><th>Lane</th><th>Brief</th></tr>'
               + "".join(f"<tr><td>{E(n)}</td><td>{E(b)}</td></tr>" for s, n, b, _ in LANES)
               + "</table></div>" + vo(f"The team: two humans, plus {len(LANES) - 1} AI agent lanes working in the same "
                                       "editor at once, each in its own lane.") + "</div></section>")

    out.append(showcase)
    media_by_day = {}
    for m in index["media"].values():
        media_by_day.setdefault(m["rel"][:10], []).append(m)
    for i, (day, bursts) in enumerate(days.items()):
        out.append(render_day(i + 1, day, bursts, [s for s in index["stills"].values() if s["rel"].startswith(day)],
                              media_by_day.get(day, []), [c for c in commits if c["time"].startswith(day)]))

    out.append('<section id="sources"><h2>Sources</h2><div class=tablewrap><table><tr><th>Source</th><th>Path</th>'
               '<th>Status</th></tr>' + "".join(f"<tr><td>{E(n)}</td><td>{E(p)}</td><td>{E(s)}</td></tr>"
                                               for n, p, s in sources) + "</table></div></section></main></body></html>")
    return "\n".join(out)


def render_day(n, day, bursts, stills, media, commits):
    date = dt.date.fromisoformat(day)
    stills = sorted(stills, key=lambda s: s["rel"])
    frames = [m for m in media if m["kind"] in ("before", "after")]
    clips = sorted((m for m in media if m["kind"] in ("clip", "timelapse")), key=lambda m: m["rel"])
    notes = load_json(f"{OUT}/{day}/notes.json", {})
    changed = [b for b in bursts if b["changes"]]
    calls, errs = sum(b["calls"] for b in bursts), sum(b["errors"] for b in bursts)
    assets = sorted({a for b in bursts for a in b["assets"] + b["imports"] + b["actors"]})
    by_lane = {}
    for a in assets:
        by_lane.setdefault(lane_of(a) or "editor", []).append(a)
    shots_by_lane = {}
    for s in stills + frames:
        shots_by_lane.setdefault(s["lane"], []).append(s)
    active = [s for s in list(LANE_NAME) if s != "timelapse" and (s in by_lane or s in shots_by_lane or s in notes)]
    err_kinds = Counter()
    for b in bursts:
        err_kinds.update(b["error_kinds"])

    o = [f'<section class="day" id="day-{day}"><h2>Day {n} · {date:%A %d %B %Y}</h2><div class="stats">'
         + "".join(f"<div><b>{v}</b>{k}</div>" for k, v in [
             ("lanes with output", len([s for s in active if s not in ("editor", "concept")])), ("Hayba calls", calls),
             ("bursts", len(bursts)), ("errors", errs), ("assets touched", len(assets)),
             ("stills", len(stills) + len(frames)), ("clips", len(clips))]) + "</div>"]
    beat = (f"{date:%B} {date.day}. Hayba logged {calls} tool calls in {len(bursts)} bursts of activity"
            + (f" between {hm(bursts[0]['start'])} and {hm(bursts[-1]['end'])}" if bursts else "")
            + f"; {errs} came back as errors. {len(assets)} assets and actors were touched.")
    if commits:
        beat += f" {len(commits)} commits landed in git."
    o.append(vo(beat))
    if err_kinds:
        k, v = err_kinds.most_common(1)[0]
        o.append(vo(f"The most common failure, {v} times: “{k}”. The lane rules route that work to other tools."))

    hl = [b for b in bursts if b.get("highlight")]
    crashes = [b for b in bursts if b.get("crashes")]
    if hl or crashes:
        o.append("<h3>Highlights</h3>")
        if crashes:
            o.append(f"<p class=meta>Editor crashes: {', '.join(hm(b['end']) for b in crashes)}. Bursts in the 20 minutes "
                     "after each crash are marked as recovery work.</p>")
        rows = []
        for b in hl:
            ms = sorted((m for m in media if m.get("burst") == f"{day}/{b['id']}"), key=lambda m: m["rel"])
            why = [LANE_NAME[x] for x in b["lanes"] if x in HIGHLIGHT_LANES] or ["after a crash"]
            clip = next((m for m in ms if m["kind"] == "clip"), None)
            frames = {m["kind"]: m for m in ms if m["kind"] in ("before", "after")}
            body = vid(clip["rel"], os.path.basename(clip["rel"]), "h" + stem_id(clip["rel"]),
                       frames["after"]["rel"] if "after" in frames else None) if clip else (
                "<p class=meta>No clip: the editor was not in front long enough, or the recording segment is still "
                "open.</p>")
            rows.append(f'<div class="lane"><h4>{hm(b["start"])}–{hm(b["end"])} · {E(", ".join(why))}</h4>'
                        f'<p class=meta>{E(b["label"])}</p>{body}</div>')
        o.append("".join(rows))
        o.append(vo(f"The big moments: {len(hl)} bursts where the look changed or the team recovered from a crash"
                    + (f", and {len(crashes)} editor crash{'es' if len(crashes) > 1 else ''} along the way." if crashes else ".")))
    o.append("<h3>Lanes</h3>")
    for s in active:
        lane_assets, shots = by_lane.get(s, []), sorted(shots_by_lane.get(s, []), key=lambda x: x["rel"])
        lb = [b for b in bursts if s in b["lanes"] or (s == "editor" and not b["lanes"] and b["changes"])]
        o.append(f'<div class="lane" id="{day}-{s}"><h4>{E(LANE_NAME[s])}</h4><p><b>Set out to:</b> {E(LANE_BRIEF[s])}</p>')
        if lane_assets:
            names = shorts(lane_assets)
            o.append(f"<p><b>Landed in the editor:</b> <span class=mono>{E(', '.join(names[:14]))}"
                     f"{' …' if len(names) > 14 else ''}</span></p>")
        if lb:
            o.append(f"<p class=meta>Active in {len(lb)} bursts, {hm(lb[0]['start'])}–{hm(lb[-1]['end'])}: "
                     + ", ".join(f'<a href="#{day}-{b["id"]}">{hm(b["start"])}</a>' for b in lb) + "</p>")
        if s in notes:
            o.append(f"<p><b>Lane report:</b> {E(str(notes[s]))}</p>")
        if shots:
            o.append('<div class="grid">' + "".join(fig(x["rel"], os.path.basename(x["rel"]), stem_id(x["rel"]))
                                                    for x in shots) + "</div>")
        bits = [f"{LANE_NAME[s]}. The brief: {LANE_BRIEF[s]}"]
        if lane_assets:
            bits.append(f"It put {len(lane_assets)} assets into the project, including "
                        + ", ".join(shorts(lane_assets)[:3]) + ".")
        if shots:
            bits.append(f"{len(shots)} stills on file, from {shots[0]['t'][11:16]} to {shots[-1]['t'][11:16]}.")
        o.append(vo(" ".join(bits)) + "</div>")

    o.append("<h3>Before / after</h3>")
    pairs = []
    by_burst = {}
    for f in frames:
        by_burst.setdefault(f["burst"], {})[f["kind"]] = f
    for bid, pr in sorted(by_burst.items()):
        if "before" in pr and "after" in pr:
            pairs.append((pr["before"], pr["after"], f"Recording, burst {bid.split('/')[1]} ({LANE_NAME.get(pr['after']['lane'], '')})"))
    by_src = {}
    for s in stills:
        by_src.setdefault(s["src"], []).append(s)
    for src, vs in by_src.items():
        vs.sort(key=lambda x: x["t"])
        pairs += [(a, b, f"{os.path.basename(src)}: {a['t'][11:16]} → {b['t'][11:16]}") for a, b in zip(vs, vs[1:])]
    if pairs:
        o.append('<div class="grid wide">' + "".join(
            f'<div class="pair-wrap"><div class="pair">{fig(a["rel"], "before", "p" + stem_id(a["rel"]))}'
            f'{fig(b["rel"], "after", "p" + stem_id(b["rel"]))}</div><p class=meta>{E(c)}</p></div>' for a, b, c in pairs)
            + "</div>")
    else:
        o.append("<p class=meta>No pairs yet. They come from finished 30-minute recording segments (frames just before and "
                 "after each burst) and from lanes re-saving the same screenshot.</p>")

    o.append("<h3>Clips</h3>")
    o.append('<div class="grid wide">' + "".join(vid(c["rel"], os.path.basename(c["rel"]), stem_id(c["rel"]))
                                                 for c in clips) + "</div>" if clips else
             "<p class=meta>No clips yet: a recording segment becomes readable once its 30 minutes close.</p>")

    o.append(f"<h3>Timeline</h3><p class=meta>{len(bursts)} bursts ({len(changed)} with changes). A burst is Hayba, "
             "editor-log and file activity with no gap longer than 2 minutes, capped at 10 minutes. Full events: "
             f'<a href="{day}/timeline.json">{day}/timeline.json</a>.</p><div class=tablewrap><table>'
             "<tr><th>Time</th><th>Lanes</th><th>What changed</th><th>Errors</th><th>Media</th></tr>")
    for b in bursts:
        links = [m for m in media if m.get("burst") == f"{day}/{b['id']}"]
        o.append(f'<tr id="{day}-{b["id"]}"><td class=mono>{hm(b["start"])}–{hm(b["end"])}</td>'
                 f'<td>{E(", ".join(LANE_NAME.get(x, x) for x in b["lanes"]) or "–")}</td><td>{E(b["label"])}'
                 f'{"" if b["changes"] else " <i>(read-only)</i>"}</td><td>{b["errors"] or ""}</td><td>'
                 + " ".join(f'<a href="#{stem_id(m["rel"])}">{m["kind"]}</a>' for m in links) + "</td></tr>")
    o.append("</table></div>")
    if commits:
        o.append("<h3>Git</h3><ul>" + "".join(f"<li><span class=mono>{E(c['hash'])} {c['time'][11:16]}</span> "
                                              f"{E(c['subject'])}</li>" for c in commits[::-1]) + "</ul>")
    return "\n".join(o) + "</section>"


PAGE_HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>FoA Devlog</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#0b0b0b;--fg:#ebe8e2;--mute:#9b978f;--line:#2a2a28;--card:#131312;--hi:#f6f3ec}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 "IBM Plex Sans",system-ui,sans-serif}
main{max-width:1180px;margin:0 auto;padding:0 16px 96px}a{color:var(--hi)}
h1,h2,h3,h4{font-family:"Cormorant Garamond",Georgia,serif;font-weight:500;letter-spacing:.01em;margin:0}
h1{font-size:clamp(36px,7vw,72px);line-height:1;margin-top:56px}h2{font-size:clamp(28px,4vw,40px);margin:72px 0 14px;padding-top:24px;border-top:1px solid var(--line)}
h3{font-size:26px;margin:40px 0 12px}h4{font-size:22px;margin-bottom:6px}
.sub{color:var(--mute);margin:8px 0 24px}.mono,.meta,td,figcaption{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12.5px}
.meta{color:var(--mute)}nav{display:flex;flex-wrap:wrap;gap:6px 18px;padding:12px 0;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:2}
nav a{color:var(--mute);text-decoration:none;font-size:13px}nav a:hover{color:var(--fg)}
.stats{display:flex;flex-wrap:wrap;gap:12px 28px;color:var(--mute);font-size:13px}.stats b{display:block;color:var(--fg);font:500 32px "Cormorant Garamond",serif}
.vo{border-left:2px solid var(--hi);background:#111110;padding:8px 14px;margin:14px 0;font-style:italic}
.vo::before{content:"VO";display:block;font:500 11px "IBM Plex Mono",monospace;letter-spacing:.14em;color:var(--mute);font-style:normal}
.lane{background:var(--card);border:1px solid var(--line);padding:16px 18px;margin:14px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin:10px 0}.grid.wide{grid-template-columns:repeat(auto-fill,minmax(min(100%,420px),1fr))}
figure{margin:0;background:#000;border:1px solid var(--line)}figure img,figure video{display:block;width:100%;aspect-ratio:16/10;object-fit:cover;background:#000}
figcaption{padding:6px 8px;color:var(--mute);word-break:break-all;background:var(--card)}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:4px}.pair-wrap p{margin:4px 0 0}
.asset img.graph{display:block;width:100%;height:auto;max-height:560px;object-fit:contain;background:#5a5a5a;margin-bottom:10px}
.asset h4{margin-top:4px}details{margin:10px 0}summary{cursor:pointer}
.tablewrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px}th{text-align:left;color:var(--mute);font-weight:500}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;vertical-align:top}td{word-break:break-word}
</style></head><body><main>
<h1>The Nightmare of Responsibility</h1>
<p class="sub">FoA devlog · Unreal 5.8 · Aholo/Manycore 3D AI hackathon · built by two humans and parallel AI agent lanes · updated {updated}</p>"""


RUN_LOCK = f"{OUT}/_build.lock"


def main():
    """Only one build at a time: overlapping runs would overwrite each other's _index.json."""
    os.makedirs(OUT, exist_ok=True)
    try:
        fd = os.open(RUN_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if time.time() - os.path.getmtime(RUN_LOCK) < 3 * 3600:
            sys.exit(f"another build_devlog run is in progress ({RUN_LOCK}); try again later")
        os.remove(RUN_LOCK)  # left behind by a killed run
        fd = os.open(RUN_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    try:
        build()
    finally:
        os.remove(RUN_LOCK)


def build():
    selftest()
    index = load_json(f"{OUT}/_index.json", {})
    for k in ("stills", "media", "showcase", "crops", "gifs", "captured", "skipped"):
        index.setdefault(k, {})

    scene, labels = scene_events()
    fresh = [e for e in hayba_events() + ue_events() + list(file_events()) if e]
    stored = [e for p in glob.glob(f"{OUT}/????-??-??/timeline.json")
              for b in load_json(p, {}).get("bursts", []) for e in b.get("events", [])]
    events = list({ekey(e): e for e in stored + fresh}.values()) + scene  # stored first so fresh wins on equal keys

    by_day = {}
    for e in events:
        by_day.setdefault(to_local(e["utc"]).strftime("%Y-%m-%d"), []).append(e)
    days = {d: [summarize(g, labels, d) for g in group_bursts(by_day[d])] for d in sorted(by_day)}
    crash_times = sorted(to_local(e["utc"]) for e in events if e["kind"] == "crash")
    for b in (b for bs in days.values() for b in bs):
        t = dt.datetime.fromisoformat(b["start"])
        b["highlight"] = b["changes"] and (bool(HIGHLIGHT_LANES & set(b["lanes"]))
                                           or any(0 < (t - c).total_seconds() <= POST_CRASH_S for c in crash_times))

    new_stills = collect_stills(index)
    segs = segments()
    new_media = cut_media(index, days, segs)
    assets = graph_assets()
    shots = ingest_graph_shots(index, assets) + ingest_widget_renders(index, assets)  # reuse lane/review captures first
    captured = capture_graphs(index, assets) if "--capture" in sys.argv else 0
    shots += ingest_graph_shots(index, assets)
    showcase = render_showcase(assets, index)  # also makes any missing comment-group crops
    new_gifs = make_gifs(index)
    showcase = render_showcase(assets, index)  # again, so GIFs made this run appear
    write_if_changed(f"{OUT}/_index.json", json.dumps(index, indent=1, ensure_ascii=False))

    commits = git_commits()
    for d, bursts in days.items():
        for b in bursts:
            ms = [m for m in index["media"].values() if m.get("burst") == f"{d}/{b['id']}"]
            b["clips"] = sorted(m["rel"] for m in ms if m["kind"] == "clip")
            b["frames"] = sorted(m["rel"] for m in ms if m["kind"] in ("before", "after"))
        write_if_changed(f"{OUT}/{d}/timeline.json", json.dumps(
            {"date": d, "timezone": f"local (UTC{dt.datetime.now().astimezone():%z})",
             "commits": [c for c in commits if c["time"].startswith(d)], "bursts": bursts}, indent=1, ensure_ascii=False))

    sources = source_status(segs)
    write_if_changed(f"{OUT}/index.html", render(days, index, commits, toolchain(), sources, showcase))

    n_still = len(index["stills"]) + sum(m["kind"] in ("before", "after") for m in index["media"].values())
    n_clip = sum(m["kind"] in ("clip", "timelapse") for m in index["media"].values())
    print(f"Days: {', '.join(f'{OUT}/{d}' for d in days)}")
    print(f"Stills: {n_still} total ({new_stills} copied this run); clips: {n_clip} total; media rendered this run: {new_media}")
    print(f"Bursts: {sum(len(b) for b in days.values())}; events: {len(events)}")
    graphs_now = sum(bool(versions(f"{SHOWCASE}/graphs/{n}")) for n, a in assets.items() if a["kind"] != "WBP")
    print(f"Showcase: {graphs_now}/{sum(a['kind'] != 'WBP' for a in assets.values())} graphs captured "
          f"({captured} captured in the editor, {shots} lane captures/renders ingested this run); "
          f"{sum(map(len, index['crops'].values()))} comment-group crops; "
          f"{sum(bool(glob.glob(f'{SHOWCASE}/widgets/{n}/*.png')) for n, a in assets.items() if a['kind'] == 'WBP')}/"
          f"{sum(a['kind'] == 'WBP' for a in assets.values())} widgets rendered; {len(index['gifs'])} GIFs ({new_gifs} built this run)")
    for name, path, status in sources:
        if status != "found":
            print(f"Source {status}: {name} ({path})")
    print(f"Page: {OUT}/index.html")


if __name__ == "__main__":
    main()
