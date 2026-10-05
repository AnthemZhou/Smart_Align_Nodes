"""Regression cases for visible port rows, separate from manual snapping."""
import unittest
from types import SimpleNamespace as NS
from smart_align_nodes.geometry import Box, layout_socket_y_anchors


def socket(name, **kwargs):
    return NS(identifier=name, enabled=True, hide=False, is_unavailable=False,
              **dict({'is_linked':True, 'hide_value':False, 'type':'VALUE'}, **kwargs))


class LayoutPortTests(unittest.TestCase):
    def anchors(self, node, height):
        return dict(layout_socket_y_anchors(node, Box(0,140,0,-height)))

    def test_collapsed_two_inputs_straddle_center(self):
        n=NS(hide=True, inputs=[socket('A'),socket('B')], outputs=[socket('Result')])
        a=self.anchors(n,28)
        self.assertEqual(a['socket:inputs:A:0'],-9)
        self.assertEqual(a['socket:inputs:B:1'],-19)
        self.assertEqual(a['socket:outputs:Result:0'],-14)

    def test_switch_inputs_are_below_output(self):
        n=NS(bl_idname='GeometryNodeSwitch',hide=False,
             inputs=[socket('Switch'),socket('False'),socket('True')],outputs=[socket('Result')])
        a=self.anchors(n,119)
        self.assertEqual(a['socket:inputs:Switch:0'],-60)
        self.assertEqual(a['socket:inputs:True:2'],-104)
        self.assertEqual(a['socket:outputs:Result:0'],-35)

    def test_hidden_outputs_do_not_leave_empty_rows(self):
        hidden=socket('X');hidden.hide=True
        n=NS(bl_idname='ShaderNodeSeparateXYZ',hide=False,
             inputs=[socket('Vector')],outputs=[hidden,socket('Z')])
        a=self.anchors(n,75)
        self.assertNotIn('socket:outputs:X:0',a)
        self.assertEqual(a['socket:outputs:Z:0'],-35)
        self.assertEqual(a['socket:inputs:Vector:0'],-60)

    def test_unknown_panel_and_unlinked_vector_keep_fallback(self):
        for kind in ('CustomPanelNode','ShaderNodeVectorMath'):
            n=NS(bl_idname=kind,hide=False,inputs=[socket('Vector',is_linked=False,type='VECTOR')],outputs=[])
            self.assertEqual(self.anchors(n,200)['socket:inputs:Vector:0'],-37)
