# Current setup dispatches components/mesh/all to normalized Teen wiring. Historical MetaHuman helper bodies
# remain below for reference only; none of those asset-loading helpers are called by the supported entrypoints.
"""Wires the character lane's MetaHuman protagonist into BP_FoAPlayer. Everything comes from the lane's assembled
BP_MHC_Protagonist (not shipped), so a rebuilt or replaced face is picked up by re-running FOA_STEP=all.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/build_protagonist.py FOA_AREAS=/Game/FoA/Characters/Player FOA_STEP=components|mesh|leader|construction|all
components: Face (the build's face AnimBP copies the body pose, custom depth stencil 4 for the PP smear); every groom BP_MHC_Protagonist carries
            (Hair, Eyebrows, ...) on the Face with its binding, its wardrobe hair materials (OverrideMaterials: without
            them a groom renders nothing), attachment name, parent bounds and simulation settings; StartOutfit;
            CharacterLight (cool point light on the boom, lighting channel 2 only; the character receives 0 and 2);
            LODSync as the build has it (it puts the grooms on their cards LODs: without it they render nothing).
            Leader-pose followers take their bounds from the body (close shots of lying or kneeling poses stay unculled).
mesh: the Body becomes the character mesh (ABP_FoAPlayer drives it through the SK_Mannequin compatible-skeleton link),
      bounds from all physics bodies.
leader: BeginPlay sets the Body as Leader Pose for StartOutfit (the garment slots are already chained).
Editor-world animation (Sequencer scrubs spawnables there): bUpdateAnimationInEditor is true on the Mesh, Body and Face
templates. Python cannot write it; Hayba object_set_property can (once; it persists):
  hayba_call.py object_set_property '{"path":"/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C:Body_GEN_VARIABLE",
  "properties":{"bUpdateAnimationInEditor":true}}'  (same for Face_GEN_VARIABLE and Default__BP_FoAPlayer_C:CharacterMesh0)"""
import importlib
import os
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
import graph_style  # noqa: E402

importlib.reload(graph_style)
at, box, link = graph_style.at, graph_style.box, graph_style.link
P = "/Game/FoA/Characters/Player"
BP_PATH = P + "/BP_FoAPlayer"
MHC = "/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist"
MH_BP = MHC + "/BP_MHC_Protagonist"
TEEN = "/Game/FoA/Characters/Protagonist/Teen/Built"
TEEN_HEAD = TEEN + "/MHC_Teen_Head"
GROOM_COPY = ("groom_asset", "binding_asset", "override_materials", "attachment_name", "use_attach_parent_bound",
              "simulation_settings")
FOLLOWERS = ("StartOutfit", "StartPants", "StartSocks", "Shirt", "Trousers", "Socks", "Tie", "Suit")  # Leader Pose layers (the Face copies its pose)
# Boom space: the boom origin is the pawn, +X points away from the camera, so this sits beyond his head, off the shoulder.
LIGHT = {"at": (110.0, -50.0, 75.0), "cd": float(os.environ.get("FOA_LIGHT_CD", "3.0")), "radius": 260.0}
RECEIVE = unreal.LightingChannels(channel0=True, channel1=False, channel2=True)
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
PIN = unreal.BlueprintGraphPinLibrary
SDS = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
LIB = unreal.SubobjectDataBlueprintFunctionLibrary


MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
LEADER = "Body"  # Leader Pose target of the outfit and garment layers: the visible MetaHuman body


def under(by_name, name, parent):
    """Re-parent an existing SCS component (Face, StartOutfit moved from Mesh to Body); a no-op when already there."""
    if name in by_name and parent in by_name:
        SDS.attach_subobject(by_name[parent], by_name[name])


