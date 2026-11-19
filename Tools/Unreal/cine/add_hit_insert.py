"""LS_WakeUp: a true insert for the hit (main's direction, 2026-11-09). Re-runnable: replaces its own camera.
Inside the medium insert (Cam_Insert, 11.37-15.0 s) the cut goes to Cam_Hit from 12.00 to 14.07 s (frames 360-422):
low and close on the nightstand top, 50 mm f/5.6, about 87 cm from the clock and 28 cm above the table, the clock
about 40% of the frame height, so the juddering clock holds for 0.33 s, the palm drops in from the top of frame, lands (12.47), and
the clock crumbles into its pile (dissolve ends 13.67), the hand holds in the sand and lifts out; then back to Cam_Insert
for the sit. v3 impact (main): a 4-frame camera kick at contact (frame 374: a small push and dip, then a damped shake) and
a long-shutter motion blur on this camera so the last frames of the strike smear.
Camera: on the room side, perpendicular to his reach, with a 3 cm eased push for life. His body stays out of frame (only
the arm enters, from the upper left); the headboard and the east wall sit soft behind the clock.
  $env:HAYBA_AGENT_ID='anim'; $env:FOA_AREAS='Cinematics'; $env:FOA_ACTORS_NEW='CINE_'; python Tools/Unreal/ue_remote.py Tools/Unreal/cine/add_hit_insert.py"""
import json
import math

import unreal

SEQ = '/Game/FoA/Cinematics/LS_WakeUp'
T0, T1 = 360, 422
CONTACT = 374  # 12.47 s: the palm meets the lid
LES = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)  # spawnable conversion
DU = unreal.MovieSceneTimeUnit.DISPLAY_RATE
SMART = unreal.MovieSceneKeyInterpolation.SMART_AUTO
place = json.load(open('P:/FoA/Saved/WakeUp/placement.json'))
lid = place['edge']['clock']  # palm contact point: the clock mesh's geometric top
aim = (lid[0], lid[1], lid[2] - 12.0)
# v2 framing: from the room side at bearing 156.5 deg from the clock, perpendicular to his line to it, so his body sits
# 36 deg off axis (outside the 50 mm frame) and only the arm enters, from the upper left. (UE: +Y is screen right.)
_b = math.radians(156.5)
start = (lid[0] + 87.0 * math.cos(_b), lid[1] + 87.0 * math.sin(_b), 108.0)
end = (lid[0] + 84.0 * math.cos(_b), lid[1] + 84.0 * math.sin(_b), 107.6)


def rot(src, dst):
    d = [b - a for a, b in zip(src, dst)]
    yaw = math.degrees(math.atan2(d[1], d[0]))
    pitch = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    return pitch, yaw


seq = unreal.load_asset(SEQ)
assert seq.get_playback_end() == 573, 'expects the v4 cut (573 frames)'
for b in list(seq.get_bindings()):  # re-runnable: drop the previous Cam_Hit and its key light
    if str(b.get_display_name()) in ('Cam_Hit', 'L6_HitKey'):
        b.remove()
cut = next(t for t in seq.get_tracks() if t.get_class().get_name() == 'MovieSceneCameraCutTrack')
for s in list(cut.get_sections()):  # and its cut sections (any earlier T1): re-merge the medium insert first
    if T0 <= s.get_start_frame() < 450 and s.get_end_frame() <= 450:
        cut.remove_section(s)
ins = next(s for s in cut.get_sections() if s.get_start_frame() == 341)
ins_id = ins.get_camera_binding_id()

LSB = unreal.LevelSequenceEditorBlueprintLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LSB.close_level_sequence()
LSB.open_level_sequence(seq)  # spawnable conversion needs the sequence open in Sequencer (as build_ls_wakeup does)
p0, y0 = rot(start, aim)
actor = EAS.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(*start), unreal.Rotator(roll=0.0, pitch=p0, yaw=y0))
actor.set_actor_label('CINE_Hit')
cc = actor.get_cine_camera_component()
fb = cc.get_editor_property('filmback')
fb.set_editor_property('sensor_width', 36.0)
fb.set_editor_property('sensor_height', 20.25)
cc.set_editor_property('filmback', fb)
fs = cc.get_editor_property('focus_settings')
fs.set_editor_property('focus_method', unreal.CameraFocusMethod.MANUAL)
fs.set_editor_property('manual_focus_distance', math.dist(start, aim))
cc.set_editor_property('focus_settings', fs)
cc.set_editor_property('current_focal_length', 50.0)
cc.set_editor_property('current_aperture', 5.6)
pp = cc.get_editor_property('post_process_settings')  # a long shutter: the strike's last frames smear
for k, v in (('motion_blur_amount', 1.0), ('motion_blur_max', 12.0)):
    pp.set_editor_property('override_' + k, True)
    pp.set_editor_property(k, v)
cc.set_editor_property('post_process_settings', pp)
cam = seq.add_possessable(actor)
for t in list(cam.get_tracks()):
    if t.get_class().get_name() == 'MovieScene3DTransformTrack':
        cam.remove_track(t)
