"""Small offline guards for cinematic ownership and rebuild persistence."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).parents[1]

def extract(file,names):
    tree=ast.parse(file.read_text(encoding='utf-8'))
    return compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),str(file),'exec')

class StoryContinuityTest(unittest.TestCase):
    def test_old_story_overlay_leaves_dream_handoff_intact(self):
        env=dict(inspect=Mock(return_value=([{'title':'Continue into the dream'}],[])),P='director')
        exec(extract(ROOT/'flow/apply_story_director.py',{'ending','hide_hud_at_end'}),env)
        self.assertIn('threshold owns',env['ending']())
        self.assertIn('threshold owns',env['hide_hud_at_end']())

    def test_animation_removes_auto_rig_and_uses_source_component(self):
        binding=Mock();binding.get_id.return_value='player-guid'
        child=Mock();child.get_parent.return_value=binding;child.get_display_name.return_value='CharacterMesh0'
        rig=Mock();rig.get_class.return_value.get_name.return_value='MovieSceneControlRigParameterTrack'
        child.get_tracks.return_value=[rig]
        seq=Mock();seq.get_bindings.return_value=[child]
        template=Mock();template.get_editor_property.return_value.get_name.return_value='CharacterMesh0'
        ue=Mock();ue.MovieSceneBindingExtensions.get_object_template.return_value=template
        env=dict(unreal=ue,PLAYER='player',UAL='anims/',LES=SimpleNamespace(add_spawnable_from_class=Mock(return_value=binding)),transform_track=Mock(),CONST=0)
        exec(extract(ROOT/'flow/build_battle_intro.py',{'player'}),env)
        self.assertEqual(env['player'](seq,[],[('walk',0,3)]),binding)
        child.remove_track.assert_called_once_with(rig)
        child.add_track.assert_called_once_with(ue.MovieSceneSkeletalAnimationTrack)
        binding.add_track.assert_not_called()

if __name__=='__main__':unittest.main()
