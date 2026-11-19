"""Run an editor script WITHOUT requesting any lease.
  $env:FOA_AGENT='integration'; python Tools/Unreal/integration/run_read.py <script.py> [KEY=VALUE ...]
Two uses only: read-only probes (the coordinator: reads are free), and the steps of a PIE burst while this lane
already holds the Hayba EXCLUSIVE lease (record_loop.sh), so no step can queue for a second EXCLUSIVE mid-burst.
Anything else that writes assets, actors or the level goes through ue_remote.py with FOA_AREAS."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import hayba_call as hc  # noqa: E402
import ue_remote  # noqa: E402

script = os.path.abspath(sys.argv[1]).replace('\\', '/')
env = dict(a.split('=', 1) for a in sys.argv[2:] if '=' in a)
env.setdefault('FOA_CALLER', hc.agent_id() or 'integration')  # pie_call uses it: END only stops the caller's own PIE
ok = ue_remote.run_hayba(script, env, [], hc.agent_id() or 'integration', None)
if ok is None:
    ok = ue_remote.run_remote(script, env)
sys.exit(0 if ok else 1)
