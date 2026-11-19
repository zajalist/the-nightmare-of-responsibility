"""Independent UE CPU-skin probe. No Blender import, coordinate mirror, or twin replay."""
import importlib
import math
from pathlib import Path

import unreal
import measure_grip_pose
importlib.reload(measure_grip_pose)

V = unreal.Vector
Q = unreal.Quat
CS = unreal.BoneSpaces.COMPONENT_SPACE
AP = unreal.AnimPoseExtensions
W = unreal.AnimPoseSpaces.WORLD
L = unreal.AnimPoseSpaces.LOCAL
DIGITS = ('index', 'middle', 'ring', 'pinky', 'thumb')


def vec(v):
    return [v.x, v.y, v.z]


def mean(vs):
    assert vs
    return sum(vs, V()) / len(vs)


def angle(a, b):
    return math.degrees(math.acos(max(-1, min(1, a.normal().dot(b.normal())))))


def spawn(world, cls, label, transform):
    gs = unreal.get_default_object(unreal.GameplayStatics)
    actor = gs.call_method('BeginDeferredActorSpawnFromClass', (world, cls.static_class(), transform,
        unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN, None, unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    actor = gs.call_method('FinishSpawningActor', (actor, transform, unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    actor.set_actor_label('TMP_anim_' + label)
    return actor


def skin(component):
    mesh = unreal.DynamicMesh()
    opts = unreal.GeometryScriptCopyMeshFromComponentOptions()
    opts.requested_lod = unreal.GeometryScriptMeshReadLOD(lod_type=unreal.GeometryScriptLODType.RENDER_DATA, lod_index=0)
    # UE drops the skin-weight attribute when hidden sections shorten its weight array.
    # Restore visibility in this same callback, before any rendered frame.
    shown = [component.is_material_section_shown(i, 0) for i in range(len(component.get_material_slot_names()))]
    try:
        component.show_all_material_sections(0)
        _, _, outcome = unreal.GeometryScript_SceneUtils.copy_mesh_from_component(component, mesh, opts, True)
    finally:
        for i, visible in enumerate(shown):
            component.show_material_section(i, 0, visible, 0)
    assert outcome == unreal.GeometryScriptOutcomePins.SUCCESS, str(outcome)
    _, positions, gaps = unreal.GeometryScript_MeshQueries.get_all_vertex_positions(mesh, False)
    _, normals, valid, ngaps = unreal.GeometryScript_Normals.get_mesh_per_vertex_normals(mesh, True)
    assert valid and not gaps and not ngaps, 'CPU mesh has missing vertices or normals'
    return mesh, list(unreal.GeometryScript_List.convert_vector_list_to_array(positions)), list(unreal.GeometryScript_List.convert_vector_list_to_array(normals))


def surface(component):
    mesh = unreal.DynamicMesh()
    _,_,outcome = unreal.GeometryScript_SceneUtils.copy_mesh_from_component(component,mesh,unreal.GeometryScriptCopyMeshFromComponentOptions(),False)
    assert outcome == unreal.GeometryScriptOutcomePins.SUCCESS
    _,positions,gaps = unreal.GeometryScript_MeshQueries.get_all_vertex_positions(mesh,False)
    _,triangles,tgaps = unreal.GeometryScript_MeshQueries.get_all_triangle_indices(mesh,False)
    assert not gaps and not tgaps
    positions = unreal.GeometryScript_List.convert_vector_list_to_array(positions)
    triangles = unreal.GeometryScript_List.convert_triangle_list_to_array(triangles)
    data = dict(mesh=component.static_mesh.get_path_name(),positions=[vec(p) for p in positions],triangles=[vec(t) for t in triangles])
    assert positions and all(0 <= i < len(positions) for t in data['triangles'] for i in t)
    return data


class Probe:
    def __init__(self, world, body, side):
        self.world, self.body, self.side = world, body, side
        self.made = []
        self.ref = AP.get_reference_pose(body.get_skinned_asset().get_editor_property('skeleton'))
        self.host = spawn(world, unreal.Actor, 'curl_probe', unreal.Transform(location=V(0, 0, 3000)))
        self.made.append(self.host)
        self.clone = self.host.call_method('AddComponentByClass', (unreal.PoseableMeshComponent.static_class(), False, unreal.Transform(), False))
        self.clone.set_skinned_asset_and_update(body.get_skinned_asset(), True)
        self.clone.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        self.host.set_actor_location(V(0, 0, 3000), False, True)
        self.rows = {}

    def ref_bone(self, bone, space=W):
        return AP.get_bone_pose(self.ref, bone, space)

    def prepare(self):
        mesh, self.rest_pos, normals = skin(self.clone)
        hand = self.clone.get_socket_location('hand_' + self.side)
        middle = self.clone.get_socket_location('middle_01_' + self.side)
        centre = hand + (middle - hand) * .55
        # Orient the metacarpal plane toward the thumb pad, independently of any baked curl sign.
        index, pinky = [self.clone.get_socket_location(f'{d}_01_{self.side}') for d in ('index','pinky')]
        forward = self.clone.get_socket_location('middle_02_'+self.side)-middle
        self.palm_ref = (pinky-index).cross(forward).normal()
        if (self.clone.get_socket_location('thumb_03_'+self.side)-(index+pinky)*.5).dot(self.palm_ref) < 0:
            self.palm_ref *= -1
        groups = {d: [] for d in DIGITS}
        palm = []
        self.hand_ids, weights = [], []
        for i, point in enumerate(self.rest_pos):
            if (point - hand).length() > 19:
                continue
            _, bw, valid = unreal.GeometryScript_BoneWeights.get_largest_vertex_bone_weight(mesh, i)
            assert valid, 'native CPU copy lost skin weights'
            bone = str(self.clone.get_bone_name(bw.bone_index))
            if bone.endswith('_' + self.side) and (bone.startswith(('hand_', 'lowerarm_')) or bone.split('_')[0] in DIGITS):
                _, ws, valid = unreal.GeometryScript_BoneWeights.get_vertex_bone_weights(mesh, i)
                assert valid
                self.hand_ids.append(i)
                weights.append([[str(self.clone.get_bone_name(v.bone_index)), v.weight] for v in ws])
            if bone == 'hand_' + self.side and normals[i].dot(self.palm_ref) > .65:
                palm.append(i)
            for d in DIGITS:
                if bone == f'{d}_03_{self.side}':
                    groups[d].append(i)
        self.palm_ids = sorted(palm, key=lambda i: (self.rest_pos[i] - centre).length())[:12]
        assert len(self.palm_ids) >= 6, 'no palmar surface patch'
        self.palm_ref = mean([normals[i] for i in self.palm_ids]).normal()
        self.tip_ids = {}
        for d, ids in groups.items():
            assert len(ids) >= 8, (d, len(ids))
            a, b = [self.clone.get_socket_location(f'{d}_0{j}_{self.side}') for j in (2, 3)]
            direction = (b - a).normal()
            self.tip_ids[d] = sorted(ids, key=lambda i: (self.rest_pos[i] - b).dot(direction), reverse=True)[:8]
        self.base_tips = {d: mean([self.rest_pos[i] for i in ids]) for d, ids in self.tip_ids.items()}
        thumb_dir = (self.ref_bone('thumb_03_'+self.side).translation-self.ref_bone('thumb_02_'+self.side).translation).normal()
        thumb_normal = (self.palm_ref-thumb_dir*self.palm_ref.dot(thumb_dir)).normal()
        self.thumb_pad_ids = {i for i in groups['thumb'] if normals[i].dot(thumb_normal) > .65}
        assert len(self.thumb_pad_ids) >= 8, 'no thumb pad surface patch'
        self.rows['reference'] = dict(palm_vertex_ids=self.palm_ids, palm_normal=vec(self.palm_ref),
            tip_vertex_ids=self.tip_ids, vertex_count=len(self.rest_pos), source='UE GetCPUSkinnedVertices render LOD 0')
        from pie_pose_capture import _xf
        self.fixture = dict(ids=self.hand_ids, weights=weights, palm_ids=self.palm_ids, tip_ids=self.tip_ids,thumb_pad_ids=sorted(self.thumb_pad_ids),
            positions=[vec(self.rest_pos[i] - self.clone.get_world_location()) for i in self.hand_ids],
            normals=[vec(normals[i]) for i in self.hand_ids],
            local={str(b):_xf(self.ref_bone(b,L)) for b in AP.get_bone_names(self.ref)},
            world={str(b):_xf(self.ref_bone(b)) for b in AP.get_bone_names(self.ref)},
            parents={str(b):str(self.clone.get_parent_bone(b)) for b in AP.get_bone_names(self.ref)})

    def measure_live(self, phone, eye, kind='phone'):
        self.kind = kind
        _, points, normals = skin(self.body)
        assert len(points) == len(self.rest_pos), 'reference and live render topology differ'
        palm_n = mean([normals[i] for i in self.palm_ids]).normal()
        palm_c = mean([points[i] for i in self.palm_ids])
        back = phone.get_world_transform().rotation.rotate_vector(V(0, 0, 1) if kind == 'phone' else V(0,1,0)).normal()
        target = phone.get_world_transform().transform_location(V(-4.5,0,0)) if kind == 'key' else phone.get_world_location()
        if kind == 'screwdriver':
            vertices = surface(phone)['positions']
            radius2 = max(x*x+y*y for x,y,z in vertices)
            handle = [V(*p) for p in vertices if p[0]**2+p[1]**2 > .65**2*radius2]
            self.handle_centre = mean(handle)
            target = phone.get_world_transform().transform_location(self.handle_centre)
        self.rows['live'] = dict(palm_normal=vec(palm_n), palm_centre=vec(palm_c), phone_back_normal=vec(back),
            palm_against_back_deg=angle(palm_n, back * -1), screen_to_eye_deg=angle(back * -1, eye - target),
            palm_to_phone_dot=palm_n.dot((target - palm_c).normal()),
            palm_vertices_world=[vec(points[i]) for i in self.palm_ids],
            tips_world={d:vec(mean([points[i] for i in ids])) for d,ids in self.tip_ids.items()},
            bones={b:vec(self.body.get_socket_location(b)) for b in ['hand_'+self.side]+[f'{d}_0{j}_{self.side}' for d in DIGITS for j in (1,2,3)]})
        self.rows['live']['tips_phone_local'] = {d:vec(phone.get_world_transform().inverse_transform_location(
            mean([points[i] for i in ids]))) for d,ids in self.tip_ids.items()}
        self.rows['live']['body_mesh'] = self.body.get_skinned_asset().get_path_name()
        self.rows['live']['hand_world_rotation'] = str(self.body.get_socket_rotation('hand_'+self.side))
        self.rows['live']['object_kind'] = kind
        wrist = self.body.get_socket_location('hand_'+self.side)
        self.rows['live']['wrist_deg'] = angle(wrist-self.body.get_socket_location('lowerarm_'+self.side),
            self.body.get_socket_location('middle_01_'+self.side)-wrist)
        if kind != 'phone':
            Path(f'P:/FoA/Saved/AnimShots/review/{kind}_surface.json').write_text(__import__('json').dumps(surface(phone)))
        thumb_normal = mean([normals[i] for i in self.thumb_pad_ids]).normal()
        self.rows['live']['thumb_pad_normal'] = vec(thumb_normal)
        self.rows['live']['thumb_pad_to_glass_deg'] = angle(thumb_normal,back)
        if kind == 'phone':
            self.rows['live']['phone_hand_in_eye'] = str(self.body.get_owner().get_editor_property('PhoneHandInEye'))
            self.rows['live']['runtime_hand_rotation_target'] = str(self.body.get_anim_instance().get_editor_property('PhoneHandRotation'))
            self.rows['live']['hold_state'] = self.hold_state(phone)
        from pie_pose_capture import local_pose, _xf
        self.fixture['live'] = dict(positions=[vec(points[i]) for i in self.hand_ids], local=local_pose(self.body),
            body_world=_xf(self.body.get_world_transform()), phone_world=_xf(phone.get_world_transform()))
        self.rows['live'].update(measure_grip_pose.finger_limits(self.fixture['live']['local'],self.fixture['local'],self.side))
        self.rows['live'].update(measure_grip_pose.wrist_rotation(self.fixture['live']['local'],self.fixture['local'],self.side))
        Path(getattr(self,'fixture_path',f'P:/FoA/Saved/AnimShots/review/ue_hand_{self.side}_fixture.json')).write_text(__import__('json').dumps(self.fixture))
        distances = {}
        mesh_distances = {}
        by_bone = {}
        spatial = unreal.GeometryScript_MeshSpatial
        obj_mesh = unreal.DynamicMesh()
        opts = unreal.GeometryScriptCopyMeshFromComponentOptions()
        _,_,outcome = unreal.GeometryScript_SceneUtils.copy_mesh_from_component(phone,obj_mesh,opts,True)
        assert outcome == unreal.GeometryScriptOutcomePins.SUCCESS
        _,bvh = spatial.build_bvh_for_mesh(obj_mesh)
        query = unreal.GeometryScriptSpatialQueryOptions()
        thumb_front_z = []
        thumb_pad_distances = []
        projected_thumb=[]
        eye_local=phone.get_world_transform().inverse_transform_location(eye)
        for i, ws in zip(self.hand_ids,self.fixture['weights']):
            bone = max(ws,key=lambda pair:pair[1])[0]
            digit = bone.split('_')[0]
            if digit not in DIGITS and digit != 'hand':
                continue
            point = phone.get_world_transform().inverse_transform_location(points[i])
            if kind=='phone' and digit=='thumb' and point.z<-.53:
                projected=eye_local+(point-eye_local)*((-.53-eye_local.z)/(point.z-eye_local.z))
                projected_thumb.append(vec(projected))
            _,hit,outcome = spatial.find_nearest_point_on_mesh(obj_mesh,bvh,points[i],query)
            assert outcome == unreal.GeometryScriptSearchOutcomePins.FOUND
            _,inside,_ = spatial.is_point_inside_mesh(obj_mesh,bvh,points[i],query)
            actual_distance = (points[i]-hit.position).length()*(-1 if inside else 1)
            mesh_distances[digit] = min(mesh_distances.get(digit,1e9),actual_distance*10)
            if kind == 'phone':
                d = [abs(v)-h for v,h in zip(vec(point),(7.35,3.55,.5))]
                distance = math.sqrt(sum(max(v,0)**2 for v in d))+min(max(d),0)
            else:
                distance = actual_distance
            distances[digit] = min(distances.get(digit,1e9),distance*10)
            by_bone[bone] = min(by_bone.get(bone,1e9),distance*10)
            if i in self.thumb_pad_ids:
                thumb_front_z.append(point.z)
                thumb_pad_distances.append(actual_distance*10)
        self.rows['live']['nominal_box_clearance_mm' if kind == 'phone' else 'skin_clearance_mm'] = distances
        self.rows['live']['actual_mesh_clearance_mm'] = mesh_distances
        self.rows['live']['actual_thumb_pad_gap_mm'] = min(thumb_pad_distances)
        self.rows['live']['nominal_box_clearance_by_bone_mm' if kind == 'phone' else 'skin_clearance_by_bone_mm'] = by_bone
        if kind == 'phone':
            self.rows['live']['thumb_pad_gap_mm'] = (-max(thumb_front_z)-.5)*10
            self.rows['live']['thumb_screen_overlap_vertices']=sum(abs(x)<6.835 and abs(y)<3.30 for x,y,z in projected_thumb)
            # One physical screen pixel is .01222cm; keep the raw edge count too.
            self.rows['live']['thumb_screen_interior_overlap_vertices']=sum(abs(x)<6.835-.01222 and abs(y)<3.30-.01222 for x,y,z in projected_thumb)
            self.rows['live']['thumb_projected_front_min_y']=min((p[1] for p in projected_thumb),default=None)
            self.rows['live']['phone_collision']={name:str(phone.get_collision_response_to_channel(channel))
                for name,channel in (('Pawn',unreal.CollisionChannel.PAWN),('Camera',unreal.CollisionChannel.CAMERA))}
        self.rows['live']['flipped_screen_control_deg'] = angle(back,eye-target)

    def bend_test(self, digit, mode, joint=2):
        for d in DIGITS:
            for j in (2,3):
                self.clone.reset_bone_transform_by_name(f'{d}_0{j}_{self.side}')
        bone = f'{digit}_0{joint}_{self.side}'
        ref_local = self.ref_bone(bone, L).rotation
        a = self.ref_bone(bone)
        forward = self.ref_bone(f'{digit}_03_{self.side}').translation-a.translation if joint == 2 else a.translation-self.ref_bone(f'{digit}_02_{self.side}').translation
        axis = unreal.MathLibrary.quat_inversed(a.rotation).rotate_vector(forward.cross(self.palm_ref).normal())
        if mode == 'negative_control':
            axis *= -1
        if mode == 'baked_curl':
            held = Q(*self.fixture['live']['local'][bone][1])
            delta = unreal.MathLibrary.multiply_quat_quat(unreal.MathLibrary.quat_inversed(ref_local), held)
            sign = 1 if delta.w >= 0 else -1
            axis = V(delta.x * sign, delta.y * sign, delta.z * sign).normal()
        s = math.sin(math.radians(10) / 2)
        delta = Q(axis.x*s, axis.y*s, axis.z*s, math.cos(math.radians(10)/2))
        parent = str(self.clone.get_parent_bone(bone))
        local = unreal.MathLibrary.multiply_quat_quat(ref_local, delta)
        world_q = unreal.MathLibrary.multiply_quat_quat(self.ref_bone(parent).rotation, local)
        self.clone.set_bone_rotation_by_name(bone, world_q.rotator(), CS)
        self.pending = digit, mode, vec(axis), joint

    def read_bend(self):
        digit, mode, axis, joint = self.pending
        _, points, _ = skin(self.clone)
        moved = mean([points[i] for i in self.tip_ids[digit]]) - self.base_tips[digit]
        self.rows.setdefault('curl_tests', []).append(dict(digit=digit, joint=joint, mode=mode, local_axis=axis,
            fingertip_motion_cm=vec(moved), toward_palm_cm=moved.dot(self.palm_ref)))

    def hold_state(self, phone):
        player, anim = self.body.get_owner(), self.body.get_anim_instance()
        return dict(open=phone.get_owner().get_editor_property('bOpen'),
            player={k:player.get_editor_property(k) for k in ('PhoneRaise','PhoneRaiseTarget','PhoneTapAlpha','PhoneTapTarget')},
            anim={k:anim.get_editor_property(k) for k in ('PhoneGripWeight','PhoneIKWeight','PhoneGripTime')})

    def capture(self, phone, label, path, base_color=False):
        xf = phone.get_world_transform()
        back, left = xf.rotation.rotate_vector(V(0,0,1)), xf.rotation.rotate_vector(V(0,1,0))
        centre = (phone.get_world_location() + self.body.get_socket_location('hand_'+self.side)) * .5
        pos = centre + back * (40 if label == 'back' else -40) + left * 18
        if label == 'side':
            pos = centre + back*10 - left*40
        if self.side == 'r':
            centre = (phone.get_world_transform().transform_location(V(-4.5,0,0))+self.body.get_socket_location('hand_r'))*.5
            forward = xf.rotation.rotate_vector(V(1,0,0))
            pos = centre-forward*30+left*(30 if label != 'back' else -30)+back*12
            if label == 'back':
                pos = centre-forward*10-left*22+back*25
            if getattr(self,'kind','') == 'screwdriver':
                centre = (xf.transform_location(self.handle_centre)+self.body.get_socket_location('hand_r'))*.5
                pos = centre + xf.rotation.rotate_vector(V(28,24 if label == 'back' else -24,-18))
        transform = unreal.Transform(location=pos, rotation=unreal.MathLibrary.find_look_at_rotation(pos, centre))
        camera = spawn(self.world, unreal.SceneCapture2D, 'phone_'+label, transform)
        self.made.append(camera)
        capture = camera.capture_component2d
        rt = unreal.RenderingLibrary.create_render_target2d(self.world, 960, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        capture.texture_target = rt
        capture.capture_source = unreal.SceneCaptureSource.SCS_BASE_COLOR if base_color else unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
        capture.capture_every_frame = False
        capture.capture_on_movement = False
        capture.always_persist_rendering_state = True
        capture.fov_angle = 45
        if not base_color:
            # Match the room's Lumen lighting; SceneCapture otherwise loses its indirect light.
            settings = capture.post_process_settings
            settings.override_dynamic_global_illumination_method = True
            settings.dynamic_global_illumination_method = unreal.DynamicGlobalIlluminationMethod.LUMEN
            settings.override_reflection_method = True
            settings.reflection_method = unreal.ReflectionMethod.LUMEN
            capture.post_process_settings = settings
        for _ in range(1 if base_color else 24):
            capture.capture_scene()
        path = Path(path)
        unreal.RenderingLibrary.export_render_target(self.world, rt, str(path.parent), path.name)
        camera.destroy_actor()
        self.made.remove(camera)

    def close(self):
        for actor in self.made:
            if unreal.SystemLibrary.is_valid(actor):
                actor.destroy_actor()
        self.made.clear()
