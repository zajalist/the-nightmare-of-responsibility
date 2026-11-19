"""Offline graph contract for chase-camera wires previously swallowed by inline comments."""
import unittest
from unittest.mock import patch
import build_clothing_chase as chase
from held_tool_graphs import Batch


class ClothingCameraTest(unittest.TestCase):
    def test_camera_target_and_position_inputs_are_connected(self):
        plans={}
        def fresh(name):
            batch=Batch(chase.P,name);plans[name]=batch
            return batch,'entry'
        with patch.object(chase,'fresh',fresh),patch.object(chase,'finish',lambda *_:None):
            chase.build_motion()
        wanted={'OnClothingCameraReady':{('camera','TopDownCamera','widefov','self')},
                'TickClothingFlight':{('view','ClothingInspectionView','viewpoint','A'),
                                      ('widealpha','ReturnValue','viewpoint','Alpha')}}
        for name,expected in wanted.items():
            actual={(o['from_node'],o['from_pin'],o['to_node'],o['to_pin']) for o in plans[name].ops if o['op']=='connect'}
            self.assertTrue(expected<=actual,(name,expected-actual))


if __name__=='__main__':unittest.main()
