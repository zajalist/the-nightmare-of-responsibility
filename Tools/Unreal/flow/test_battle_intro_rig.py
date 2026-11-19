"""Offline safeguards for the narrowly allowlisted battle-intro rig repair."""
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
import repair_battle_intro_rig as repair


class BattleIntroRigTest(unittest.TestCase):
    def rig(self,rig_class,keys):
        track=Mock();track.get_editor_property.return_value.get_class.return_value.get_name.return_value=rig_class
        data={'sections':[{'channels':[{'keys':list(range(keys))}]}]}
        with patch.object(repair,'track_data',return_value=data):return repair.rig_audit(track)

    def test_only_unkeyed_auto_fk_rig_is_eligible(self):
        self.assertTrue(self.rig('FKControlRig',0)['confirmed_empty_auto_rig'])
        self.assertFalse(self.rig('FKControlRig',1)['confirmed_empty_auto_rig'])
        self.assertFalse(self.rig('AuthoredPoseRig_C',0)['confirmed_empty_auto_rig'])

    def test_unreadable_rig_is_not_treated_as_empty(self):
        track=Mock();track.get_editor_property.side_effect=RuntimeError('not exposed')
        with patch.object(repair,'track_data',return_value={'sections':[{'channels':[]}]}):
            row=repair.rig_audit(track)
        self.assertFalse(row['confirmed_empty_auto_rig'])
        self.assertIn('not exposed',row['rig_read_error'])

    def test_standard_mannequin_autorig_identity_is_verified_via_sequence_proxy(self):
        track=Mock();track.get_editor_property.side_effect=RuntimeError('not exposed')
        rig=Mock();rig.get_class.return_value.get_name.return_value='CR_Mannequin_Body_C'
        rig.get_class.return_value.get_path_name.return_value='/Game/Characters/Mannequins/Rigs/CR_Mannequin_Body.CR_Mannequin_Body_C'
        api=SimpleNamespace(ControlRigSequencerLibrary=SimpleNamespace(get_control_rigs=lambda _: [SimpleNamespace(track=track,control_rig=rig)]))
        with patch.dict(sys.modules,unreal=api),patch.object(repair,'track_data',return_value={'sections':[{'channels':[{'keys':[]}]}]}):
            self.assertTrue(repair.rig_audit(track,object())['confirmed_empty_auto_rig'])
            rig.get_class.return_value.get_path_name.return_value='/Game/FoA/Characters/Custom.CR_Mannequin_Body_C'
            self.assertFalse(repair.rig_audit(track,object())['confirmed_empty_auto_rig'])

    def test_wakeup_and_manual_pose_cannot_enter_repair(self):
        with patch.dict(sys.modules,unreal=SimpleNamespace()):
            for path in ('/Game/FoA/Cinematics/LS_WakeUp','/Game/FoA/Cinematics/LS_WakeUp_ManualPose'):
                seq=Mock();seq.get_path_name.return_value=path
                with self.assertRaisesRegex(AssertionError,'outside allowlist'):repair.process(seq,True)

    def test_copy_preserves_params_ranges_rows_easing_and_completion(self):
        original=Mock();original.has_start_frame.return_value=original.has_end_frame.return_value=True
        original.get_start_frame.return_value=63;original.get_end_frame.return_value=87
        original.get_row_index.return_value=2;original.get_completion_mode.return_value='RestoreState'
        params=object();easing=object();original.get_editor_property.side_effect={'params':params,'easing':easing}.__getitem__
        replacement=Mock();section=replacement.add_section.return_value
        with patch.object(repair,'section_data',return_value={'preserved':'checked'}):repair.copy_section(original,replacement)
        section.set_range.assert_called_once_with(63,87)
        section.set_row_index.assert_called_once_with(2)
        section.set_completion_mode.assert_called_once_with('RestoreState')
        self.assertEqual(section.set_editor_property.call_args_list[0].args,('params',params))
        self.assertEqual(section.set_editor_property.call_args_list[1].args,('easing',easing))


if __name__=='__main__':unittest.main()
