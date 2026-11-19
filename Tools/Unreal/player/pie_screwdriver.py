"""Screwdriver proof shares the guarded key driver (proof_guard, QA slot, owned burst)."""
import os
os.environ['FOA_TOOL_KIND']='screwdriver'
try:
    exec(compile(open('P:/FoA/Tools/Unreal/player/pie_key_grip.py',encoding='utf-8').read(),__file__,'exec'))
finally:
    os.environ.pop('FOA_TOOL_KIND',None)
