"""Frame recorder for PIE proofs: FOA_REC=START requests 'Shot showui' about 8 times a second from a slate post-tick
callback (the PIE viewport renders the frame, so window focus does not matter); FOA_REC=STOP unregisters it.
Frames land in Saved/Screenshots/WindowsEditor/ScreenShot#####.png. Run via ue_remote.py while holding the lock."""
import os
import unreal


def start(u=unreal, step=0.125):
    state = {'t': 0.0}
    ues = u.get_editor_subsystem(u.UnrealEditorSubsystem)

    def tick(dt, u=u, ues=ues, state=state, step=step):
        state['t'] += dt
        if state['t'] < step:
            return
        state['t'] = 0.0
        world = ues.get_game_world()
        if world:
            u.SystemLibrary.execute_console_command(world, 'Shot showui')
    u._foa_rec = u.register_slate_post_tick_callback(tick)
    print('rec started')


def stop(u=unreal):
    h = getattr(u, '_foa_rec', None)
    if h is not None:
        u.unregister_slate_post_tick_callback(h)
        u._foa_rec = None
    print('rec stopped')


start() if os.environ.get('FOA_REC') == 'START' else stop()
