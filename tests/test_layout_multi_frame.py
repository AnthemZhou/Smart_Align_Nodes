import json
import unittest
from dataclasses import replace
from pathlib import Path

from test_layout import node, repeat
from smart_align_nodes.layout import (Box, LayoutNode, LayoutLink, LayoutSettings,
                                     solve_layout, layout_diagnostics, _within_neighborhood)


class MultiFrameTests(unittest.TestCase):
    def fixture(self):
        data=json.loads((Path(__file__).parent/'fixtures/multi_frame_layout.json').read_text())
        nodes=[LayoutNode(**dict(n,box=Box(*n['box'],n['key']),location=tuple(n['location']))) for n in data['nodes']]
        links=[LayoutLink(**dict(e,reroutes=tuple(e.get('reroutes',())))) for e in data['links']]
        return nodes,links,LayoutSettings(**data['settings'])

    def test_reported_selection_keeps_frames_nearby_and_separate(self):
        nodes,links,settings=self.fixture()
        plan=solve_layout(nodes,links,settings)
        self.assertEqual(plan.metrics['anchored_frames'],['Frame.012','Frame.013'])
        self.assertFalse(plan.warnings)
        self.assertEqual(layout_diagnostics(nodes,links,plan.boxes)['node_overlaps'],0)
        for n in nodes:
            if n.kind=='FRAME' or not n.selected:
                self.assertEqual(plan.locations[n.key],n.location)
            else:
                self.assertLess(max(abs(plan.locations[n.key][i]-n.location[i]) for i in (0,1)),200)
        constrained=next(r for r in plan.partial_results if 'Radius.001' in r['nodes'])
        self.assertEqual((constrained['method'],constrained['reason']),('local','frame_clearance'))
        self.assertGreater(constrained['moved'],0)
        for k in constrained['nodes']:
            self.assertNotIn(k,plan.alignment_decisions)  # no rejected structured rules
        for _ in range(5):
            again=solve_layout(repeat(nodes,plan),links,settings)
            self.assertEqual(plan.locations,again.locations)
            plan=again

    def test_selection_order_and_extra_enclosing_frame_do_not_reanchor_groups(self):
        nodes,links,settings=self.fixture()
        plan=solve_layout(nodes,links,settings)
        reverse=solve_layout(nodes[::-1],links[::-1],settings)
        self.assertEqual(plan.locations,reverse.locations)
        outer=solve_layout([replace(n,selected=True) if n.key=='Frame.011' else n for n in nodes],links,settings)
        for n in nodes:
            if n.kind!='FRAME':
                self.assertEqual(plan.locations[n.key],outer.locations[n.key])
        # Selecting another node outside the common ancestor must not cause
        # that ancestor to carry both groups into an outer full repack.
        extra=node('outside',-5000,3000)
        wrapped=solve_layout([replace(n,selected=True) if n.key=='Frame.011' else n for n in nodes]+[extra],links,settings)
        for n in nodes:
            if n.kind!='FRAME':
                self.assertEqual(plan.locations[n.key],wrapped.locations[n.key])
        self.assertEqual(wrapped.locations['outside'],extra.location)

    def test_cross_frame_selected_endpoint_is_still_a_scope_boundary(self):
        nodes=[node('f',width=1000,height=600,kind='FRAME'),
               node('a',50,-80,parent='f'),node('b',650,-180,parent='f'),
               node('g',2000,0,width=1000,height=600,kind='FRAME'),
               node('c',2050,-80,parent='g'),node('d',2650,-180,parent='g'),
               node('z',3400,-180)]
        links=[LayoutLink('a','b'),LayoutLink('b','c'),LayoutLink('c','d'),LayoutLink('d','z')]
        plan=solve_layout(nodes,links)
        for frame in ('f','g'):
            single=solve_layout([replace(n,selected=n.parent==frame) for n in nodes],links)
            for n in nodes:
                if n.parent==frame:
                    self.assertEqual(plan.locations[n.key],single.locations[n.key])
        self.assertEqual(plan.locations['z'],(3400,-180))

    def test_neighborhood_rejects_large_translation_even_without_growth(self):
        settings=LayoutSettings()
        boxes={'a':node('a').box,'b':node('b',400).box}
        self.assertTrue(_within_neighborhood(boxes,boxes,boxes,settings))
        for dx,dy in ((10000,0),(0,-10000)):
            shifted={k:b.translated(dx,dy) for k,b in boxes.items()}
            self.assertFalse(_within_neighborhood(boxes,boxes,shifted,settings))


if __name__=='__main__':
    unittest.main()
