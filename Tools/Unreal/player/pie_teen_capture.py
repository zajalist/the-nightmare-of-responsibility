"""Inject after free roam: bounded real-player portrait/idle evidence, no PIE start/stop or actor spawning."""
import json
import os
from pathlib import Path
import time
import traceback
import unreal

OUT = Path("P:/FoA/Saved/CharacterShots/teen_pie")
OUT.mkdir(parents=True, exist_ok=True)
include_suit = os.environ.get("FOA_INCLUDE_SUIT", "0") == "1"
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
player = unreal.GameplayStatics.get_player_character(world, 0)
pc = unreal.GameplayStatics.get_player_controller(world, 0)
assert player and pc, "Inject only after free roam starts"
parts = {c.get_name(): c for c in player.get_components_by_class(unreal.SkeletalMeshComponent)}
body, face = parts["Body"], parts["Face"]
expected_face = "/Game/FoA/Characters/Protagonist/Teen/Built_N/MHC_Face_N_Head.MHC_Face_N_Head"
expected_body = "/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/Body/SKM_MHC_Protagonist_BodyMesh.SKM_MHC_Protagonist_BodyMesh"
director_class = unreal.load_class(None, "/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C")
assert face.get_skeletal_mesh_asset().get_path_name() == expected_face, "Actual runtime pawn still has the adult face"
dna_data = next(d for d in face.get_skeletal_mesh_asset().get_editor_property("asset_user_data")
                if d.get_class().get_name() == "DNAAssetUserData")
dna_asset = dna_data.get_editor_property("dna_asset")
assert dna_asset and "/Teen/Built_N/DNA/" in dna_asset.get_path_name(), "New head must retain its actual teenage facial rig"
assert body.get_skeletal_mesh_asset().get_path_name() == expected_body, "Fixture expects starter body"
original_anim = body.get_anim_instance().get_class().get_path_name()
assert original_anim.endswith("ABP_FoAPlayer_MH_C"), original_anim
for groom in player.get_components_by_class(unreal.GroomComponent):
    if groom.get_name() in ("Hair", "Eyebrows"):
        assert "Teen/Built" in groom.get_editor_property("groom_asset").get_path_name()
        assert groom.get_editor_property("binding_asset").get_editor_property("target_skeletal_mesh") == face.get_skeletal_mesh_asset()
        assert not groom.get_editor_property("render_custom_depth")

boom = player.get_component_by_class(unreal.SpringArmComponent)
camera = player.get_component_by_class(unreal.CameraComponent)
saved = {"rotation": pc.get_control_rotation(), "arm": boom.get_editor_property("target_arm_length"),
         "target": boom.get_editor_property("target_offset"), "socket": boom.get_editor_property("socket_offset"),
         "collision": boom.get_editor_property("do_collision_test"), "fov": camera.get_editor_property("field_of_view"),
         "lag": boom.get_editor_property("enable_camera_lag"), "rotation_lag": boom.get_editor_property("enable_camera_rotation_lag")}
saved_location = player.get_actor_location()
saved_actor_rotation = player.get_actor_rotation()
initial_loadout={n:parts[n].is_visible()for n in ("Shirt","Trousers","Tie","Socks","Suit","BootsWornMesh")if n in parts}
assert not any(initial_loadout.values()) and parts["StartOutfit"].is_visible(), ("Fixture requires starter loadout",initial_loadout)
yaw = player.get_actor_rotation().yaw
forehead = face.get_socket_location("FACIAL_C_12IPV_Forehead1")
chin = face.get_socket_location("FACIAL_C_12IPV_Chin3")
face_center = (forehead + chin) * .5
body_head = body.get_socket_location("head")
assert body.get_bone_index("head") >= 0 and 120 < body_head.z < 220, ("Invalid body head", str(body_head))
# FACIAL bones can exist while RigLogic has not produced useful component-space transforms.
# First make the head visible using the animated body head, then inspect rather than aiming at the origin.
head_height = body_head.z - player.get_actor_location().z - 1.0
state = {"t0": time.time(), "handle": None, "phase": 0, "front_n": 0, "idle_n": 0,
         "shots": [], "passed": False, "face": expected_face, "body": expected_body, "body_anim": original_anim,
         "dna": dna_asset.get_path_name(), "samples": [], "sample_second": -1,
         "player_path": player.get_path_name(), "portrait_pivot_z": player.get_actor_location().z + head_height,
         "standing_location": str(player.get_actor_location()), "include_suit": include_suit,
         "suit_active": False, "suit_idle_n": 0, "frame": 0, "last_shot_frame": -100,
         "last_shot_elapsed": -100, "pending_view": None, "suit_diagnostics": {}, "initial_head_z": body_head.z, "initial_loadout":initial_loadout}


