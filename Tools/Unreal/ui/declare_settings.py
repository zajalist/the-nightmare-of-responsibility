"""Create Settings signatures before its body references them; C++ compile/save before wire_settings.py."""
import unreal

source=open('P:/FoA/Tools/Unreal/ui/wire_settings.py',encoding='utf-8').read()
marker='\ndef fn(name):'
assert source.count(marker)==1,'Settings declaration boundary changed'
exec(compile(source.split(marker)[0],__file__,'exec'))
unreal.EditorAssetLibrary.save_loaded_asset(unreal.load_asset(P_),False)
print('Settings signatures saved; C++ compile/save in the same asset lease before wiring bodies')
