"""Moves a rigged glTF/GLB character's pivot to its feet, for UE (characters stand on their origin).
  python -I Tools/Unreal/player/glb_pivot_to_feet.py <in.glb> <out.glb>
Lux3D's auto-rig exports the body centered on the origin (feet ~0.9 m below it). Interchange's import offset does not
bake into a skeletal mesh's bind pose, and the IK retargeter scales pelvis travel by pelvis height above the origin
(~0 here, so the hips freeze). Translating the skeleton's parent node lifts every joint and, through the unchanged
inverse bind matrices, every skinned vertex. Only the JSON chunk is rewritten; the binary chunk is copied as-is."""
import json
import struct
import sys


def main(src, dst):
    with open(src, "rb") as f:
        magic, version, _ = struct.unpack("<III", f.read(12))
        assert magic == 0x46546C67, "not a GLB file"
        jlen, jtype = struct.unpack("<II", f.read(8))
        doc = json.loads(f.read(jlen))
        rest = f.read()  # BIN chunk header + data, untouched
    nodes = doc["nodes"]
    joints = set(doc["skins"][0]["joints"])
    parent = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}
    root_joint = next(j for j in joints if parent.get(j) not in joints)
    holder = parent.get(root_joint)
    assert holder is not None, "the root joint has no parent node to translate"
    assert not any(k in nodes[holder] for k in ("rotation", "scale", "matrix")), "parent node already transformed"
    min_y = min(doc["accessors"][p["attributes"]["POSITION"]]["min"][1]
                for m in doc["meshes"] for p in m["primitives"])  # glTF is Y-up, meters
    t = nodes[holder].get("translation", [0.0, 0.0, 0.0])
    nodes[holder]["translation"] = [t[0], t[1] - min_y, t[2]]
    body = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    body += b" " * (-len(body) % 4)  # chunks stay 4-byte aligned
    with open(dst, "wb") as f:
        f.write(struct.pack("<III", magic, version, 12 + 8 + len(body) + len(rest)))
        f.write(struct.pack("<II", len(body), jtype))
        f.write(body)
        f.write(rest)
    print(f"{nodes[holder].get('name')}: lifted {-min_y:.3f} m (feet were at y={min_y:.3f}) -> {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