def optional_property(obj,name):
    try:
        value=obj.get_editor_property(name)
        return value.get_path_name() if isinstance(value,unreal.Object) else str(value)
    except Exception as error:
        return "unavailable:"+str(error)


def view(angle, distance, height, fov=45.0):
    # Runtime BlueprintReadWrite attributes use NotifyMode::Never; editor setters reconstruct SCS components in PIE.
    boom.target_arm_length = distance
    boom_base_height = boom.get_world_location().z - player.get_actor_location().z
    boom.target_offset = unreal.Vector(0, 0, height - boom_base_height)
    boom.socket_offset = unreal.Vector(0, 0, 0)
    boom.do_collision_test = False
    boom.enable_camera_lag = False
    boom.enable_camera_rotation_lag = False
    camera.set_field_of_view(fov)
    pc.set_control_rotation(unreal.Rotator(pitch=-3, yaw=yaw + angle, roll=0))


def shot(label):
    projection = None
    assert body.is_visible() and face.is_visible(), ("Visible character parts hidden",label)
    assert (pc.player_camera_manager.get_camera_location()-body.get_socket_location("head")).length()>50, ("Camera inside avatar",label)
    if label.startswith("front_idle_") or label == "profile":
        width,height = pc.get_viewport_size()
        head = body.get_socket_location("head")
        actual = {"forehead":face.get_socket_location("FACIAL_C_12IPV_Forehead1"),
                  "chin":face.get_socket_location("FACIAL_C_12IPV_Chin3")}
        plausible = all((v-head).length() < 25 for v in actual.values()) and 8 < (actual["forehead"]-actual["chin"]).length() < 35
        state.setdefault("landmark_samples",[]).append({"label":label,"head":str(head),
            "forehead":str(actual["forehead"]),"chin":str(actual["chin"]),"plausible":plausible,
            "indices":{n:face.get_bone_index(n) for n in ("FACIAL_C_12IPV_Forehead1","FACIAL_C_12IPV_Chin3")}})
        # The body-head target is explicit diagnostic framing until facial joints pass plausibility.
        points = actual if plausible else {"head_target":head+unreal.Vector(0,0,-1)}
        points["center"] = (actual["forehead"]+actual["chin"])*.5 if plausible else head+unreal.Vector(0,0,-1)
        projection = {"viewport":[width,height],"points":{}}
        for name,point in points.items():
            raw = pc.project_world_location_to_screen(point,True)
            screen = raw if hasattr(raw,"x") else next((v for v in (raw or []) if hasattr(v,"x")),None)
            assert screen is not None, (name,"face landmark did not project",str(raw))
            nx,ny=screen.x/width,screen.y/height
            projection["points"][name]={"world":[point.x,point.y,point.z],"screen":[screen.x,screen.y],"normalized":[nx,ny]}
            assert .05<nx<.95 and .05<ny<.95, (label,name,"cropped face landmark",nx,ny)
        cx,cy=projection["points"]["center"]["normalized"]
        assert .2<cx<.8 and .2<cy<.8, (label,"face center outside safe framing",cx,cy)
    unreal.SystemLibrary.execute_console_command(world, f"Shot filename={OUT.as_posix()}/{label}.png -nosuffix", pc)
    state["shots"].append({"label": label, "wall": time.time(),"projection":projection})
    state["last_shot_frame"] = state["frame"]
    state["last_shot_elapsed"] = time.time() - state["t0"]


