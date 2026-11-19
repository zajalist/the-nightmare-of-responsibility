"""Offline content audit (phase 1): classify every /Game package and write Saved/Cleanup/audit.json.

  python Tools/Cleanup/audit.py

Inputs: Saved/Cleanup/registry/chunk_*.json (from registry_dump.py, run read-only in the editor), Config/*.ini,
every text file under Tools/, and the bytes of every package under Content/ (string soft references and the
package-trailer payload hashes that identify identical texture source data). Touches nothing under Content.

Classes: a = reached from the game's roots over registry edges; b = not a, but a Tools script names it (or it hangs
off one that does); c = unreferenced, a deletion candidate; d = unsure (reached only through a raw string inside
some package, only from the template map, or a test leftover that a Tools QA script still names).
"""
import collections
import fnmatch
import glob
import json
import os
import re
import struct
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONTENT = os.path.join(ROOT, "Content")
OUT = os.path.join(ROOT, "Saved", "Cleanup", "audit.json")

# Retired by the user (MetaHuman player replaced by the MakeHuman teen): deletable even though old mh_* scripts name it.
APPROVED_RETIRE = ("/Game/FoA/Characters/Protagonist/", "/Game/Fab/MetaHuman/")
TEMPLATE_MAP = "/Game/ThirdPerson/Lvl_ThirdPerson"
TEST_SEGMENTS = re.compile(r"/(_QA|_FingerQA|_HeroRigTest|TMP_[^/]*|Test[^/]*|Scratch[^/]*|Probe[^/]*)(/|$)", re.I)
TOKEN = re.compile(rb"/Game/[A-Za-z0-9_\-./]+")
TOKEN16 = re.compile(rb"/\x00G\x00a\x00m\x00e\x00/\x00(?:[A-Za-z0-9_\-./]\x00)+")
TEXT_EXT = {".py", ".ps1", ".sh", ".json", ".txt", ".csv", ".md", ".html", ".bat", ".cmd", ".ini", ".hlsl"}
COMPRESSED = re.compile(r"^(DXT|BC|ASTC|ETC|PF_DXT|PF_BC)", re.I)
# Only these can load an asset from a string at runtime (LoadAsset/LoadClass pins, DataTable or level-script strings).
# Raw paths inside meshes, anims and materials are import metadata (Interchange source data, retarget source), not loads.
STRING_SOURCES = {"Blueprint", "WidgetBlueprint", "AnimBlueprint", "DataTable", "CurveTable", "StringTable", "World",
                  "LevelSequence"}
BPP = {"DXT1": .5, "BC4": .5, "DXT3": 1, "DXT5": 1, "BC5": 1, "BC6H": 1, "BC7": 1, "G8": 1, "G16": 2,
       "B8G8R8A8": 4, "R8G8B8A8": 4, "FloatRGBA": 8, "A16B16G16R16": 8, "R16F": 2, "R32F": 4}


def pkg_file(pkg):
    rel = pkg[len("/Game/"):].replace("/", os.sep)
    for ext in (".uasset", ".umap"):
        f = os.path.join(CONTENT, rel + ext)
        if os.path.exists(f):
            return f
    return None


def to_pkg(token, packages):
    """'/Game/A/B.B_C' -> ('asset', '/Game/A/B'); folder or name prefix -> ('prefix', p); else (None, p)."""
    t = token.rstrip("/.'\"")
    last = t.rfind("/")
    dot = t.find(".", last)
    p = t[:dot] if dot >= 0 else t
    if p in packages:
        return "asset", p
    if p.endswith("_C") and p[:-2] in packages:
        return "asset", p[:-2]
    if any(k.startswith(p) for k in packages):
        return "prefix", p
    return None, p


