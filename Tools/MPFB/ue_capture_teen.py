"""In-editor review stills of the imported teen (SK_Teen_*), one outfit per run, in the bedroom light and the game's
post process. Adapted from Tools/Unreal/mh_capture.py. Run inside the editor lock:
  $env:FOA_AREAS='Characters'; $env:FOA_ACTORS_NEW='TMP_rlchar_'; python Tools/Unreal/ue_remote.py Tools/MPFB/ue_capture_teen.py FOA_OUTFIT=wake|suit
Spawns TMP_rlchar_* SkeletalMeshActors (body, head, garments; all in the shared bind pose, garments led by the body),
hides the body skin sections under the worn garments and the inner-garment sections under worn outer garments
(ShowMaterialSection, as BP_FoAPlayer will), stencil 4 on the head (face, hair and brows live on SK_Teen_Head),
a TMP SceneCapture2D + TMP lights, writes <outfit>_{front,tq,side,back,face}.png to FOA_OUT, then destroys everything.
The level is not saved."""
import math
import os
import time
import json
import sys

import unreal

OUT = os.environ.get("FOA_OUT", "P:/FoA/Saved/CharacterShots/mpfb/ue")
MESH = "/Game/FoA/Characters/Teen/Mesh/"
OUTFITS = {"wake": {"Polo": "foa_polo_layered", "Pants": "toigo_wool_pants", "Socks": "joepal_crude_low_socks"},
           "suit": {"Suit": "male_elegantsuit01", "Shoes": "shoes03"}}
OUTFIT = os.environ.get("FOA_OUTFIT", "wake")
FWD_YAW = float(os.environ.get("FOA_FWD_YAW", "90"))  # the mesh faces +Y in actor space
WAIT = float(os.environ.get("FOA_WAIT", "6"))
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def sweep():
    for a in EAS.get_all_level_actors():
        try:
            if a.get_actor_label().startswith("TMP_rlchar_"):
                EAS.destroy_actor(a)
        except Exception as e:
            print("TEEN_CAPTURE sweep error", e)


def hide_sections(comp, worn):
    """Hide every material section whose slot name says it lies under a worn garment."""
    if os.environ.get("FOA_HIDE_SECTIONS") == "0":
        return []
    mesh = comp.get_skinned_asset() if hasattr(comp, "get_skinned_asset") else comp.skeletal_mesh
    hidden = []
    for i, m in enumerate(mesh.materials):
        slot = str(m.material_slot_name)
        tail = slot.split("under_", 1)[1] if "under_" in slot else ""
        if tail and any(g in tail for g in worn):
            comp.show_material_section(i, i, False, 0)
            hidden.append(slot)
    return hidden


