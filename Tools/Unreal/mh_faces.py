"""Six face directions (A-F) for the protagonist, as MetaHuman Creator preview characters on editor B. No builds.

  $env:FOA_EDITOR='B'; python P:/FoA-B/Tools/Unreal/ue_remote.py P:/FoA-B/Tools/Unreal/mh_faces.py FOA_STEP=<step> [FOA_FACE=A]

Steps:
  setup  - duplicate MHC_Protagonist (the current, built look: body, outfit, hair) to Faces/MHC_Face_A..F and
           Faces/MHC_Protagonist_Backup (only the ones missing), save them
  probe  - read-only: face-model coefficient stats of the male presets and of MHC_Protagonist, landmark count
  face   - FOA_FACE: blend the direction's presets in face-model coefficient space, push it away from the average
           (character), add asymmetry, take the dominant preset's skin, set its hair/brows/beard; commit and save
  shoot  - FOA_FACE: spawn the preview actor (transient) and capture clean studio portraits (front, 3/4; neutral
           light, no grade, no smear) away from the room, then one in-room shot at PlayerStart_WakeUp under the
           level's dream grade. PNGs to FOA_OUT/<face>/. Every TMP_character_ actor is destroyed afterwards.
"""
import math
import os
import random
import time
import unreal

ROOT = "/Game/FoA/Characters/Protagonist"
SRC = f"{ROOT}/MHC_Protagonist"
FACES = f"{ROOT}/Faces"
PRESETS = "/MetaHumanCharacter/Optional/Presets"
GROOMS = "/MetaHumanCharacter/Optional/Grooms/Bindings"
SUB = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
STEP = os.environ.get("FOA_STEP", "probe")
FACE = os.environ.get("FOA_FACE", "A")
OUT = os.environ.get("FOA_OUT", "P:/FoA/Saved/CharacterShots/faces")
WAIT = float(os.environ.get("FOA_WAIT", "30"))
MALE = ["Bo", "Bruce", "Cameron", "Dominic", "Isaiah", "Jorge", "Kelvin", "Lorenzo", "Mateo", "Mikel", "Omari",
        "Orlando", "Trey", "Victor", "Walter"]