def relead_garments(ed):
    """The garment chain (built by build_player_bp.py, above y 1900) led from Mesh; point every Leader Pose call that
    still reads Mesh at the MetaHuman Body instead (the Mesh is now the hidden Mannequin driver)."""
    PINL = unreal.BlueprintGraphPinLibrary
    for n in list(ed.list_all_nodes()):
        if not BEL.get_node_title(n).replace(" ", "").startswith("SetLeaderPose"):
            continue
        lead = BEL.find_input_pin(n, "NewLeaderBoneComponent")
        src = [PINL.get_owning_node(q) for q in PINL.list_connected_pins(lead)]
        if src and BEL.get_node_title(src[0]).replace(" ", "") in ("GetMesh", "Mesh"):
            x, y = BEL.get_node_pos(src[0]).x, BEL.get_node_pos(src[0]).y
            g = at(ed.add_get_member_variable_node(LEADER, ""), x, y + 60)
            PINL.break_pin_links(lead)
            link(g, LEADER, n, "NewLeaderBoneComponent")
    for n in list(ed.list_all_nodes()):  # getters of Mesh left with no links
        if BEL.get_node_title(n).replace(" ", "") in ("GetMesh", "Mesh") and \
                not any(PINL.list_connected_pins(q) for q in BEL.list_output_pins(n)):
            ed.remove_nodes([n])


def bp_closed():
    bp = unreal.load_asset(BP_PATH)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    return bp


def templates(bp):
    """{component variable name: component template} of a Blueprint (inherited ones too)."""
    out = {}
    for h in SDS.k2_gather_subobject_data_for_blueprint(bp):
        d = LIB.get_data(h)
        out.setdefault(str(LIB.get_variable_name(d)), LIB.get_object_for_blueprint(d, bp))
    return out


def source():
    """The character lane's assembled MetaHuman: body, face and outfit meshes, and its groom components."""
    mh = templates(unreal.load_asset(MH_BP))
    mesh_of = lambda n: mh[n].get_editor_property("skeletal_mesh_asset") if n in mh else None  # noqa: E731
    grooms = {n: c for n, c in mh.items() if isinstance(c, unreal.GroomComponent) and c.get_editor_property("groom_asset")}
    face = unreal.load_asset(TEEN_HEAD) if EAL.does_asset_exist(TEEN_HEAD) else mesh_of("Face")
    return mesh_of("Body"), face, mesh_of("SkeletalMesh"), grooms


# The build's component names -> ours (LODSync addresses components by name).
SYNC_NAMES = {"SkeletalMesh": "StartOutfit"}


def lod_sync(bp, by_name, ensure):
    """LODSync copied from the build, names translated. It is what makes the grooms render: it maps Hair/Eyebrows to
    their cards and mesh LODs (3/5/7). Without it a groom picks strands at every distance (auto LOD), and strands
    render nothing here (bald). Cards are the low-end-friendly choice anyway."""
    src = templates(unreal.load_asset(MH_BP)).get("LODSync")
    if not src:
        print("no LODSync on the build: grooms keep their own LOD choice")
        return
    have = set(templates(bp))
    ours = lambda n: SYNC_NAMES.get(n, n)  # noqa: E731
    if "LODSync" not in by_name:
        actor = next(h for h in SDS.k2_gather_subobject_data_for_blueprint(bp)
                     if LIB.is_actor(LIB.get_data(h)))  # actor components hang off the actor itself
        h, fail = SDS.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=actor, new_class=unreal.LODSyncComponent,
                                                                     blueprint_context=bp))
        assert not str(fail), fail
        SDS.rename_subobject(h, "LODSync")
        by_name["LODSync"] = h
    dst = LIB.get_object_for_blueprint(LIB.get_data(by_name["LODSync"]), bp)
    sync = []
    for c in src.get_editor_property("components_to_sync"):
        n = ours(str(c.get_editor_property("name")))
        if n in have:
            c.set_editor_property("name", n)
            sync.append(c)
    mapping = {}
    for k, v in src.get_editor_property("custom_lod_mapping").items():
        if ours(str(k)) in have:
            mapping[ours(str(k))] = v
    # forced_lod 0, not the build's -1: the outfit Leader-Poses the Body, and a Body on LOD1+ drops the twist and
    # corrective bones the trousers and sleeves are skinned to, so those vertices stay in the reference A-pose (the
    # missing trousers and floating sleeves in PIE). One hero character at LOD 0 is affordable.
    for k, v in (("num_lods", src.get_editor_property("num_lods")), ("forced_lod", 0),
                 ("min_lod", src.get_editor_property("min_lod")), ("components_to_sync", sync), ("custom_lod_mapping", mapping)):
        dst.set_editor_property(k, v)
    print("LODSync:", [str(c.get_editor_property("name")) for c in sync],
          {k: list(v.get_editor_property("mapping")) for k, v in mapping.items()})


