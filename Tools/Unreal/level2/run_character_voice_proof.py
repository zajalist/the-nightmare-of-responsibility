"""One bounded, owned voice-only PIE burst, with guaranteed END and lease release."""
import os
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).parent))
from build_character_voice import call,editor_lock

owner='main-character-voice'
os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner,FOA_CALLER=owner)
Path('P:/FoA/Saved/CharacterVoice/proof_driver.pid').write_text(str(os.getpid()))
token=editor_lock.acquire(owner,wait_s=30,ttl=70)
started=False
try:
    if token:os.environ['FOA_LEASE']=token
    assert not call('editor_get_state')['pie_running']
    call('python_exec_file',path='P:/FoA/Tools/Unreal/ui/pie_call.py',env={'FOA_CALL':'BEGIN','FOA_CALLER':owner},resources=['global'])
    started=True
    time.sleep(1)
    call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/character_voice_proof.py',resources=['global'])
finally:
    try:
        if started:
            call('python_exec_file',path='P:/FoA/Tools/Unreal/ui/pie_call.py',env={'FOA_CALL':'END','FOA_CALLER':owner},resources=['global'])
            time.sleep(.5)
            assert not call('editor_get_state')['pie_running']
    finally:editor_lock.release(owner)
