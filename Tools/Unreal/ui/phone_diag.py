"""Read-only BP_Phone check before the swap (main 2026-11-10: exactly ONE screen drawer; anim found the glass drawing the
lock screen while the Screen WidgetComponent, 0.15 cm off the glass, drew the Today list). Writes Saved/UIShots/aaa/phone_diag.txt
(the remote run's printed output is truncated).
  python Tools/Unreal/ue_remote.py Tools/Unreal/ui/phone_diag.py FOA_AREAS=/Game/FoA/UI/Game/BP_Phone"""
import traceback

import unreal

OUT = 'P:/FoA/Saved/UIShots/aaa/phone_diag.txt'
lines = []


def say(*a):
    lines.append(' '.join(str(x) for x in a))


def guard(fn):
    try:
        fn()
    except Exception:
        say('ERROR', traceback.format_exc()[-600:])


bp = unreal.load_asset('/Game/FoA/UI/Game/BP_Phone')
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    def one(h=h):
        data = lib.get_data(h)
        obj = lib.get_object(data)
        say('component', lib.get_variable_name(data), obj.get_class().get_name() if obj else None)
        if isinstance(obj, unreal.SceneComponent):
            say('  attach', obj.get_attach_parent().get_name() if obj.get_attach_parent() else None, obj.get_attach_socket_name(),
                'rel', obj.get_editor_property('relative_location'), obj.get_editor_property('relative_rotation'),
                'scale', obj.get_editor_property('relative_scale3d'))
        if isinstance(obj, unreal.WidgetComponent):
            for p in ('widget_class', 'two_sided', 'draw_size', 'space', 'override_materials', 'render_custom_depth'):
                guard(lambda p=p: say('  widget', p, obj.get_editor_property(p)))
        if isinstance(obj, unreal.StaticMeshComponent):
            guard(lambda: say('  mesh overrides', [m.get_path_name() if m else None for m in obj.get_editor_property('override_materials')]))
            sm = obj.get_editor_property('static_mesh')
            for i, s in enumerate(sm.get_editor_property('static_materials')):
                m = s.get_editor_property('material_interface')
                say('  slot', i, s.get_editor_property('material_slot_name'), m.get_path_name() if m else None)
                if isinstance(m, unreal.MaterialInstance):
                    guard(lambda m=m: say('    parent', m.get_editor_property('parent').get_path_name()))
                    guard(lambda m=m: say('    textures', m.get_editor_property('texture_parameter_values')))
            for name in ('Screen', 'Thumb_Rest', 'Palm_L'):
                guard(lambda name=name: say('  socket', name, sm.find_socket(name).get_editor_property('relative_location'),
                                            sm.find_socket(name).get_editor_property('relative_rotation')))
    guard(one)
say('sds api', [m for m in dir(sds) if 'socket' in m.lower() or 'attach' in m.lower()], [m for m in dir(lib) if 'socket' in m.lower()])
say('SCS_Node', hasattr(unreal, 'SCS_Node'))
open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
print('phone diag ->', OUT, len(lines), 'lines')
