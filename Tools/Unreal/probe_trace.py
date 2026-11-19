"""Read-only: trace straight down at each FOA_PTS point and print the first surface hit (actor label and z).
  python Tools/Unreal/ue_remote.py Tools/Unreal/probe_trace.py "FOA_PTS=-355,190;-104,272" [FOA_FROM=400]
Uses complex (per-triangle) collision; actors with NoCollision are not hit."""
import os

import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
top = float(os.environ.get("FOA_FROM", "400"))
for pt in [p for p in os.environ.get("FOA_PTS", "").split(";") if p.strip()]:
    x, y = (float(v) for v in pt.split(",")[:2])
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, top), unreal.Vector(x, y, -50.0),
                                                 unreal.TraceTypeQuery.ECC_VISIBILITY, True, [],
                                                 unreal.DrawDebugTrace.NONE, True)
    if hit is None:
        print(f"({x:.0f},{y:.0f}) no hit")
        continue
    parts = hit.to_tuple()
    vecs = [v for v in parts if isinstance(v, unreal.Vector)]
    comp = next((v for v in parts if isinstance(v, unreal.PrimitiveComponent)), None)
    z = min((v.z for v in vecs if abs(v.x - x) < 0.5 and abs(v.y - y) < 0.5 and -50.0 < v.z < top), default=None)
    print(f"({x:.0f},{y:.0f}) z={z:.1f} {comp.get_owner().get_actor_label() if comp else None}")
