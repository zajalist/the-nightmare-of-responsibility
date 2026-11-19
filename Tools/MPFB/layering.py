"""Automatic garment layering for MPFB characters. Run it after MPFB has fitted the .mhclo clothes, so layers never
interpenetrate and skin never shows through cloth, at rest or in motion. No hand fitting.

Two kinds of pair:
- Garment over garment, e.g. the tee over the pants and the pants over the socks.
  - order: the outer is the one with the higher mhclo z_depth. On a tie (MakeHuman ships most clothes at 50), the
    garment that meets the other with its LOWER part drapes over it: the tee hem over the waistband, the cuffs
    over the socks.
  - separate: wherever the inner pokes out or sits within MIN_GAP, the outer eases outward until the inner sits
    PUSH under it, faded over RINGS edge rings so there's no step. The inner doesn't move: sinking the pants exposed
    skin under the tee (2026-11-07). SINK_INNER lets it sink too, but only as far as the body allows (BODY_GAP).
  - hide: inner faces fully covered and more than HIDE_FROM_HEM inside the outer's open edges go into group
    "Hidden_by.<outer>" with a Mask. Export turns that group into a material section the game hides while the
    outer is worn.
  - weights: the outer's hem first takes up to RIDE_MAX of the inner's weights near its edge, so it rides on what
    it lies on (a tee hem on the lap when sitting). Then the covered band of the inner takes the outer's weights
    (nearest-face interpolated, fading out), so the two layers move together.
- Garment over the body.
  - hide: skin the garment fully covers, more than HIDE_FROM_HEM from its edges, joins its Delete.<asset> group.
    MPFB's own name is used; the group is created when the asset ships none, as toigo_wool_pants doesn't.
  - separate: the garment eases out wherever visible skin still pokes through it.

"Outward" for a vertex is the body's surface normal at the nearest body point, taken at rest, then carried into
any pose by the vertex's own skinning. Garment normals aren't used: they flip at folded hems and waistbands.
check_pair() is the red/green test. It counts visible inner vertices outside the outer surface, inside its covered
region, in the current pose."""
from contextlib import contextmanager

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from mpfb_common import mpfb

PUSH, MIN_GAP = 0.003, 0.002          # inner ends 3 mm under the outer; closer than 2 mm (or outside) gets fixed
REACH_IN, REACH_OUT = 0.04, 0.03      # covered region: outer within 4 cm in front, or up to 3 cm behind (poking)
BODY_REACH, NEAR_REACH = 0.08, 0.03   # loose cloth hangs up to 8 cm off the skin; creases/crotch use nearest point
RINGS, HIDE_FROM_HEM = 3, 0.03
MIN_OPENING = 0.15                    # boundary loops shorter than this (fly, button holes) are not garment openings
ISLAND_MAX = 300                      # visible patches up to this many faces, enclosed by hidden ones and away from
                                      # every open edge of the garment, are under it too (the crotch between the legs)
HEM_RIDE, RIDE_MAX = 0.06, 0.5         # an outer hem takes up to half the weights of what it lies on, fading over 6 cm
WEIGHT_RINGS = 6                      # the inner's shared-weight band fades out over this many rings past the cover
BODY_GAP = 0.0015
SKIN_GAP, SKIN_PUSH = 0.004, 0.005    # cloth keeps 5 mm off skin it nearly touches: room for creases in motion
SINK_INNER = False


def mhclo_type(obj):
    return mpfb("services.objectservice", "ObjectService").get_object_type(obj)


def is_body(obj):
    return mhclo_type(obj) == "Basemesh"


def z_depth(obj):
    props = mpfb("ui.create_assets.makeclothes", "MakeClothesObjectProperties")
    return float(props.get_value("z_depth", entity_reference=obj) or 50)


@contextmanager
def unmasked(*objs):
    """Mask modifiers off, so evaluated vertex indices equal data indices."""
    ms = [m for o in objs for m in o.modifiers if m.type == "MASK" and m.show_viewport]
    for m in ms:
        m.show_viewport = False
    try:
        yield
    finally:
        for m in ms:
            m.show_viewport = True


@contextmanager
def rest(rig):
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()
    try:
        yield
    finally:
        rig.data.pose_position = "POSE"
        bpy.context.view_layer.update()