def queue_view(*args):
    state["pending_view"] = args


def component_diagnostics():
    def path(obj):return obj.get_path_name() if obj else None
    def value(obj,name):
        try:
            val=obj.get_editor_property(name)
            return path(val) if isinstance(val,unreal.Object) else str(val)
        except Exception as error:return "unavailable:"+str(error)
    data={"actor_hidden":value(player,"hidden"),"camera_close":value(player,"bCameraClose"),"components":{}}
    for name in ("Body","Face","Suit","StartOutfit"):
        c=parts[name]
        origin,extent,radius=unreal.SystemLibrary.get_component_bounds(c)
        data["components"][name]={"mesh":path(c.get_skeletal_mesh_asset()),"visible":c.is_visible(),
            "bounds_origin":[origin.x,origin.y,origin.z],"bounds_extent":[extent.x,extent.y,extent.z],
            "bone_count":c.get_num_bones(),"head_index":c.get_bone_index("head"),
            "anim_instance":path(c.get_anim_instance()), "anim_class":value(c,"anim_class"),
            "post_process_class":value(c.get_skeletal_mesh_asset(),"post_process_anim_blueprint"),
            "post_process_instance":path(c.get_post_process_instance()),
            "post_process_disabled":optional_property(c,"disable_post_process_blueprint"),
            "tick_option":value(c,"visibility_based_anim_tick_option"),
            "head_world":str(c.get_socket_location("head")),
            "materials":[path(c.get_material(i)) for i in range(c.get_num_materials())],
            **{flag:value(c,flag) for flag in ("hidden_in_game","owner_no_see","render_in_main_pass", "bounds_scale",
                 "leader_pose_component","use_attach_parent_bound","use_bounds_from_leader_pose_component",
                 "consider_all_bodies_for_bounds","forced_lod_model")}}
    return data


def assert_pose_scale():
    for name in ("Body","Face","Suit"):
        c=parts[name]
        if name=="Suit" and not c.is_visible():continue
        head=c.get_socket_location("head")
        assert abs(head.z-state["initial_head_z"]) < 40, (name,"head pose exploded",str(head),state["initial_head_z"])
    _,extent,_=unreal.SystemLibrary.get_component_bounds(body)
    assert extent.z*2<250, ("Body bounds exploded",str(extent))


def finish(error=None):
    cleanup_errors=[]
    def cleanup(label,action):
        try:action()
        except Exception as problem:cleanup_errors.append(label+":"+str(problem))
    try:
        if state["suit_active"]:
            cleanup("restore clothes",lambda:player.call_method("UnequipAll"))
            state["suit_active"] = False
        cleanup("restore player",lambda:player.teleport(saved_location,saved_actor_rotation))
        cleanup("restore control",lambda:pc.set_control_rotation(saved["rotation"]))
        for name,value in (("target_arm_length",saved["arm"]),("target_offset",saved["target"]),
                           ("socket_offset",saved["socket"]),("do_collision_test",saved["collision"]),
                           ("enable_camera_lag",saved["lag"]),("enable_camera_rotation_lag",saved["rotation_lag"])):
            cleanup(name,lambda n=name,v=value:setattr(boom,n,v))
        cleanup("restore fov",lambda:camera.set_field_of_view(saved["fov"]))
    finally:
        if state["handle"] is not None:
            cleanup("unregister callback",lambda:unreal.unregister_slate_post_tick_callback(state["handle"]))
        state["handle"] = None
        state["cleanup_errors"] = cleanup_errors
        state["error"] = str(error) if error else "; ".join(cleanup_errors) if cleanup_errors else None
        if state["error"]:state["passed"]=False
        state["elapsed"] = time.time() - state["t0"]
        OUT.parent.joinpath("teen_pie.json").write_text(json.dumps(state,indent=2))
        unreal.log("TEEN actual player capture " + ("PASS" if state["passed"] else "FAIL "+str(state["error"])))