sec = cam.add_track(unreal.MovieScene3DTransformTrack).add_section()
sec.set_range(0, seq.get_playback_end())
ch = {str(c.channel_name): c for c in sec.get_all_channels()}
# The camera kick at contact, offsets from the eased push: frame: (forward, right, up cm, pitch, roll deg).
# v2 (main, hit5): bigger, not longer, so it reads at 30 fps.
KICK = {CONTACT + 1: (2.9, 0.0, -1.6, -1.45, 0.0), CONTACT + 2: (1.6, -0.9, 0.55, 0.65, 0.9),
        CONTACT + 3: (0.7, 0.55, -0.2, -0.2, -0.45)}


def base(f):  # the two-key SMART_AUTO push is a smoothstep with flat end tangents
    s = min(max((f - T0) / (T1 - T0), 0.0), 1.0)
    s = s * s * (3 - 2 * s)
    return tuple(a + (b - a) * s for a, b in zip(start, end))


assert T0 < CONTACT - 1 and CONTACT + 5 < T1
LIN = unreal.MovieSceneKeyInterpolation.LINEAR
for f in (T0, CONTACT - 1, CONTACT, *KICK, CONTACT + 5, T1):
    loc = base(f)
    pitch, yaw = rot(loc, aim)
    fw, rt, up, dp, roll = KICK.get(f, (0.0,) * 5)
    y = math.radians(yaw)
    fwd, right = (math.cos(y), math.sin(y)), (-math.sin(y), math.cos(y))  # UE +Y is screen right at yaw 0
    loc = (loc[0] + fw * fwd[0] + rt * right[0], loc[1] + fw * fwd[1] + rt * right[1], loc[2] + up)
    for n, v in (('Location.X', loc[0]), ('Location.Y', loc[1]), ('Location.Z', loc[2]),
                 ('Rotation.X', roll), ('Rotation.Y', pitch + dp), ('Rotation.Z', yaw)):
        ch[n].add_key(unreal.FrameNumber(f), v, 0.0, DU, LIN if CONTACT <= f <= CONTACT + 3 else SMART)

out = LES.convert_to_spawnable(cam)
cam = out[0] if out else cam
cam.set_display_name('Cam_Hit')
if unreal.SystemLibrary.is_valid(actor) and not actor.is_actor_being_destroyed():
    EAS.destroy_actor(actor)  # Sequencer normally removes it
# L6_HitKey: the dial's glow seen up close. A small shadowless point light 25 cm in front of the clock toward the camera,
# level with the lid, short radius so only the clock, the palm and the pile catch it; alive only for the true insert.
kp = (lid[0] + 25.0 * math.cos(_b), lid[1] + 25.0 * math.sin(_b), lid[2] - 2.0)
la = EAS.spawn_actor_from_class(unreal.PointLight, unreal.Vector(*kp), unreal.Rotator())
la.set_actor_label('CINE_HitKey')
lc = la.get_component_by_class(unreal.LocalLightComponent)
lc.set_mobility(unreal.ComponentMobility.MOVABLE)
lc.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
lc.set_editor_property('intensity', 0.025)  # 0.35 blew the clock out (hit_insert3); 0.025 per world's skin fix (2026-11-10)
lc.set_editor_property('attenuation_radius', 45.0)
lc.set_editor_property('cast_shadows', False)
lc.set_editor_property('source_radius', 3.0)
lc.set_editor_property('light_color', unreal.Color(r=230, g=242, b=255, a=255))
lb = seq.add_possessable(la)
out = LES.convert_to_spawnable(lb)
lb = out[0] if out else lb
lb.set_display_name('L6_HitKey')
if unreal.SystemLibrary.is_valid(la) and not la.is_actor_being_destroyed():
    EAS.destroy_actor(la)
for tr in lb.get_tracks():  # alive only for the insert
    if tr.get_class().get_name() == 'MovieSceneSpawnTrack':
        for sp in tr.get_sections():
            sp.set_range(0, seq.get_playback_end())
            c0 = sp.get_all_channels()[0]
            for k in list(c0.get_keys()):
                c0.remove_key(k)
            c0.set_default(False)
            c0.add_key(unreal.FrameNumber(0), False, 0.0, DU)
            c0.add_key(unreal.FrameNumber(T0), True, 0.0, DU)
            c0.add_key(unreal.FrameNumber(T1), False, 0.0, DU)
ins.set_range(341, T0)
hit = cut.add_section()
hit.set_range(T0, T1)
hit.set_camera_binding_id(seq.get_binding_id(cam))
back = cut.add_section()
back.set_range(T1, 450)
back.set_camera_binding_id(ins_id)
unreal.EditorAssetLibrary.save_loaded_asset(seq, False)
LSB.close_level_sequence()
print('HIT_INSERT', 'kick', sorted(KICK), 'blur', pp.get_editor_property('motion_blur_amount'), [(s.get_start_frame(), s.get_end_frame()) for s in sorted(cut.get_sections(), key=lambda s: s.get_start_frame())],
      'cam', [round(v, 1) for v in start], 'rot', [round(v, 2) for v in rot(start, aim)], 'focus', round(math.dist(start, aim), 1))