def evaluated(obj):
    """World-space coordinates and polygons of the evaluated (posed, masked) mesh."""
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = ev.to_mesh()
    mw = obj.matrix_world
    co = [mw @ p.co for p in m.vertices]
    polys = [tuple(p.vertices) for p in m.polygons]
    ev.to_mesh_clear()
    return co, polys


def bvh(obj):
    co, polys = evaluated(obj)
    return BVHTree.FromPolygons(co, polys), co, polys


def body_of(rig):
    return next(o for o in rig.children if is_body(o))


def body_tree(rig):
    """The skin surface in the current pose, without the clothes masks (they hide skin, not shape)."""
    body = body_of(rig)
    masks = [m for m in body.modifiers if m.type == "MASK"]
    state = [m.show_viewport for m in masks]
    for m in masks:
        m.show_viewport = m.vertex_group == "body" and not m.invert_vertex_group  # only MPFB's helper mask
    tree = bvh(body)[0]
    for m, on in zip(masks, state):
        m.show_viewport = on
    return tree


def rest_dirs(obj, rig):
    """Outward direction per data vertex, at rest: the body normal at the nearest body point."""
    with rest(rig), unmasked(obj):
        co, _ = evaluated(obj)
        bt = body_tree(rig)
        return [bt.find_nearest(p)[1] for p in co]


def posed_dirs(obj, rig, dirs0):
    """Carry the rest directions into the current pose with each vertex's skinning (linear blend of bone rotations)."""
    mats = {pb.name: (pb.matrix @ pb.bone.matrix_local.inverted()).to_3x3() for pb in rig.pose.bones if pb.bone.use_deform}
    names = {vg.index: vg.name for vg in obj.vertex_groups}
    out = []
    for v, d in zip(obj.data.vertices, dirs0):
        m, tot = Matrix.Diagonal((0.0, 0.0, 0.0)), 0.0
        for g in v.groups:
            b = names.get(g.group)
            if b in mats and g.weight > 0:
                m += mats[b] * g.weight
                tot += g.weight
        out.append((m @ d).normalized() if tot > 0 else d)
    return out


def coverage(co, dirs, outer_tree, reach_in=REACH_IN):
    """Per vertex: (covered, signed distance to the outer surface: + = poking out through it, hit point)."""
    out = []
    for p, n in zip(co, dirs):
        f = outer_tree.ray_cast(p + n * 1e-6, n, reach_in)   # outer in front: we are under it
        if f[0] is not None:
            out.append((True, -f[3], f[0]))
            continue
        b = outer_tree.ray_cast(p - n * 1e-6, -n, REACH_OUT)  # outer behind us: we poke out through it
        out.append((True, b[3], b[0]) if b[0] is not None else (False, None, None))
    return out


def covered_by(garment, co, dirs, tree):
    """Skin coverage: a ray out along the skin normal meets the garment within BODY_REACH, or (creases, crotch) the
    nearest garment point is within NEAR_REACH and lies outward of the skin."""
    hits = []
    for p, n in zip(co, dirs):
        f = tree.ray_cast(p + n * 1e-6, n, BODY_REACH)
        if f[0] is not None:
            hits.append(f[0])
            continue
        loc, _, _, d = tree.find_nearest(p, NEAR_REACH)
        hits.append(loc if loc is not None and (loc - p).dot(n) > 0.5 * d else None)
    return hits


def visible_mask(obj):
    """Per data vertex: does it render? Reads the Mask modifiers (Hidden_by.*, Delete.*, MPFB's helper mask)."""
    vis = [True] * len(obj.data.vertices)
    for m in obj.modifiers:
        if m.type != "MASK" or not m.show_viewport or m.vertex_group not in obj.vertex_groups:
            continue
        gi = obj.vertex_groups[m.vertex_group].index
        for v in obj.data.vertices:
            inside = any(e.group == gi and e.weight > 0 for e in v.groups)
            if inside == m.invert_vertex_group:
                vis[v.index] = False
    return vis


def rings_from(mesh, seeds, rings):
    """{vertex: ring number} for vertices up to `rings` edges away from the seeds (seeds excluded), and adjacency."""
    adj = [[] for _ in mesh.vertices]
    for e in mesh.edges:
        a, b = e.vertices
        adj[a].append(b)
        adj[b].append(a)
    ring, frontier, seen = {}, set(seeds), set(seeds)
    for r in range(1, rings + 1):
        nxt = {j for i in frontier for j in adj[i] if j not in seen}
        for j in nxt:
            ring[j] = r
        seen |= nxt
        frontier = nxt
    return ring, adj


