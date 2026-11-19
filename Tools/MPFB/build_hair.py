"""T2: strand hair on the user's teen with MPFB's own hair editor (CC0 hair editor pack by Tomas Klecer), plus
strand eyebrows, rendered in Cycles next to the old MakeHuman card hair.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/MPFB/build_hair.py [asset=basic_short_hair] [brows=wild_eyebrow]
        [tag=<name>] [views=front,tq,side,back] [cards=short02] [samples=192] [save=1] [k=v tuning...]
Tuning keys are MPFB's hair-editor properties (see HAIR below and hairproperties.py), e.g. length=0.8 clump=0.4.
Writes Saved/CharacterShots/mpfb/hair/<tag>_<view>.png (+ cards_<view>.png) and, with save=1,
P:/FoA-Assets/character/mpfb/teen/foa_teen_hair.blend. Never writes the user's MHM."""
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
from load_teen import load_teen  # noqa: E402
from mpfb_common import ASSETS, SHOTS, args, ensure_dir, mpfb  # noqa: E402
from stage import shoot, stage  # noqa: E402

PROPS = mpfb("ui.haireditorpanel.hairproperties", "DYNAMIC_HAIR_PROPS_DEFINITIONS")
MAT_PROPS = mpfb("ui.haireditorpanel.hairproperties", "DYNAMIC_HAIR_MATERIAL_PROPS_DEFINITIONS")
ObjectService = mpfb("services.objectservice", "ObjectService")
HumanService = mpfb("services.humanservice", "HumanService")
AssetService = mpfb("services.assetservice", "AssetService")
ModifierService = mpfb("services.modifierservice", "ModifierService")

# A heavier 16-17-year-old: short and messy, fuller on top, natural dark brown (value matters more than hue: B&W game).
HAIR = dict(length=0.9, density=1.0, thickness=0.00024, frizz=0.1, clump=0.15, clump_distance=0.006,
            clump_tip_spread=0.012, noise=0.35, noise_distance=0.004, noise_scale=10.0, curl=0.0)
COLOR = dict(color1=(0.055, 0.035, 0.020, 1.0), color2=(0.014, 0.009, 0.005, 1.0), darken_root=0.5,
             root_color_length=0.3)


def set_input(obj, mod_name, ident, value):
    mod = obj.modifiers[mod_name]
    old = ModifierService.get_node_group_input(mod, ident)
    ModifierService.set_node_group_input(mod, ident, float(value))
    print(f"  {obj.name}.{mod_name}[{ident}] {old} -> {value}")
    obj.update_tag()


def apply_strands(body, asset, tuning, colors):
    with bpy.context.temp_override(object=body, active_object=body, selected_objects=[body]):
        if not getattr(body, "MPFB_HAI_hair_setup", False):
            bpy.ops.mpfb.setup_hair_operator()
        bpy.ops.mpfb.apply_hair_operator(hair_asset=asset)
    obj = bpy.data.objects[asset]
    defaults = {k: ModifierService.get_node_group_input(obj.modifiers[m], i) for k, (m, i, _) in PROPS.items() if m in obj.modifiers}
    print("DEFAULTS", asset, {k: round(v, 4) if isinstance(v, float) else v for k, v in defaults.items()})
    for key, value in tuning.items():
        if key in PROPS:
            mod, ident, _ = PROPS[key]
            if mod in obj.modifiers:
                set_input(obj, mod, ident, value)
    mat = obj.active_material
    group = next((n for n in mat.node_tree.nodes if n.type == "GROUP"), None)
    for key, value in colors.items():
        label = MAT_PROPS[key][0]
        if group and label in group.inputs:
            group.inputs[label].default_value = value
    seen = set()
    def roughen(tree):
        if tree in seen:
            return
        seen.add(tree)
        for node in tree.nodes:
            if node.type in ('BSDF_HAIR_PRINCIPLED', 'BSDF_PRINCIPLED') and 'Roughness' in node.inputs:
                node.inputs['Roughness'].default_value = .6
            if node.type == 'GROUP' and node.node_tree:
                roughen(node.node_tree)
    roughen(mat.node_tree)
    return obj


