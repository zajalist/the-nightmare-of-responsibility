"""Actual bed-edge pose: production versus flat tangent normals, exact state restore."""
import unreal,time,json,traceback
from pathlib import Path
ns={'__name__':'__underarm_owned__'}
exec(Path('P:/FoA/Tools/Unreal/player/pie_wake_handoff_capture.py').read_text(),ns)
S=ns['S'];p=ns['p'];pc=ns['pc'];folder=ns['folder'];oldtick=ns['tick'];oldfinish=ns['finish']
unreal.unregister_slate_post_tick_callback(S['h']);held={}
def finish(reason):
    restored=False
    try:
        if held:
            held['polo'].set_material(0,held['material'])
            for c,flag in held['components']:c.set_component_tick_enabled(flag)
            for a,flag in held['actors']:a.set_actor_tick_enabled(flag)
            held['sequence'].play()
            restored=held['polo'].get_material(0)==held['material']
    finally:
        (folder/'underarm_normal_probe.json').write_text(json.dumps(dict(reason=reason,restored=restored,mesh=held.get('mesh'),lod=held.get('lod'),trials=held.get('trials',[])),indent=2))
        oldfinish(reason)
ns['finish']=finish
def tick(dt):
    try:
        if not held:
            oldtick(dt)
            if S['done']:return
            if 'bed_edge' in S['shots']:
                polo=p.get_editor_property('StartOutfit');seq=ns['d'].get_editor_property('SeqPlayer');seq.pause()
                held.update(start=time.monotonic(),phase=0,trials=[],polo=polo,material=polo.get_material(0),sequence=seq,mesh=polo.get_skinned_asset().get_path_name(),
                    components=[(c,c.is_component_tick_enabled()) for c in p.get_components_by_class(unreal.ActorComponent)],actors=[(a,a.is_actor_tick_enabled()) for a in(p,pc,pc.player_camera_manager)])
                for c,flag in held['components']:c.set_component_tick_enabled(False)
                for a,flag in held['actors']:a.set_actor_tick_enabled(False)
                held['lod']={}
                for key in ('predicted_lod_level','forced_lod_model','min_lod_model'):
                    try:held['lod'][key]=str(polo.get_editor_property(key))
                    except Exception:pass
            return
        elapsed=time.monotonic()-held['start'];phase=held['phase'];polo=held['polo']
        if phase==0 and elapsed>.4:ns['shot']('underarm_production');held['phase']=1
        elif phase==1 and elapsed>.6:
            mid=polo.create_dynamic_material_instance(0)
            mid.set_scalar_parameter_value('WrinkleIntensity',0)
            mid.set_vector_parameter_value('FabricResponse',unreal.LinearColor(0,.86,.3,1))
            mid.set_scalar_parameter_value('CorruptionPulse',0)
            held['mid']=mid;held['phase']=2
        elif phase==2 and elapsed>1.2:ns['shot']('underarm_flat_normal');held['phase']=3
        elif phase==3 and elapsed>1.4:polo.set_material(0,held['material']);held['phase']=4
        elif phase==4 and elapsed>2:ns['shot']('underarm_restored');held['phase']=5
        elif phase==5 and elapsed>2.3:return finish('underarm_normal_probe_passed')
        if phase!=held['phase']:
            held['trials'].append(dict(phase=held['phase'],head=list(p.get_editor_property('Body').get_socket_location('head').to_tuple()),camera=list(pc.player_camera_manager.get_camera_location().to_tuple())))
        if elapsed>4:return finish('underarm_probe_timeout')
    except Exception:finish(traceback.format_exc())
S['h']=unreal.register_slate_post_tick_callback(tick)
