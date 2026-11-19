"""Bedroom v3, run INSIDE the open editor:  python Tools/Unreal/ue_remote.py Tools/Unreal/bedroom_v3.py

7.5 x 6 m room, 3 m ceiling, three-sided bay window on the -Y wall, chimney breast on the -X wall.
Real trims (baseboard, crown, casings, sashes, muntins, sills, mantel), textured plaster and wood floor.
Furniture is MOVED, never rebuilt, so hand placements survive: each group shifts as a unit with its wall.
Imports (once) the procedural trims, Lux3D props and extra Poly Haven props it needs.
"""
import importlib
import math
import os
import sys
import traceback

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal")
import build_bedroom as B  # noqa: E402  (helper library; does not rebuild on import)

importlib.reload(B)
log, EAS, EAL, AT, MEL = B.log, B.EAS, B.EAL, B.AT, B.MEL
MATH = unreal.MathLibrary

H, T = 300.0, 30.0
POLY = [(-375, 300), (375, 300), (375, -300), (90, -300), (30, -390), (-150, -390), (-210, -300), (-375, -300)]
# segment i runs POLY[i] -> POLY[i+1]; openings: (kind, s0, s1, z_bottom, z_top), s measured from POLY[i]
OPENINGS = {1: [("door", 165.0, 260.0, 0.0, 215.0)],
            3: [("window", 26.0, 82.0, 85.0, 215.0)],
            4: [("window", 35.0, 145.0, 85.0, 215.0)],
            5: [("window", 26.0, 82.0, 85.0, 215.0)]}
CHIMNEY = {"x_face": -330.0, "y0": -80.0, "y1": 80.0, "fire_y": 45.0, "fire_h": 85.0, "mantel_z": 125.0}
PROC, LUX, PH = "/Game/FoA/Procedural", "/Game/FoA/Lux3D", "/Game/FoA/Props"


# ---------- geometry helpers ----------

def inside(p):
    x, y, hit = p[0], p[1], False
    for i in range(len(POLY)):
        (x1, y1), (x2, y2) = POLY[i], POLY[(i + 1) % len(POLY)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def seg(i):
    p0, p1 = POLY[i], POLY[(i + 1) % len(POLY)]
    L = math.dist(p0, p1)
    d = ((p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L)
    n = (-d[1], d[0])
    mid = ((p0[0] + p1[0]) / 2 + n[0] * 5, (p0[1] + p1[1]) / 2 + n[1] * 5)
    if not inside(mid):
        n = (-n[0], -n[1])
    return p0, p1, L, d, n


def at(p0, d, s, n=None, off=0.0):
    x, y = p0[0] + d[0] * s, p0[1] + d[1] * s
    if n:
        x, y = x + n[0] * off, y + n[1] * off
    return (x, y)


def spawn(mesh, label, folder, loc, rot, scale=(1, 1, 1), mat=None, movable=False):
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc), rot)
    smc = a.get_editor_property("static_mesh_component")
    if movable:
        smc.set_mobility(unreal.ComponentMobility.MOVABLE)
    smc.set_static_mesh(mesh)
    a.set_actor_scale3d(unreal.Vector(*scale))
    if mat:
        for k in range(max(1, smc.get_num_materials())):
            smc.set_material(k, mat)
    a.set_actor_label(label)
    a.set_folder_path(folder)
    return a


