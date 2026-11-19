"""T3: export the baked strand hair for UE Groom: one Alembic for the scalp, one for the brows, Blender metres, then
re-import each and assert the curve and point counts survive the round trip.
  pwsh -File Tools/MPFB/run_blender.ps1 -Blend P:/FoA-Assets/character/mpfb/teen/foa_teen_hair.blend Tools/MPFB/export_hair_abc.py [out_dir]
Default out: P:/FoA-Assets/character/mpfb/export/hair/. Never saves the .blend.
UE import (Groom): Alembic is Y-up and in metres here, so in the Groom import options set Conversion Settings
Rotation X = 90 and Scale = (100, -100, 100) (Epic's Y-up default is (1, -1, 1); the 100 turns metres into cm)."""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
from mpfb_common import ASSETS, args, ensure_dir  # noqa: E402

PIECES = {"scalp": "basic_short_hair", "brows": "wild_eyebrow"}


def counts(obj):
    d = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    if obj.type == "CURVE":
        return len(d.splines), sum(len(s.points) for s in d.splines)
    return len(d.curves), len(d.points)


def main():
    out = ensure_dir(args()[0] if args() else os.path.join(ASSETS, "export", "hair"))
    expected = {}
    for piece, name in PIECES.items():
        obj = bpy.data.objects.get(name)
        if obj is None and piece == "brows":
            continue  # the selected eyebrow001 cards remain on the head
        if obj is None or obj.type != "CURVES" or obj.modifiers:
            raise SystemExit(f"{name}: expected a baked Curves object (run build_hair.py save=1 first)")
        expected[piece] = counts(obj)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        path = os.path.join(out, f"SM_Teen_Groom_{piece.capitalize()}.abc")
        bpy.ops.wm.alembic_export(filepath=path, selected=True, start=1, end=1, global_scale=1.0,
                                  evaluation_mode="RENDER", export_hair=True, export_particles=False)
        print("wrote", path, "curves/points", expected[piece])
    bpy.ops.wm.read_homefile(use_empty=True)
    for piece in expected:
        path = os.path.join(out, f"SM_Teen_Groom_{piece.capitalize()}.abc")
        before = set(bpy.data.objects)
        bpy.ops.wm.alembic_import(filepath=path)
        new = [o for o in bpy.data.objects if o not in before]
        got = [counts(o) for o in new if o.type in ("CURVES", "CURVE")]
        if got and new[0].type == "CURVE":  # legacy curve import: count splines and points instead
            got = [(len(o.data.splines), sum(len(s.points) for s in o.data.splines)) for o in new if o.type == "CURVE"]
        total = (sum(g[0] for g in got), sum(g[1] for g in got))
        print("reimport", piece, total, "expected", expected[piece], "types", [o.type for o in new])
        assert total == expected[piece], f"{piece}: round trip changed the counts {expected[piece]} -> {total}"
    print("ROUNDTRIP OK", expected)


main()