def run():
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Wait for PIE to stop'
    cloth_qa=bool(os.environ.get('FOA_CLOTH_QA'))
    neutral_diagnostic=os.environ.get('FOA_NEUTRAL_NORMAL')=='1'
    compare_geometry=os.environ.get('FOA_COMPARE_GEOMETRY')=='1'
    blink_qa=os.environ.get('FOA_BLINK_QA')=='1'
    pose_name=os.environ.get('FOA_POSE_NAME')
    fold_loop=os.environ.get('FOA_FOLD_LOOP')=='1'
    os.makedirs(OUT, exist_ok=True)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    ps = next((a for a in EAS.get_all_level_actors() if a.get_actor_label() == "PlayerStart_WakeUp"), None)
    p = ps.get_actor_location() if ps else unreal.Vector(60, -80, 100)
    if os.environ.get("FOA_BASE"):  # "x,y": a clearer spot than the wake-up start
        x, y = (float(v) for v in os.environ["FOA_BASE"].split(","))
        p = unreal.Vector(x, y, 0.0)
    base = unreal.Vector(p.x, p.y, float(os.environ.get('FOA_BASE_Z','1000' if cloth_qa else '0')))
    sweep()
    made = []
    worn = list(OUTFITS[OUTFIT].values())

    def spawn(asset, label):
        a = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, base, unreal.Rotator(0, 0, 0))
        a.set_actor_label("TMP_rlchar_" + label)
        a.skeletal_mesh_component.set_skeletal_mesh_asset(unreal.load_asset(MESH + asset))
        made.append(a)
        return a

    body = spawn("SK_Teen_Body", "Body")
    if os.environ.get('FOA_ANIM'):
        bc=body.skeletal_mesh_component
        animation=unreal.load_asset(os.environ['FOA_ANIM']);assert animation
        assert animation.get_editor_property('skeleton')==bc.get_skinned_asset().skeleton
        bc.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        bc.set_animation(animation)
        bc.set_position(float(os.environ.get('FOA_ANIM_TIME','0')),False)
        bc.set_update_animation_in_editor(True)
    print("TEEN_CAPTURE body hidden", hide_sections(body.skeletal_mesh_component, worn))
    head = spawn("SK_Teen_Head", "Head")
    hc = head.skeletal_mesh_component
    hc.set_render_custom_depth(True)
    hc.set_custom_depth_stencil_value(4)
    layers = [head]
    cloth_mids = []
    polo = None
    for piece in OUTFITS[OUTFIT]:
        g = spawn("SK_Teen_" + piece, piece)
        if piece=='Polo':polo=g.skeletal_mesh_component
        if os.environ.get("FOA_WRINKLES"):
            weight = float(os.environ["FOA_WRINKLES"])
            phase = float(os.environ.get("FOA_PHASE", "0"))
            for i in range(g.skeletal_mesh_component.get_num_materials()):
                mi = g.skeletal_mesh_component.create_dynamic_material_instance(i)
                cloth_mids.append(mi)
                for side in ("L", "R"):
                    mi.set_vector_parameter_value("WrinkleWeights" + side, unreal.LinearColor(weight, weight, weight, weight))
                    mi.set_vector_parameter_value("WrinklePhases" + side, unreal.LinearColor(phase, phase, phase, phase))
        print("TEEN_CAPTURE", piece, "hidden", hide_sections(g.skeletal_mesh_component, worn))
        layers.append(g)
    for a in layers:
        if not (blink_qa and a==head):
            a.skeletal_mesh_component.set_leader_pose_component(body.skeletal_mesh_component)
        a.attach_to_actor(body, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                          unreal.AttachmentRule.KEEP_WORLD, False)
    hair = None
    if os.environ.get('FOA_GROOM') == '1':
        skin=unreal.load_asset('/Game/FoA/Characters/Teen/Materials/MI_Teen_Skin_Groom')
        assert skin, 'Bake and import the matched scalp tint first'
        hc.set_material(0,skin)
        hc.prestream_textures(30,True)
        hair = EAS.spawn_actor_from_class(unreal.GroomActor, base, unreal.Rotator())
        hair.set_actor_label('TMP_rlchar_Groom')
        made.append(hair)
        gc = hair.get_component_by_class(unreal.GroomComponent)
        gc.attach_to_component(hc, '', unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                               unreal.AttachmentRule.KEEP_WORLD, False)
        groom=unreal.load_asset('/Game/FoA/Characters/Teen/Hair/GR_Teen_Scalp')
        rigid=all(l.binding_type==unreal.GroomBindingType.RIGID for g in groom.hair_groups_lod for l in g.lods)
        gc.set_groom_asset(groom)
        gc.set_material(0, unreal.load_asset('/Game/FoA/Characters/Teen/Hair/MI_Teen_Strands'))
        gc.set_binding_asset(None if rigid else unreal.load_asset('/Game/FoA/Characters/Teen/Hair/GB_Teen_Scalp_Head'))
        gc.set_editor_property('attachment_name','head' if rigid else '')
        gc.set_render_custom_depth(True)
        gc.set_custom_depth_stencil_value(4)
        for i, material in enumerate(hc.get_skinned_asset().materials):
            if 'short01' in str(material.material_slot_name):
                hc.show_material_section(i, i, False, 0)
    cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, base, unreal.Rotator())
    cap.set_actor_label("TMP_rlchar_Capture")
    made.append(cap)
    comp = cap.capture_component2d
    if os.environ.get('FOA_NO_SHADOW')=='1':
        comp.set_editor_property('show_flag_settings',[unreal.EngineShowFlagsSetting(show_flag_name='DynamicShadows',enabled=False)])
    if os.environ.get('FOA_NO_POST') == '1':
        comp.set_editor_property('show_flag_settings',[unreal.EngineShowFlagsSetting(show_flag_name='PostProcessing',enabled=False)])
    rt = unreal.RenderingLibrary.create_render_target2d(world, 1080, 1080, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    comp.set_editor_property("texture_target", rt)
    comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    if os.environ.get("FOA_BASECOLOR") == "1":
        comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR)
    comp.set_editor_property("capture_every_frame", False)
    comp.set_editor_property("always_persist_rendering_state", True)
    if os.environ.get("FOA_ISOLATE") == "1":
        comp.set_editor_property("primitive_render_mode", unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
        for actor in [body] + layers:
            if not os.environ.get('FOA_ONLY_PIECE') or actor.get_actor_label()=='TMP_rlchar_'+os.environ['FOA_ONLY_PIECE']:
                comp.show_only_actor_components(actor)
        if hair:
            comp.show_only_actor_components(hair)
    pp = comp.get_editor_property("post_process_settings")
    pp.set_editor_property("override_auto_exposure_method", True)
    pp.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    pp.set_editor_property("override_auto_exposure_apply_physical_camera_exposure", True)
    pp.set_editor_property("auto_exposure_apply_physical_camera_exposure", False)
    pp.set_editor_property("override_auto_exposure_bias", True)
    pp.set_editor_property("auto_exposure_bias", float(os.environ.get("FOA_EXP_BIAS", "0")))
    comp.set_editor_property("post_process_settings", pp)
    comp.set_editor_property("post_process_blend_weight", 1.0)
    for i, (off, cd) in enumerate((((150, -60, 175), 1.0), ((-120, -90, 150), 0.35), ((-40, 160, 190), 0.6))):
        lt = EAS.spawn_actor_from_class(unreal.PointLight, base + unreal.Vector(*off), unreal.Rotator())
        lt.set_actor_label(f"TMP_rlchar_Light{i}")
        made.append(lt)
        lc = lt.point_light_component
        lc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
        lc.set_editor_property("intensity", float(os.environ.get("FOA_LIGHT_CD", "40")) * cd)
        lc.set_editor_property("attenuation_radius", 600.0)
        lc.set_editor_property("source_radius", 25.0)

    def fwd(deg):
        a = math.radians(FWD_YAW + deg)
        return unreal.Vector(math.cos(a), math.sin(a), 0.0)

    def look(frm, to):
        cap.set_actor_location_and_rotation(frm, unreal.MathLibrary.find_look_at_rotation(frm, to), False, True)

    def shoot(name):
        for _ in range(4):
            comp.capture_scene()
        unreal.RenderingLibrary.export_render_target(world, rt, OUT, f"{OUTFIT}_{name}.png")
        print("TEEN_CAPTURE wrote", f"{OUT}/{OUTFIT}_{name}.png")

    torso = base + unreal.Vector(0, 0, 95)
    face = base + unreal.Vector(0, 0, 168)
    shots = [("front", torso, 0, 300, 45), ("tq", torso, 40, 300, 45),
             ("side", torso, 90, 300, 45), ("back", torso, 180, 300, 45),
             ("face", face, 35, 95, 30)]
    if os.environ.get("FOA_WRINKLES"):
        shots = [("folds", base + unreal.Vector(0, 0, 123), 30, 145, 35)]
        if os.environ.get("FOA_FOLD_LOOP") == "1":
            shots = [(f"folds_{i:02d}", *shots[0][1:]) for i in range(8)]
    if os.environ.get("FOA_DETAIL") == "1":
        shots = [("waist", base + unreal.Vector(0, 0, 104), 0, 105, 35),
                 ("waist_tq", base + unreal.Vector(0, 0, 104), 45, 105, 35),
                 ("cuff", base + unreal.Vector(52, 0, 105), 0, 100, 30),
                 ("shoulder", base + unreal.Vector(25, 0, 143), 35, 110, 30)]
    if os.environ.get('FOA_HAIR_DETAIL') == '1':
        shots = [(name, base + unreal.Vector(0, 0, 174), angle, 80, 30)
                 for name, angle in [('front',0),('tq',35),('side',90),('back',180)]]
    if os.environ.get('FOA_CLOTH_QA'):
        shots=[(f'{version}_{view}',None,0,0,35) for view in ('front','side')
               for version in (('flat','after') if neutral_diagnostic else ('before','after'))]
    if blink_qa:
        shots=[(name,base+unreal.Vector(0,0,174),0,70,25) for name in ('open','closed')]

    def cleanup(success=True):
        for a in reversed(made):
            try:
                EAS.destroy_actor(a)
            except Exception as e:
                print("TEEN_CAPTURE destroy error", e)
        sweep()
        with open(os.path.join(OUT, f"_{OUTFIT}_done.txt"), "w") as fh:
            fh.write("done" if success else "error")

    st = {"next": time.time() + WAIT, "h": None, "i": 0, "stage": 0}

    def tick(_dt):  # textures stream and sections update on later ticks
        if time.time() < st["next"]:
            return
        try:
            name, tgt, deg, dist, fov = shots[st["i"]]
            if st["stage"] == 0:
                if blink_qa:
                    for morph in ('eyeBlinkLeft','eyeBlinkRight'):
                        hc.set_morph_target(morph,1.0 if name=='closed' else 0.0)
                if cloth_qa:
                    bc=body.skeletal_mesh_component
                    sys.path.insert(0,'P:/FoA/Tools/Cloth')
                    import wrinkle_driver
                    names=['pelvis','spine_01','spine_03','neck_01']+[x+'_'+s for s in 'lr' for x in ('upperarm','lowerarm','hand','thigh','calf','foot')]
                    heads={}
                    for n in names:
                        position=bc.get_socket_location(n)
                        heads[n]=(position.x,position.y,position.z)
                    weights=wrinkle_driver.weights(heads,garment='Polo')
                    if compare_geometry:
                        mesh_path=('/Game/FoA/Characters/Teen/_QA/SK_Teen_Polo_BeforeHem' if name.startswith('before')
                                   else MESH+'SK_Teen_Polo')
                        polo.set_skeletal_mesh_asset(unreal.load_asset(mesh_path))
                        polo.set_leader_pose_component(bc)
                    source='/Game/FoA/Characters/Teen/Cloth/MI_Teen_Polo'+('_Before' if name.startswith('before') else '')
                    polo.set_material(0,unreal.load_asset(source))
                    mid=polo.create_dynamic_material_instance(0)
                    for key,value in zip(('WeightsL','WeightsR','PhasesL','PhasesR'),weights):
                        mid.set_vector_parameter_value('Wrinkle'+key,unreal.LinearColor(*value))
                    if name.startswith('flat'):
                        mid.set_scalar_parameter_value('WrinkleIntensity',0)
                        mid.set_vector_parameter_value('FabricResponse',unreal.LinearColor(0,.86,.3,1))
                    target=(bc.get_socket_location('pelvis')+bc.get_socket_location('neck_01'))*.5
                    lying=pose_name=='lying'
                    offset=unreal.Vector(175,0,25) if name.endswith('side') else (unreal.Vector(0,10,175) if lying else unreal.Vector(0,175,15))
                    tgt=target;deg=0;dist=0
                    comp.set_editor_property('fov_angle',35)
                    look(target+offset,target)
                    with open(os.path.join(OUT,'pose_weights.json'),'w') as stream:json.dump({'heads':heads,'weights':weights,'angles':wrinkle_driver.angles(heads)},stream,indent=2)
                if fold_loop:
                    phase = st["i"] * math.tau / len(shots)
                    for mi in cloth_mids:
                        for side in ("L", "R"):
                            mi.set_vector_parameter_value("WrinklePhases" + side, unreal.LinearColor(phase, phase, phase, phase))
                if not cloth_qa:
                    comp.set_editor_property("fov_angle", fov)
                    look(tgt + fwd(deg) * dist + unreal.Vector(0, 0, 6), tgt)
                if hair:
                    comp.set_editor_property('capture_every_frame',True)
                st["stage"] = 1
            else:
                if hair:
                    comp.set_editor_property('capture_every_frame',False)
                shoot(name)
                st["i"] += 1
                st["stage"] = 0
            st["next"] = time.time() + (1.0 if hair else 0.3)
            if st["i"] == len(shots):
                unreal.unregister_slate_post_tick_callback(st["h"])
                cleanup()
        except Exception:
            unreal.unregister_slate_post_tick_callback(st["h"])
            cleanup(False)
            raise

    st["h"] = unreal.register_slate_post_tick_callback(tick)


try:
    run()
except Exception:
    sweep()
    raise