def trailer(path):
    """[(payload hash hex, bytes on disk, raw size)] from the UE5 package trailer: the editor bulk data (texture source pixels)."""
    with open(path, "rb") as fh:
        fh.seek(0, 2)
        size = fh.tell()
        if size < 48:
            return []
        fh.seek(size - 20)
        tag, tlen, _ = struct.unpack("<QQI", fh.read(20))
        if tag != 0x29BFCA045138DE76 or tlen > size:
            return []
        fh.seek(size - tlen)
        head = fh.read(min(tlen, 4096))
    htag, _ver, hlen, _plen = struct.unpack_from("<QiIQ", head, 0)
    if htag != 0xD1C43B2E80A5F697:
        return []
    n = struct.unpack_from("<i", head, 24)[0]
    o = 28 + (1 if n and hlen - 28 - 49 * n == 1 else 0)  # legacy trailers carry one access-mode byte here
    out = []
    for _ in range(n):
        out.append((head[o:o + 20].hex(), *struct.unpack_from("<qq", head, o + 28)))  # after hash and offset
        o += 49
    return out


def main():
    reg = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "Saved", "Cleanup", "registry", "chunk_*.json"))):
        reg.update(json.load(open(f, encoding="utf-8"))["packages"])
    packages = set(reg)

    info = {}
    for p, r in reg.items():
        f = pkg_file(p)
        main_asset = next((a for a in r["assets"] if a["name"] == p.rsplit("/", 1)[1]), r["assets"][0])
        info[p] = {"class": main_asset["class"], "size": os.path.getsize(f) if f else 0, "file": f,
                   "tags": main_asset["tags"],
                   "hard": [d for d in r["hard"] if d in packages and d != p],
                   "soft": [d for d in r["soft"] if d in packages and d != p]}
    on_disk = set()
    for dp, _, fs in os.walk(CONTENT):
        for n in fs:
            if n.endswith((".uasset", ".umap")):
                rel = os.path.relpath(os.path.join(dp, n), CONTENT).rsplit(".", 1)[0].replace(os.sep, "/")
                on_disk.add("/Game/" + rel)

    # Raw '/Game/...' strings inside each package (Blueprint LoadAsset/LoadClass pins, DataTable strings, ...).
    strings = {}
    for p, i in info.items():
        if not i["file"] or not (i["class"] in STRING_SOURCES or i["class"].endswith("DataAsset")
                                 or reg[p]["assets"][0]["class_pkg"].startswith("/Game/")):
            continue
        data = open(i["file"], "rb").read()
        toks = {m.group(0).decode("ascii", "ignore") for m in TOKEN.finditer(data)}
        toks |= {m.group(0)[::2].decode("ascii", "ignore") for m in TOKEN16.finditer(data)}
        hits = {q for kind, q in (to_pkg(t, packages) for t in toks) if kind == "asset"}
        strings[p] = sorted(hits - {p} - set(i["hard"]) - set(i["soft"]))

    # Config roots.
    cfg_roots = {}
    for f in glob.glob(os.path.join(ROOT, "Config", "*.ini")):
        for ln, line in enumerate(open(f, encoding="utf-8", errors="replace"), 1):
            if line.lstrip().startswith(";"):
                continue
            for t in TOKEN.findall(line.encode()):
                kind, q = to_pkg(t.decode(), packages)
                if kind == "asset":
                    cfg_roots.setdefault(q, []).append(f"Config/{os.path.basename(f)}:{ln}")

    # Tools references: exact assets are build-input roots; folder/name prefixes only matter for moves.
    tool_assets, tool_prefixes, tool_missing = collections.defaultdict(set), collections.defaultdict(set), set()
    for dp, dirs, fs in os.walk(os.path.join(ROOT, "Tools")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        if os.path.normcase(dp).startswith(os.path.normcase(os.path.join(ROOT, "Tools", "Cleanup"))):
            continue
        for n in fs:
            if os.path.splitext(n)[1].lower() not in TEXT_EXT:
                continue
            f = os.path.join(dp, n)
            rel = os.path.relpath(f, ROOT).replace(os.sep, "/")
            text = open(f, "rb").read()
            here = set()
            for t in TOKEN.findall(text):
                kind, q = to_pkg(t.decode("ascii", "ignore"), packages)
                if kind == "asset":
                    tool_assets[q].add(rel)
                elif kind == "prefix":
                    tool_prefixes[q].add(rel)
                    here.add(t.decode("ascii", "ignore").rstrip("'\""))
                elif len(q) > len("/Game/"):
                    tool_missing.add(q)
            # SFX = "/Game/FoA/Audio/SFX/" ... load_asset(SFX + "Bed/SFX_Bed_Sit_01"): compose prefix + literal.
            # shortcut: same-file composition only; a prefix imported from another module is missed (rare, see plan).
            if here:
                for lit in set(re.findall(rb"[\"']([A-Za-z0-9_][A-Za-z0-9_/.\-]*)[\"']", text)):
                    lit = lit.decode("ascii", "ignore")
                    for pre in here:
                        glue = "" if pre.endswith(("/", "_")) else "/"
                        kind, q = to_pkg(pre + glue + lit, packages)
                        if kind == "asset":
                            tool_assets[q].add(rel)

    def closure(roots, edges):
        parent = {r: None for r in roots if r in info}
        todo = list(parent)
        while todo:
            p = todo.pop()
            for d in edges(p):
                if d not in parent:
                    parent[d] = p
                    todo.append(d)
        return parent

    reg_edges = lambda p: info[p]["hard"] + info[p]["soft"]
    all_edges = lambda p: reg_edges(p) + strings.get(p, [])
    template = {p for p in info if p == TEMPLATE_MAP or p.startswith("/Game/__External") and "/Lvl_ThirdPerson/" in p}
    game_roots = sorted(set(cfg_roots) | {p for p in info if info[p]["class"] == "World"} - template)
    runtime = closure(game_roots, reg_edges)
    runtime_str = closure(game_roots, all_edges)
    template_cl = closure(sorted(template), reg_edges)
    tools = closure(sorted(tool_assets), all_edges)

    referencers = collections.defaultdict(set)
    for p in info:
        for d in all_edges(p):
            referencers[d].add(p)

    def chain(parent, p, n=6):
        out = []
        while p is not None and len(out) < n:
            out.append(p)
            p = parent.get(p)
        return out

    lanes = json.load(open(os.path.join(ROOT, "Saved", "QA", "lanes.json"), encoding="utf-8"))
    now = time.time()
    assets = {}
    for p, i in sorted(info.items()):
        test = bool(TEST_SEGMENTS.search(p))
        retire = p.startswith(APPROVED_RETIRE)
        note = ""
        if i["class"] == "ObjectRedirector":
            cls, note = "c", "redirector: fix up, then it goes"
        elif p in runtime:
            cls, note = "a", " <- ".join(chain(runtime, p))
        elif p in template_cl:
            cls, note = "d", "used only by the template map Lvl_ThirdPerson"
        elif p in runtime_str:
            cls, note = "d", "reached from the game only through a raw string in: " + ", ".join(
                sorted(r for r in referencers[p] if r in runtime_str)[:4])
        elif retire:
            cls, note = "c", "retired MetaHuman player (user-approved)" + (
                "; dead Tools refs: " + ", ".join(sorted(tool_assets[p])[:3]) if tool_assets.get(p) else "")
        elif p in tools and test:
            cls, note = "d", "test leftover still named by: " + ", ".join(sorted(tool_assets.get(p) or {"(dependency)"})[:3])
        elif p in tools:
            cls = "b"
            note = "named by " + ", ".join(sorted(tool_assets[p])[:4]) if p in tool_assets else \
                "dependency of Tools-named " + " <- ".join(chain(tools, p, 3)[1:])
        else:
            cls = "c"
            live = sorted(referencers[p])
            note = ("test leftover; " if test else "") + ("referenced only by other candidates: " + ", ".join(live[:3])
                                                         if live else "no referencers")
        rel = os.path.relpath(i["file"], ROOT).replace(os.sep, "/") if i["file"] else ""
        assets[p] = {"class": cls, "type": i["class"], "bytes": i["size"], "note": note,
                     "owner": next((ln for ln, globs in lanes.items() if any(fnmatch.fnmatch(rel, g) for g in globs)), ""),
                     "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(i["file"]))) if rel else "",
                     "recent": bool(rel) and now - os.path.getmtime(i["file"]) < 48 * 3600,
                     "tools": sorted(tool_assets.get(p, ())),
                     "deps": sorted(set(reg_edges(p))),
                     "referencers": sorted(referencers[p])}

    # Textures: oversize, uncompressed, duplicate source pixels; plus a rough cooked-size estimate.
    mesh_size = {}
    for p, i in info.items():
        if "ApproxSize" in i["tags"]:
            try:
                mesh_size[p] = max(float(x) for x in i["tags"]["ApproxSize"].split("x"))
            except ValueError:
                pass

    def meshes_using(tex):
        seen, todo, found = {tex}, [tex], []
        for _ in range(5):
            nxt = []
            for q in todo:
                for r in referencers[q]:
                    if r not in seen:
                        seen.add(r)
                        (found if r in mesh_size else nxt).append(r)
            todo = nxt
        return found

    textures, dup_groups = [], collections.defaultdict(list)
    for p, i in info.items():
        if not i["class"].startswith("Texture") or "Dimensions" not in i["tags"]:
            continue
        w, h = (int(x) for x in re.findall(r"\d+", i["tags"]["Dimensions"])[:2])  # "WxH", "WxH*slices"
        cap = int(i["tags"].get("MaxTextureSize", "0") or 0)
        if cap and max(w, h) > cap:  # cooked size honours MaxTextureSize
            w, h = max(1, w * cap // max(w, h)), max(1, h * cap // max(w, h))
        fmt = i["tags"].get("Format", "")
        ui = "/UI/" in p
        meshes = meshes_using(p)
        small = bool(meshes) and max(mesh_size[m] for m in meshes) <= 60
        limit = 1024 if (ui or small) else 2048
        payload = trailer(i["file"]) if i["file"] else []
        if payload:
            dup_groups[tuple(sorted(h for h, _, _ in payload))].append(p)
        textures.append({"path": p, "w": w, "h": h, "format": fmt, "compression": i["tags"].get("CompressionSettings"),
                         "lod_group": i["tags"].get("LODGroup"), "max_size": i["tags"].get("MaxTextureSize"),
                         "bytes": i["size"], "class": assets[p]["class"], "ui": ui, "small_prop": small,
                         "oversized": max(w, h) > limit, "limit": limit,
                         "uncompressed": bool(fmt) and not COMPRESSED.match(fmt),
                         "cooked_est": int(w * h * BPP.get(fmt, 1) * 4 / 3)})
    dups = [sorted(g) for g in dup_groups.values() if len(g) > 1]
    tex_cooked = {t["path"]: t["cooked_est"] for t in textures}

    def cooked(p):
        i = info[p]
        if i["class"].startswith("Texture") and "Dimensions" in i["tags"]:
            return tex_cooked[p]
        payloads = trailer(i["file"]) if i["file"] else []
        editor_only = sum(s for _, s, _ in payloads)
        if i["class"] == "SoundWave":  # shortcut: raw PCM -> ~1/8 for compressed audio; measure a real cook to upgrade
            return int(sum(r for _, _, r in payloads) / 8) + max(0, i["size"] - editor_only)
        return max(0, i["size"] - editor_only)

    for p in assets:
        assets[p]["cooked_est"] = cooked(p)

    # Deletion tiers for class c. T1: user-approved (retired MetaHuman). T2: plain leftovers (tests, backups, importer
    # leftovers next to the used asset, unused copies of used textures, unused template content). T3: owning lane confirms.
    dup_of_used = {q for g in dups if any(assets[x]["class"] == "a" for x in g) for q in g if assets[q]["class"] == "c"}
    used_roots = {"/".join(q.split("/")[:5]) for q, a in assets.items() if a["class"] == "a"
                  and q.startswith(("/Game/FoA/Props/", "/Game/FoA/Lux3D/", "/Game/FoA/Door/", "/Game/FoA/Dressing/"))}
    for q, a in assets.items():
        if a["class"] != "c":
            continue
        if a["type"] == "ObjectRedirector":
            a["tier"] = "fixup"
        elif q.startswith(APPROVED_RETIRE):
            a["tier"] = "T1"
        elif (TEST_SEGMENTS.search(q) or re.search(r"(_Before\w*|_\d{6})$", q) or q.startswith("/Game/LevelPrototyping/")
              or q in dup_of_used or ("/".join(q.split("/")[:5]) in used_roots
                                      and a["type"] in ("Texture2D", "Material", "MaterialInstanceConstant"))):
            a["tier"] = "T2"
        else:
            a["tier"] = "T3"
    # Anything unused that still points into the retired MetaHuman (suit/boots on its skeleton, its face ABP, the MH
    # retargeter) goes with it: otherwise the delete-time reference check would keep the MetaHuman pieces alive.
    changed = True
    while changed:
        changed = False
        for q, a in assets.items():
            if a["class"] in ("b", "c") and a.get("tier") != "T1":
                hit = [x for x in a["deps"] if assets.get(x, {}).get("tier") == "T1"]
                if hit:
                    a.update({"class": "c", "tier": "T1", "note": f"depends on the retired MetaHuman ({hit[0]}); "
                              + (f"dead Tools refs: {', '.join(a['tools'][:3])}" if a["tools"] else a["note"])})
                    changed = True

    empty, has_files = [], set()
    for dp, dirs, fs in os.walk(CONTENT, topdown=False):  # bottom-up: a folder is empty when no file is below it
        if fs or any(os.path.join(dp, d) in has_files for d in dirs):
            has_files.add(dp)
        elif dp != CONTENT:
            empty.append(os.path.relpath(dp, ROOT).replace(os.sep, "/"))

    totals = collections.defaultdict(lambda: {"count": 0, "bytes": 0, "cooked_est": 0})
    for a in assets.values():
        for key in (a["class"], "c:" + a["tier"]) if "tier" in a else (a["class"],):
            t = totals[key]
            t["count"] += 1
            t["bytes"] += a["bytes"]
            t["cooked_est"] += a["cooked_est"]
    result = {
        "generated_from": "AssetRegistry dump (registry_dump.py) + Config + Tools + package bytes",
        "roots": {"config": cfg_roots, "maps": [p for p in game_roots if info[p]["class"] == "World"],
                  "template_map": sorted(template)},
        "registry_vs_disk": {"in_registry_not_on_disk": sorted(packages - on_disk),
                             "on_disk_not_in_registry": sorted(on_disk - packages)},
        "totals": dict(totals),
        "assets": assets,
        "redirectors": [p for p in assets if assets[p]["type"] == "ObjectRedirector"],
        "empty_folders": sorted(empty),
        "textures": sorted(textures, key=lambda t: -t["bytes"]),
        "duplicate_textures": dups,
        "tools_prefix_refs": {k: sorted(v) for k, v in sorted(tool_prefixes.items())},
        "tools_missing_refs": sorted(tool_missing),
        "string_only_edges": {p: s for p, s in strings.items() if s},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1)
    for k in sorted(totals):
        t = totals[k]
        print(f"class {k}: {t['count']:5d} packages {t['bytes'] / 2**20:8.1f} MB on disk, ~{t['cooked_est'] / 2**20:7.1f} MB cooked")
    print("redirectors", len(result["redirectors"]), "empty folders", len(empty), "duplicate texture groups", len(dups),
          "registry/disk mismatches", len(result["registry_vs_disk"]["in_registry_not_on_disk"]),
          len(result["registry_vs_disk"]["on_disk_not_in_registry"]))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
