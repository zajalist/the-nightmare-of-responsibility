"""Verify the native proof setter's actual Python container conversion without touching current progress."""
import unreal


def main():
    kind = unreal.load_class(None, '/Game/FoA/Gameplay/GI_FoA.GI_FoA_C')
    original = str(unreal.get_default_object(kind).get_editor_property('SaveSlot'))
    probe = unreal.new_object(kind)
    known = {unreal.Name('Knows.KeySnaps')}
    lines = [unreal.Text('Transient proof line')]
    probe.call_method('SetProofProgressContext', ('FoA_QA_TransientOnly', known, lines))
    assert str(probe.get_editor_property('SaveSlot')) == 'FoA_QA_TransientOnly'
    assert {str(v) for v in probe.get_editor_property('Knowledge')} == {'Knows.KeySnaps'}
    assert [str(v) for v in probe.get_editor_property('Notebook')] == ['Transient proof line']
    probe.call_method('SetProofProgressContext', (original, set(), []))
    assert not probe.get_editor_property('Knowledge') and not probe.get_editor_property('Notebook')
    assert str(unreal.get_default_object(kind).get_editor_property('SaveSlot')) == original
    print('PASS transient-only native progress setter: Name set/Text array conversion, clear and restore; current progress untouched')


main()
