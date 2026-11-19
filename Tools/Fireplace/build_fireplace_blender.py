"""FoA bedroom fireplace, c. 1905: painted timber surround, cast-iron arched insert, firebrick firebox, encaustic hearth.

  powershell -File P:/FoA-Tools/blender_scripts/run_blender.ps1 -Script P:/FoA/Tools/Fireplace/build_fireplace_blender.py
  ... -ScriptArgs preview      also renders B&W previews to P:/FoA-Tools/_work/fireplace_*.png

Modelled in cm in a local frame, exported as glTF in metres to P:/FoA-Assets/blender/Fireplace/:
  +X out of the chimney-breast face into the room, Y along the wall, Z up; origin = breast face centre on the floor
  (world (-330, 0, 0) in L_Tutorial_Bedroom). Everything is symmetric in Y (glTF -> Unreal mirrors Y).
Meshes (material slots in brackets):
  SM_FP_Surround [Paint]           fluted pilasters on plinths, capitals, corbels, frieze panel + tablet, bed mould, shelf
  SM_FP_Insert   [Iron]            arched register plate: reeded arch band, beads, keystone, rosettes, grate, ash fret
  SM_FP_Firebox  [Brick, Soot]     splayed firebrick cheeks and leaning fireback; vertex colour R = clean (0 = soot)
  SM_FP_Hearth   [Tiles, Slate]    tile slab (UVs 0..1 over the 136 x 41.2 cm field) inside a bullnosed slate kerb
  SM_FP_Coal     [Coal, Ash]       coal on the grate, ash bed under it
Mantel shelf top: z = 125, front edge x = 21.7, ends y = +-76.7.
"""
import math
import os
import random
import sys

sys.path.insert(0, r"P:\FoA-Tools\blender_scripts")
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import foa_common as C  # noqa: E402

OUT = r"P:\FoA-Assets\blender\Fireplace"
TEX = r"P:\FoA-Assets\procedural\fireplace"
HZ = 2.5                      # hearth top (cm)
OPEN_HW, OPEN_TOP = 48.0, 96.0  # surround opening half width and height
R0, ZS = 22.0, 44.0           # insert: arch half width (radius) and springing height
PX = 0.8                      # insert plate front face (x)
X_HAT = Vector((1, 0, 0))
# offset_poly2d's sign convention, measured: GROW * d grows a clockwise outline by d
GROW = 1.0 if C.offset_poly2d([Vector((0, 1)), Vector((1, 1)), Vector((1, 0)), Vector((0, 0))], 0.1)[0].y > 1.0 else -1.0


# ------------------------------------------------------------------ helpers
def box(mb, x0, x1, y0, y1, z0, z1, mat=0):
    v = [mb.v((x, y, z)) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    for f in ((0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)):
        mb.f([v[i] for i in f], mat)


def cyl(mb, p0, p1, r, segs=12, mat=0):
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0).normalized()
    u = ax.cross(Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 1, 0))).normalized()
    w = ax.cross(u)
    rings = [[mb.v(p + r * (math.cos(2 * math.pi * k / segs) * u + math.sin(2 * math.pi * k / segs) * w))
              for k in range(segs)] for p in (p0, p1)]
    for k in range(segs):
        k2 = (k + 1) % segs
        mb.f([rings[0][k], rings[0][k2], rings[1][k2], rings[1][k]], mat)
    mb.f(list(reversed(rings[0])), mat)
    mb.f(rings[1], mat)


def rosette(mb, centre, prof, segs=48, petals=0, amp=0.0, petal_from=0.0, yscale=1.0, mat=0):
    """Turned boss facing +X: prof is (r, h) from the centre out; optional scalloped petals beyond petal_from."""
    cx, cy, cz = centre
    rows = []
    for r, h in prof:
        if r < 1e-6:
            rows.append([mb.v((cx + h, cy, cz))] * segs)
            continue
        row = []
        for k in range(segs):
            t = 2 * math.pi * k / segs
            rr = r * (1 + amp * math.cos(petals * t)) if petals and r > petal_from else r
            row.append(mb.v((cx + h, cy + rr * math.cos(t) * yscale, cz + rr * math.sin(t))))
        rows.append(row)
    for j in range(len(rows) - 1):
        a, b = rows[j], rows[j + 1]
        for k in range(segs):
            k2 = (k + 1) % segs
            mb.f([a[k], a[k2], b[k2], b[k]], mat)
    mb.f(list(reversed(rows[-1])), mat)  # back cap, hidden against the plate


def half_round(r, n=8):
    return [(r * math.cos(math.pi * i / n), r * math.sin(math.pi * i / n)) for i in range(n + 1)]


def to_obj(mb, name, mats, recalc=True, sharp=35):
    ob = mb.to_object(name, mats, recalc=recalc)
    C.mark_sharp_by_angle(ob, sharp)
    return ob


def finish(obs, name, bevel=None):
    """Optionally bevel each part, join, scale cm -> m."""
    for ob in obs:
        if bevel and ob.get("bevel", True):
            C.bevel(ob, bevel[0], bevel[1], 35)
    ob = C.join(obs, name) if len(obs) > 1 else obs[0]
    ob.name = ob.data.name = name
    ob.scale = (0.01, 0.01, 0.01)
    C.set_active(ob)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return ob


def boolean_cut(ob, cutter):
    m = ob.modifiers.new("cut", 'BOOLEAN')
    m.operation, m.solver, m.object = 'DIFFERENCE', 'EXACT', cutter
    C.apply_modifiers(ob)
    bpy.data.objects.remove(cutter)


def edge_path(off, z_lo, n_arc=48):
    """(y, z) polyline `off` cm outside the arch opening edge: left jamb bottom, over the arch, right jamb bottom."""
    r = R0 + off
    arc = [(r * math.cos(math.pi - math.pi * i / n_arc), ZS + r * math.sin(math.pi - math.pi * i / n_arc)) for i in range(n_arc + 1)]
    return [(-r, z_lo)] + arc + [(r, z_lo)]