def components():
    bp = bp_closed()
    by_name = {str(LIB.get_variable_name(LIB.get_data(h))): h for h in SDS.k2_gather_subobject_data_for_blueprint(bp)}

    def ensure(name, cls, parent):
        if name not in by_name:
            h, fail = SDS.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=by_name[parent], new_class=cls,
                                                                         blueprint_context=bp))
            assert not str(fail), fail
            SDS.rename_subobject(h, name)
            by_name[name] = h
        return LIB.get_object_for_blueprint(LIB.get_data(by_name[name]), bp)

    body_mesh, face_mesh, outfit, grooms = source()
    assert face_mesh and body_mesh, f"no Face/Body mesh on {MH_BP}"
    face_anim = templates(unreal.load_asset(MH_BP))["Face"].get_editor_property("anim_class")
    if EAL.does_asset_exist('/Game/FoA/Characters/Player/ABP_FoA_Face'):
        face_anim = unreal.load_class(None, '/Game/FoA/Characters/Player/ABP_FoA_Face.ABP_FoA_Face_C')
    assert face_anim, f"no face AnimBP on {MH_BP}"
    graph_style.ensure_variable(bp, "bStartCinematic", BEL.get_basic_type_by_name("bool"), "false")
    BEL.set_blueprint_variable_instance_editable(bp, "bStartCinematic", True)  # set on LS_WakeUp's spawnable (MRQ copy)
    # Epic's MetaHuman route: the visible body retargets every frame from the hidden Mannequin (Mesh), which runs
    # ABP_FoAPlayer, montages and Sequencer; the body's own post-process ABP (RigLogic correctives) runs on top.
    body = ensure("Body", unreal.SkeletalMeshComponent, "Mesh")
    body.set_skeletal_mesh_asset(body_mesh)
    body.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_BLUEPRINT)
    body.set_editor_property("anim_class", EAL.load_blueprint_class(P + "/ABP_FoAPlayer_MH"))
    body.set_editor_property("consider_all_bodies_for_bounds", True)  # bounds follow the pose (lying, kneeling)
    body.set_collision_profile_name("NoCollision")
    face = ensure("Face", unreal.SkeletalMeshComponent, "Body")
    under(by_name, "Face", "Body")
    face.set_skeletal_mesh_asset(face_mesh)
    face.set_editor_property("render_custom_depth", True)
    face.set_editor_property("custom_depth_stencil_value", 4)  # PP lane's face smear
    face.set_collision_profile_name("NoCollision")
    # The MetaHuman way: the Face runs the build's face AnimBP (Copy Pose From Mesh, attached parent), not Leader
    # Pose. Leader Pose never evaluates the face's own bones, so its facial joints sit wrong and the groom bindings
    # (which read them) render nothing: that was the bald head.
    face.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_BLUEPRINT)
    face.set_editor_property("anim_class", face_anim)
    face.set_editor_property("use_attach_parent_bound", True)  # bounds of the posed body, not a standing box
    for name, src in grooms.items():
        g = ensure(name, unreal.GroomComponent, "Face")
        for k in GROOM_COPY:
            g.set_editor_property(k, src.get_editor_property(k))
        if EAL.does_asset_exist(TEEN_HEAD) and name in ("Hair", "Eyebrows"):
            g.set_editor_property("groom_asset", unreal.load_asset(TEEN + "/Grooms/GR_Teen_" + name))
            g.set_editor_property("binding_asset", unreal.load_asset(TEEN + "/Grooms/GB_Teen_" + name))
            mats = [unreal.load_asset(TEEN + "/Grooms/MI_Teen_" + name + "_" + str(i))
                    for i in range(3 if name == "Hair" else 2)]
            assert all(mats), "Persist the teenage groom materials before rebuilding the player"
            g.set_editor_property("override_materials", mats)
        g.set_editor_property("render_custom_depth", False)  # hair is outside the face-front post-process mask
        g.set_editor_property("custom_depth_stencil_value", 0)
    for name, c in templates(bp).items():  # a groom the new build dropped (no beard any more, say) stops rendering
        if isinstance(c, unreal.GroomComponent) and name not in grooms:
            c.set_editor_property("groom_asset", None)
            c.set_editor_property("binding_asset", None)
    if isinstance(outfit, unreal.SkeletalMesh):
        o = ensure("StartOutfit", unreal.SkeletalMeshComponent, "Body")
        under(by_name, "StartOutfit", "Body")
        o.set_skeletal_mesh_asset(outfit)
        o.set_editor_property("component_tags", ["Outfit", "StartOutfit"])
        o.set_collision_profile_name("NoCollision")
    else:
        print("StartOutfit skipped: the build has no outfit mesh on its SkeletalMesh component")
    # Character-only light: soft cool edge from beyond him (it orbits with the boom), lighting channel 2 only, no shadows.
    rim = ensure("CharacterLight", unreal.PointLightComponent, "CameraBoom")
    for k, v in (("relative_location", unreal.Vector(*LIGHT["at"])), ("intensity_units", unreal.LightUnits.CANDELAS),
                 ("intensity", LIGHT["cd"]), ("attenuation_radius", LIGHT["radius"]), ("source_radius", 25.0),
                 ("soft_source_radius", 40.0), ("use_temperature", True), ("temperature", 8200.0), ("specular_scale", 0.4),
                 ("cast_shadows", False), ("lighting_channels", unreal.LightingChannels(channel0=False, channel1=False, channel2=True))):
        rim.set_editor_property(k, v)
    lod_sync(bp, by_name, ensure)
    have = templates(bp)
    for name in ("Body", "Face") + FOLLOWERS + tuple(grooms):
        if name in have:
            have[name].set_editor_property("lighting_channels", RECEIVE)
    for name in FOLLOWERS:  # leader-pose followers: bounds follow the posed body, not a stale standing box
        if name in have:
            have[name].set_editor_property("use_bounds_from_leader_pose_component", True)
    EAL.save_loaded_asset(bp, False)
    print("protagonist components:", sorted(k for k in have if k in FOLLOWERS + tuple(grooms) + ("CharacterLight",)),
          "groom materials:", {n: [m.get_name() if m else None for m in g.get_editor_property("override_materials")]
                               for n, g in grooms.items()})


