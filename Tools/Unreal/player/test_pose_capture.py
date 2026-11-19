"""Named screenshots cannot accidentally collect another lane's numbered frame."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

calls=[]
sys.modules['unreal']=SimpleNamespace(RelativeTransformSpace=SimpleNamespace(RTS_PARENT_BONE_SPACE=0,RTS_WORLD=1),
    SystemLibrary=SimpleNamespace(execute_console_command=lambda world,cmd:calls.append(cmd)))
spec=importlib.util.spec_from_file_location('capture',Path(__file__).with_name('pie_pose_capture.py'))
capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
with tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/'owned.png'; state={}
    capture.request_shot(state,None,path)
    assert calls==[f'Shot filename={path.as_posix()} -nosuffix']
    assert not capture.collect_shot(state)
    path.write_bytes(b'frame')
    since=state['pending_shot'][0]
    os.utime(path,(since-1,since-1))
    assert not capture.collect_shot(state)
    os.utime(path,(since+1,since+1))
    assert capture.collect_shot(state) and not state.get('pending_shot')
print('Named screenshot: pending, stale and fresh-frame controls pass')