# Teenagers (16-19, the user's update). Young presets by their thumbnails: Bo, Cameron, Kelvin, Mateo, Mikel, Omari;
# older ones (Bruce, Dominic, Jorge, Lorenzo, Victor, Walter) lend only a little bone structure.
YOUNG = ["Bo", "Cameron", "Mikel", "Mateo", "Kelvin", "Omari"]
OLD = ["Bruce", "Dominic", "Jorge", "Lorenzo", "Victor", "Walter"]
# direction: presets and weights, push away from the male average (character), youth (+ along young-minus-old),
# asymmetry strength, skin source (a young preset: its face texture carries the age), optional skin tone (u, v),
# grooms ("" clears the slot = clean shave; every face gets the thin peach fuzz), seed for the asymmetry pattern
DIRS = {
    "A": dict(label="East Asian, angular cheekbones, side-swept fringe",
              mix={"Bo": 0.55, "Kelvin": 0.45}, push=1.3, youth=1.3, asym=0.6, skin="Bo",
              hair="WI_Hair_M_SideSweptFringe", brows="WI_Eyebrows_M_FlatThick", beard="", seed=1),
    "B": dict(label="Black, long face, high cheekbones, short twists",
              mix={"Mikel": 0.6, "Cameron": 0.4}, push=1.35, youth=1.2, asym=0.6, skin="Mikel",
              hair="WI_Hair_M_TwistedBraids", brows="WI_Eyebrows_M_Dense", beard="", seed=2),
    "C": dict(label="South Asian, soft oval face, strong nose, short side-swept fringe",
              mix={"Mateo": 0.6, "Bo": 0.3, "Lorenzo": 0.1}, push=1.25, youth=1.4, asym=0.5, skin="Bo",
              tone=(0.72, 0.72), hair="WI_Hair_S_SideSweptFringe", brows="WI_Eyebrows_M_Thick", beard="", seed=3),
    "D": dict(label="Northern European, square jaw, heavy brow, messy crop",
              mix={"Kelvin": 0.45, "Orlando": 0.3, "Bo": 0.25}, push=1.3, youth=1.5, asym=0.7, skin="Bo",
              tone=(0.3, 0.45), hair="WI_Hair_S_Messy", brows="WI_Eyebrows_M_Unruly", beard="", seed=4),
    "E": dict(label="Mediterranean, long nose, narrow face, messy swept-up hair",
              mix={"Mateo": 0.45, "Bo": 0.3, "Lorenzo": 0.25}, push=1.3, youth=1.5, asym=0.6, skin="Bo",
              tone=(0.45, 0.5), hair="WI_Hair_S_SweptUp", brows="WI_Eyebrows_M_Natural", beard="", seed=5),
    "F": dict(label="Mixed Black and Polynesian, broad face, curly fade",
              mix={"Cameron": 0.5, "Omari": 0.3, "Dominic": 0.2}, push=1.35, youth=1.4, asym=0.8, skin="Cameron",
              hair="WI_Hair_S_CurlyFade", brows="WI_Eyebrows_M_Messy", beard="", seed=6),
}
# Round 2 (the user: "a slightly more fat person teenager ... more interesting customization ... to stand out"):
# heavier, softer teens (G-L). Extra keys: heavy (fuller face landmarks + HEAVY_BODY), freckles, accents (region:
# (redness, saturation, lightness)), eyes (left, right) iris (u, v, pattern) for heterochromia, hairp (hair-only
# groom params by name), browp (brow/lash/fuzz params), ear (one ear out, cm). The game is monochrome: eye colour
# reads only as light or dark, so heterochromia is a pale eye against a dark one.
DIRS.update({
    "G": dict(label="Irish, fair and freckled, ginger curly mop, pale eyes",
              mix={"Bo": 0.4, "Orlando": 0.35, "Kelvin": 0.25}, push=1.25, youth=1.6, asym=0.6, skin="Bo",
              tone=(0.15, 0.3), hair="WI_Hair_M_BobCurly", brows="WI_Eyebrows_M_Fine", beard="", seed=7, heavy=1.0,
              freckles=dict(mask="TYPE2", density=0.85, strength=0.6, saturation=0.6, tone_shift=0.6),
              accents={"cheeks": (0.85, 0.6, 0.45), "nose": (0.75, 0.55, 0.5)},
              eyes=((0.12, 0.15, 3), (0.12, 0.15, 3)),
              hairp={"melanin": 0.3, "redness": 0.9}, browp={"melanin": 0.3, "redness": 0.85}),
    "H": dict(label="East Asian, bleached two-tone hair with dark roots, slit brow, flushed skin",
              mix={"Bo": 0.75, "Kelvin": 0.25}, push=1.3, youth=1.5, asym=0.6, skin="Bo",
              hair="WI_Hair_M_Layered", brows="WI_Eyebrows_M_Slit", beard="", seed=8, heavy=1.0,
              accents={"forehead": (0.8, 0.6, 0.45), "chin": (0.8, 0.6, 0.45), "cheeks": (0.75, 0.55, 0.5)},
              eyes=((0.85, 0.85, 1), (0.85, 0.85, 1)),
              hairp={"melanin": 0.05, "lightness": 0.9, "redness": 0.1, "useombre": True, "ombreshift": 0.25,
                     "ombrecontrast": 0.8, "ombreintensity": 1.0, "ombreu": 0.9, "ombrev": 0.95},
              browp={"melanin": 0.95}),
    "I": dict(label="Black, heterochromia (one pale eye), shaved-side cut, uneven skin tone",
              mix={"Mikel": 0.45, "Cameron": 0.35, "Bo": 0.2}, push=1.3, youth=1.4, asym=0.8, skin="Cameron",
              hair="WI_Hair_M_FauxMohawk", brows="WI_Eyebrows_M_Dense", beard="", seed=9, heavy=0.9,
              accents={"forehead": (0.4, 0.5, 0.62), "nose": (0.5, 0.5, 0.35), "chin": (0.5, 0.5, 0.35),
                       "under_eye": (0.6, 0.55, 0.2)},
              eyes=((0.1, 0.1, 6), (0.9, 0.9, 6)),
              hairp={"melanin": 0.97}, browp={"melanin": 0.97}),
    "J": dict(label="South Asian, overgrown fringe over the eyes, acne, one ear sticking out",
              mix={"Mateo": 0.6, "Bo": 0.4}, push=1.25, youth=1.6, asym=0.6, skin="Bo", tone=(0.65, 0.65),
              hair="WI_Hair_M_SideSweptFringe", brows="WI_Eyebrows_M_Thick", beard="", seed=10, heavy=1.0, ear=0.45,
              freckles=dict(mask="TYPE3", density=0.45, strength=0.4, saturation=1.0, tone_shift=0.0),
              accents={"forehead": (0.9, 0.7, 0.45), "chin": (0.9, 0.7, 0.45)},
              eyes=((0.8, 0.8, 4), (0.8, 0.8, 4)),
              hairp={"melanin": 0.95}, browp={"melanin": 0.95}),
    "K": dict(label="Latino, bowl cut, wide brows, amber eyes, round soft face",
              mix={"Mateo": 0.4, "Bo": 0.35, "Jorge": 0.25}, push=1.3, youth=1.7, asym=0.6, skin="Bo",
              tone=(0.5, 0.55), hair="WI_Hair_M_BobStraight", brows="WI_Eyebrows_M_Wide", beard="", seed=11,
              heavy=1.2, accents={"cheeks": (0.7, 0.55, 0.5)},
              eyes=((0.55, 0.35, 8), (0.55, 0.35, 8)),
              hairp={"melanin": 0.85, "redness": 0.2}, browp={"melanin": 0.9}),
    "L": dict(label="Polynesian, long hair in a messy bun, broad face, freckled brown skin, light hazel eyes",
              mix={"Cameron": 0.35, "Omari": 0.3, "Dominic": 0.35}, push=1.3, youth=1.7, asym=0.7, skin="Cameron",
              tone=(0.75, 0.6), hair="WI_Hair_S_UpdoBuns", brows="WI_Eyebrows_M_Full", beard="", seed=12, heavy=1.1,
              freckles=dict(mask="TYPE1", density=0.6, strength=0.45, saturation=0.4, tone_shift=0.9),
              eyes=((0.4, 0.25, 2), (0.4, 0.25, 2)),
              hairp={"melanin": 0.9}, browp={"melanin": 0.92}),
})
DIRS["M"] = dict(
    label="Silver swept-back hair, defined jaw, straight nose, realistic youthful face",
    mix={"Orlando": 0.55, "Lorenzo": 0.25, "Kelvin": 0.2}, push=1.05, youth=0.2,
    asym=0.25, skin="Bo", tone=(0.22, 0.42), hair="WI_Hair_S_SlickBack",
    brows="WI_Eyebrows_M_Thick", beard="", seed=13,
    hairp={"melanin": 0.05, "redness": 0.0, "whiteness": 0.94, "lightness": 0.25,
           "roughness": 0.38}, browp={"melanin": 0.85, "redness": 0.0, "whiteness": 0.0},
    eyes=((0.2, 0.15, 3), (0.2, 0.15, 3)),
    # Offset the old lineup's round cheeks and softened jaw for the supplied reference.
    landmarks={23: (0.02, -0.14, 0.12), 66: (-0.02, -0.14, 0.12),
               29: (-0.2, -0.12, 0), 2: (0.2, -0.12, 0),
               46: (0.35, 0, -0.12), 68: (-0.35, 0, -0.12),
               64: (0, 0.22, 0.04), 62: (0, 0.16, -0.15),
               24: (0, 0.08, -0.12), 77: (0, 0.08, -0.12),
               37: (0, 0, 0.12), 53: (0, 0, 0.12)})