# ------------------------------------------------------------------ surround (painted timber)
def surround(mat):
    parts = []
    # front board: legs and frieze as one inverted-U slab, 2.2 cm thick
    mb = C.MB()
    outline = [Vector(p) for p in ((-70, 121), (70, 121), (70, HZ), (OPEN_HW, HZ), (OPEN_HW, OPEN_TOP),
                                   (-OPEN_HW, OPEN_TOP), (-OPEN_HW, HZ), (-70, HZ))]
    C.extrude_outline(mb, outline, [(0, 0.0), (0, 2.2)], lambda y, z, h: (h, y, z))
    parts.append(to_obj(mb, "board", [mat]))

    # architrave moulding round the opening: ovolo, cove, flat
    prof = [(0.0, 0.0), (0.0, 0.55)] + [(0.65 + 0.65 * math.cos(a), 0.55 + 0.65 * math.sin(a)) for a in
                                        [math.pi - i * math.pi / 12 for i in range(1, 7)]]
    prof += [(1.0, 1.2)] + [(1.6 + 0.6 * math.cos(a), 1.2 + 0.6 * math.sin(a)) for a in
                            [math.pi + i * math.pi / 12 for i in range(1, 7)]]
    prof += [(3.15, 0.6), (3.35, 0.45), (3.4, 0.25), (3.4, 0.0)]
    mb = C.MB()
    C.sweep(mb, [(2.2, -OPEN_HW, HZ), (2.2, -OPEN_HW, OPEN_TOP), (2.2, OPEN_HW, OPEN_TOP), (2.2, OPEN_HW, HZ)],
            prof, (1, 0, 0), (1, 0, 0))
    parts.append(to_obj(mb, "architrave", [mat], sharp=40))

    plinth = [(0.3, 0.0), (0.3, 1.2), (0.0, 1.5), (0.0, 13.0), (0.15, 13.1), (0.35, 13.4), (0.5, 13.85), (0.55, 14.3),
              (0.55, 14.8), (0.8, 14.8), (0.8, 16.5)]
    capital = [(0.0, 0.0), (0.3, 0.25), (0.42, 0.65), (0.3, 1.05), (0.3, 1.5), (0.55, 1.9), (0.8, 2.5), (0.9, 3.1),
               (0.9, 3.4), (1.2, 3.4), (1.2, 6.0)]
    for sgn in (-1, 1):
        yc = 59.0 * sgn
        mb = C.MB()
        C.rect_rings(mb, (2.9, yc, HZ), (1, 0, 0), (0, 1, 0), 2.9, 8.5, plinth, (0, 0, 1), fill_first=True)
        parts.append(to_obj(mb, f"plinth{sgn}", [mat], sharp=40))
        # pilaster with three stopped flutes (boolean capsules)
        mb = C.MB()
        box(mb, 1.7, 4.8, yc - 7, yc + 7, HZ + 16.0, 86.3)
        pil = to_obj(mb, f"pilaster{sgn}", [mat])
        cut = C.MB()
        r, half = 1.05, 27.5
        cap = [(0.0, -half - r)] + [(r * math.sin(a), -half - r * math.cos(a)) for a in [i * math.pi / 12 for i in range(1, 7)]]
        cap += [(r * math.sin(a), half + r * math.cos(a)) for a in [math.pi / 2 - i * math.pi / 12 for i in range(0, 6)]] + [(0.0, half + r)]
        for dy in (-3.7, 0.0, 3.7):
            C.lathe(cut, cap, 16, xform=Matrix.Translation((4.8, yc + dy, 52.5)))
        boolean_cut(pil, cut.to_object("cutter", [mat]))
        C.mark_sharp_by_angle(pil, 35)
        parts.append(pil)
        mb = C.MB()
        C.rect_rings(mb, (3.5, yc, 86.0), (1, 0, 0), (0, 1, 0), 1.3, 7.0, capital, (0, 0, 1), fill_first=True)
        parts.append(to_obj(mb, f"capital{sgn}", [mat], sharp=40))
        # corbel: side profile with a deep cove, extruded 12 cm wide; carries the shelf
        side = [(2.2, 92.0), (6.4, 92.0), (6.4, 93.4)]
        side += [(11.0 - 4.6 * math.cos(t), 93.4 + 22.6 * math.sin(t)) for t in [i * math.pi / 28 for i in range(1, 14)]]
        side += [(11.0, 116.0), (11.4, 116.0), (11.4, 121.0), (2.2, 121.0)]
        mb = C.MB()
        C.extrude_outline(mb, [Vector(p) for p in side], [(0, -6.0), (0, 6.0)], lambda x, z, h, yc=yc: (x, yc + h, z))
        parts.append(to_obj(mb, f"corbel{sgn}", [mat]))
        # scroll roundels on both corbel cheeks: big one under the shelf, small one at the foot
        scroll = [(0.0, 0.95), (0.45, 0.9), (0.75, 0.66), (0.92, 0.62), (1.15, 0.8), (1.65, 0.8), (1.92, 0.55),
                  (2.25, 0.6), (2.75, 0.42), (3.1, 0.12), (3.1, 0.0), (0.0, 0.0)]
        mb = C.MB()
        for side in (-1, 1):
            rot = Matrix.Rotation(-side * math.pi / 2, 4, 'X')  # local +Z -> side * +Y
            for (cx_, cz_, k) in ((6.2, 114.8, 2.7 / 3.1), (4.2, 95.6, 1.4 / 3.1)):
                prof = [(r * k, h * min(1.0, k * 1.4)) for r, h in scroll]
                C.lathe(mb, prof, 32, xform=Matrix.Translation((cx_, yc + side * 5.98, cz_)) @ rot)
        ob = to_obj(mb, f"scrolls{sgn}", [mat], sharp=60)
        ob["bevel"] = False
        parts.append(ob)

    # frieze: applied moulded panel frame, centre tablet with an oval patera
    ogee = [(0.0, 0.0), (0.0, 0.35), (0.2, 0.7), (0.55, 0.85), (0.9, 0.7), (1.15, 0.45), (1.4, 0.3), (1.4, 0.0)]
    mb = C.MB()
    C.sweep(mb, [(2.2, -45, 100.2), (2.2, 45, 100.2), (2.2, 45, 113.5), (2.2, -45, 113.5)], ogee, (1, 0, 0), (1, 0, 0),
            closed_path=True, caps=False)
    parts.append(to_obj(mb, "frieze_frame", [mat], sharp=40))
    mb = C.MB()
    C.rect_rings(mb, (2.2, 0.0, 106.85), (0, 1, 0), (0, 0, 1), 12.0, 4.0,
                 [(0.5, 0.0), (0.5, 0.2), (0.15, 0.55), (0.0, 0.8)], (1, 0, 0), fill_first=True)
    parts.append(to_obj(mb, "tablet", [mat], sharp=40))
    mb = C.MB()
    rosette(mb, (3.0, 0.0, 106.85), [(0, 1.3), (0.7, 1.25), (1.1, 1.0), (1.3, 0.7), (1.6, 0.6), (2.1, 0.85), (2.6, 0.75),
                                     (3.0, 0.35), (3.1, 0.0)], segs=48, petals=10, amp=0.1, petal_from=1.5, yscale=1.7)
    ob = to_obj(mb, "patera", [mat], sharp=60)
    ob["bevel"] = False
    parts.append(ob)

    # bed mould under the shelf, returned to the wall at both ends
    bed = [(0.0, 0.0), (0.0, 4.5), (-3.6, 4.5), (-3.6, 3.9), (-3.3, 3.75), (-2.9, 3.5), (-2.5, 3.1), (-2.2, 2.6),
           (-1.95, 2.1), (-1.65, 1.6), (-1.3, 1.2), (-0.9, 0.9), (-0.5, 0.75), (-0.5, 0.0)]
    mb = C.MB()
    C.sweep(mb, [(0.0, -70, 116.5), (2.2, -70, 116.5), (2.2, 70, 116.5), (0.0, 70, 116.5)], bed, (0, 0, 1), (0, 0, 1))
    parts.append(to_obj(mb, "bedmould", [mat], sharp=40))

    # shelf: 4 cm thick with a rounded thumbnail edge on three sides (the back runs into the wall)
    shelf = [(-0.5, 0.0), (0.0, 0.5), (0.0, 1.3), (0.3, 1.55), (0.55, 1.95), (0.68, 2.45), (0.68, 2.85), (0.55, 3.3),
             (0.3, 3.65), (0.0, 3.85), (-0.35, 4.0)]
    mb = C.MB()
    C.rect_rings(mb, (10.0, 0.0, 121.0), (1, 0, 0), (0, 1, 0), 11.0, 76.0, shelf, (0, 0, 1), fill_first=True)
    parts.append(to_obj(mb, "shelf", [mat], sharp=40))
    return finish(parts, "SM_FP_Surround", bevel=(0.25, 2))


