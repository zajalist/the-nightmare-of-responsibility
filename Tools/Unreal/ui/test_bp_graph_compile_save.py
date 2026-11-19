"""Self-test (no editor): bp_graph.compile_save compiles first and saves only a clean compile. A failed compile must
raise and save nothing; a clean one is saved once; the Hayba lines (compile, defaults, save) stay queued in that order.
Fails on the old save-before-compile behaviour.  python Tools/Unreal/ui/test_bp_graph_compile_save.py [bp_graph.py]"""
import json
import os
import sys
import tempfile
import types

src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bp_graph.py')


class _Any:   # every attribute exists and is callable: enough for the module-level setup in bp_graph.py
    def __getattr__(self, name):
        return _Any()

    def __call__(self, *a, **k):
        return _Any()


def run(compile_ok):
    saved, order = [], []
    fake = types.ModuleType('unreal')
    for name in ('BlueprintGraphPinLibrary', 'BlueprintGraphEditor', 'LinearColor', 'IntPoint', 'Vector2D', 'AssetEditorSubsystem'):
        setattr(fake, name, _Any())
    fake.BlueprintStatus = types.SimpleNamespace(BS_UP_TO_DATE='ok', BS_UP_TO_DATE_WITH_WARNINGS='warn', BS_ERROR='error')
    bp = types.SimpleNamespace(status=None, get_editor_property=lambda k: bp.status)

    def compile_blueprint(b):
        order.append('compile')
        b.status = 'ok' if compile_ok else 'error'
    bel = _Any()
    bel.compile_blueprint = compile_blueprint
    fake.BlueprintEditorLibrary = bel
    fake.WidgetBlueprint = type('WidgetBlueprint', (), {})
    fake.EditorAssetLibrary = types.SimpleNamespace(save_asset=lambda *a, **k: (order.append('save'), saved.append(a)) and True)
    fake.load_asset = lambda path: bp
    sys.modules['unreal'] = fake
    ns = {}
    exec(open(src, encoding='utf-8').read(), ns)
    ns['lint_exec'] = lambda b: None
    q = os.path.join(tempfile.mkdtemp(), 'q.jsonl')
    os.environ['FOA_HAYBA_QUEUE'] = q
    raised = False
    try:
        ns['compile_save']('/Game/T/BP_Test', {'X': 1})
    except RuntimeError:
        raised = True
    calls = [json.loads(line)['cmd'] for line in open(q, encoding='utf-8')] if os.path.exists(q) else []
    return saved, order, raised, calls


saved, order, raised, calls = run(compile_ok=False)
assert raised and not saved, f'failed compile: raised={raised} saved={saved} order={order}'
saved, order, raised, calls = run(compile_ok=True)
assert not raised and order == ['compile', 'save'], f'clean compile: order={order} raised={raised}'
assert calls[0] == 'blueprint_compile' and calls[-1] == 'asset_save', calls
print('compile_save selftest OK', order, calls)
