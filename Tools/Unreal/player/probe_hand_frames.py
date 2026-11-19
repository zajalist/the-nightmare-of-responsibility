"""Read-only: the screwdriver mesh's handle end and the reference-pose hand frames of the visible body and the Manny.
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/probe_hand_frames.py
Writes Saved/AnimShots/screwdriver/hand_frames.json."""
import json
from pathlib import Path
import unreal

out = {}
mesh = unreal.load_asset('/Game/FoA/Props/screwdriver/screwdriver_1k/StaticMeshes/screwdriver_1k')
v = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, 0)[0]
zs = [p.z for p in v]
lo, hi = min(zs), max(zs)
bands = []
for i in range(10):  # radial size per tenth of the length: the handle is the fat end
    a, b = lo + (hi - lo) * i / 10, lo + (hi - lo) * (i + 1) / 10
    r = [(p.x ** 2 + p.y ** 2) ** 0.5 for p in v if a <= p.z <= b]
    bands.append((round(a, 2), round(b, 2), round(max(r), 2) if r else 0))
out['screwdriver'] = dict(z=[lo, hi], verts=len(v), radius_by_band=bands)
BONES = ['upperarm_r', 'lowerarm_r', 'hand_r', 'middle_metacarpal_r', 'index_metacarpal_r', 'pinky_metacarpal_r',
         'index_01_r', 'middle_01_r', 'ring_01_r', 'pinky_01_r', 'thumb_01_r', 'thumb_02_r', 'thumb_03_r',
         'index_03_r', 'middle_03_r', 'lowerarm_twist_01_r', 'lowerarm_twist_02_r']
W = unreal.AnimPoseSpaces.WORLD
for tag, path in (('mh', '/Game/FoA/Characters/Protagonist/Common/Female/Medium/NormalWeight/Body/metahuman_base_skel'),
                  ('manny', '/Game/Characters/Mannequins/Meshes/SK_Mannequin')):
    sk = unreal.load_asset(path)
    pose = unreal.AnimPoseExtensions.get_reference_pose(sk)
    names = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(pose)]
    row = {}
    for b in BONES:
        if b in names:
            t = unreal.AnimPoseExtensions.get_bone_pose(pose, b, W)
            q = t.rotation
            row[b] = dict(loc=[round(t.translation.x, 2), round(t.translation.y, 2), round(t.translation.z, 2)],
                          x=[round(c, 3) for c in q.get_axis_x().to_tuple()], y=[round(c, 3) for c in q.get_axis_y().to_tuple()],
                          z=[round(c, 3) for c in q.get_axis_z().to_tuple()])
    out[tag] = row
    out[tag + '_fingers'] = [n for n in names if n.endswith('_r') and any(k in n for k in ('index', 'middle', 'ring', 'pinky', 'thumb'))]
Path('P:/FoA/Saved/AnimShots/screwdriver/hand_frames.json').write_text(json.dumps(out, indent=1))
print('HAND_FRAMES ok')