def bar(mesh, label, folder, a, b, n_in, z, mat):
    """Horizontal trim run from a to b at height z; the profile's +Y faces n_in (into the room)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    if L < 0.5:
        return None
    d = (dx / L, dy / L)
    if -d[1] * n_in[0] + d[0] * n_in[1] < 0:  # left normal must point into the room
        a, d = b, (-d[0], -d[1])
    rot = MATH.make_rot_from_xz(unreal.Vector(d[0], d[1], 0), unreal.Vector(0, 0, 1))
    return spawn(mesh, label, folder, (a[0], a[1], z), rot, (L / 100.0, 1, 1), mat)


def vbar(mesh, label, folder, p, z0, z1, n_in, mat):
    """Vertical member from z0 to z1 at p; profile depth faces n_in. Profiles used here are symmetric."""
    rot = MATH.make_rot_from_xy(unreal.Vector(0, 0, 1), unreal.Vector(n_in[0], n_in[1], 0))
    return spawn(mesh, label, folder, (p[0], p[1], z0), rot, ((z1 - z0) / 100.0, 1, 1), mat)


# ---------- assets ----------

def meshes_in(folder):
    out = []
    for path in EAL.list_assets(folder, recursive=True, include_folder=False):
        obj = EAL.load_asset(path)
        if isinstance(obj, unreal.StaticMesh):
            out.append(obj)
    return out


def import_once(src, dest):
    if EAL.does_directory_exist(dest) and meshes_in(dest):
        return meshes_in(dest)
    if not os.path.exists(src):
        log("WARN missing source", src)
        return []
    t = unreal.AssetImportTask()
    for k, v in (("filename", src), ("destination_path", dest), ("automated", True), ("replace_existing", True), ("save", True)):
        t.set_editor_property(k, v)
    AT.import_asset_tasks([t])
    found = meshes_in(dest)
    log("imported", os.path.basename(src), "->", dest, len(found), "mesh(es)")
    return found


def proc(name):
    m = import_once(f"P:/FoA-Assets/procedural/{name}.gltf", f"{PROC}/{name}")
    return m[0] if m else None


def lux(name):
    folder = f"P:/FoA-Assets/lux3d/{name}"
    glb = next((os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".glb")), None) if os.path.isdir(folder) else None
    return import_once(glb, f"{LUX}/{name}") if glb else []


def ph(asset_id):
    folder = f"P:/FoA-Assets/polyhaven/models/{asset_id}"
    gl = next((os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".gltf")), None) if os.path.isdir(folder) else None
    return import_once(gl, f"{PH}/{asset_id}") if gl else []


def fit(mesh, label, folder, center_xy, floor_z, target, axis="max", yaw=None, movable=True):
    """Uniformly scale a mesh so its longest horizontal side (or height with axis='z') equals target, and place it."""
    b = mesh.get_bounds()
    o, e = b.origin, b.box_extent
    size = 2 * e.z if axis == "z" else 2 * max(e.x, e.y)
    s = target / size if size > 0 else 1.0
    if yaw is None:
        yaw = 0.0
    t = math.radians(yaw)
    rx, ry = s * (o.x * math.cos(t) - o.y * math.sin(t)), s * (o.x * math.sin(t) + o.y * math.cos(t))
    loc = (center_xy[0] - rx, center_xy[1] - ry, floor_z - s * (o.z - e.z))
    return spawn(mesh, label, folder, loc, unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw), (s, s, s), movable=movable)


# ---------- materials ----------

def materials():
    grey = unreal.load_asset("/Game/FoA/Materials/M_Greybox")
    # The surfaces lane owns these (M_Surface, Tools/Unreal/build_surfaces.py); rebuilding them here would undo it.
    surf = {k: unreal.load_asset(f"{B.MATS}/{n}") for k, n in (("floor", "MI_Floor_OldWood"), ("wall", "MI_Wall_Plaster"),
                                                                ("ceiling", "MI_Ceiling_Plaster"))}
    if not all(surf.values()):
        floor_tex = B.import_texture_set("old_wooden_floor_02")
        wall_tex = B.import_texture_set("beige_wall_002", max_size=1024)
        world = B.make_world_aligned_master(floor_tex)
        surf = {"floor": B.make_instance("MI_Floor_OldWood", world, {"Tint": (0.85, 0.85, 0.85)}, {"TileSize": 200.0}, floor_tex),
                "wall": B.make_instance("MI_Wall_Plaster", world, {"Tint": (0.8, 0.8, 0.8)}, {"TileSize": 250.0}, wall_tex),
                "ceiling": B.make_instance("MI_Ceiling_Plaster", world, {"Tint": (0.9, 0.9, 0.9)}, {"TileSize": 250.0}, wall_tex)}

    def g(name, v, rough, metal=0.0):
        return B.make_instance(name, grey, {"Color": (v, v, v * 0.97)}, {"Roughness": rough, "Metallic": metal, "Emissive": 0.0})

    glass = B.fresh("M_Glass", B.MATS, unreal.Material, unreal.MaterialFactoryNew())
    B.setp(glass, "blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    B.setp(glass, "translucency_lighting_mode", B.enum(unreal.TranslucencyLightingMode, "TLM_SURFACE", "TLM_SURFACE_PER_PIXEL_LIGHTING"), quiet=True)
    col = B.expr(glass, unreal.MaterialExpressionConstant3Vector, -400, -100, constant=unreal.LinearColor(0.02, 0.022, 0.025, 1))
    op = B.expr(glass, unreal.MaterialExpressionConstant, -400, 50, r=0.18)
    rough = B.expr(glass, unreal.MaterialExpressionConstant, -400, 150, r=0.04)
    B.out(col, B.MP.MP_BASE_COLOR)
    B.out(op, B.MP.MP_OPACITY)
    B.out(rough, B.MP.MP_ROUGHNESS)
    MEL.recompile_material(glass)
    return {
        **surf,
        "trim": g("MI_Trim_Paint", 0.55, 0.45),
        "soot": g("MI_Soot", 0.015, 0.95),
        "stone": g("MI_Hearth_Stone", 0.16, 0.8),
        "glass": glass,
        "sand": unreal.load_asset("/Game/FoA/Materials/MI_DarkSand_Black"),
    }


# ---------- build ----------

def actors_by_label():
    out = {}
    for a in EAS.get_all_level_actors():
        out.setdefault(a.get_actor_label(), []).append(a)
    return out


def clear_shell():
    doomed = []
    seen_pp = False
    for a in EAS.get_all_level_actors():
        folder, label = str(a.get_folder_path()), a.get_actor_label()
        if folder in ("Room", "Room/Walls", "Room/Trim", "Room/Windows", "Room/Chimney", "Dev", "FX/Sand", "FX/SandMounds") \
                or label.startswith(("Door_", "DEV_")):
            doomed.append(a)
        if label == "PP_DreamMono":
            if seen_pp:
                doomed.append(a)  # duplicate volume applied the effect twice
            seen_pp = True
    EAS.destroy_actors(doomed)
    log("cleared", len(doomed), "shell/dev actors")
    for stale in ("MI_Floor_Wood", "MI_Ceiling"):
        if EAL.does_asset_exist(f"{B.MATS}/{stale}"):
            EAL.delete_asset(f"{B.MATS}/{stale}")


def build_shell(M):
    W = "Room/Walls"
    xs, ys = [p[0] for p in POLY], [p[1] for p in POLY]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    fx, fy = max(xs) - min(xs) + 2 * T, max(ys) - min(ys) + 2 * T
    B.place("Floor", "Room", (cx, cy, -10), (fx, fy, 20), M["floor"])
    B.place("Ceiling", "Room", (cx, cy, H + 15), (fx, fy, 30), M["ceiling"])
    for i in range(len(POLY)):
        p0, _p1, L, d, n = seg(i)
        yaw = math.degrees(math.atan2(d[1], d[0]))
        pieces, cursor = [], -T / 2
        for _kind, s0, s1, zb, zt in sorted(OPENINGS.get(i, []), key=lambda o: o[1]):
            pieces.append((cursor, s0, -20.0, H + 20))
            if zb > 0:
                pieces.append((s0, s1, -20.0, zb))
            pieces.append((s0, s1, zt, H + 20))
            cursor = s1
        pieces.append((cursor, L + T / 2, -20.0, H + 20))
        for k, (a, b, z0, z1) in enumerate(pieces):
            if b - a > 0.1 and z1 - z0 > 0.1:
                c = at(p0, d, (a + b) / 2, n, -T / 2)
                B.place(f"Wall_{i}_{k}", W, (c[0], c[1], (z0 + z1) / 2), (b - a, T, z1 - z0), M["wall"], yaw=yaw)


def build_chimney(M, trim):
    C, xf = "Room/Chimney", CHIMNEY["x_face"]
    depth, xc = xf - (-375), (xf + -375) / 2
    y0, y1, fy, fh = CHIMNEY["y0"], CHIMNEY["y1"], CHIMNEY["fire_y"], CHIMNEY["fire_h"]
    B.place("Chimney_JambL", C, (xc, (y0 - fy) / 2, fh / 2), (depth, -fy - y0, fh), M["wall"])
    B.place("Chimney_JambR", C, (xc, (y1 + fy) / 2, fh / 2), (depth, y1 - fy, fh), M["wall"])
    B.place("Chimney_Breast", C, (xc, 0, (fh + H + 20) / 2), (depth, y1 - y0, H + 20 - fh), M["wall"])
    B.place("Chimney_FireboxBack", C, (-367.5, 0, fh / 2), (15, 2 * fy, fh), M["soot"])
    B.place("Chimney_Hearth", C, (xf + 22.5, 0, 1.5), (45, (y1 - y0) + 10, 3), M["stone"])
    bar(trim["mantel"], "Chimney_Mantel", C, (xf, y1 + 15), (xf, y0 - 15), (1, 0), CHIMNEY["mantel_z"], M["trim"])
    # baseboard and crown around the breast are mitered runs from Tools/Unreal/place_trims.py


def build_trims_and_openings(M, trim):
    # Baseboards, crown and window casings are mitered runs from Tools/Unreal/place_trims.py (run it after this);
    # clear_shell() removes them with the rest of Room/Trim.
    TR, WI = "Room/Trim", "Room/Windows"
    for i in range(len(POLY)):
        p0, _p1, L, d, n = seg(i)
        yaw = math.degrees(math.atan2(d[1], d[0]))
        for j, (kind, s0, s1, zb, zt) in enumerate(OPENINGS.get(i, [])):
            tag = f"{kind}_{i}_{j}"
            if kind != "window":
                top = zt + 9.0
                for side, s in (("L", s0 - 4.5), ("R", s1 + 4.5)):
                    vbar(trim["casing"], f"Casing_{tag}_{side}", TR, at(p0, d, s), 0.0, top, n, M["trim"])
                bar(trim["casing"], f"Casing_{tag}_Head", TR, at(p0, d, s0 - 9), at(p0, d, s1 + 9), n, zt + 4.5, M["trim"])
                continue
            bar(trim["sill"], f"Sill_{tag}", WI, at(p0, d, s0 - 8), at(p0, d, s1 + 8), n, zb, M["trim"])
            mid = lambda s: at(p0, d, s, n, -15.0)  # noqa: E731  frame sits mid-wall
            bar(trim["frame"], f"Sash_{tag}_Bottom", WI, mid(s0), mid(s1), n, zb + 3, M["trim"])
            bar(trim["frame"], f"Sash_{tag}_Top", WI, mid(s0), mid(s1), n, zt - 3, M["trim"])
            vbar(trim["frame"], f"Sash_{tag}_L", WI, mid(s0 + 3), zb, zt, n, M["trim"])
            vbar(trim["frame"], f"Sash_{tag}_R", WI, mid(s1 - 3), zb, zt, n, M["trim"])
            vbar(trim["muntin"], f"Muntin_{tag}_V", WI, mid((s0 + s1) / 2), zb + 3, zt - 3, n, M["trim"])
            bar(trim["muntin"], f"Muntin_{tag}_H", WI, mid(s0 + 3), mid(s1 - 3), n, (zb + zt) / 2, M["trim"])
            c = mid((s0 + s1) / 2)
            B.place(f"Glass_{tag}", WI, (c[0], c[1], (zb + zt) / 2), (s1 - s0, 0.6, zt - zb), M["glass"], yaw=yaw)


def move_group(labels, A, delta):
    for lab in labels:
        for a in A.get(lab, []):
            a.set_actor_location(a.get_actor_location() + unreal.Vector(*delta), False, False)


def place_furniture(M):
    A = actors_by_label()
    group_of = lambda prefix: [l for l in A if l == prefix or l.startswith(prefix + "_")]  # noqa: E731

    def move_to(anchor, labels, target_xy):
        if anchor not in A:
            log("WARN missing", anchor)
            return
        cur = A[anchor][0].get_actor_location()
        move_group(labels, A, (target_xy[0] - cur.x, target_xy[1] - cur.y, 0.0))

    move_to("Desk", ["Desk", "DeskLamp", "Chair", "Light_DeskLamp", "Spot_Screwdriver_DeskDrawer"], (-337.5, 190.0))
    move_to("Bed", ["Bed", "Boot_L", "Boot_R", "Spot_Key_InBoot", "PlayerStart_WakeUp"], (270.0, -150.0))
    move_to("Commode", group_of("Commode"), (-150.0, 269.0))
    move_to("Wardrobe", group_of("Wardrobe") + ["Spot_Hanger_WardrobeSide"], (282.0, 247.0))
    for a in [x for lab in group_of("WallClock") for x in A[lab]]:
        a.set_actor_location(unreal.Vector(CHIMNEY["x_face"], 0.0, 200.0), False, False)
    for a in A.get("PlayerStart_WakeUp", []):
        a.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=40.0), False)

    P = "Interactables/Items"
    bedding = lux("bedding")
    if bedding:
        bed = A["Bed"][0].get_actor_location()
        fit(bedding[0], "Bedding_Lux3D", "Room/Furniture", (bed.x, bed.y), 40.0, 195.0,
            yaw=0.0 if bedding[0].get_bounds().box_extent.x >= bedding[0].get_bounds().box_extent.y else 90.0)
    door = lux("bedroom_door")
    if door:
        e = door[0].get_bounds().box_extent
        fit(door[0], "Door_Bedroom", "Interactables/Door", (370.0, 87.5), 0.0, 213.0, axis="z",
            yaw=90.0 if e.x >= e.y else 0.0)  # thin side along world X, i.e. in the +X wall
    key = lux("door_key")
    if key:
        spot = A["Spot_Key_InBoot"][0].get_actor_location()
        fit(key[0], "Key_Lux3D", P, (spot.x, spot.y), spot.z - 6, 7.0)
    hanger = lux("wire_hanger")
    if hanger:
        spot = A["Spot_Hanger_WardrobeSide"][0].get_actor_location()
        fit(hanger[0], "Hanger_Lux3D", P, (spot.x, spot.y - 0.0), 150.0, 40.0)
    nightstand = ph("ClassicNightstand_01")
    if nightstand:
        B.prop("Nightstand", "Room/Furniture", [m.get_path_name() for m in nightstand], (348.0, -62.0), yaw=90.0)

    mound = {k: proc(f"SM_SandMound_{k}") for k in "ABC"}
    commode_top = 121.2
    for label, key_, xy, z, s in (("SandMound_OnCommode", "A", (-150.0, 266.0), commode_top, 0.42),
                                  ("SandMound_Bay", "B", (-60.0, -340.0), 0.0, 0.9),
                                  ("SandMound_Hearth", "C", (-280.0, -130.0), 0.0, 0.7),
                                  ("SandMound_Path", "A", (150.0, -40.0), 0.0, 0.55)):
        if mound[key_]:
            spawn(mound[key_], label, "FX/SandMounds", (xy[0], xy[1], z),
                  unreal.Rotator(roll=0.0, pitch=0.0, yaw=37.0 * len(label)), (s, s, s), M["sand"])


def lights_and_cameras():
    A = actors_by_label()

    def put(label, loc, rot=None):
        for a in A.get(label, []):
            a.set_actor_location(unreal.Vector(*loc), False, False)
            if rot:
                a.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=rot[0], yaw=rot[1]), False)

    put("Light_Moon", (-60.0, -560.0, 260.0), (-32.0, 90.0))
    put("Light_HallwayLeak", (435.0, 87.5, 40.0))
    put("Shot_ThirdPerson", (-60.0, -60.0, 175.0), (-8.1, 18.7))
    put("Shot_Wide", (-340.0, 280.0, 270.0), (-16.9, -50.3))
    put("Shot_Window", (250.0, 100.0, 160.0), (-2.0, -124.0))
    put("Shot_TopDown", (0.0, -45.0, 1500.0), (-89.9, 0.0))


def main():
    clear_shell()
    M = materials()
    trim = {k: proc(v) for k, v in (("base", "SM_Baseboard"), ("crown", "SM_CrownMolding"), ("casing", "SM_Casing"),
                                    ("frame", "SM_FrameBar"), ("muntin", "SM_Muntin"), ("sill", "SM_Sill"),
                                    ("mantel", "SM_Mantel"))}
    build_shell(M)
    build_chimney(M, trim)
    build_trims_and_openings(M, trim)
    place_furniture(M)
    lights_and_cameras()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    EAL.save_directory("/Game/FoA", only_if_is_dirty=True, recursive=True)


try:
    main()
    log("V3 OK")
except Exception:
    log("V3 FAILED\n" + traceback.format_exc())
print("\n".join(B.LINES[-40:]))