DIRS["N"] = dict(
    label="Natural teen, short brown side-swept hair, soft jaw and straight brows",
    mix={"Kelvin": 0.65, "Bo": 0.25, "Orlando": 0.1}, push=1.0, youth=0.45,
    asym=0.15, skin="Kelvin", tone=(0.28, 0.4), hair="WI_Hair_S_SideSweptFringe",
    brows="WI_Eyebrows_M_Natural", beard="", seed=14,
    hairp={"melanin": 0.65, "redness": 0.22, "whiteness": 0.0, "lightness": 0.0,
           "roughness": 0.4}, browp={"melanin": 0.75, "redness": 0.15, "whiteness": 0.0},
    landmarks={46: (-0.12, 0, 0.1), 68: (0.12, 0, 0.1), 62: (0, 0, 0.18),
               24: (0, 0, -0.08), 77: (0, 0, -0.08),
               26: (0, 0, -0.12), 10: (0, 0, -0.12),
               37: (0, 0, 0.10), 53: (0, 0, 0.10)})
# a heavier, soft teenage build (round 2): chubby, not obese (cm)
HEAVY_BODY = {"height": 176.0, "chest": 112.0, "underbust": 106.0, "waist": 104.0, "hip": 110.0, "high_hip": 104.0,
              "neck_base": 46.0, "neck": 42.0, "thigh": 64.0, "knee": 42.0, "calf": 41.0, "bicep": 35.0, "elbow": 29.0,
              "forearm": 29.0, "wrist": 18.0, "across_shoulder": 46.0, "hand_circumference": 22.0}
# a normal teenage build, not slim: the protagonist's sturdy 180 cm adult body, younger (cm)
TEEN_BODY = {"height": 178.0, "chest": 102.0, "underbust": 94.0, "waist": 84.0, "hip": 98.0, "high_hip": 92.0,
             "neck_base": 42.0, "neck": 38.0, "thigh": 56.0, "knee": 38.0, "calf": 37.0, "bicep": 32.0, "elbow": 26.0,
             "forearm": 27.0, "wrist": 17.0, "across_shoulder": 45.0, "hand_circumference": 21.0}
GROOM_DIR = {"hair": "Hair", "brows": "Eyebrows", "beard": "Beards", "mustache": "Mustaches", "fuzz": "Peachfuzz"}
SLOT_KW = {"hair": "hair", "brows": "eyebrow", "beard": "beard", "mustache": "mustache", "fuzz": "peachfuzz"}
# landmark indices on MHC_Protagonist (P:/FoA/Saved/CharacterShots/faces/landmarks.json, cm, x = sideways,
# y = forward, z = up): upper eyelids, inner and mid brows, nose tip, mouth corners, jaw angles (+x side, -x side)
UPPER_LID = ([20, 35, 36], [44, 51, 52])
BROW = ([24, 26], [77, 10])
NOSE_TIP, MOUTH, JAW = 64, (32, 48), (46, 68)
CHEEK, CHEEK_LOW, NOSTRIL = (23, 66), (29, 2), (45, 67)
EYE_OUTER, LOWER_LID, CHIN = (18, 22), (37, 53), 62
HAIR_MELANIN = {"A": 0.95, "B": 0.97, "C": 0.92, "D": 0.55, "E": 0.85, "F": 0.95}
HAIR_MELANIN.update({"G": 0.3, "H": 0.05, "I": 0.97, "J": 0.95, "K": 0.85, "L": 0.9})
JOWL, UNDER_CHIN, EAR = (28, 1), (8, 12), ([38, 39, 73], [54, 56, 69])