def tick(_dt):
    elapsed = time.time() - state["t0"]
    try:
        state["frame"] += 1
        if state["pending_view"] and state["frame"]-state["last_shot_frame"]>=3 and elapsed-state["last_shot_elapsed"]>=.12:
            view(*state["pending_view"])
            state["pending_view"] = None
        def path(obj):
            return obj.get_path_name() if obj else None
        def observe():
            instance = body.get_anim_instance()
            current_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
            current_player = unreal.GameplayStatics.get_player_character(current_world, 0) if current_world else None
            director = unreal.GameplayStatics.get_actor_of_class(current_world, director_class) if current_world else None
            beat = director.get_editor_property("Beat") if director else None
            sequence = director.get_editor_property("SeqPlayer") if director else None
            gi = unreal.GameplayStatics.get_game_instance(current_world) if current_world else None
            return {"elapsed": elapsed, "world": path(current_world), "player": path(current_player),
                    "face_mesh": path(face.get_skeletal_mesh_asset()), "body_mesh": path(body.get_skeletal_mesh_asset()),
                    "body_anim": path(instance.get_class()) if instance else None,
                    "body_mode": str(body.get_editor_property("animation_mode")),
                    "body_anim_class": path(body.get_editor_property("anim_class")),
                    "view_target": path(pc.get_view_target()), "camera": camera.get_path_name(),
                    "camera_active": camera.is_active(), "boom": boom.get_path_name(),
                    "boom_length": boom.get_editor_property("target_arm_length"),
                    "control_yaw": pc.get_control_rotation().yaw,
                    "camera_location": str(pc.player_camera_manager.get_camera_location()),
                    "boom_location":str(boom.get_world_location()),
                    "face_post_process_instance":path(face.get_post_process_instance()),
                    "face_post_process_disabled":optional_property(face,"disable_post_process_blueprint"),
                    "facial_joints":{n:str(face.get_socket_location(n))for n in ("FACIAL_C_FacialRoot","FACIAL_C_Jaw","FACIAL_L_Eye","FACIAL_R_Eye","FACIAL_C_ForeheadSkin","FACIAL_C_Chin3","FACIAL_C_12IPV_Forehead1","FACIAL_C_12IPV_Chin3")},
                    "same_player": current_player == player,
                    "game_time": unreal.GameplayStatics.get_time_seconds(current_world) if current_world else None,
                    "time_dilation": unreal.GameplayStatics.get_global_time_dilation(current_world) if current_world else None,
                    "beat_id": str(beat.get_editor_property("Id")) if beat else None,
                    "day_count": gi.get_editor_property("DayCount") if gi else None,
                    "wake_sequence_playing": sequence.is_playing() if sequence else None}
        if int(elapsed) != state["sample_second"]:
            state["sample_second"] = int(elapsed)
            state["samples"].append(observe())
        if elapsed > 23:
            raise AssertionError("Teen capture exceeded bounded runtime")
        if state["phase"] == 0:
            assert player.teleport(unreal.Vector(0,-40,saved_location.z),saved_actor_rotation), "No clear central portrait spot"
            state["standing_location"]=str(player.get_actor_location())
            view(180, 100, head_height)
            state["phase"] = 1
        elif state["phase"] == 1 and elapsed >= 1 + state["front_n"] * .30:
            shot(f"front_idle_{state['front_n']:02d}")
            state["front_n"] += 1
            if state["front_n"] == 12:
                state["phase"] = 2
        elif state["phase"] == 2 and elapsed >= 5:
            view(90, 100, head_height)
            state["phase"] = 3
        elif state["phase"] == 3 and elapsed >= 6:
            shot("profile")
            queue_view(0, 145, 0, 105.0)
            state["phase"] = 4
        elif state["phase"] == 4 and elapsed >= 8:
            shot("rear_full")
            queue_view(180, 145, 0, 105.0)
            state["phase"] = 5
        elif state["phase"] == 5 and elapsed >= 10 + state["idle_n"] * .3:
            shot(f"full_idle_{state['idle_n']:02d}")
            state["idle_n"] += 1
            if state["idle_n"] == 12:
                state["phase"] = 6
        elif state["phase"] == 6 and elapsed >= 15:
            observed = observe()
            state["final_observed"] = observed
            state["suit_diagnostics"]["portrait_end"] = component_diagnostics()
            assert_pose_scale()
            assert observed["face_mesh"] == expected_face, observed
            assert observed["body_mesh"] == expected_body, observed
            assert observed["body_anim"] == original_anim, observed
            state["weighted_face_pose_plausible"] = len(state.get("landmark_samples",[]))>=13 and all(p["plausible"]for p in state["landmark_samples"])
            state["portrait_passed"] = state["weighted_face_pose_plausible"]
            assert observed["same_player"] and observed["camera_active"], observed
            if include_suit:
                state["suit_diagnostics"]["before_equip"] = component_diagnostics()
                state["suit_validation"] = "Direct visual Equip API fixture; no inventory/reward pacing assertion"
                player.call_method("Equip", ("Suit",))
                state["suit_active"] = True
                view(180,145,0,105.0)
                state["phase"] = 7
            else:
                assert state["portrait_passed"], "Weighted facial poses never became plausible; diagnostic fallback frames are not a face-rig PASS"
                state["passed"] = True
                finish()
        elif state["phase"] == 7 and elapsed >= 16:
            assert body.get_skeletal_mesh_asset().get_name() == "SK_FoA_Body_Suited"
            assert body.get_anim_instance().get_class().get_path_name() == original_anim
            assert parts["Suit"].is_visible() and not parts["StartOutfit"].is_visible()
            state["suit_mesh"] = parts["Suit"].get_skeletal_mesh_asset().get_path_name()
            state["suited_body"] = body.get_skeletal_mesh_asset().get_path_name()
            state["suit_diagnostics"]["after_equip"] = component_diagnostics()
            assert_pose_scale()
            shot("suit_front")
            queue_view(0,145,0,105.0)
            state["phase"] = 8
        elif state["phase"] == 8 and elapsed >= 17:
            shot("suit_rear")
            queue_view(180,72,38,50.0)
            state["phase"] = 9
        elif state["phase"] == 9 and elapsed >= 18:
            shot("suit_tie")
            queue_view(180,145,0,105.0)
            state["phase"] = 10
        elif state["phase"] == 10 and elapsed >= 18.8 + state["suit_idle_n"] * .3:
            if state["suit_idle_n"] == 3:state["suit_diagnostics"]["suit_idle"] = component_diagnostics()
            assert_pose_scale()
            shot(f"suit_idle_{state['suit_idle_n']:02d}")
            state["suit_idle_n"] += 1
            if state["suit_idle_n"] == 8:
                state["phase"] = 11
        elif state["phase"] == 11 and elapsed >= 21.3:
            player.call_method("UnequipAll")
            state["suit_active"] = False
            assert body.get_skeletal_mesh_asset().get_path_name() == expected_body
            assert body.get_anim_instance().get_class().get_path_name() == original_anim
            assert not parts["Suit"].is_visible() and parts["StartOutfit"].is_visible()
            state["suit_restored"] = True
            assert state["portrait_passed"], "Weighted facial poses never became plausible; suit evidence captured separately"
            state["passed"] = True
            finish()
    except Exception as error:
        state["traceback"] = traceback.format_exc()
        finish(error)


state["handle"] = unreal.register_slate_post_tick_callback(tick)
print("TEEN actual-player capture scheduled", 22 if include_suit else 15, "seconds; original body/camera/position restored afterward")
