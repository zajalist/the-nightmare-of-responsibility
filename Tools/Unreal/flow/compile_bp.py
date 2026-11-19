"""Compiles mech_flow Blueprints and prints any compiler errors or warnings per graph (Python compiles are allowed again
since the 21:11 PythonScriptPlugin hotfix; use Hayba blueprint_compile instead when Hayba is reachable).
    python Tools/Unreal/ue_remote.py Tools/Unreal/flow/compile_bp.py [FOA_BP=/Game/FoA/Gameplay/BP_BeatDirector,...]"""
import os

exec(open('P:/FoA/Tools/Unreal/flow/flow_common.py').read())
for path in os.environ.get('FOA_BP', DIR).split(','):
    compile_bp(path)
    report(path)
    print('compiled', path)