def scan(*paths):
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(list(paths), True)


def face_path(f):
    return f"{FACES}/MHC_Face_{f}"


def edit(ch):
    # a fresh edit session shows the Topology debug material unless the character asks for Skin
    ch.set_editor_property("preview_material_type", unreal.MetaHumanCharacterSkinPreviewMaterial.EDITABLE)
    vs = ch.get_editor_property("viewport_settings")  # SceneCapture2D draws no hair strands; cards it does
    vs.set_editor_property("always_use_hair_cards", True)
    ch.set_editor_property("viewport_settings", vs)
    if not SUB.try_add_object_to_edit(ch):
        raise RuntimeError(f"{ch.get_name()} is already open for edit (close its editor tab)")


def done(ch):
    if SUB.is_object_added_for_editing(ch):
        SUB.remove_object_to_edit(ch)


def coeffs(ch):
    edit(ch)
    try:
        return list(SUB.get_face_model_coefficients(ch))
    finally:
        done(ch)


def stats(v):
    n = len(v)
    m = sum(v) / n
    return dict(n=n, mean=round(m, 4), min=round(min(v), 3), max=round(max(v), 3),
                rms=round(math.sqrt(sum(x * x for x in v) / n), 4))


def step_setup():
    scan(ROOT, FACES)
    for name in ["MHC_Protagonist_Backup"] + [f"MHC_Face_{f}" for f in os.environ.get("FOA_FACES", "".join(DIRS))]:
        dst = f"{FACES}/{name}"
        if unreal.EditorAssetLibrary.does_asset_exist(dst):
            print("MH_FACES exists", dst)
            continue
        ok = unreal.EditorAssetLibrary.duplicate_asset(SRC, dst)
        unreal.EditorAssetLibrary.save_asset(dst, only_if_is_dirty=False)
        print("MH_FACES duplicated", dst, bool(ok))


CACHE = f"{OUT}/preset_coeffs.json"


def preset_coeffs(budget_s=18.0):
    """Male presets' face-model coefficients, cached on disk. Each read opens the preset for edit (slow), so one run
    reads only what fits in budget_s; run the probe step again until it reports all presets cached."""
    import json
    allc = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    missing = [n for n in MALE if n not in allc]
    if missing:
        scan(PRESETS)
        t0 = time.time()
        for n in missing:
            if time.time() - t0 > budget_s:
                break
            allc[n] = coeffs(unreal.load_asset(f"{PRESETS}/{n}"))
            print("MH_PROBE cached", n, round(time.time() - t0, 1), "s")
        os.makedirs(OUT, exist_ok=True)
        with open(CACHE, "w") as fh:
            json.dump(allc, fh)
    return allc


def step_probe():
    allc = preset_coeffs()
    left = [n for n in MALE if n not in allc]
    print("MH_PROBE presets cached", len(allc), "missing", left)
    if left:
        return
    for n in MALE:
        print("MH_PROBE", n, stats(allc[n]))
    if os.environ.get("FOA_LANDMARKS") == "1":
        ch = unreal.load_asset(SRC)
        edit(ch)
        try:
            lm = list(SUB.get_face_landmarks(ch))
            print("MH_PROBE landmarks", len(lm))
            with open(f"{OUT}/landmarks.json", "w") as fh:
                import json
                json.dump([[v.x, v.y, v.z] for v in lm], fh)
        finally:
            done(ch)


def set_slot(col, inst, slots, key, item_name):
    """Select a groom in its slot, or clear the slot when item_name is "" (clean shave)."""
    slot = next((x for x in slots if SLOT_KW[key] in x.lower()), None)
    if slot is None:
        print("MH_FACE no slot for", key)
        return
    if not item_name:
        inst.set_single_slot_selection(slot, unreal.MetaHumanPaletteItemKey())  # a null key empties the slot
        print("MH_FACE cleared", slot)
        return
    item = unreal.load_asset(f"{GROOMS}/{GROOM_DIR[key]}/{item_name}.{item_name}")
    if item is None:
        print("MH_FACE missing item", item_name)
        return
    keys = list(col.get_item_keys_for_wardrobe_item(item)) or [col.try_add_item_from_wardrobe_item(slot, item)]
    inst.set_single_slot_selection(slot, keys[0])
    print("MH_FACE", key, slot, item_name)


