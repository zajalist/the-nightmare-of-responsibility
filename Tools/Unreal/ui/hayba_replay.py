"""Run a UI build script in the editor, then replay the Hayba calls it queued (bp_graph's HAYBA lines), in order.
Hold the editor lock as FOA_AGENT=ui.
  python Tools/Unreal/ui/hayba_replay.py Tools/Unreal/ui/build_front_end.py [KEY=VALUE ...]   # script, then its calls
  python Tools/Unreal/ui/hayba_replay.py --calls calls.jsonl                                   # just a call list
  python Tools/Unreal/ui/hayba_replay.py --selftest     # a failed blueprint_compile must block that Blueprint's asset_save
A failed asset_save falls back to EditorAssetLibrary.save_asset through ue_remote (Hayba's save was policy-blocked)."""
import json
import os
import subprocess
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
from hayba_call import connect, send  # noqa: E402

ROOT = 'P:/FoA'


def ue_remote(script, *args):
    p = subprocess.run([sys.executable, f'{ROOT}/Tools/Unreal/ue_remote.py', script, *args], capture_output=True,
                       text=True, cwd=ROOT, env={**os.environ, 'MSYS_NO_PATHCONV': '1'})
    return p.stdout + p.stderr


def save_python(paths):
    tmp = os.path.join(os.environ.get('TEMP', '.'), 'foa_ui_save.py')
    with open(tmp, 'w', encoding='utf-8') as fh:
        fh.write('import unreal\n' + ''.join(f'print("saved", {p!r}, unreal.EditorAssetLibrary.save_asset({p!r}, '
                                             f'only_if_is_dirty=False))\n' for p in paths))
    print(ue_remote(tmp).strip().splitlines()[-len(paths):])


def send_retry(state, cmd, params, tries=8):
    """Hayba drops connections while the editor is busy with other lanes: reconnect and retry with backoff."""
    import time
    for k in range(tries):
        try:
            with connect() as sock:  # one socket per call: the server caps live connections at 16 for all lanes
                return send(sock, cmd, params)
        except (ConnectionError, OSError) as e:
            state['sock'] = None
            print(f'  .. {cmd}: {e}; retry {k + 1}')
            time.sleep(min(4 + 3 * k, 20))
    raise ConnectionError(f'Hayba unreachable for {cmd}')


def replay(calls, send_call=None):
    state, done, failed = {}, set(), 0
    broken = set()  # Blueprints whose compile failed in this batch: never saved after that (an 80 s broken BP_ViewFill, 11-10)
    for cmd, params in calls:
        key = cmd + json.dumps(params, sort_keys=True)
        if key in done:  # scripts that compile_save twice queue the same calls twice
            continue
        done.add(key)
        if cmd == 'asset_save' and broken & set(params.get('asset_paths', [])):
            print('SKIP asset_save', sorted(broken & set(params.get('asset_paths', []))),
                  'its compile failed in this batch: fix or roll back the graph, then compile and save')
            failed += 1
            continue
        r = (send_call or (lambda c, p: send_retry(state, c, p)))(cmd, params)
        ok = bool(r.get('ok', r.get('success', False)))
        if not ok and cmd.endswith('create_widget') and 'exist' in json.dumps(r).lower():
            ok = True  # a retried create whose first attempt landed
        print(('ok  ' if ok else 'FAIL'), cmd, json.dumps(params)[:140], '' if ok else json.dumps(r)[:400])
        if not ok and cmd in ('blueprint_compile', 'ui_compile_widget'):
            broken.add(params.get('path') or params.get('widget_blueprint_path'))
        if not ok and cmd == 'asset_save':
            save_python(params.get('asset_paths', []))
        elif not ok:
            failed += 1
    return failed


def selftest():
    """A failed compile must stop the queued save of the same Blueprint (and only that one)."""
    sent = []

    def fake(cmd, params):
        sent.append((cmd, params))
        return {'ok': not (cmd == 'blueprint_compile' and params['path'] == '/Game/A')}
    calls = [('blueprint_compile', {'path': '/Game/A'}), ('asset_save', {'asset_paths': ['/Game/A']}),
             ('blueprint_compile', {'path': '/Game/B'}), ('asset_save', {'asset_paths': ['/Game/B']})]
    failed = replay(calls, fake)
    saves = [p['asset_paths'] for c, p in sent if c == 'asset_save']
    assert saves == [['/Game/B']], saves
    assert failed == 2, failed  # the failed compile and the skipped save both count
    print('selftest OK')


def main(argv):
    if argv[0] == '--selftest':
        selftest()
        return 0
    if argv[0] == '--calls':
        with open(argv[1], encoding='utf-8') as fh:
            calls = [(d['cmd'], d.get('params', {})) for d in map(json.loads, filter(str.strip, fh))]
    else:
        queue = os.path.join(os.environ.get('TEMP', '.'), f'foa_hayba_queue_{os.getpid()}.jsonl').replace(os.sep, '/')
        out = ue_remote(argv[0], *argv[1:], f'FOA_HAYBA_QUEUE={queue}')
        calls = []
        if os.path.exists(queue):  # the script queued its calls in a file (bp_graph.hayba); stdout is capped
            with open(queue, encoding='utf-8') as fh:
                calls = [(d['cmd'], d.get('params', {})) for d in map(json.loads, filter(str.strip, fh))]
            os.remove(queue)
        for line in out.splitlines():
            if line.startswith('HAYBA ') and not calls:
                _, cmd, raw = line.split(' ', 2)
                calls.append((cmd, json.loads(raw)))
            elif line.strip() and 'comment flag' not in line:
                print('  |', line[:220])
        if 'Traceback' in out:
            print('SCRIPT FAILED: not replaying its calls')
            return 1
    return 1 if replay(calls) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
