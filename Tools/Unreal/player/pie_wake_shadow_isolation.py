"""Hold the actual +.15s handoff pose; isolate shadow casters with runtime setters."""
import unreal,time,json,traceback
from pathlib import Path
ns={'__name__':'__wake_shadow_owned__'}
exec(Path('P:/FoA/Tools/Unreal/player/pie_wake_handoff_capture.py').read_text(),ns)
S=ns['S'];p=ns['p'];pc=ns['pc'];w=ns['w'];folder=ns['folder']
oldtick=ns['tick'];oldfinish=ns['finish'];unreal.unregister_slate_post_tick_callback(S['h'])
held={};trials=[('held_baseline',()),('body_off',('Body',)),('outfit_off',('StartOutfit',)),('pants_off',('StartPants',)),('socks_off',('StartSocks',)),('all_casters_off',('*',)),('casters_restored',())]
def restore():
    for c,flag in held.get('shadows',[]):c.set_cast_shadow(flag)
    for c,flag in held.get('components',[]):c.set_component_tick_enabled(flag)
    for a,flag in held.get('actors',[]):a.set_actor_tick_enabled(flag)
def finish(reason):
    try:restore()
    finally:
        (folder/'shadow_isolation.json').write_text(json.dumps(dict(reason=reason,trials=held.get('trials',[]),restored=True),indent=2))
        oldfinish(reason)
ns['finish']=finish
def tick(dt):
    try:
        if not held:
            oldtick(dt)
            if S['done']:return
            if S['exit'] is not None and time.monotonic()-S['start']-S['exit']>.15:
                held.update(start=time.monotonic(),phase=0,trials=[],components=[(c,c.is_component_tick_enabled()) for c in p.get_components_by_class(unreal.ActorComponent)],actors=[(a,a.is_actor_tick_enabled()) for a in (p,pc,pc.player_camera_manager)],shadows=[(c,bool(c.get_editor_property('cast_shadow'))) for c in p.get_components_by_class(unreal.PrimitiveComponent)])
                for c,flag in held['components']:c.set_component_tick_enabled(False)
                for a,flag in held['actors']:a.set_actor_tick_enabled(False)
            return
        elapsed=time.monotonic()-held['start'];i=held['phase']
        if i<len(trials):
            label,disabled=trials[i]
            if elapsed>=i*.4 and held.get('applied')!=i:
                for c,flag in held['shadows']:c.set_cast_shadow(False if '*' in disabled or c.get_name() in disabled else flag)
                held['applied']=i
            if elapsed>.2+i*.4:
                ns['shot'](label)
                held['trials'].append(dict(label=label,disabled=disabled,head=list(p.get_editor_property('Body').get_socket_location('head').to_tuple()),camera=list(pc.player_camera_manager.get_camera_location().to_tuple())))
                held['phase']+=1
        elif i==len(trials) and elapsed>3.1:
            return finish('shadow_source_isolation_passed')
        if elapsed>5:return finish('shadow_source_isolation_timeout')
    except Exception:
        held['error']=traceback.format_exc();finish(held['error'])
S['h']=unreal.register_slate_post_tick_callback(tick)
