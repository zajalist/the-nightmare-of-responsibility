"""Offline guards for the final explicit ownership list and read-only audit."""
import tempfile
from pathlib import Path
import unittest
import validate_level_integration as v


class FinalValidation(unittest.TestCase):
    def row(self):
        return dict(pie_running=False,world=v.BEDROOM+'.L_Tutorial_Bedroom',actor_count=236,
                    temporary_actors=[],essential_actors=dict(BP_BeatDirector_C=['BeatDirector'],
                        BP_Encounter_C=['Encounter_T8'],PlayerStart=['PlayerStart_WakeUp']),
                    dirty_assets=[],dirty_maps=[v.BEDROOM],assets=[dict(exists=True,on_disk=True)])

    def test_known_dirty_bedroom_is_reported_without_saving(self):
        v.validate_inventory(self.row())
        self.assertNotIn(v.BEDROOM,v.BLUEPRINTS)
        self.assertFalse(set(v.SEQUENCES).intersection(v.BLUEPRINTS))
        source=Path(v.__file__).read_text()
        self.assertNotIn('save_current_level(',source)
        self.assertNotIn('save_dirty_packages(',source)
        self.assertNotIn('delete_asset(',source)

    def test_inventory_rejects_real_regressions(self):
        for field,value in (('pie_running',True),('actor_count',237),('temporary_actors',['TMP_test']),
                            ('dirty_assets',[v.SEQUENCES[0]]),('assets',[dict(exists=True,on_disk=False)])):
            row=self.row();row[field]=value
            with self.subTest(field=field),self.assertRaises(AssertionError):v.validate_inventory(row)
        row=self.row();row['essential_actors']['BP_Encounter_C']=[]
        with self.assertRaises(AssertionError):v.validate_inventory(row)

    def test_exact_allowlist_has_new_assets_and_prior_ownership(self):
        self.assertEqual(len(v.BLUEPRINTS),len(set(v.BLUEPRINTS)))
        self.assertEqual(len(v.BLUEPRINTS),22)
        self.assertIn('/Game/FoA/Gameplay/BPC_Interactor',v.BLUEPRINTS)
        self.assertIn('/Game/FoA/Level2/Journey/BP_L2StopSet',v.BLUEPRINTS)
        self.assertIn('/Game/FoA/UI/Game/WBP_Phone',v.BLUEPRINTS)
        self.assertIn('/Game/FoA/UI/Game/WBP_HUD',v.BLUEPRINTS)
        self.assertIn('/Game/FoA/Level2/Journey/WBP_L2Interview',v.BLUEPRINTS)
        self.assertTrue(all('/Game/FoA/' in p and p.rsplit('/',1)[-1].startswith(('BP_','BPC_','WBP_'))
                            for p in v.BLUEPRINTS))

    def test_protected_hashes_include_missing_files_and_detect_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);before=v.hashes(root)
            self.assertTrue(all(x is None for x in before.values()))
            path=root/v.PROTECTED[0];path.parent.mkdir(parents=True);path.write_bytes(b'original')
            first=v.hashes(root);path.write_bytes(b'changed')
            self.assertNotEqual(first[v.PROTECTED[0]],v.hashes(root)[v.PROTECTED[0]])


if __name__=='__main__':unittest.main()