def fit_to_head(body, hair_objs):
    """The pack's grooms sit on MPFB's default human; ours has a different head. Give them a stand-in surface whose
    rest_position is the default human and whose evaluated shape is ours (same base-mesh topology and UVs), so each
    groom's own Deform Curves on Surface node carries every strand onto this head, roots and directions."""
    TargetService = mpfb("services.targetservice", "TargetService")
    dg = bpy.context.evaluated_depsgraph_get()
    default = HumanService.create_human()  # MPFB defaults, as the grooms were made on
    def shape(obj):
        masks = [m for m in obj.modifiers if m.show_viewport and m.type == "MASK"]  # keep the rig: it places the mesh
        for m in masks:
            m.show_viewport = False
        bpy.context.view_layer.update()
        ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        m = ev.to_mesh()
        co = [obj.matrix_world @ v.co for v in m.vertices]
        ev.to_mesh_clear()
        for mm in masks:
            mm.show_viewport = True
        return co
    co_default, co_ours = shape(default), shape(body)
    print("FIT head top z: default %.3f, teen %.3f; body loc %s rig loc %s" % (max(p.z for p in co_default[:13380]),
          max(p.z for p in co_ours[:13380]), tuple(body.matrix_world.translation), tuple(body.parent.location) if body.parent else None))
    assert len(co_default) == len(co_ours), "default human and teen must share the MakeHuman base mesh"
    bpy.data.objects.remove(default)
    me = body.data.copy()
    surf = bpy.data.objects.new("TMP_hair_surface", me)
    bpy.context.scene.collection.objects.link(surf)
    surf.shape_key_clear()
    for v, p in zip(me.vertices, co_default):
        v.co = p
    surf.shape_key_add(name="Basis")
    sk = surf.shape_key_add(name="teen")
    for d, p in zip(sk.data, co_ours):
        d.co = p
    sk.value = 1.0
    surf.add_rest_position_attribute = True
    surf.hide_render = True
    surf.hide_viewport = False
    print("FIT uv layers", [u.name for u in me.uv_layers], "hair uv", [h.data.surface_uv_map for h in hair_objs])
    for h in hair_objs:
        h.data.surface = surf
        h.data.surface_uv_map = "UVMap" if "UVMap" in me.uv_layers else me.uv_layers[0].name
        h.parent = None
        h.matrix_world.identity()
    bpy.context.view_layer.update()
    return surf


LIFT, BASE, SAT = 0.16, 0.0012, 0.04   # volume: strands rise off the scalp 1.2 mm + LIFT x arc length (to 4 cm),
TOP_BAND, SIDE_LIFT = 0.12, 0.35       # at full LIFT on the crown, fading to SIDE_LIFT of it 12 cm below the top


def bake(obj):
    """Freeze the groom: a new plain Curves object holding the evaluated result of its geometry-node stack
    (interpolation, clumps, noise, surface fit). Applying the modifiers one by one loses the surface fit, so the
    evaluated curves are copied attribute by attribute instead. Alembic/Groom export needs plain curves anyway."""
    import numpy as np
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    sizes = [c.points_length for c in ev.curves]
    data = bpy.data.hair_curves.new(obj.name + "_baked")
    data.add_curves(sizes)
    for name in ("position", "radius"):
        src = ev.attributes.get(name)
        if src is None:
            continue
        width = 3 if src.data_type == "FLOAT_VECTOR" else 1
        buf = np.empty(len(src.data) * width, dtype=np.float32)
        src.data.foreach_get("vector" if width == 3 else "value", buf)
        dst = data.attributes.get(name) or data.attributes.new(name, src.data_type, src.domain)
        dst.data.foreach_set("vector" if width == 3 else "value", buf)
    for m in obj.data.materials:
        data.materials.append(m)
    baked = bpy.data.objects.new(obj.name, data)
    bpy.context.scene.collection.objects.link(baked)
    baked.matrix_world = obj.matrix_world
    old = obj.name
    bpy.data.objects.remove(obj)
    baked.name = old
    print("BAKE", old, len(sizes), "curves", sum(sizes), "points")
    return baked


