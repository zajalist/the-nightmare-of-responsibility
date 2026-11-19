import json,time
from pathlib import Path
import unreal
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
clock=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/FoA/Gameplay/BP_ClockTick.BP_ClockTick_C'));assert clock
hands={n:clock.get_editor_property(n) for n in ('Hours','Minutes','Seconds')}
assert all(hands.values())
start={n:a.get_actor_transform() for n,a in hands.items()}
out=Path('P:/FoA/Saved/Integration/clock_runtime.json')
gs=unreal.get_default_object(unreal.GameplayStatics);xf=unreal.Transform()
cap=gs.call_method('BeginDeferredActorSpawnFromClass',(w,unreal.SceneCapture2D.static_class(),xf,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
cap=gs.call_method('FinishSpawningActor',(cap,xf,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
cap.set_actor_location_and_rotation(unreal.Vector(-230,0,200),unreal.Rotator(0,180,0),False,True)
c=cap.capture_component2d;c.fov_angle=28;c.capture_every_frame=True;c.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
c.texture_target=unreal.RenderingLibrary.create_render_target2d(w,800,800,unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
S={'start':time.monotonic(),'rows':[],'h':None,'first':False}
def finish(error=None):
    unreal.unregister_slate_post_tick_callback(S['h']);cap.destroy_actor()
    out.write_text(json.dumps({'error':error,'rows':S['rows']},indent=2))
def tick(dt):
    try:
        t=time.monotonic()-S['start']
        row={'t':t}
        for n,a in hands.items():
            q=start[n].rotation;delta=unreal.Quat(-q.x,-q.y,-q.z,q.w)*a.get_actor_transform().rotation
            assert (start[n].translation-a.get_actor_location()).length()<.00001
            row[n]=delta.rotator().pitch
        S['rows'].append(row)
        if t>1.2 and not S['first']:
            unreal.RenderingLibrary.export_render_target(w,c.texture_target,'P:/FoA/Saved/Integration','clock_before.png');S['first']=True
        if t>4.2:
            assert row['Seconds']<=-18 and abs(row['Seconds']/60-row['Minutes'])<.001,row
            assert abs(row['Minutes']/12-row['Hours'])<.001,row
            unreal.RenderingLibrary.export_render_target(w,c.texture_target,'P:/FoA/Saved/Integration','clock_after.png');finish()
    except Exception as exc:finish(repr(exc))
S['h']=unreal.register_slate_post_tick_callback(tick)