def mesh():
    bp = bp_closed()
    m = unreal.get_default_object(bp.generated_class()).get_editor_property("mesh")
    m.set_skeletal_mesh_asset(unreal.load_asset(MANNY))
    m.set_editor_property("anim_class", EAL.load_blueprint_class(P + "/ABP_FoAPlayer"))
    m.set_editor_property("visible", False)  # the driver: never drawn, the MetaHuman Body retargets from it
    m.set_editor_property("visibility_based_anim_tick_option",
                          unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)  # hidden, still posed
    m.set_editor_property("cast_shadow", False)
    EAL.save_loaded_asset(bp, False)
    print("driver mesh:", m.get_editor_property("skeletal_mesh_asset").get_path_name(), "visible", m.get_editor_property("visible"))


MINE = {"Face", "StartOutfit", "Mesh", "Body", "Shirt", "Trousers", "Socks", "Tie", "Suit", "bStartCinematic", "Branch", "SetCinematic"}


def component_names(bp):
    """SCS component variables (inherited ones too); list_member_variable_names only lists plain variables."""
    return set(templates(bp))


def clear_mine(ed, keep, titles):
    """Re-runnable steps: drop this step's own nodes (titles compared without spaces, getters with or without 'Get')
    where keep(node) is False, and its comment boxes by title."""
    for n in list(ed.list_all_nodes()):
        t = BEL.get_node_title(n).replace(" ", "")
        t = t[3:] if t.startswith("Get") and t[3:] in MINE else t
        if not keep(n) and (t.startswith(("SetLeaderPose", "SetUpdateAnimationInEditor")) or t in MINE):
            ed.remove_nodes([n])
    for c in list(ed.list_comment_nodes()):
        if BEL.get_comment_text(c) in titles:
            ed.remove_comment_node(c)