def lift(body, obj, lift_k, base):
    """Keep every strand point out of the scalp, rising with distance from its root, so the groom has volume and
    nothing lies buried in the low-poly head. Then relax each strand once so the pushed points don't kink."""
    import numpy as np
    from mathutils.bvhtree import BVHTree
    masks = [m for m in body.modifiers if m.type == "MASK" and m.vertex_group != "body"]
    for m in masks:
        m.show_viewport = False
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mb = ev.to_mesh()
    tree = BVHTree.FromPolygons([body.matrix_world @ v.co for v in mb.vertices], [tuple(p.vertices) for p in mb.polygons])
    ev.to_mesh_clear()
    for m in masks:
        m.show_viewport = True
    data = obj.data
    n = len(data.points)
    pos = np.empty(n * 3, dtype=np.float32)
    data.attributes["position"].data.foreach_get("vector", pos)
    pos = pos.reshape(-1, 3)
    mw, mwi = obj.matrix_world, obj.matrix_world.inverted()
    moved, worst = 0, 0.0
    top = max((mw @ Vector(pos[c.first_point_index])).z for c in data.curves)
    for c in data.curves:
        a, k = c.first_point_index, c.points_length
        pts = [mw @ Vector(pos[i]) for i in range(a, a + k)]
        crown = min(1.0, max(0.0, 1.0 - (top - pts[0].z) / TOP_BAND))  # 1 on the crown, 0 at the nape and sides
        k_lift = lift_k * (SIDE_LIFT + (1.0 - SIDE_LIFT) * crown)
        s = 0.0
        for j in range(1, k):
            s += (pts[j] - pts[j - 1]).length
            want = base + k_lift * min(s, SAT)
            loc, nrm, _, _ = tree.find_nearest(pts[j])
            if loc is None:
                continue
            sd = (pts[j] - loc).dot(nrm)
            if sd < want:
                pts[j] = pts[j] + nrm * (want - sd)
                moved += 1
                worst = max(worst, want - sd)
        for j in range(1, k - 1):  # one relax pass along the strand, root fixed
            pts[j] = pts[j] * 0.5 + (pts[j - 1] + pts[j + 1]) * 0.25
        for j, p in enumerate(pts):
            pos[a + j] = mwi @ p
    data.attributes["position"].data.foreach_set("vector", pos.ravel())
    data.update_tag()
    return dict(points=n, moved=moved, worst_mm=round(worst * 1000, 1))


def scalp_tint(body, hair, color=(0.02, 0.013, 0.008), reach=0.012):
    """Darken the skin under the hair, as hair artists paint the scalp: a 'FoA_scalp' vertex mask from the strand roots
    multiplies the skin colour in Blender. In UE the same mask is baked into the head's base colour (or an MI mask)."""
    from mathutils.kdtree import KDTree
    d = hair.data
    roots = [hair.matrix_world @ Vector(d.points[c.first_point_index].position) for c in d.curves]
    kd = KDTree(len(roots))
    for i, p in enumerate(roots):
        kd.insert(p, i)
    kd.balance()
    masks = [m for m in body.modifiers if m.type == "MASK" and m.show_viewport]
    for m in masks:
        m.show_viewport = False
    bpy.context.view_layer.update()  # the depsgraph must see the masks off, or vertex indices won't match the data
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    cos = [body.matrix_world @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    for m in masks:
        m.show_viewport = True
    attr = body.data.color_attributes.get("FoA_scalp") or body.data.color_attributes.new("FoA_scalp", "FLOAT_COLOR", "POINT")
    for i, p in enumerate(cos):
        _, _, dist = kd.find(p)
        w = max(0.0, 1.0 - dist / reach) if dist is not None else 0.0
        attr.data[i].color = (w, w, w, 1.0)
    for slot in body.material_slots:
        nt = slot.material.node_tree if slot.material else None
        bsdf = nt and next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not bsdf or not bsdf.inputs["Base Color"].links:
            continue
        src = bsdf.inputs["Base Color"].links[0].from_socket
        a = nt.nodes.new("ShaderNodeAttribute")
        a.attribute_name = "FoA_scalp"
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs[7].default_value = (*color, 1.0)
        nt.links.new(a.outputs["Fac"], mix.inputs["Factor"])
        nt.links.new(src, mix.inputs[6])
        nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])