def set_melanin(ch):
    """Groom colour on the preview collection (the edited copy), written back to the asset. Round 1: one melanin for
    every groom. Round 2: d["hairp"] on the hair item only, d["browp"] on the others, matched by parameter name with
    spaces and a leading b dropped (UseOmbre, bUseOmbre and use ombre all match "useombre")."""
    d = DIRS[FACE]
    collection = SUB.get_preview_collection(ch)
    pinst = collection.default_instance
    hair_keys = list(collection.get_item_keys_for_slot("Hair"))
    assert hair_keys, "Hair slot identity is required; palette paths contain GUID keys, not asset filenames"
    n = 0
    hair_paths = 0
    for ip in pinst.get_instance_parameter_item_paths():
        params = list(pinst.get_instance_parameters(item_path=ip))
        entries = [ip.get_editor_property("item"), *ip.get_editor_property("parent_items")]
        is_hair = any(entry.references_same_asset(key) for entry in entries for key in hair_keys)
        hair_paths += int(is_hair)
        want = d.get("hairp" if is_hair else "browp")
        if os.environ.get("FOA_LIST_PARAMS") == "1":
            print("MH_PARAMS", "hair" if is_hair else "other", str(ip)[:160], [str(p_.name) for p_ in params])
        for p_ in params:
            nm = str(p_.name).lower().replace(" ", "")
            key = nm[1:] if nm.startswith("b") and nm[1:] in (want or {}) else nm
            if want is None:
                if "melanin" in nm and "red" not in nm:
                    p_.set_float(value=HAIR_MELANIN[FACE])
                    n += 1
            elif key in want:
                v = want[key]
                ok = p_.set_bool(value=v) if isinstance(v, bool) else p_.set_float(value=float(v))
                n += 1 if ok else 0
    assert hair_paths > 0, "No Hair item parameter paths matched the actual palette keys"
    SUB.on_edit_preview_collection(ch)
    print("MH_FACE groom params set", n)


def step_face():
    d = DIRS[FACE]
    scan(PRESETS, FACES)
    path = face_path(FACE)
    ch = unreal.load_asset(path)
    if ch is None:
        raise RuntimeError(f"missing {path}: run FOA_STEP=setup")
    allc = preset_coeffs()
    n = len(allc[MALE[0]])

    def avg(names):
        return [sum(allc[k][i] for k in names) / len(names) for i in range(n)]
    mean, young, old = avg(MALE), avg(YOUNG), avg(OLD)
    blend = [sum(w * allc[k][i] for k, w in d["mix"].items()) for i in range(n)]
    # character: away from the average male face along the blend's own difference; youth: along young minus old
    target = [mean[i] + d["push"] * (blend[i] - mean[i]) + d["youth"] * (young[i] - old[i]) for i in range(n)]
    # wardrobe edits happen outside the edit session (as in Epic's examples)
    col, inst = ch.internal_collection, ch.internal_collection.default_instance
    slots = [str(x) for x in col.get_slot_names()]
    stubble = "Stubble" in d["beard"] or "Uneven" in d["beard"]
    for key, item in (("hair", d["hair"]), ("brows", d["brows"]), ("beard", d["beard"]),
                      ("mustache", d.get("mustache", "WI_Mustache_S_Stubble" if stubble else "")),
                      ("fuzz", "WI_Peachfuzz_M_Thin")):
        set_slot(col, inst, slots, key, item)
    edit(ch)
    try:
        # A head-only replacement retains the body that all fitted clothes were authored against.
        cons = SUB.get_body_constraints(ch)
        body_before = [(str(c.name), c.is_active, c.target_measurement) for c in cons]
        if os.environ.get("FOA_PRESERVE_BODY") != "1":
            body = HEAVY_BODY if d.get("heavy") else TEEN_BODY
            for index, c in enumerate(cons):  # Unreal array structs must be written back after editing.
                k = str(c.name).lower().replace(" ", "_")
                c.is_active = k in body
                if c.is_active:
                    c.target_measurement = body[k]
                cons[index] = c
            SUB.set_body_constraints(ch, cons)
            SUB.commit_body_state(ch)
        SUB.set_face_model_coefficients(ch, target)
        SUB.commit_face_state(ch)
        lm = list(SUB.get_face_landmarks(ch))
        rnd = random.Random(d["seed"])
        side = rnd.choice((0, 1))  # which side carries the asymmetry
        a = d["asym"]
        moves = {}

        def mv(i, x=0.0, y=0.0, z=0.0):
            v = moves.get(i, [0.0, 0.0, 0.0])
            moves[i] = [v[0] + x, v[1] + y, v[2] + z]
        for s_ in (0, 1):
            out = 1.0 if s_ == 0 else -1.0  # +x side is side 0; "out" points away from the centre line
            droop = 0.13 + (0.04 * a if s_ == side else 0.0)  # tired: heavy upper lids
            for i in UPPER_LID[s_]:
                mv(i, z=-droop)
            for i in BROW[s_]:  # brows a little lower (heavy lids) but further back (less brow ridge, younger)
                mv(i, y=-0.1, z=-0.06)
            mv(EYE_OUTER[s_], x=out * 0.08)  # wider eyes
            mv(LOWER_LID[s_], z=-0.05)
            mv(CHEEK[s_], x=out * 0.15, y=0.12)  # fuller cheeks
            mv(CHEEK_LOW[s_], x=out * 0.12, y=0.08)
            mv(NOSTRIL[s_], x=-out * 0.07)  # narrower, smaller nose
            h = d.get("heavy", 0.0)
            if h:  # heavier: full cheeks and jowls, wider soft jaw line
                mv(CHEEK[s_], x=out * 0.2 * h, y=0.05 * h)
                mv(CHEEK_LOW[s_], x=out * 0.3 * h, y=0.08 * h)
                mv(JOWL[s_], x=out * 0.3 * h, z=-0.1 * h)
                mv(JAW[s_], x=out * 0.2 * h, z=-0.15 * h)
            else:
                mv(JAW[s_], x=-out * 0.15, z=0.12)  # softer jaw
        mv(NOSE_TIP, y=-0.15)  # less nose projection
        mv(CHIN, y=-0.06)
        if d.get("heavy"):  # a soft under-chin
            mv(UNDER_CHIN[0], y=0.45 * d["heavy"], z=-0.3 * d["heavy"])
            mv(UNDER_CHIN[1], y=0.55 * d["heavy"], z=-0.25 * d["heavy"])
        if d.get("ear"):  # one ear sticks out
            for i in EAR[side]:
                mv(i, x=(1.0 if side == 0 else -1.0) * d["ear"])
        sx = 1.0 if side == 0 else -1.0  # +x side is side 0
        mv(BROW[side][1], z=0.12 * a)  # one brow sits higher
        mv(NOSE_TIP, x=sx * 0.08 * a)  # nose tip off centre
        mv(MOUTH[side], z=-0.06 * a)  # one mouth corner lower
        mv(JAW[side], x=sx * 0.12 * a)  # one jaw angle wider
        for i, offset in d.get("landmarks", {}).items():
            mv(i, *offset)
        idx = sorted(moves)
        SUB.translate_face_landmarks(ch, idx, [unreal.Vector(*moves[i]) for i in idx])
        SUB.commit_face_state(ch)
        print("MH_FACE coeffs", stats(target), "landmarks moved", len(idx), "side", side)
        src = unreal.load_asset(f"{PRESETS}/{d['skin']}").get_editor_property("skin_settings")
        skin = src
        sk = skin.skin
        sk.roughness = 1.12  # matte: the shine was the user's complaint
        if d.get("tone"):
            sk.u, sk.v = d["tone"]
        skin.skin = sk
        acc = skin.accents
        ue = acc.under_eye  # tired: darker, slightly red under-eye
        ue.lightness, ue.redness, ue.saturation = 0.22, 0.62, 0.55
        acc.under_eye = ue
        skin.accents = acc
        for region, (red, sat, light) in d.get("accents", {}).items():
            r = getattr(acc, region)
            r.redness, r.saturation, r.lightness = red, sat, light
            setattr(acc, region, r)
        skin.accents = acc
        fr = skin.freckles
        f = d.get("freckles")
        fr.mask = getattr(unreal.MetaHumanCharacterFrecklesMask, f["mask"] if f else "NONE")
        if f:
            fr.density, fr.strength, fr.saturation, fr.tone_shift = (f["density"], f["strength"], f["saturation"],
                                                                     f["tone_shift"])
        skin.freckles = fr
        skin.enable_texture_overrides = False
        SUB.commit_skin_settings(ch, skin)
        if d.get("eyes"):
            es = unreal.MetaHumanCharacterEyesSettings()
            for side_name, (u, v, pat) in zip(("eye_left", "eye_right"), d["eyes"]):
                eye = getattr(es, side_name)
                iris = eye.iris
                iris.primary_color_u, iris.primary_color_v = u, v
                iris.secondary_color_u, iris.secondary_color_v = u, min(1.0, v + 0.1)
                iris.pattern = getattr(unreal.MetaHumanCharacterEyesIrisPattern, f"IRIS{pat:03d}")
                eye.iris = iris
                setattr(es, side_name, eye)
            SUB.commit_eyes_settings(ch, es)
        SUB.assemble_for_preview(character=ch)
        set_melanin(ch)
        if os.environ.get("FOA_PRESERVE_BODY") == "1":
            assert [(str(c.name), c.is_active, c.target_measurement)
                    for c in SUB.get_body_constraints(ch)] == body_before, "Head edit changed fitted body constraints"
        print("MH_FACE", FACE, "done", path, "face_tex", sk.face_texture_index, "u,v", round(sk.u, 2), round(sk.v, 2))
    finally:
        done(ch)
    unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)