# ------------------------------------------------------------------ insert (cast iron)
def rib(mb, a, b, t, r0, x0, ends=(0, 0.02, 0.06, 0.12, 0.2, 0.8, 0.88, 0.94, 0.98, 1.0), n=8):
    """Reed: half-round ridge from a to b (y, z) on the plate at x0, rounded ends; t = unit (y, z) across the reed."""
    A, B = Vector((x0, a[0], a[1])), Vector((x0, b[0], b[1]))
    T = Vector((0, t[0], t[1]))
    e = 0.2
    rings = []
    for s in ends:
        q = abs(2 * s - 1)
        r = r0 * (math.sqrt(max(0.0, 1 - ((q - (1 - e)) / e) ** 2)) if q > 1 - e else 1.0)
        P = A.lerp(B, s)
        rings.append([mb.v(P + r * (math.cos(math.pi * i / n) * T + math.sin(math.pi * i / n) * X_HAT)) for i in range(n + 1)])
    for j in range(len(rings) - 1):
        r1, r2 = rings[j], rings[j + 1]
        for i in range(n):
            mb.f([r1[i], r1[i + 1], r2[i + 1], r2[i]])
        mb.f([r1[n], r1[0], r2[0], r2[n]])


def insert(mat):
    parts = []
    # register plate with the arched opening; 0.8 cm chamfer round the opening on the front
    mb = C.MB()
    arc = [(R0 * math.cos(a), ZS + R0 * math.sin(a)) for a in [i * math.pi / 40 for i in range(41)]]
    outline = [(-49.5, 98.0), (49.5, 98.0), (49.5, HZ), (R0, HZ)] + arc + [(-R0, HZ), (-49.5, HZ)]
    C.extrude_outline(mb, [Vector(p) for p in outline], [(0, -2.0), (0, 0.0), (-GROW * PX, PX)], lambda y, z, h: (h, y, z))
    parts.append(to_obj(mb, "plate", [mat], sharp=30))
    # keystone
    mb = C.MB()
    C.extrude_outline(mb, [Vector(p) for p in ((-3.7, 78.8), (3.7, 78.8), (2.7, 67.1), (-2.7, 67.1))],
                      [(0, 0.6), (0, 1.9), (-GROW * 0.45, 2.35)], lambda y, z, h: (h, y, z))
    parts.append(to_obj(mb, "keystone", [mat]))
    detail = C.MB()  # everything below is round-section: no bevel needed
    x0 = PX - 0.1
    # beads either side of the reeded band, and a flat-topped frame bead round the plate
    for off, r, zlo in ((2.2, 0.55, HZ + 1.0), (10.6, 0.65, HZ + 1.0)):
        C.sweep(detail, [(x0, y, z) for y, z in edge_path(off, zlo)], half_round(r), (1, 0, 0), (1, 0, 0))
    frame = [(-1.2, 0.0), (-1.2, 0.45), (-0.85, 0.85), (0.0, 1.0), (0.85, 0.85), (1.2, 0.45), (1.2, 0.0)]
    C.sweep(detail, [(x0, -45.5, HZ), (x0, -45.5, 93.5), (x0, 45.5, 93.5), (x0, 45.5, HZ)], frame, (1, 0, 0), (1, 0, 0))
    # reeding: ribs perpendicular to the opening edge, fanning out round the arch; gap under the keystone
    step, a_off, b_off = 2.3, 3.4, 9.4
    for z in [HZ + 3.0 + i * step for i in range(int((ZS - HZ - 3.0) / step) + 1)]:
        for s in (-1, 1):
            rib(detail, (s * (R0 + a_off), z), (s * (R0 + b_off), z), (0, 1), 0.6, x0)
    n_arc = int(math.pi * R0 / step)
    for i in range(1, n_arc):
        th = math.pi * i / n_arc
        if abs(th - math.pi / 2) < math.radians(7.5):
            continue
        c, s = math.cos(th), math.sin(th)
        rib(detail, (c * (R0 + a_off), ZS + s * (R0 + a_off)), (c * (R0 + b_off), ZS + s * (R0 + b_off)), (-s, c), 0.6, x0)
    # spandrel rosettes, side panels with small rosettes, top bead with a row of pellets
    # cast relief stays shallow (< 1 cm) with stepped profiles, so the edges read crisp instead of blobby
    big = [(0, 0.95), (0.55, 0.9), (0.85, 0.72), (0.95, 0.48), (1.1, 0.42), (1.25, 0.6), (1.5, 0.66), (3.8, 0.6),
           (4.4, 0.5), (4.75, 0.32), (4.85, 0.12), (4.9, 0.0)]
    small = [(r * 0.5, h * 0.75) for r, h in big]
    for s in (-1, 1):
        rosette(detail, (x0, s * 37.5, 76.5), big, segs=96, petals=8, amp=0.2, petal_from=1.4)
        rosette(detail, (x0, s * 38.5, 52.0), small, segs=64, petals=6, amp=0.2, petal_from=0.7)
        C.sweep(detail, [(x0, s * 35.2, 9.0), (x0, s * 41.8, 9.0), (x0, s * 41.8, 45.0), (x0, s * 35.2, 45.0)],
                half_round(0.4, 6), (1, 0, 0), (1, 0, 0), closed_path=True, caps=False)
    C.sweep(detail, [(x0, -44.2, 84.2), (x0, 44.2, 84.2)], half_round(0.55), (1, 0, 0), (1, 0, 0))
    for i in range(27):
        rosette(detail, (x0, -41.6 + 3.2 * i, 88.6), [(0, 0.38), (0.3, 0.36), (0.48, 0.28), (0.56, 0.14), (0.58, 0.0)], segs=20)
    # grate: posts with ball finials, four front bars, a heavier bottom rail, floor bars running back
    for s in (-1, 1):
        cyl(detail, (-0.6, s * 20.6, HZ), (-0.6, s * 20.6, 30.5), 0.85, 12)
        rosette(detail, (-0.6, s * 20.6, 31.6), [(0, 1.2), (0.6, 1.05), (1.0, 0.6), (1.15, 0.0), (1.0, -0.6),
                                                  (0.6, -1.05), (0, -1.2)], segs=16)
    for z in (14.0, 18.2, 22.4, 26.6):
        cyl(detail, (-0.6, -20.6, z), (-0.6, 20.6, z), 0.6, 10)
    cyl(detail, (-0.6, -20.6, 11.0), (-0.6, 20.6, 11.0), 0.9, 12)
    for y in (-16.0, -10.7, -5.3, 0.0, 5.3, 10.7, 16.0):
        cyl(detail, (-0.6, y, 10.6), (-20.0, y, 10.6), 0.5, 8)
    cyl(detail, (-20.0, -17.0, 10.6), (-20.0, 17.0, 10.6), 0.6, 8)
    # ash-pan fret: rails and balusters across the foot of the opening
    cyl(detail, (0.3, -R0 - 0.3, 10.0), (0.3, R0 + 0.3, 10.0), 0.7, 12)
    cyl(detail, (0.3, -R0 - 0.3, HZ + 0.6), (0.3, R0 + 0.3, HZ + 0.6), 0.6, 12)
    for i in range(16):
        y = -19.5 + 2.6 * i
        cyl(detail, (0.3, y, HZ + 0.6), (0.3, y, 10.0), 0.38, 8)
    ob = to_obj(detail, "detail", [mat], sharp=38)
    ob["bevel"] = False
    parts.append(ob)
    return finish(parts, "SM_FP_Insert", bevel=(0.2, 2))