def leader():
    bp = bp_closed()
    ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "EventGraph")
    clear_mine(ed, lambda n: BEL.get_node_pos(n).y < 1900, {"Face follows body", "Start in cinematic"})  # own row: y > 1900
    leads = [n for n in ed.list_all_nodes()
             if BEL.get_node_title(n).replace(" ", "").startswith("SetLeaderPose") and BEL.get_node_pos(n).y < 1900]
    last = max(leads, key=lambda n: BEL.get_node_pos(n).x)  # end of the garment chain
    lx, ly = BEL.get_node_pos(last).x, BEL.get_node_pos(last).y
    ly = 2000  # own row under the garment chain (re-runs find and replace exactly these nodes)
    relead_garments(ed)
    body = at(ed.add_get_member_variable_node(LEADER, ""), lx + 300, ly + 420)
    prev, made = last, [body]
    names = [n for n in ("StartOutfit",) if n in component_names(bp)]
    for i, name in enumerate(names):
        g = at(ed.add_get_member_variable_node(name, ""), lx + 300 + i * 300, ly + 200)
        c = at(ed.add_call_function_node("/Script/Engine.SkinnedMeshComponent:SetLeaderPoseComponent"), lx + 300 + i * 300, ly)
        link(prev, None, c, None)
        link(g, name, c, "self")
        link(body, LEADER, c, "NewLeaderBoneComponent")
        prev = c
        made += [g, c]
    box(ed, "Face follows body", "", made, "anim")
    # Last in BeginPlay: a sequence's spawnable copy starts in cinematic mode (no look-at, no foot IK).
    x = lx + 300 + len(names) * 300 + 100
    flag = at(ed.add_get_member_variable_node("bStartCinematic", ""), x, ly + 200)
    br = at(ed.add_branch_node(), x + 220, ly)
    cine = graph_style.self_call(ed, "SetCinematic", x + 480, ly)
    graph_style.value(cine, "bEnable", "true")
    baseline = graph_style.self_call(ed, "SetSandOverlay", x, ly - 180)
    graph_style.value(baseline, "Amount", "0.06")
    link(prev, None, baseline, None)
    link(baseline, None, br, None)
    link(flag, "bStartCinematic", br, "Condition")
    link(br, "Then", cine, None)
    box(ed, "Start in cinematic", "", [baseline, flag, br, cine], "state")
    EAL.save_loaded_asset(bp, False)
    print("leader pose chain:", names, "+ bStartCinematic gate")


def construction():
    """Same Leader Pose chain in the Construction Script: editor-world spawns (Sequencer preview, MRQ) never run BeginPlay."""
    bp = bp_closed()
    ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "UserConstructionScript")
    clear_mine(ed, lambda n: False, {"Layers follow body", "Animate in editor"})
    nodes = list(ed.list_all_nodes())
    entry = next(n for n in nodes if BEL.get_node_title(n) == "Construction Script")
    parent = [n for n in nodes if BEL.get_node_title(n).startswith("Parent:")]
    prev = parent[0] if parent else entry
    while True:  # append after whatever chain other lanes may have hung off the entry
        nxt = [PIN.get_owning_node(q) for q in PIN.list_connected_pins(BEL.find_then_pin(prev))] if PIN.is_valid(BEL.find_then_pin(prev)) else []
        if not nxt:
            break
        prev = nxt[0]
    x, y = BEL.get_node_pos(prev).x + 320, BEL.get_node_pos(prev).y
    have = component_names(bp)
    names = [n for n in FOLLOWERS if n in have]
    body = at(ed.add_get_member_variable_node(LEADER, ""), x, y + 420)
    made = [body]
    for i, name in enumerate(names):
        g = at(ed.add_get_member_variable_node(name, ""), x + i * 300, y + 200)
        c = at(ed.add_call_function_node("/Script/Engine.SkinnedMeshComponent:SetLeaderPoseComponent"), x + i * 300, y)
        link(prev, None, c, None)
        link(g, name, c, "self")
        link(body, LEADER, c, "NewLeaderBoneComponent")
        prev = c
        made += [g, c]
    box(ed, "Layers follow body", "", made, "anim")
    EAL.save_loaded_asset(bp, False)
    print("construction leader chain:", names)


def compile_save():
    bp = bp_closed()
    print("Compile BP_FoAPlayer through Hayba blueprint_compile after authoring")
    EAL.save_loaded_asset(bp, False)


def wiring():  # rerun of the graph half only: leader chains, then compile
    leader()
    construction()
    compile_save()


def teen_components():
    """Current component path. Historical MH authoring helpers above are no longer dispatched."""
    import runpy
    runpy.run_path('P:/FoA/Tools/Unreal/player/swap_teen_components.py', run_name='__main__')


def all_steps():
    teen_components()
    leader()
    construction()
    compile_save()


{"components": teen_components, "mesh": teen_components, "leader": leader, "construction": construction,
 "wiring": wiring, "all": all_steps}[os.environ["FOA_STEP"]]()
