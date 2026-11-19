"""Self-guarding for the anim lane's PIE proof drivers (slate post-tick callbacks). 2026-11-10 16:53: pie_phone.py
outlived its own burst (record_anim's 45 s cap ended PIE first), sat registered in the editor's Python, and woke up
inside world's EXCLUSIVE PIE, which it disrupted. A guarded driver:
- arm(S, tick) registers the callback and records the PIE it was started in (the wall-clock start of that PIE
  session); with no PIE running it refuses to arm;
- live(S) is the first thing tick() calls: it returns the PIE world only while that same session runs; when PIE is
  gone, or another session (anyone else's) is running, it unregisters the callback and returns None;
- done(S) unregisters (idempotent); call it from finish() and from any except branch."""
import time

import unreal


def _world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def _session_start(w):
    return time.time() - unreal.GameplayStatics.get_real_time_seconds(w)


def arm(S, tick, tag):
    w = _world()
    if not w or not unreal.SystemLibrary.is_valid(w):
        unreal.log('[anim] %s not armed: no PIE running' % tag)
        return False
    S['guard'] = dict(start=_session_start(w), tag=tag)
    S['h'] = unreal.register_slate_post_tick_callback(tick)
    unreal.log('[anim] %s armed (guarded to the PIE that started %.1f s ago)' % (tag, time.time() - S['guard']['start']))
    return True


def done(S):
    h = S.pop('h', None)
    if h is not None:
        unreal.unregister_slate_post_tick_callback(h)


def live(S):
    w = _world()
    g = S.get('guard')
    if not w or not unreal.SystemLibrary.is_valid(w) or not g or abs(_session_start(w) - g['start']) > 2.0:  # PIE gone, or a session this driver did not start in
        unreal.log('[anim] %s stood down: %s' % (g['tag'] if g else '?', 'PIE ended' if not w else 'not my PIE session'))
        done(S)
        return None
    return w
