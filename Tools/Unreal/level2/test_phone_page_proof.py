"""The phone proof must wait for its independent lock overlay, not just SetPage."""
import unittest
from phone_progress_proof import PhoneProof


class PageProof(unittest.TestCase):
    def setUp(self):
        class Widget:
            def __init__(self,opacity=1.,index=0):self.opacity,self.index=opacity,index
            def get_render_opacity(self):return self.opacity
            def get_active_widget_index(self):return self.index
        self.pages=Widget();self.lock=Widget(0.)
        self.widget=dict(Pages=self.pages,Ovl_Lock=self.lock,LockT=2.,CurrentPage=0,bReadingMessage=False)
        self.proof=PhoneProof.__new__(PhoneProof)
        self.proof.get=lambda obj,name:obj[name]
        self.proof.valid=lambda obj:obj is not None

    def test_tasks_index_does_not_bypass_lock_overlay(self):
        self.assertTrue(self.proof.pages_ready(self.widget))
        self.lock.opacity=.2
        self.assertFalse(self.proof.pages_ready(self.widget))
        with self.assertRaisesRegex(AssertionError,'lock screen'):self.proof.page_view(self.widget,0)
        self.lock.opacity=0.;self.pages.opacity=.8
        self.assertFalse(self.proof.pages_ready(self.widget))
        self.pages.opacity=1.;self.widget['LockT']=1.2
        self.assertFalse(self.proof.pages_ready(self.widget))

    def test_selected_and_rendered_page_must_match(self):
        self.assertEqual(self.proof.page_view(self.widget,0)['page'],0)
        self.pages.index=2
        with self.assertRaisesRegex(AssertionError,'drawing'):self.proof.page_view(self.widget,0)
        self.pages.index=1;self.widget.update(CurrentPage=1,bReadingMessage=True)
        self.assertTrue(self.proof.page_view(self.widget,1,reading=True)['reading'])


if __name__=='__main__':unittest.main()