# ------------------------------------------------------------------ firebox (firebrick, sooted)
def grid(mb, corners, nu, nv, want, mat=0):
    """Bilinear patch p00, p10, p11, p01 subdivided nu x nv; faces wound so their normal points along `want`."""
    p00, p10, p11, p01 = (Vector(c) for c in corners)
    ids = [[mb.v((p00.lerp(p10, i / nu)).lerp(p01.lerp(p11, i / nu), j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            q = [ids[i][j], ids[i + 1][j], ids[i + 1][j + 1], ids[i][j + 1]]
            a, b, c = (mb.verts[k] for k in q[:3])
            if (b - a).cross(c - a).dot(Vector(want)) < 0:
                q.reverse()
            mb.f(q, mat, smooth=False)


def firebox(mats):
    mb = C.MB()
    xb, xf, xt, zl, zt = -28.0, -2.0, -17.0, 50.0, 76.0   # back, front, top of the leaning fireback, lean start, top
    yb, yf = 15.0, R0
    yt = yf - (yf - yb) * (xf - xt) / (xf - xb)            # cheek half-width where the fireback top meets it
    grid(mb, [(xb, -yb, HZ), (xb, yb, HZ), (xb, yb, zl), (xb, -yb, zl)], 10, 16, (1, 0, 0))
    grid(mb, [(xb, -yb, zl), (xb, yb, zl), (xt, yt, zt), (xt, -yt, zt)], 10, 9, (1, 0, -0.4))
    for s in (-1, 1):
        grid(mb, [(xf, s * yf, HZ), (xb, s * yb, HZ), (xb, s * yb, zl), (xf, s * yf, zl)], 9, 16, (0, -s, 0))
        grid(mb, [(xf, s * yf, zl), (xb, s * yb, zl), (xt, s * yt, zt), (xf, s * yf, zt)], 9, 9, (0, -s, 0))
    grid(mb, [(xb, -yb, HZ), (PX, -(yf + PX), HZ), (PX, yf + PX, HZ), (xb, yb, HZ)], 10, 10, (0, 0, 1))
    grid(mb, [(xt, -yt, zt), (xf, -yf, zt), (xf, yf, zt), (xt, yt, zt)], 2, 2, (0, 0, -1), mat=1)  # throat
    ob = mb.to_object("SM_FP_Firebox", mats, recalc=False)
    ca = ob.data.color_attributes.new("Col", 'BYTE_COLOR', 'POINT')
    rnd = random.Random(3)
    blot = [(rnd.uniform(-28, 0), rnd.uniform(-20, 20), rnd.uniform(5, 75), rnd.uniform(4, 9)) for _ in range(40)]
    for i, v in enumerate(ob.data.vertices):
        x, y, z = v.co
        soot = 0.3 + 0.7 * min(1.0, max(0.0, (z - 8.0) / 50.0)) ** 0.8          # blacker going up
        soot += 0.25 * math.exp(-(y / 9.0) ** 2) * min(1.0, max(0.0, (z - 12) / 20))  # flame path up the middle
        soot -= sum(0.12 * math.exp(-((x - bx) ** 2 + (y - by) ** 2 + (z - bz) ** 2) / (br * br)) for bx, by, bz, br in blot)
        if z < HZ + 0.01:
            soot = 0.55 + 0.25 * math.exp(-(y / 12.0) ** 2)
        clean = 1.0 - min(1.0, max(0.0, soot))
        ca.data[i].color = (clean, clean, clean, 1.0)
    ob.data.color_attributes.active_color = ca
    return finish([ob], "SM_FP_Firebox")


# ------------------------------------------------------------------ hearth (tiles + slate kerb)
FX0, FX1, FY = PX, 42.0, 68.0


def hearth(mats):
    mb = C.MB()
    box(mb, FX0, FX1, -FY, FY, 0.0, HZ, mat=1)
    kerb = [(2.05, 0.0), (2.05, 3.0), (-0.8, 3.0), (-1.4, 2.85), (-1.8, 2.45), (-2.0, 1.9), (-2.0, 0.0)]
    C.sweep(mb, [(0.0, -(FY + 2), 0.0), (FX1 + 2, -(FY + 2), 0.0), (FX1 + 2, FY + 2, 0.0), (0.0, FY + 2, 0.0)],
            kerb, (0, 0, 1), (0, 0, 1), mat=1)
    ob = to_obj(mb, "SM_FP_Hearth", mats, sharp=40)
    uv = ob.data.uv_layers.new(name="UVMap")
    for poly in ob.data.polygons:
        top = poly.material_index == 1 and poly.normal.z > 0.99 and abs(poly.center.z - HZ) < 1e-3
        if top:
            poly.material_index = 0
        for li in poly.loop_indices:
            co = ob.data.vertices[ob.data.loops[li].vertex_index].co
            if top:  # unique 0..1 over the tile field; v = 1 - depth so image row 0 is the back edge
                uv.data[li].uv = ((co.y + FY) / (2 * FY), 1.0 - (co.x - FX0) / (FX1 - FX0))
    hob = finish([ob], "SM_FP_Hearth")
    return hob


# ------------------------------------------------------------------ ash and cinders (a cold grate)
STONES = r"P:\FoA-Assets\polyhaven\models\namaqualand_stones_01\namaqualand_stones_01_1k.gltf"  # CC0 scan


def scan_stones(target_tris=320):
    """Loose stones from the Poly Haven scan, decimated, each centred and scaled to unit size: [(verts, faces)]."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=STONES)
    imported = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    for o in imported:
        C.set_active(o)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='LOOSE')
        bpy.ops.object.mode_set(mode='OBJECT')
    pieces = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    out = []
    for o in pieces:
        n = len(o.data.polygons)
        if n > 600:
            d = o.modifiers.new("dec", 'DECIMATE')
            d.ratio = target_tris / n
            C.apply_modifiers(o)
        vs = [v.co.copy() for v in o.data.vertices]
        lo = Vector([min(v[i] for v in vs) for i in range(3)])
        hi = Vector([max(v[i] for v in vs) for i in range(3)])
        size = max(hi - lo)
        if size > 0.02 and len(o.data.polygons) > 60:  # drop scan crumbs
            c = (lo + hi) / 2
            out.append(([(v - c) / size for v in vs], [list(p.vertices) for p in o.data.polygons]))
    for o in [o for o in bpy.data.objects if o not in before]:
        bpy.data.objects.remove(o)
    print("STONES", len(out))
    return out


def ash_sheet(mb, x0, x1, y_half, z0, height, n, mat):
    """Heightfield of ash: z = z0 + height(x, y); faces up."""
    def p(i, j):
        x, y = x0 + (x1 - x0) * i / n, -y_half + 2 * y_half * j / n
        return mb.v((x, y, z0 + height(x, y)))
    ids = [[p(i, j) for j in range(n + 1)] for i in range(n + 1)]
    for i in range(n):
        for j in range(n):
            q = [ids[i][j], ids[i + 1][j], ids[i + 1][j + 1], ids[i][j + 1]]
            a, b, c = (mb.verts[k] for k in q[:3])
            if (b - a).cross(c - a).z < 0:
                q.reverse()
            mb.f(q, mat, smooth=True)


def coal(mats):
    rnd = random.Random(11)
    wob = [(rnd.uniform(0.6, 1.8), rnd.uniform(0.6, 1.8), rnd.uniform(0, 6.28)) for _ in range(6)]

    def noise(x, y):
        return sum(math.sin(x * a * 0.35 + ph) * math.sin(y * b * 0.35 + ph * 1.7) for a, b, ph in wob) / len(wob)

    def low(x, y):  # under the grate: a mound of fallen ash, deepest under the middle
        edge = min(1.0, (20.5 - abs(y)) / 3.0, (x + 26.0) / 4.0)
        return max(0.05, (0.4 + 4.2 * math.exp(-(y / 11.0) ** 2 - ((x + 9.0) / 11.0) ** 2) + 0.5 * noise(x, y)) * edge)

    def top(x, y):  # on the grate bars: the burnt-out bed, sloping down to the front bar
        edge = min(1.0, (19.0 - abs(y)) / 3.0, (-1.4 - x) / 2.5, (x + 19.5) / 2.0)
        return max(0.0, (0.6 + 3.6 * math.exp(-(y / 10.5) ** 2 - ((x + 11.0) / 8.0) ** 2) + 0.6 * noise(x, y)) * edge)

    mb = C.MB()
    ash_sheet(mb, -26.0, 0.4, 20.5, HZ, low, 40, 1)
    ash_sheet(mb, -19.5, -1.4, 19.0, 11.2, top, 36, 1)
    stones = scan_stones()
    for k in range(30):  # chunky cinders a third sunk in the bed, bigger towards the back
        vs, fs = stones[k % len(stones)]
        x, y = rnd.uniform(-17.0, -3.8), rnd.uniform(-14.5, 14.5)
        size = rnd.uniform(2.8, 5.2) * (1.0 + 0.25 * (-x / 17.0))
        rot = Matrix.Rotation(rnd.uniform(0, 6.28), 3, 'Z') @ Matrix.Rotation(rnd.uniform(-0.6, 0.6), 3, 'X')
        sc = Vector((rnd.uniform(0.85, 1.15), rnd.uniform(0.85, 1.15), rnd.uniform(0.9, 1.2))) * size
        centre = Vector((x, y, 11.2 + top(x, y) + 0.15 * size))
        ids = [mb.v(centre + rot @ Vector((v.x * sc.x, v.y * sc.y, v.z * sc.z))) for v in vs]
        for f in fs:
            mb.f([ids[i] for i in f], 0, smooth=True)
    ob = mb.to_object("SM_FP_Coal", mats, merge=0, recalc=False)
    C.mark_sharp_by_angle(ob, 60)
    return finish([ob], "SM_FP_Coal")


# ------------------------------------------------------------------ baked masks (AO / edges / cavity) on UV1
def bake_context():
    """Breast face (with the firebox left open) and floor, so the AO bake sees the real contact shadows."""
    obs = []
    for (y0, y1, z0, z1) in ((-0.8, -0.23, 0, 3), (0.23, 0.8, 0, 3), (-0.23, 0.23, 0.8, 3)):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(-0.001, (y0 + y1) / 2, (z0 + z1) / 2), rotation=(0, math.pi / 2, 0))
        o = bpy.context.active_object
        o.scale = (z1 - z0, y1 - y0, 1)
        obs.append(o)
    bpy.ops.mesh.primitive_plane_add(size=6, location=(1.5, 0, -0.0005))
    obs.append(bpy.context.active_object)
    return obs


def bake_masks(ob, size, out_png, wear=(0.45, 6.0, 0.9), stain_fn=None):
    """UV1 'Bake' (smart project) + the final wear map as a packed PNG, so the material only has to lerp:
    R = AO (15 cm), G = wear (exposed edges x 3D noise: paint chips / polished iron / worn kerb),
    B = grime (crevices + occlusion x 3D noise), A = 1 - smoke stain (stain_fn(P_cm, N) on baked texel positions).
    wear = (edge amount, sharpness, grime amount). Noise is sampled in 3D at each texel's position: no UV seams."""
    import numpy as np
    scn = bpy.context.scene
    scn.render.engine = 'CYCLES'
    scn.cycles.device = 'CPU'
    scn.cycles.samples = 48
    if scn.world is None:
        scn.world = bpy.data.worlds.new("BakeWorld")
    me = ob.data
    uv1 = me.uv_layers.new(name="Bake")
    me.uv_layers.active = uv1
    C.set_active(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    img = bpy.data.images.new(ob.name + "_bake", size, size, alpha=False, float_buffer=True)
    m = bpy.data.materials.new("_Bake")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    bev = nt.nodes.new("ShaderNodeBevel")
    bev.inputs["Radius"].default_value = 0.012
    bev.samples = 16
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = 'DOT_PRODUCT'
    rng = nt.nodes.new("ShaderNodeMapRange")
    rng.inputs["From Min"].default_value, rng.inputs["From Max"].default_value = 1.0, 0.9   # 1 = flat, 0.9 = edge
    nt.links.new(bev.outputs["Normal"], dot.inputs[0])
    nt.links.new(geo.outputs["Normal"], dot.inputs[1])
    nt.links.new(dot.outputs["Value"], rng.inputs["Value"])
    nt.links.new(rng.outputs["Result"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.nodes.active = tex
    orig = [sl.material for sl in ob.material_slots]
    for sl in ob.material_slots:
        sl.material = m
    chans = []
    for kind, dist in (("AO", 0.15), ("EMIT", 0.15), ("AO", 0.02)):
        scn.world.light_settings.distance = dist
        bpy.ops.object.bake(type=kind, margin=8, use_clear=True)
        px = np.empty(size * size * 4, np.float32)
        img.pixels.foreach_get(px)
        chans.append(px.reshape(size, size, 4)[..., 0].copy())
    geo_px = []
    for socket in ("Position", "Normal"):
        nt.links.new(geo.outputs[socket], em.inputs["Color"])
        bpy.ops.object.bake(type='EMIT', margin=8, use_clear=True)
        px = np.empty(size * size * 4, np.float32)
        img.pixels.foreach_get(px)
        geo_px.append(px.reshape(size, size, 4)[..., :3].copy())
    P = geo_px[0] * 100.0
    ao, edge, open_ = chans
    n = 0.6 * noise3(P, 0.45) + 0.4 * noise3(P, 0.12)              # chip-sized + patch-sized breakup, 0..1
    amount, sharp, grime_amt = wear
    wear_m = np.clip((edge * open_ * (n + 0.5) - (1.0 - amount)) * sharp, 0.0, 1.0)
    grime_m = np.clip(((1.0 - open_) + (1.0 - ao) * 0.5) * grime_amt * (noise3(P, 0.2) + 0.6), 0.0, 1.0)
    alpha = np.ones((size, size), np.float32)
    if stain_fn:
        alpha = 1.0 - np.clip(stain_fn(P, geo_px[1]), 0.0, 1.0)
    chans = [ao, wear_m, grime_m]
    for sl, mat in zip(ob.material_slots, orig):
        sl.material = mat
    packed = bpy.data.images.new(os.path.basename(out_png)[:-4], size, size, alpha=True)
    rgba = np.dstack(chans + [alpha]).clip(0, 1)
    packed.pixels.foreach_set(rgba.ravel())
    packed.filepath_raw = out_png
    packed.file_format = 'PNG'
    packed.save()
    me.uv_layers.active = me.uv_layers[0]
    print("BAKED", out_png, [round(float(c.mean()), 3) for c in chans + [alpha]])


def noise3(P, freq, seed=7):
    """Smooth 3D value noise in 0..1 at positions P (cm), feature size ~1/freq cm (numpy, trilinear, hashed lattice)."""
    import numpy as np
    q = P * freq
    i = np.floor(q).astype(np.int64)
    f = q - i
    f = f * f * (3 - 2 * f)

    def h(dx, dy, dz):
        k = (i[..., 0] + dx) * 73856093 ^ (i[..., 1] + dy) * 19349663 ^ (i[..., 2] + dz) * 83492791 ^ seed * 2654435761
        return ((k * 2654435761) % 1000003) / 1000003.0

    x0 = h(0, 0, 0) * (1 - f[..., 0]) + h(1, 0, 0) * f[..., 0]
    x1 = h(0, 1, 0) * (1 - f[..., 0]) + h(1, 1, 0) * f[..., 0]
    x2 = h(0, 0, 1) * (1 - f[..., 0]) + h(1, 0, 1) * f[..., 0]
    x3 = h(0, 1, 1) * (1 - f[..., 0]) + h(1, 1, 1) * f[..., 0]
    y0 = x0 * (1 - f[..., 1]) + x1 * f[..., 1]
    y1 = x2 * (1 - f[..., 1]) + x3 * f[..., 1]
    return (y0 * (1 - f[..., 2]) + y1 * f[..., 2]).astype(np.float32)


def _smooth(a, b, x):
    import numpy as np
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _breakup(P):
    import numpy as np
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    return 0.75 + 0.25 * np.sin(x * 0.21 + y * 0.17 + 1.3) * np.sin(z * 0.19 - y * 0.13) + 0.1 * np.sin(z * 0.33 + y * 0.29 + 0.7)


def stain_insert(P, N):
    """Smoke that escaped the opening for decades: a plume up the plate above the arch, darker round the arch edge."""
    import numpy as np
    y, z = P[..., 1], P[..., 2]
    w = 13.0 + 0.35 * np.clip(z - 66.0, 0, None)
    plume = 0.6 * np.exp(-(y / w) ** 2) * _smooth(56.0, 68.0, z) * np.exp(-np.clip(z - 68.0, 0, None) / 28.0)
    r = np.hypot(y, z - ZS)
    rim = 0.35 * np.exp(-((r - R0) / 3.5) ** 2) * _smooth(40.0, 62.0, z)
    return (plume + rim) * _breakup(P)


def stain_surround(P, N):
    """Faint plume on the frieze above the opening; smoke curling under the shelf and bed mould near the wall."""
    import numpy as np
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    frieze = 0.35 * np.exp(-(y / 22.0) ** 2) * _smooth(94.0, 97.0, z) * np.exp(-np.clip(z - 96.0, 0, None) / 12.0) * (N[..., 0] > 0.5)
    under = (0.3 * np.exp(-(y / 30.0) ** 2) * np.exp(-np.clip(x - 2.0, 0, None) / 9.0) * (N[..., 2] < -0.3)
             * _smooth(110.0, 116.0, z))
    return (frieze + under) * _breakup(P)


# ------------------------------------------------------------------ materials, UVs, export, previews
def mats():
    def m(name, col, metal=0.0, rough=0.5):
        return C.material(name, col, metal, rough)
    M = {"Paint": m("Paint", (0.62, 0.6, 0.55), 0.0, 0.42), "Iron": m("Iron", (0.05, 0.05, 0.05), 0.6, 0.42),
         "Brick": m("Brick", (0.22, 0.11, 0.07), 0.0, 0.9), "Soot": m("Soot", (0.004, 0.004, 0.004), 0.0, 1.0),
         "Tiles": m("Tiles", (0.3, 0.3, 0.3), 0.0, 0.45), "Slate": m("Slate", (0.035, 0.036, 0.04), 0.0, 0.55),
         "Coal": m("Coal", (0.012, 0.012, 0.012), 0.0, 0.28), "Ash": m("Ash", (0.33, 0.32, 0.3), 0.0, 1.0)}
    # previews only: brick darkened by the vertex-colour soot mask, hearth with the generated tile texture
    nt = M["Brick"].node_tree
    bsdf = nt.nodes["Principled BSDF"]
    ca = nt.nodes.new("ShaderNodeVertexColor")
    ca.layer_name = "Col"
    mul = nt.nodes.new("ShaderNodeVectorMath")
    mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = (0.22, 0.11, 0.07)
    nt.links.new(ca.outputs["Color"], mul.inputs[0])
    nt.links.new(mul.outputs[0], bsdf.inputs["Base Color"])
    tex_path = os.path.join(TEX, "T_FP_Hearth_BaseColor.png")
    if os.path.exists(tex_path):
        nt = M["Tiles"].node_tree
        img = nt.nodes.new("ShaderNodeTexImage")
        img.image = bpy.data.images.load(tex_path)
        nt.links.new(img.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    return M


def export(ob, name):
    os.makedirs(OUT, exist_ok=True)
    for o in bpy.context.view_layer.objects:
        o.select_set(o == ob)
    props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    kw = dict(filepath=os.path.join(OUT, name + ".gltf"), export_format='GLTF_SEPARATE', use_selection=True,
              export_yup=True, export_apply=True, export_texcoords=True, export_normals=True, export_materials='EXPORT',
              export_image_format='NONE', export_cameras=False, export_lights=False, export_animations=False)
    if "export_vertex_color" in props:
        kw["export_vertex_color"] = 'ACTIVE'
    elif "export_colors" in props:
        kw["export_colors"] = True
    bpy.ops.export_scene.gltf(**{k: v for k, v in kw.items() if k in props})
    print("EXPORTED", kw["filepath"], "tris", C.tri_count(ob))


def bounds(ob):
    cs = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return [min(c[i] for c in cs) for i in range(3)], [max(c[i] for c in cs) for i in range(3)]


def preview():
    C.preview_setup(cam_loc=(2.6, -1.1, 1.55), target=(0.0, 0.0, 0.62), lens=40, floor=True, bw=True,
                    key=(1.8, -2.4, 2.2), key_power=500, grey=0.12)
    plaster = C.material("_Plaster", (0.55, 0.53, 0.5), 0.0, 0.9)
    for (y0, y1, z0, z1) in ((-0.8, -0.23, 0, 3), (0.23, 0.8, 0, 3), (-0.23, 0.23, 0.8, 3)):  # breast face, firebox left open
        bpy.ops.mesh.primitive_plane_add(size=1, location=(-0.002, (y0 + y1) / 2, (z0 + z1) / 2), rotation=(0, math.pi / 2, 0))
        wall = bpy.context.active_object
        wall.scale = (z1 - z0, y1 - y0, 1)
        wall.data.materials.append(plaster)
    C.render(r"P:\FoA-Tools\_work\fireplace_wide.png")
    cam = bpy.context.scene.camera
    cam.location = (1.05, -0.45, 0.62)
    C.look_at(cam, (0.0, 0.0, 0.42))
    C.render(r"P:\FoA-Tools\_work\fireplace_insert.png")
    cam.location = (0.9, 0.85, 1.1)
    C.look_at(cam, (0.05, 0.55, 0.95))
    C.render(r"P:\FoA-Tools\_work\fireplace_corbel.png")


def main():
    C.reset()
    M = mats()
    obs = {"SM_FP_Surround": surround(M["Paint"]), "SM_FP_Insert": insert(M["Iron"]),
           "SM_FP_Firebox": firebox([M["Brick"], M["Soot"]]), "SM_FP_Hearth": hearth([M["Tiles"], M["Slate"]]),
           "SM_FP_Coal": coal([M["Coal"], M["Ash"]])}
    C.box_uv(obs["SM_FP_Surround"], 1.0)
    C.box_uv(obs["SM_FP_Insert"], 1.0)
    C.box_uv(obs["SM_FP_Firebox"], 0.5)   # 2 m per UV: matches the medieval_red_brick 2 m tile
    C.box_uv(obs["SM_FP_Coal"], 1.0)
    # hearth: kerb gets box UVs in a second pass that leaves the tile top alone
    h = obs["SM_FP_Hearth"]
    bm = bmesh.new()
    bm.from_mesh(h.data)
    uvl = bm.loops.layers.uv.active
    for f in bm.faces:
        if f.material_index == 1:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for lp in f.loops:
                c = lp.vert.co
                lp[uvl].uv = (c.x, c.y) if ax == 2 else ((c.y, c.z) if ax == 0 else (c.x, c.z))
    bm.to_mesh(h.data)
    bm.free()

    if "nobake" not in sys.argv:
        ctx = bake_context()
        for name, size, wear, fn in (("SM_FP_Surround", 2048, (0.45, 6.0, 0.9), stain_surround),
                                     ("SM_FP_Insert", 2048, (0.55, 5.0, 1.0), stain_insert),
                                     ("SM_FP_Hearth", 1024, (0.6, 4.0, 0.6), None)):
            bake_masks(obs[name], size, os.path.join(TEX, "T_FP_Mask_" + name[6:] + ".png"), wear, fn)
        for o in ctx:
            bpy.data.objects.remove(o)
    s_min, s_max = bounds(obs["SM_FP_Surround"])
    assert abs(s_max[2] - 1.25) < 1e-3, s_max          # shelf top at 125 cm
    assert s_max[0] < 0.225 and s_max[1] < 0.77, s_max    # shelf depth and half width
    assert s_min[2] > 0.0249, s_min                        # stands on the hearth
    i_min, i_max = bounds(obs["SM_FP_Insert"])
    assert i_max[0] < 0.025 and abs(i_max[1]) < 0.5, i_max  # stays behind the surround face and inside the opening
    for name, ob in obs.items():
        export(ob, name)
    if "preview" in sys.argv:
        preview()


main()