def boundary_kd(obj, co):
    """KD tree of the garment's openings: boundary loops at least MIN_OPENING long (waist, cuffs, sleeves, neck).
    Small holes (a fly, a button hole) aren't openings: skin 'near' them is still deep under the cloth."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    edges = [e for e in bm.edges if e.is_boundary]
    by_vert = {}
    for e in edges:
        for v in e.verts:
            by_vert.setdefault(v.index, []).append(e)
    seen, pts = set(), []
    for e in edges:
        if e.index in seen:
            continue
        loop, stack = [], [e]
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            loop.append(x)
            stack.extend(y for v in x.verts for y in by_vert[v.index] if y.index not in seen)
        if sum((co[x.verts[0].index] - co[x.verts[1].index]).length for x in loop) >= MIN_OPENING:
            pts.extend(co[v.index] for x in loop for v in x.verts)
    bm.free()
    kd = KDTree(max(len(pts), 1))
    for k, p in enumerate(pts):
        kd.insert(p, k)
    kd.balance()
    return kd


def overlap_height(a, b):
    """Where a meets b, as a fraction of a's own height (0 = its lowest point), and how many of a's verts meet b."""
    tb = bvh(b)[0]
    co, _ = evaluated(a)
    zs = [p.z for p in co]
    lo, hi = min(zs), max(zs)
    near = [(p.z - lo) / max(hi - lo, 1e-6) for p in co if tb.find_nearest(p, 0.02)[0] is not None]
    return (float(np.mean(near)) if near else None), len(near)


def garments(rig):
    return [o for o in rig.children if o.type == "MESH" and mhclo_type(o).lower() == "clothes"]


def garment_pairs(rig):
    """[(outer, inner)] for every overlapping garment pair, outermost layers first."""
    clothes, pairs = garments(rig), []
    for i, a in enumerate(clothes):
        for b in clothes[i + 1:]:
            ha, na = overlap_height(a, b)
            hb, nb = overlap_height(b, a)
            if not na or not nb:
                continue  # never touch: socks vs tee
            if z_depth(a) != z_depth(b):
                pairs.append((a, b) if z_depth(a) > z_depth(b) else (b, a))
            else:
                pairs.append((a, b) if ha < hb else (b, a))
    rank = {o.name: sum(1 for p in pairs if p[1] is o) for o in clothes}
    return sorted(pairs, key=lambda p: rank[p[0].name])


def check_pair(outer, inner, rig, dirs0, region=None):
    """(# visible inner verts outside the outer surface in its covered region, worst mm, # covered), current pose.
    `inner` may be the body (skin showing through cloth); `region` limits it to the skin the garment covers at rest,
    so a hand brushing the thigh doesn't count as the pants failing."""
    tree = bvh(outer)[0]  # what renders of the outer
    with unmasked(inner):
        co, _ = evaluated(inner)
    vis = visible_mask(inner)
    cov = coverage(co, posed_dirs(inner, rig, dirs0), tree, BODY_REACH if is_body(inner) else REACH_IN)
    idx = [i for i, ok in enumerate(vis) if ok and (region is None or i in region) and cov[i][0]]
    bad = [cov[i][1] for i in idx if cov[i][1] > 0.0]
    return len(bad), (max(bad) * 1000 if bad else 0.0), len(idx)


def body_region(garment, rig):
    """Skin vertices the garment covers at rest (for check_pair on the body)."""
    body = body_of(rig)
    with rest(rig), unmasked(body, garment):
        tree = bvh(garment)[0]
        co, _ = evaluated(body)
    dirs = rest_dirs(body, rig)
    return {i for i, h in enumerate(covered_by(garment, co, dirs, tree)) if h is not None}


def separate(outer, inner, rig, region=None, log=print):
    """Ease the outer out (and optionally sink the inner) until every covered inner vertex sits PUSH under it."""
    me, ome = inner.data, outer.data
    to_in, to_out = inner.matrix_world.inverted(), outer.matrix_world.inverted()
    dirs = rest_dirs(inner, rig)
    vis = visible_mask(inner)
    done, eased, max_out = set(), set(), 0.0
    with rest(rig), unmasked(inner, outer):
        for it in range(4):
            tree, _, opolys = bvh(outer)
            btree = body_tree(rig)
            co, _ = evaluated(inner)
            cov = coverage(co, dirs, tree, BODY_REACH if is_body(inner) else REACH_IN)
            gap, push = (SKIN_GAP, SKIN_PUSH) if is_body(inner) else (MIN_GAP, PUSH)
            limit = -gap if it == 0 else 0.0  # later passes only fix what still pokes out: no creeping band
            need = {i: c[1] + push for i, c in enumerate(cov)
                    if c[0] and c[1] > limit and vis[i] and (region is None or i in region)}
            if not need:
                break

            def room(i):
                if not SINK_INNER or is_body(inner):
                    return 0.0
                h = btree.ray_cast(co[i] - dirs[i] * 1e-6, -dirs[i], 0.2)
                return max(0.0, (h[3] if h[0] is not None else btree.find_nearest(co[i])[3]) - BODY_GAP)

            d_in, out_push = np.zeros((len(me.vertices), 3)), {}
            for i, amount in need.items():
                sink = min(amount, room(i))
                d_in[i] = -np.array(dirs[i]) * sink
                if amount - sink > 1e-5:  # the outer makes up the rest by easing out over it
                    for vi in opolys[tree.find_nearest(cov[i][2])[2]]:
                        if vi not in out_push or out_push[vi][0] < amount - sink:
                            out_push[vi] = (amount - sink, dirs[i])
            if SINK_INNER and not is_body(inner):
                ring, adj = rings_from(me, need.keys(), RINGS)
                for _ in range(25):
                    for j in ring:
                        d_in[j] = np.mean([d_in[k] for k in adj[j]], axis=0)
                for j in ring:
                    lim, mag = room(j), np.linalg.norm(d_in[j])
                    if mag > lim:
                        d_in[j] *= lim / mag
                for i in list(need) + list(ring):
                    me.vertices[i].co = to_in @ (co[i] + Vector(d_in[i]))
                me.update()
            if out_push:
                ocur = [outer.matrix_world @ v.co for v in ome.vertices]
                d_out = np.zeros((len(ome.vertices), 3))
                for vi, (a, n) in out_push.items():
                    d_out[vi] = np.array(n) * a
                oring, oadj = rings_from(ome, out_push.keys(), RINGS)
                for _ in range(25):  # eased verts fixed, the band relaxes between them and the untouched cloth
                    for j in oring:
                        d_out[j] = np.mean([d_out[k] for k in oadj[j]], axis=0)
                for i in list(out_push) + list(oring):
                    ome.vertices[i].co = to_out @ (ocur[i] + Vector(d_out[i]))
                ome.update()
                max_out = max(max_out, float(np.linalg.norm(d_out, axis=1).max()))
                eased |= set(out_push)
            done |= set(need)
    log(f"  {outer.name} over {inner.name}: {len(done)} inner verts too close or poking, outer eased out at "
        f"{len(eased)} verts (max {max_out * 1000:.1f} mm)")
    return done


def hide_covered(outer, inner, rig, group, log=print):
    """Put inner faces that are fully covered, deeper than HIDE_FROM_HEM inside the outer's edges, in `group` + Mask."""
    with rest(rig), unmasked(inner, outer):
        tree, ocos, _ = bvh(outer)
        kd = boundary_kd(outer, [outer.matrix_world @ v.co for v in outer.data.vertices])
        co, _ = evaluated(inner)
    dirs = rest_dirs(inner, rig)
    if is_body(inner):
        hits = covered_by(outer, co, dirs, tree)
    else:
        hits = [c[2] for c in coverage(co, dirs, tree)]
    deep = [h is not None and kd.find(h)[2] > HIDE_FROM_HEM for h in hits]
    inb = None
    if is_body(inner):  # never touch MPFB's helper geometry
        gi = inner.vertex_groups["body"].index
        inb = {v.index for v in inner.data.vertices if any(e.group == gi and e.weight > 0 for e in v.groups)}
        deep = [d and i in inb for i, d in enumerate(deep)]
    me = inner.data
    hide = [all(deep[i] for i in p.vertices) for p in me.polygons]
    # Close islands: small patches of still-visible faces enclosed by hidden ones (a crotch vertex whose ray found no
    # cloth, say) are under the garment too, unless they reach toward one of its open edges.
    near_edge = [h is not None and kd.find(h)[2] <= HIDE_FROM_HEM for h in hits]
    by_edge = {}
    for p in me.polygons:
        for k in p.edge_keys:
            by_edge.setdefault(k, []).append(p.index)
    seen = set()
    for p in me.polygons:
        if hide[p.index] or p.index in seen or (inb is not None and not all(i in inb for i in p.vertices)):
            continue
        comp, stack = [], [p.index]
        while stack:  # full flood fill: a truncated one would leave fragments that look like islands later
            f = stack.pop()
            if f in seen:
                continue
            seen.add(f)
            comp.append(f)
            stack.extend(g for k in me.polygons[f].edge_keys for g in by_edge[k] if not hide[g] and g not in seen
                         and (inb is None or all(i in inb for i in me.polygons[g].vertices)))
        if len(comp) <= ISLAND_MAX and not any(near_edge[i] for f in comp for i in me.polygons[f].vertices):
            for f in comp:
                hide[f] = True
    hidden = [p for p in me.polygons if hide[p.index]]
    keep = {i for p in me.polygons if not hide[p.index] for i in p.vertices}
    verts = sorted({i for p in hidden for i in p.vertices} - keep)  # a Mask drops faces touching these: exactly `hidden`
    g = inner.vertex_groups.get(group) or inner.vertex_groups.new(name=group)
    g.add(verts, 1.0, "REPLACE")
    if not any(m.type == "MASK" and m.vertex_group == group for m in inner.modifiers):
        mod = inner.modifiers.new(group, "MASK")
        mod.vertex_group, mod.invert_vertex_group = group, True
    log(f"  {inner.name} under {outer.name}: {len(hidden)} faces hidden ({group})")
    return {i for p in hidden for i in p.vertices}


def transfer_weights(src, dst, rig, factors, group):
    """dst takes src's skin weights (nearest-face interpolated) at the given per-vertex factors, then renormalises."""
    g = dst.vertex_groups.get(group) or dst.vertex_groups.new(name=group)
    for i, f in factors.items():
        g.add([i], float(f), "REPLACE")
    had = {vg.name for vg in dst.vertex_groups}
    bones = {b.name for b in rig.data.bones if b.use_deform}
    for vg in src.vertex_groups:  # the modifier only fills destination groups that exist
        if vg.name not in had:
            dst.vertex_groups.new(name=vg.name)
    with rest(rig):
        dt = dst.modifiers.new("TMP_layer_weights", "DATA_TRANSFER")
        dt.object, dt.use_object_transform = src, True
        dt.use_vert_data, dt.data_types_verts = True, {"VGROUP_WEIGHTS"}
        dt.vert_mapping = "POLYINTERP_NEAREST"
        dt.layers_vgroup_select_src, dt.layers_vgroup_select_dst = "ALL", "NAME"
        dt.mix_mode, dt.mix_factor, dt.vertex_group = "REPLACE", 1.0, group
        with bpy.context.temp_override(object=dst, active_object=dst, selected_objects=[dst]):
            bpy.ops.object.modifier_move_to_index(modifier=dt.name, index=0)
            bpy.ops.object.modifier_apply(modifier=dt.name)
            bpy.ops.object.vertex_group_normalize_all(group_select_mode="BONE_DEFORM", lock_active=False)
    for vg in [vg for vg in dst.vertex_groups if vg.name not in had and vg.name not in bones]:
        dst.vertex_groups.remove(vg)  # src's bookkeeping groups (Delete.*, Layer.*) came along; drop them


def share_weights(outer, inner, rig, band, log=print):
    """The inner's band (covered + hidden verts, fading over RINGS rings) takes the outer's skin weights."""
    ring, _ = rings_from(inner.data, band, WEIGHT_RINGS)
    factors = {i: 1.0 for i in band}
    factors.update({j: 1.0 - r / (WEIGHT_RINGS + 1) for j, r in ring.items()})
    transfer_weights(outer, inner, rig, factors, "Layer." + outer.name)
    log(f"  {inner.name}: {len(factors)} verts share {outer.name}'s weights")


def hem_ride(outer, inner, rig, log=print):
    """The outer's open edge rides on what's under it: verts within HEM_RIDE of the edge, with the inner beneath,
    take up to RIDE_MAX of the inner's weights (fading inward). A tee hem then lies on the lap when he sits
    instead of the thighs rising through it. Run before share_weights, while the inner still has its own weights."""
    with rest(rig), unmasked(inner, outer):
        ocos = [outer.matrix_world @ v.co for v in outer.data.vertices]
        kd = boundary_kd(outer, ocos)
        itree = bvh(inner)[0]
    odirs = rest_dirs(outer, rig)
    factors = {}
    for i, (p, n) in enumerate(zip(ocos, odirs)):
        e = kd.find(p)[2]
        if e < HEM_RIDE and itree.ray_cast(p - n * 1e-6, -n, REACH_IN)[0] is not None:
            factors[i] = RIDE_MAX * (1.0 - e / HEM_RIDE)
    if factors:
        transfer_weights(inner, outer, rig, factors, "Ride." + inner.name)
    log(f"  {outer.name}: {len(factors)} hem verts ride on {inner.name}")


def ease_for_poses(outer, inner, rig, pose_names=("sit", "crouch", "walk", "bend", "twist_l30", "twist_r30"), log=print):
    """Rest-pose easing can't foresee skinning: where the inner still pokes out of the outer in a test pose, ease the
    outer outward at rest (along its rest outward direction) by 1.5x what it lacked in that pose plus PUSH, take
    the largest need over all poses, fade it over RINGS rings, and repeat until no pose pokes (max 6 rounds)."""
    from poses import apply_pose, reset
    body = body_of(rig)
    dirs_in = rest_dirs(inner, rig)
    dirs_out = rest_dirs(outer, rig)
    vis = visible_mask(inner)
    ome = outer.data
    for rnd in range(6):
        need = {}
        for pose in pose_names:
            apply_pose(rig, body, pose)
            with unmasked(outer, inner):  # data-indexed faces so the need maps back onto outer vertices
                tree, _, opolys = bvh(outer)
                co, _ = evaluated(inner)
            cov = coverage(co, posed_dirs(inner, rig, dirs_in), tree)
            for i, c in enumerate(cov):
                if vis[i] and c[0] and c[1] > -MIN_GAP:
                    face = tree.find_nearest(c[2])[2]
                    for vi in opolys[face]:  # overshoot: a rest-pose push maps imperfectly onto the posed crease
                        need[vi] = max(need.get(vi, 0.0), 1.5 * (c[1] + PUSH))
        reset(rig)
        if not need:
            break
        cur = [outer.matrix_world @ v.co for v in ome.vertices]
        d = np.zeros((len(ome.vertices), 3))
        for vi, a in need.items():
            if vi < len(d):
                d[vi] = np.array(dirs_out[vi]) * a
        ring, adj = rings_from(ome, need.keys(), RINGS)
        for _ in range(25):
            for j in ring:
                d[j] = np.mean([d[k] for k in adj[j]], axis=0)
        to_out = outer.matrix_world.inverted()
        for i in list(need) + list(ring):
            ome.vertices[i].co = to_out @ (cur[i] + Vector(d[i]))
        ome.update()
        log(f"  {outer.name} over {inner.name}: round {rnd + 1}, eased {len(need)} verts for posed fit "
            f"(max {max(need.values()) * 1000:.1f} mm)")


def layer_all(rig, log=print):
    body = body_of(rig)
    for g in garments(rig):  # skin first: hide what each garment covers, then ease it over what still pokes
        log(f"skin under {g.name}")
        hide_covered(g, body, rig, "Delete." + g.name.split(".", 1)[-1], log)
        separate(g, body, rig, region=body_region(g, rig), log=log)
    pairs = garment_pairs(rig)
    for outer, inner in pairs:
        log(f"layer: {outer.name} (outer) over {inner.name}")
        separate(outer, inner, rig, log=log)
        hidden = hide_covered(outer, inner, rig, "Hidden_by." + outer.name, log)
        with rest(rig), unmasked(inner, outer):
            tree = bvh(outer)[0]
            co, _ = evaluated(inner)
        dirs = rest_dirs(inner, rig)
        covered = {i for i, c in enumerate(coverage(co, dirs, tree)) if c[0]}
        hem_ride(outer, inner, rig, log)
        share_weights(outer, inner, rig, covered | hidden, log)
        ease_for_poses(outer, inner, rig, log=log)
    return pairs
