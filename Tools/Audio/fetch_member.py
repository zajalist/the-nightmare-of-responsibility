"""Pull one member out of a remote Sonniss bundle zip via HTTP Range, using the local _index/*.jsonl.

usage: python -I fetch_member.py <index.jsonl> <member name> <out_dir>
Writes <out_dir>/<basename of member>. out_dir must be new or empty (downloads are untrusted).
"""
import json, os, struct, sys, urllib.request, zlib


def get_range(url, start, length):
    req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{start + length - 1}", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        if r.status != 206:
            raise SystemExit(f"server ignored Range (status {r.status})")
        data = r.read()
    if len(data) != length:
        raise SystemExit(f"short read {len(data)} != {length}")
    return data


def main(index_path, member, out_dir):
    with open(index_path, encoding="utf-8") as f:
        url = json.loads(f.readline())["url"]
        entry = next((d for d in map(json.loads, f) if d["name"] == member), None)
    if entry is None:
        raise SystemExit(f"member not in index: {member}")
    if os.path.isdir(out_dir) and os.listdir(out_dir):
        raise SystemExit(f"out_dir not empty: {out_dir}")
    hdr = get_range(url, entry["lho"], 30)
    sig, _, _, method, _, _, _, _, _, nlen, xlen = struct.unpack("<IHHHHHIIIHH", hdr)
    if sig != 0x04034B50 or method != entry["method"]:
        raise SystemExit(f"bad local header sig={sig:#x} method={method}")
    raw = get_range(url, entry["lho"] + 30 + nlen + xlen, entry["csize"])
    data = zlib.decompress(raw, -15) if method == 8 else raw
    if len(data) != entry["usize"] or (zlib.crc32(data) & 0xFFFFFFFF) != entry["crc"]:
        raise SystemExit("size/crc mismatch")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, os.path.basename(member))
    with open(out, "wb") as f:
        f.write(data)
    print(f"ok {len(data)} bytes crc ok -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
