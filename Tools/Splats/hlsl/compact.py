"""Writes the paste-ready Custom-node code for the MF_SplatFlow 'Motion' node: flow_lib.hlsl + flow_eval.hlsl,
comments and indentation stripped (the documented sources stay the source of truth; check them with check_hlsl.py).
    python Tools/Splats/hlsl/compact.py   ->   hlsl/gen/MF_SplatFlow_Motion.compact.hlsl"""
import os
import re

H = os.path.dirname(os.path.abspath(__file__))
for node, entry in (("Offset", "flow_offset.hlsl"), ("Look", "flow_look.hlsl"), ("Motion", "flow_eval.hlsl")):
    lines = []
    for f in ("flow_lib.hlsl", entry):
        for line in open(os.path.join(H, f), encoding="utf-8"):
            line = re.sub(r"\s*//.*$", "", line).strip()  # HLSL here has no '//' inside strings
            if line:
                lines.append(line)
    head = f"// MF_SplatFlow_{node} - compact copy; documented source: Tools/Splats/hlsl/flow_lib.hlsl + {entry} (offline check: check_hlsl.py)"
    out = os.path.join(H, "gen", f"MF_SplatFlow_{node}.compact.hlsl")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join([head] + lines) + "\n")
    print(out, os.path.getsize(out))
