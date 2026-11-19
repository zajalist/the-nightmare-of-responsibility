"""Save the given UI assets inside a lease (waits out PIE bursts; retries a locked file a few times).
  python Tools/Unreal/ui/textfx/save_assets.py /Game/Path/A /Game/Path/B"""
import sys, time
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import editor_lock, hayba_call as hc  # noqa: E401
paths = sys.argv[1:]
tok = editor_lock.acquire('ui', wait_s=1800, ttl=120, areas=paths)
try:
    for attempt in range(6):
        assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
        d = hc.call('asset_save', {'asset_paths': paths, 'force': True}).get('data') or {}
        print(attempt, 'saved', d.get('saved'), 'failed', d.get('failed'))
        if not d.get('failed'):
            break
        time.sleep(10)
finally:
    if tok:
        hc.release('ui', tok); editor_lock.forget('ui', tok)
