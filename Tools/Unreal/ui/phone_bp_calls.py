"""Hayba calls that create BP_Phone (the diegetic phone): SM_Phone (surfaces lane, Lux3D), the screen as a world-space
WidgetComponent drawing WBP_Phone, and PhoneCam (CineCamera, focus on the screen) for the push-in. Graph: wire_bp_phone.py.
  python Tools/Unreal/ui/phone_bp_calls.py > Saved/UIShots/phone_bp.jsonl
SM_Phone: 16 x 7.2 x 1.2 cm, long axis +X (top of the phone), screen quad on the -Y face (6.68 x 14.86 cm).
The widget draws 540 x 1201 px; world size = 0.01237 cm per px, so the WidgetComponent scale is 0.01237."""
import json

P = '/Game/FoA/UI/Game/BP_Phone'
calls = []


def c(cmd, **p):
    calls.append({'cmd': cmd, 'params': p})


c('blueprint_create', name='BP_Phone', package_path=P, parent_class_path='/Script/Engine.Actor')
c('blueprint_add_component', path=P, component_class_path='/Script/Engine.StaticMeshComponent', component_name='Mesh')
c('blueprint_add_component', path=P, component_class_path='/Script/UMG.WidgetComponent', component_name='Screen')
c('blueprint_add_component', path=P, component_class_path='/Script/CinematicCamera.CineCameraComponent',
  component_name='PhoneCam')
c('blueprint_compile', path=P)
c('blueprint_get_info', path=P)
if __name__ == '__main__':
    for d in calls:
        print(json.dumps(d))
