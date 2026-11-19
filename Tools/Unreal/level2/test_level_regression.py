"""Offline receipt and save-absence checks; never imports the native QA runner."""
import ast
import hashlib
from pathlib import Path
import tempfile
import unittest


tree=ast.parse(Path(__file__).with_name('run_level_regression.py').read_text())
scope={'hashlib':hashlib}
exec(compile(ast.Module(body=[node for node in tree.body if isinstance(node,ast.FunctionDef)],type_ignores=[]),
             'run_level_regression.py','exec'),scope)


class RegressionReceiptTests(unittest.TestCase):
    def test_only_completed_all_pass_receipts_succeed(self):
        check=scope['check_result']
        check({'result':{'why':'done','steps':4,'passed':4}})
        for result in ('error: failed',{'why':'cap','steps':4,'passed':4},
                       {'why':'done','steps':4,'passed':3},{'why':'done','steps':0,'passed':0},{}):
            with self.subTest(result=result),self.assertRaises(AssertionError):check({'result':result})

    def test_absent_save_is_distinct_from_created_or_changed_save(self):
        digest=scope['player_save_hash']
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'FoA.sav'
            self.assertIsNone(digest(path))
            path.write_bytes(b'original');before=digest(path)
            self.assertEqual(before,hashlib.sha256(b'original').hexdigest())
            path.write_bytes(b'changed');self.assertNotEqual(digest(path),before)


if __name__=='__main__':unittest.main()
