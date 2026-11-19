"""Author one debug graph group; the host replays native compile/save before the dependent group."""
import os
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())


def compile_save(path, defaults=None):
    lint_exec(unreal.load_asset(path))
    hayba('blueprint_compile', path=path, save=True)


F = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
C = lambda path: path + '.' + path.rsplit('/', 1)[1] + '_C'
exec(open('P:/FoA/Tools/Unreal/ui/install_debug_shortcuts.py', encoding='utf-8').read())
if os.environ.get('FOA_DEBUG_PART') == 'frontend':
    compile_save(F)
