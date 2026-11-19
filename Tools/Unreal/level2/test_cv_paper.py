"""Offline asset contract: readable authored text, correct UVs/normal and closed paper."""
from collections import Counter
import unittest

import numpy as np
import cv_paper as p
import cv_paper_setup as setup
import journey_data


class PaperTests(unittest.TestCase):
    def test_front_faces_eye_and_uv_keeps_print_upright(self):
        front=p.geometry()[0]
        self.assertTrue(all(n[0]<-.99 for n in front['n']))
        for position,uv in zip(front['p'],front['uv']):
            # glTF (x,z,-y); camera-right UE+Y maps to texture-right U.
            self.assertAlmostEqual(uv[0],-position[2]/.21+.5)
            self.assertAlmostEqual(uv[1],.5-position[1]/.297)

    def test_closed_a4_paper_with_valid_triangle_winding(self):
        parts=p.geometry();edges=Counter();all_points=[]
        for part in parts:
            all_points.extend(part['p'])
            for i in range(0,len(part['i']),3):
                indices=part['i'][i:i+3];a,b,c=[np.array(part['p'][j]) for j in indices]
                self.assertGreater(np.dot(np.cross(b-a,c-a),part['n'][indices[0]]),0)
                for j,k in ((0,1),(1,2),(2,0)):
                    edge=tuple(sorted(tuple(round(v,8) for v in part['p'][indices[q]]) for q in (j,k)))
                    edges[edge]+=1
        self.assertEqual(set(edges.values()),{2},'open or nonmanifold paper')
        extent=np.ptp(all_points,axis=0)
        self.assertAlmostEqual(extent[1],.297);self.assertAlmostEqual(extent[2],.21)

    def test_authored_initial_cv_and_print_material(self):
        self.assertEqual(p.TEXT,('Curriculum vitae','Experience','I have no job experience.','Skills','Availability'))
        doc=p.document(p.geometry())
        self.assertEqual(doc['materials'][0]['pbrMetallicRoughness']['baseColorTexture'],{'index':0})
        self.assertEqual(doc['images'][0]['uri'],'T_L2CVPaper.png')
        self.assertEqual(p.texture().size,(1536,2172))
        self.assertEqual(p.TEXT[2],journey_data.STOPS[0]['truth'])
        self.assertTrue((p.FONT/'OFL.txt').is_file())
        # At 70% of a 1080px viewport, the body glyphs remain at least 20px high.
        font=p.ImageFont.truetype(str(p.FONT/'DarkerGrotesque-Medium.ttf'),104)
        bounds=font.getbbox(p.TEXT[2])
        self.assertGreaterEqual((bounds[3]-bounds[1])*.7*1080/2172,20)

    def test_item_merge_preserves_existing_rows_and_is_idempotent(self):
        row=dict(Name='Key',DisplayName='Door key',LookLine='Existing line',Mesh='/Game/Key.Key',
                 Icon='None',UsedBecomes='KeyStub',CombineWith='None',CombineInto='None')
        rows=[row];merged=setup.merge_row(rows,'/Game/Paper.Paper')
        self.assertEqual(rows,[row]);self.assertEqual(merged[0],row)
        self.assertEqual(merged[-1]['Name'],'L2CVPaper')
        self.assertEqual(merged[-1]['DisplayName'],'');self.assertEqual(merged[-1]['LookLine'],'')
        self.assertEqual(setup.merge_row(merged,'/Game/Paper.Paper'),merged)
        with self.assertRaises(AssertionError):setup.merge_row([dict(row,NewMeaning='unknown')],'/Game/Paper.Paper')

    def test_import_rejects_wrong_axes_and_units(self):
        setup.validate_bounds([.157,21,29.7])
        for size in ([.00157,.21,.297],[21,.157,29.7],[.157,29.7,21]):
            with self.assertRaises(AssertionError):setup.validate_bounds(size)


if __name__=='__main__':unittest.main()