def sweep(reason):
    n = 0
    for a in EAS.get_all_level_actors():
        try:
            if a.get_actor_label().startswith("TMP_character_"):
                EAS.destroy_actor(a)
                n += 1
        except Exception as e:
            print("MH_FACES sweep error", e)
    if n:
        print("MH_FACES swept", n, reason)


def look(cam, frm, to):
    cam.set_actor_location_and_rotation(frm, unreal.MathLibrary.find_look_at_rotation(frm, to), False, True)


def neutral_pp(comp, bias):
    """Component post process: manual exposure and a neutral grade, so the level's dream grade doesn't apply."""
    pp = comp.get_editor_property("post_process_settings")
    for k, v in (("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                 ("auto_exposure_apply_physical_camera_exposure", False), ("auto_exposure_bias", bias),
                 ("color_saturation", unreal.Vector4(1, 1, 1, 1)), ("color_contrast", unreal.Vector4(1, 1, 1, 1)),
                 ("color_gamma", unreal.Vector4(1, 1, 1, 1)), ("color_gain", unreal.Vector4(1, 1, 1, 1)),
                 ("color_offset", unreal.Vector4(0, 0, 0, 0)), ("scene_color_tint", unreal.LinearColor(1, 1, 1, 1)),
                 ("vignette_intensity", 0.0), ("bloom_intensity", 0.0), ("film_grain_intensity", 0.0),
                 ("scene_fringe_intensity", 0.0), ("color_grading_intensity", 0.0), ("white_temp", 6500.0),
                 ("depth_of_field_fstop", 32.0), ("motion_blur_amount", 0.0),
                 # UE's default filmic curve, replacing the level's crushed toe and shoulder
                 ("film_slope", 0.88), ("film_toe", 0.55), ("film_shoulder", 0.26), ("film_black_clip", 0.0),
                 ("film_white_clip", 0.04)):
        try:
            pp.set_editor_property("override_" + k, True)
            pp.set_editor_property(k, v)
        except Exception as e:
            print("MH_FACES pp skip", k, str(e)[:80])
    comp.set_editor_property("post_process_settings", pp)
    comp.set_editor_property("post_process_blend_weight", 1.0)


def manual_only(comp, bias):
    pp = unreal.PostProcessSettings()
    for k, v in (("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                 ("auto_exposure_apply_physical_camera_exposure", False), ("auto_exposure_bias", bias)):
        pp.set_editor_property("override_" + k, True)
        pp.set_editor_property(k, v)
    comp.set_editor_property("post_process_settings", pp)


def step_shoot():
    out = f"{OUT}/{FACE}"
    os.makedirs(out, exist_ok=True)
    marker = os.path.join(out, "_done.txt")
    if os.path.exists(marker):
        os.remove(marker)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    # ue_remote removes KEY=VALUE env vars when this run returns, before the deferred shots: read them now
    bias = float(os.environ.get("FOA_EXP_BIAS", "-1"))  # EV -1: bracketed on face A
    bracket = [float(x) for x in os.environ.get("FOA_BRACKET", "").split(",") if x]
    with_room = os.environ.get("FOA_ROOM", "1") == "1"  # 0: studio only (round 2), one preview actor, less memory
    turntable = os.environ.get("FOA_TURNTABLE", "0") == "1"
    global GROOM_LOD
    GROOM_LOD = int(os.environ.get("FOA_GROOM_LOD", "-1"))  # >= 0 forces that groom LOD (cards) for the capture
    ps = next((a for a in EAS.get_all_level_actors() if a.get_actor_label() == "PlayerStart_WakeUp"), None)
    p = ps.get_actor_location() if ps else unreal.Vector(60, -80, 100)
    room = unreal.Vector(p.x, p.y, 0.0)
    studio = unreal.Vector(p.x + 30000.0, p.y, 0.0)  # empty space 300 m away, at floor height (out of the fog depth)
    ch = unreal.load_asset(face_path(FACE))
    sweep("left by an earlier run")
    made, deferred = [], [False]

    def spawn(cls, at, label):
        a = EAS.spawn_actor_from_class(cls, at, unreal.Rotator())
        a.set_actor_label(label)
        made.append(a)
        return a

    def cleanup():
        for a in reversed(made):
            try:
                if a is not None:
                    EAS.destroy_actor(a)
            except Exception as e:
                print("MH_FACES destroy error", e)
        sweep("after the shots")
        try:
            done(ch)  # also removes the subsystem's preview actor
        except Exception as e:
            print("MH_FACES done error", e)
        with open(marker, "w") as fh:
            fh.write("done")

    edit(ch)
    try:
        actor = SUB.spawn_meta_human_actor(ch, True)
        actor.set_actor_label("TMP_character_Face")
        made.append(actor)
        actor.set_actor_location(studio, False, True)
        # a second preview actor already standing in the room: a preview actor moved after assembly loses its grooms
        if with_room:
            room_actor = SUB.spawn_meta_human_actor(ch, True)
            room_actor.set_actor_label("TMP_character_FaceRoom")
            made.append(room_actor)
            room_actor.set_actor_location(room, False, True)
        # assemble after the spawn: grooms reach only the actors registered when the assembly finishes
        SUB.assemble_for_preview(character=ch)
        cap = spawn(unreal.SceneCapture2D, studio, "TMP_character_Capture")
        comp = cap.capture_component2d
        rt = unreal.RenderingLibrary.create_render_target2d(world, 1024, 1024, unreal.TextureRenderTargetFormat.RTF_RGBA8)
        comp.set_editor_property("texture_target", rt)
        comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        comp.set_editor_property("capture_every_frame", False)
        comp.set_editor_property("always_persist_rendering_state", True)
        # soft studio: big key front-left, fill front-right, rim behind; a grey backdrop card behind the head
        for i, (off, cd) in enumerate((((140, 90, 190), 1.0), ((-120, 110, 160), 0.45), ((40, -150, 200), 0.6))):
            lt = spawn(unreal.PointLight, studio + unreal.Vector(*off), f"TMP_character_Light{i}")
            lc = lt.point_light_component
            lc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
            lc.set_editor_property("intensity", 60.0 * cd)
            lc.set_editor_property("attenuation_radius", 800.0)
            lc.set_editor_property("source_radius", 40.0)
            lc.set_editor_property("soft_source_radius", 60.0)
        card = spawn(unreal.StaticMeshActor, studio + unreal.Vector(0, -120, 150), "TMP_character_Backdrop")
        card.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
        card.set_actor_scale3d(unreal.Vector(6, 0.05, 4))  # thin wall behind the head (seen from +Y)

        def fwd(deg):
            a = math.radians(90 + deg)  # MetaHumans face +Y
            return unreal.Vector(math.cos(a), math.sin(a), 0.0)

        def snap(name, warm=20):  # many captures: TSR and Lumen settle (dithered hair cards, noisy GI)
            for _ in range(warm):
                comp.capture_scene()
            comp.capture_scene()
            unreal.RenderingLibrary.export_render_target(world, rt, out, name + ".png")

        def head_at(who=None):
            """Face centre: the head bone of the preview body, raised to eye height and moved forward (+Y)."""
            who = who or actor
            for c in who.get_components_by_class(unreal.SkeletalMeshComponent):
                if c.does_socket_exist("head"):
                    return c.get_socket_location("head") + unreal.Vector(0, 6, 8)
            return who.get_actor_location() + unreal.Vector(0, 0, 166)

        def shots():
            comp.set_editor_property("show_flag_settings", [
                unreal.EngineShowFlagsSetting(show_flag_name=f, enabled=False) for f in
                ("PostProcessMaterial", "DirectionalLights", "Fog", "DepthOfField", "MotionBlur", "Grain")])
            cards_lod = GROOM_LOD
            for g in actor.get_components_by_class(unreal.GroomComponent):
                ga = g.get_editor_property("groom_asset")
                lods = []
                if ga:
                    for grp in ga.get_editor_property("hair_groups_lod"):
                        lods.append([str(l.get_editor_property("geometry_type")).split(".")[-1][:6] for l in grp.get_editor_property("lods")])
                print("MH_FACES groom", g.get_name(), ga.get_name() if ga else None, "lods", lods[:1])
                assert cards_lod < 0, "Use the Creator hair-cards preview; GroomComponent forced LOD is native-only"
            head = head_at()
            print("MH_FACES head", FACE, [round(v, 1) for v in (head.x - studio.x, head.y - studio.y, head.z)])
            comp.set_editor_property("fov_angle", 22)
            st["head"] = head
            st["queue"] = [(f"front_ev{b:+.1f}", 0, b) for b in bracket]
            st["queue"] += [(name, deg, bias) for name, deg in (("front", 0), ("tq", 35), ("profile", 90))]
            if turntable:
                st["queue"] += [(f"turn_{i:02d}", deg, bias) for i, deg in enumerate(range(-90, 91, 15))]
            assert st["queue"]
            comp.set_editor_property("capture_every_frame", True)
            next_shot()

        def next_shot():
            _, deg, exposure = st["queue"][0]
            neutral_pp(comp, exposure)
            head = st["head"]
            look(cap, head + fwd(deg) * 110, head)
            st["shot_start"], st["frames"] = time.time(), 0

        def room_shot():
            comp.set_editor_property("show_flag_settings", [])
            comp.set_editor_property("post_process_settings", unreal.PostProcessSettings())
            comp.set_editor_property("post_process_blend_weight", 0.0)
            comp.set_editor_property("fov_angle", 24)  # head and shoulders: wider, the grooms drop to LODs the preview lacks
            head = head_at(room_actor)
            aim = head + unreal.Vector(0, 0, -6)
            look(cap, aim + fwd(30) * 140 + unreal.Vector(0, 0, 4), aim)
            fill = spawn(unreal.PointLight, head + fwd(30) * 150 + unreal.Vector(0, 0, 25), "TMP_character_RoomFill")
            fl = fill.point_light_component
            fl.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
            fl.set_editor_property("intensity", 12.0)
            fl.set_editor_property("attenuation_radius", 400.0)
            fl.set_editor_property("source_radius", 30.0)
            snap("room", warm=20)
            print("MH_FACES shot", FACE, out)

        st = {"t0": time.time(), "h": None, "phase": 0}

        def tick(_dt):
            t = time.time() - st["t0"]
            if st["phase"] == 0 and t >= WAIT:
                st["phase"] = 1
                try:
                    shots()
                except Exception as e:
                    print("MH_FACES shoot error", e)
                    st["phase"] = 2
            elif st["phase"] == 1:
                st["frames"] += 1
                # Temporal hair dithering must settle over rendered frames, not repeated calls in one tick.
                if st["frames"] < 24 or time.time() - st["shot_start"] < 1.0:
                    return
                try:
                    unreal.RenderingLibrary.export_render_target(world, rt, out, st["queue"][0][0] + ".png")
                    st["queue"].pop(0)
                    if st["queue"]:
                        next_shot()
                    else:
                        comp.set_editor_property("capture_every_frame", False)
                        if with_room:
                            room_shot()
                        st["phase"] = 2
                except Exception as e:
                    print("MH_FACES capture error", e)
                    st["phase"] = 2
            if st["phase"] == 2:
                st["phase"] = 3
                unreal.unregister_slate_post_tick_callback(st["h"])
                cleanup()
        st["h"] = unreal.register_slate_post_tick_callback(tick)
        deferred[0] = True
        print("MH_FACES deferred", WAIT, "s", FACE)
    finally:
        if not deferred[0]:
            cleanup()


if __name__ == "__main__":
    {"setup": step_setup, "probe": step_probe, "face": step_face, "shoot": step_shoot}[STEP]()
