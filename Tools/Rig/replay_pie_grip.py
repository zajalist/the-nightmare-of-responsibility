"""Replay a PIE grip pose in the Blender twin (anim lane): the Body's local pose captured in PIE
(Tools/Unreal/player/pie_pose_capture.capture_grip) on the twin rig, and the touched objects (the game's own meshes,
exported by export_grip_meshes.py) placed where they were relative to the Body, then rig's mesh check (hand and
forearm), the whole-body clearance, and renders from the eye and the side. This is the in-game proof at mesh level.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/replay_pie_grip.py pose=<pose_*.json> [tag=key_seated]"""
import json
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import grip_twin as G  # noqa: E402
import hand_twin as H  # noqa: E402

ARGS = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--") + 1:] if "=" in a) if "--" in sys.argv else {}
OUT = "P:/FoA/Saved/RigShots/pie_replay"
os.makedirs(OUT, exist_ok=True)
BODY_SCALE = 170.0 / 180.0


def main():
    cap = json.load(open(ARGS["pose"]))
    tag = ARGS.get("tag", os.path.splitext(os.path.basename(ARGS["pose"]))[0])
    rig, _ = H.load_teen()
    rig.reset()
    H.pose_from_ue_local(rig, {b: v[1] for b, v in cap["hold"].items()}, {b: v[0] for b, v in cap["hold"].items()})
    bw = cap["body_world"]
    body = G.ue_matrix(bw[0], bw[1], bw[2])
    frames = []
    for name, o in cap["objects"].items():
        mesh = (o.get("mesh") or "").split(".")[-1]
        if not mesh or not os.path.exists(f"{G.UE_EXPORT}/{mesh}.fbx"):
            print("REPLAY skip", name, mesh, flush=True)
            continue
        fr = G.load_ue_mesh(mesh)
        G.place_in_body(fr, G.ue_matrix(*o["world"]), body)
        frames.append(fr)
    hand = cap.get("hand", "hand_r")
    obj = next(iter(cap["objects"].values()))
    expected = body.inverted() @ G.ue_matrix(*obj["world"]) @ G.ue_matrix(*obj["in_hand"]).inverted()
    replay_error_mm = (rig.head(hand) - expected.translation).length * 1000 * BODY_SCALE
    assert replay_error_mm < 0.1, ("PIE hand did not round-trip", replay_error_mm)
    side = hand[-1]
    check = H.check(rig, frames, side)
    trees = [H._tree([f])[0] for f in frames]
    clear = G.body_clear_mm(rig, trees, BODY_SCALE)
    eye = H.ue_point(rig, "head", H.EYE_HEAD)
    target = rig.head(hand) + (rig.head(f"middle_01_{side}") - rig.head(hand)) * 0.6
    H.render_fp(rig, eye, target, os.path.join(OUT, f"{tag}_fp.png"))
    H.render_side(rig, target, Vector((-1, 0.6, 0.3)), os.path.join(OUT, f"{tag}_side.png"), dist_m=0.45)
    H.render_side(rig, target, Vector((0.4, 0.5, 0.8)), os.path.join(OUT, f"{tag}_top.png"), dist_m=0.3)
    rep = dict(pose=ARGS["pose"], digits={k: (v["min_mm"], v["violations"]) for k, v in check["digits"].items()},
               min_gap_ok=check["pass"], body_clear=clear, replay_hand_error_mm=replay_error_mm)
    json.dump(rep, open(os.path.join(OUT, f"{tag}_report.json"), "w"), indent=1)
    print("REPLAY", tag, json.dumps(rep), flush=True)


main()