def check_scalp(body, hair, cam, head, out, tag):
    """Scalp-spot test: interior scalp (skin with >= 6 strand roots within 8 mm) renders flat white, everything else
    flat black, hair included; any white pixel blob in front/3-4/side/back/top views is a bald spot. Returns
    {view: (white pixels, largest blob)}. Red-proven by running with the hair hidden (every view lights up)."""
    import numpy as np
    from mathutils.kdtree import KDTree
    d = hair.data
    roots = [hair.matrix_world @ Vector(d.points[c.first_point_index].position) for c in d.curves]
    kd = KDTree(len(roots))
    for i, p in enumerate(roots):
        kd.insert(p, i)
    kd.balance()
    masks = [m for m in body.modifiers if m.type == "MASK" and m.show_viewport]
    for m in masks:
        m.show_viewport = False
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    inner = [len(kd.find_range(body.matrix_world @ v.co, 0.008)) >= 6 for v in me.vertices]
    neighbours = [set() for _ in body.data.vertices]
    for edge in body.data.edges:
        a,b=edge.vertices
        neighbours[a].add(b); neighbours[b].add(a)
    for _ in range(2):  # exclude the hairline, where vertex colour interpolation extends beyond the roots
        inner = [value and all(inner[n] for n in neighbours[i]) for i,value in enumerate(inner)]
    ev.to_mesh_clear()
    for m in masks:
        m.show_viewport = True
    attr = body.data.color_attributes.get("FoA_scalp_core") or body.data.color_attributes.new("FoA_scalp_core", "FLOAT_COLOR", "POINT")
    for i, ok in enumerate(inner):
        attr.data[i].color = (1.0, 1.0, 1.0, 1.0) if ok else (0.0, 0.0, 0.0, 1.0)
    white = bpy.data.materials.new("TMP_scalp_white")
    white.use_nodes = True
    nt = white.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    e = nt.nodes.new("ShaderNodeEmission")
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_name = "FoA_scalp_core"
    nt.links.new(a.outputs["Color"], e.inputs["Color"])
    nt.links.new(e.outputs[0], o.inputs["Surface"])
    black = bpy.data.materials.new("TMP_black")
    black.use_nodes = True
    black.node_tree.nodes.clear()
    ob = black.node_tree.nodes.new("ShaderNodeOutputMaterial")
    eb = black.node_tree.nodes.new("ShaderNodeEmission")
    eb.inputs["Color"].default_value = (0, 0, 0, 1)
    black.node_tree.links.new(eb.outputs[0], ob.inputs["Surface"])
    saved = {}
    for obj in bpy.data.objects:
        if obj.type in ("MESH", "CURVES") and not obj.hide_render:
            saved[obj.name] = [sl.material for sl in obj.material_slots]
            for sl in obj.material_slots:
                sl.material = white if obj == body else black
    scn = bpy.context.scene
    old = (scn.render.engine, scn.render.resolution_x, scn.render.resolution_y, scn.view_settings.view_transform)
    scn.render.engine = "CYCLES"
    scn.cycles.samples = 16
    scn.render.resolution_x = scn.render.resolution_y = 600
    scn.view_settings.view_transform = "Standard"
    res = {}
    for v, yaw, lift in (("front", 0, 0.06), ("tq", 35, 0.06), ("side", 90, 0.06), ("back", 180, 0.06), ("top", 180, 0.55)):
        path = f"{out}/{tag}_scalpcheck_{v}.png"
        shoot(cam, head, 0.75, yaw, 85, path, lift=lift)
        img = bpy.data.images.load(path)
        px = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)[:, :, 0] > 0.5
        bpy.data.images.remove(img)
        # A scalp spot spans several pixels; subpixel spaces between separate fibres are expected.
        core=np.logical_and.reduce([np.roll(np.roll(px,dy,0),dx,1) for dy in (-1,0,1) for dx in (-1,0,1)])
        px=np.logical_or.reduce([np.roll(np.roll(core,dy,0),dx,1) for dy in (-1,0,1) for dx in (-1,0,1)])
        seen, best = np.zeros_like(px), 0
        for y, x in zip(*np.nonzero(px)):  # largest 4-connected white blob
            if seen[y, x]:
                continue
            stack, size = [(y, x)], 0
            seen[y, x] = True
            while stack:
                cy, cx = stack.pop()
                size += 1
                for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                    if 0 <= ny < px.shape[0] and 0 <= nx < px.shape[1] and px[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            best = max(best, size)
        res[v] = (int(px.sum()), best)
    for name, mats in saved.items():
        for sl, m in zip(bpy.data.objects[name].material_slots, mats):
            sl.material = m
    scn.render.engine, scn.render.resolution_x, scn.render.resolution_y, scn.view_settings.view_transform = old
    print("SCALPCHECK", tag, res)
    return res


def strand_count(obj):
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    data = ev.data
    return len(data.curves), len(data.points)


def main():
    opts = dict(a.split("=", 1) for a in args() if "=" in a)
    asset = opts.get("asset", "basic_short_hair")
    tag = opts.get("tag", asset)
    tuning = {} if opts.get("notune") else dict(HAIR, **{k: float(v) for k, v in opts.items() if k in PROPS})
    body, rig = load_teen()
    brow_asset = opts.get("brows", "none")  # the user picked MakeHuman card brows (eyebrow001)
    for o in list(rig.children):  # strand brows, if asked for, replace the card brows
        if brow_asset != "none" and ObjectService.get_object_type(o) == "Eyebrows":
            bpy.data.objects.remove(o)
    cards = next((o for o in rig.children if ObjectService.get_object_type(o) == "Hair"), None)
    hair = apply_strands(body, asset, tuning, COLOR)
    brows = None
    if brow_asset != "none":
        brows = apply_strands(body, brow_asset, {}, COLOR)
    if opts.get("fit", "1") == "1":
        fit_to_head(body, [h for h in (hair, brows) if h])
    hair = bake(hair)
    brows = bake(brows) if brows else None
    stats = lift(body, hair, float(opts.get("lift", LIFT)), float(opts.get("base", BASE)))
    if brows:
        lift(body, brows, 0.0, 0.0005)
    if opts.get("shell", "1") == "1" and cards is not None:  # fill the user's card cut (short01), not MPFB's look
        from hair_shell import comb_shell
        comb_shell(body, hair, cards)
    if cards is not None:
        cards.hide_render = True
    if opts.get("scalp", "1") == "1":
        scalp_tint(body, hair)
    n_curves, n_points = strand_count(hair)
    print("LIFT", stats)
    if opts.get("hidebody"):
        body.hide_render = True
    print(f"STRANDS {asset}: {n_curves} curves, {n_points} points" + (f"; brows {strand_count(brows)}" if brows else ""))

    out = ensure_dir(os.path.join(SHOTS, "hair"))
    cam = stage(engine="CYCLES", res=(900, 900))
    if opts.get('cpu') == '1':
        bpy.context.scene.cycles.device = 'CPU'
    bpy.context.scene.cycles.samples = int(opts.get("samples", 192))
    eyes = ObjectService.find_object_of_type_amongst_nearest_relatives(body, "Eyes")
    head = sum((eyes.matrix_world @ Vector(c) for c in eyes.bound_box), Vector()) / 8 + Vector((0, 0.02, 0.05))
    views = dict(front=0, tq=35, side=90, back=180, face=30)
    wanted = opts.get("views", "front,tq,side,back,face").split(",")
    for v in wanted:
        dist = 0.42 if v == "face" else float(opts.get("dist", 0.75))
        aim = head + Vector((0, 0, -0.035)) if v == "face" else head
        shoot(cam, aim, dist, views[v], 85, f"{out}/{tag}_{v}.png", lift=0.03 if v == "face" else 0.06)
    if cards is not None and opts.get("usercards", "1") == "1":  # the user's own short01 cards, same cameras
        hair.hide_render, cards.hide_render = True, False
        for slot in cards.material_slots:
            if slot.material and hasattr(slot.material, "surface_render_method"):
                slot.material.surface_render_method = "DITHERED"
        if "FoA_scalp" in body.data.color_attributes:
            body.data.color_attributes["FoA_scalp"].name = "FoA_scalp_off"
        for v in wanted:
            dist = 0.42 if v == "face" else float(opts.get("dist", 0.75))
            aim = head + Vector((0, 0, -0.035)) if v == "face" else head
            shoot(cam, aim, dist, views[v], 85, f"{out}/short01cards_{v}.png", lift=0.03 if v == "face" else 0.06)
        hair.hide_render, cards.hide_render = False, True
        if "FoA_scalp_off" in body.data.color_attributes:
            body.data.color_attributes["FoA_scalp_off"].name = "FoA_scalp"
    if opts.get("check", "1") == "1":
        check_scalp(body, hair, cam, head, out, tag)
        if opts.get("redcheck") == "1":  # red proof: without the hair the same test must light up
            hair.hide_render = True
            check_scalp(body, hair, cam, head, out, tag + "_nohair")
            hair.hide_render = False
    if opts.get("cards"):  # the old MakeHuman card hair on the same head, same cameras
        hair.hide_render = True
        if "FoA_scalp" in body.data.color_attributes:  # no scalp tint under the old cards: a fair comparison
            body.data.color_attributes["FoA_scalp"].name = "FoA_scalp_off"
        cards = HumanService.add_mhclo_asset(AssetService.find_asset_absolute_path(opts["cards"] + ".mhclo", asset_subdir="hair"),
                                             body, asset_type="Hair", subdiv_levels=0, material_type="GAMEENGINE")
        for slot in cards.material_slots:
            if slot.material and hasattr(slot.material, "surface_render_method"):
                slot.material.surface_render_method = "DITHERED"
        for v in wanted:
            shoot(cam, head, 0.75, views[v], 85, f"{out}/cards_{opts['cards']}_{v}.png", lift=0.06)
        bpy.data.objects.remove(cards)
        hair.hide_render = False
    if opts.get("save") == "1":
        for o in [o for o in bpy.data.objects if o.type in ("LIGHT", "CAMERA")]:
            bpy.data.objects.remove(o)
        blend = os.path.join(ensure_dir(os.path.join(ASSETS, "teen")), "foa_teen_hair.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend)
        print("saved", blend)


if __name__ == '__main__':
    main()
