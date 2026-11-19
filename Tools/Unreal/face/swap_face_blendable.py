"""Make the face blur live on the level's PP_DreamMono (approved by main 2026-11-09): read the blendables as they
are now, replace M_PP_DreamFace with M_PP_FaceBlur in its slot (append it if neither is there), keep every other
entry and weight exactly. Prints the array before and after. Save the level afterwards (editor_lock.py save_level).
  python Tools/Unreal/ue_remote.py Tools/Unreal/face/swap_face_blendable.py FOA_ACTORS=PP_DreamMono
FOA_OFF=1 takes M_PP_FaceBlur off the volume (before any recompile, editor-rules 9); a later plain run puts it back.
(M_PP_DreamFace was deleted 2026-11-10, so there is no swap back to it any more.)"""
import os

import unreal

NEW, OLD = '/Game/FoA/PostProcess/FaceBlur/M_PP_FaceBlur', '/Game/FoA/PostProcess/M_PP_DreamFace'


def run():
    off = os.environ.get('FOA_OFF') == '1'
    put, take = NEW, OLD
    ppv = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
               if isinstance(a, unreal.PostProcessVolume) and a.get_actor_label() == 'PP_DreamMono')
    s = ppv.get_editor_property('settings')
    arr = list(s.get_editor_property('weighted_blendables').get_editor_property('array'))
    names = lambda a: [(b.get_editor_property('object').get_name() if b.get_editor_property('object') else None,
                        b.get_editor_property('weight')) for b in a]
    print('before', names(arr))
    new_obj = unreal.load_asset(put)
    out, done = [], False
    for b in arr:
        o = b.get_editor_property('object')
        wb = unreal.WeightedBlendable()
        wb.set_editor_property('weight', b.get_editor_property('weight'))
        if o and o.get_path_name().split('.')[0] in (take, put):
            if done or off:
                continue  # never two face passes; off: drop it
            wb.set_editor_property('object', new_obj)
            done = True
        else:
            wb.set_editor_property('object', o)
        out.append(wb)
    if not done and not off:
        wb = unreal.WeightedBlendable()
        wb.set_editor_property('weight', 1.0)
        wb.set_editor_property('object', new_obj)
        out.append(wb)
    wbs = unreal.WeightedBlendables()
    wbs.set_editor_property('array', out)
    s.set_editor_property('weighted_blendables', wbs)
    ppv.set_editor_property('settings', s)
    after = names(ppv.get_editor_property('settings').get_editor_property('weighted_blendables').get_editor_property('array'))
    print('after', after)
    assert [n for n, _ in after].count(new_obj.get_name()) == (0 if off else 1), after
    face = ('M_PP_FaceBlur', 'M_PP_DreamFace')
    assert [n for n in names(arr) if n[0] not in face] == [n for n in after if n[0] not in face], 'other blendables changed'


run()
