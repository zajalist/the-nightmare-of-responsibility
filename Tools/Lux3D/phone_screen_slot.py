"""Offline (system Python + trimesh): add a clean screen quad to the Lux3D smartphone as its own material slot.

  python Tools/Lux3D/phone_screen_slot.py <retopo.glb> <out.glb> [--screen +y|-y|+z|-z|+x|-x] [--top +x|-x|+z|-z|...]

The retopo GLB's atlas UVs can't carry a widget, so the screen is a separate 2-triangle quad with 0..1 UVs (U to the
right, V down as seen from the front, so WBP_Phone maps upright) floating 0.2 mm above the screen face, inset by the
bezel. Output: ONE glTF mesh with two primitives (Body, Screen), which Unreal imports as one static mesh, two slots.
"""
import argparse
import json
import struct

import numpy as np
import trimesh

BEZEL = 0.035  # fraction of each in-plane extent left as bezel around the screen
LIFT = 0.0002  # metres above the face, enough to win the depth test without a visible step


def axis(spec):
    v = np.zeros(3)
    v["xyz".index(spec[1])] = 1.0 if spec[0] == "+" else -1.0
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--screen", default=None, help="screen normal; default: the thin axis, + side")
    ap.add_argument("--top", default=None, help="phone top direction; default: + of the longest axis")
    a = ap.parse_args()
    scene = trimesh.load(a.src, force="scene")
    body = scene.to_geometry()
    lo, hi = body.bounds
    ext = hi - lo
    order = np.argsort(ext)  # thin, mid, long
    n = axis(a.screen) if a.screen else np.eye(3)[order[0]]
    up = axis(a.top) if a.top else np.eye(3)[order[2]]
    right = np.cross(up, n)  # seen from the front (looking along -n), with 'up' up, 'right' is up x n
    assert abs(np.dot(n, up)) < 1e-6 and np.linalg.norm(right) > 0.5, "screen and top axes must differ"
    c = (lo + hi) / 2
    face_pos = np.dot(hi if np.dot(n, np.ones(3)) > 0 else lo, np.abs(n))
    half_r = abs(np.dot(ext, np.abs(right))) / 2 * (1 - 2 * BEZEL)
    half_u = abs(np.dot(ext, np.abs(up))) / 2 * (1 - 2 * BEZEL)
    centre = c - np.abs(n) * np.dot(c, np.abs(n)) + np.abs(n) * face_pos + n * LIFT
    corners = [centre - right * half_r + up * half_u, centre + right * half_r + up * half_u,
               centre + right * half_r - up * half_u, centre - right * half_r - up * half_u]
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]  # top-left, top-right, bottom-right, bottom-left (V down)
    screen = trimesh.Trimesh(vertices=np.array(corners), faces=[[0, 2, 1], [0, 3, 2]], process=False)
    if np.dot(screen.face_normals[0], n) < 0:
        screen.faces = screen.faces[:, ::-1]
    screen.visual = trimesh.visual.TextureVisuals(uv=np.array(uvs, dtype=float),
                                                  material=trimesh.visual.material.PBRMaterial(name="Screen",
                                                                                               baseColorFactor=[5, 5, 6, 255]))
    out = trimesh.Scene()
    out.add_geometry(body, geom_name="Body")
    out.add_geometry(screen, geom_name="Screen")
    glb = out.export(file_type="glb")
    open(a.dst, "wb").write(merge_meshes(glb))
    print(f"extent m {np.round(ext, 4)}, screen normal {n}, top {up}, screen {2 * half_r:.4f} x {2 * half_u:.4f} m -> {a.dst}")


def merge_meshes(glb):
    """One node + one mesh holding every primitive, so the importer makes a single static mesh with one slot each."""
    jlen = struct.unpack_from("<I", glb, 12)[0]
    gltf = json.loads(glb[20:20 + jlen])
    rest = glb[20 + jlen:]
    prims = [p for m in gltf["meshes"] for p in m["primitives"]]
    gltf["meshes"] = [{"name": "SM_Phone", "primitives": prims}]
    gltf["nodes"] = [{"name": "SM_Phone", "mesh": 0}]
    gltf["scenes"] = [{"nodes": [0]}]
    gltf["scene"] = 0
    j = json.dumps(gltf, separators=(",", ":")).encode()
    j += b" " * (-len(j) % 4)
    body = struct.pack("<II", len(j), 0x4E4F534A) + j + rest
    return struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body


if __name__ == "__main__":
    main()
