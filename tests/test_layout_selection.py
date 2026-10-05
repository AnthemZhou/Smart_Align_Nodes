import unittest
from dataclasses import replace
from types import SimpleNamespace

from smart_align_nodes.context import layout_selected_names
from smart_align_nodes.layout import LayoutLink, solve_layout
from test_layout import node


def expand(snapshot):
    live = {n.key: SimpleNamespace(name=n.key, type=n.kind, select=n.selected, parent=None)
            for n in snapshot}
    for n in snapshot:
        live[n.key].parent = live.get(n.parent)
    selected = layout_selected_names(SimpleNamespace(nodes=list(live.values())))
    return [replace(n, selected=n.key in selected) for n in snapshot], live


class FrameSelectionTests(unittest.TestCase):
    def test_frame_only_partial_and_full_selection_have_identical_layout(self):
        nodes = [node('frame', width=900, height=800, kind='FRAME'),
                 node('inner', 30, -50, width=500, height=600, kind='FRAME', parent='frame', selected=False),
                 node('a', 60, -100, parent='inner', selected=False),
                 node('b', 65, -400, parent='inner', selected=False),
                 node('c', 650, -200, parent='frame', selected=False),
                 node('outside', 1500, -200, selected=False)]
        links = [LayoutLink('a', 'b'), LayoutLink('b', 'c'), LayoutLink('c', 'outside')]
        expected = None
        for explicit in ({'frame'}, {'frame', 'a'}, {'frame', 'inner', 'a', 'b', 'c'}):
            original = [replace(n, selected=n.key in explicit) for n in nodes]
            effective, live = expand(original)
            self.assertEqual({n.key for n in effective if n.selected}, {'frame', 'inner', 'a', 'b', 'c'})
            self.assertEqual({n.name for n in live.values() if n.select}, explicit)
            plan = solve_layout(effective, links)
            self.assertEqual(plan.locations['outside'], (1500, -200))
            self.assertGreater(plan.boxes['b'].left, plan.boxes['a'].right)
            if expected is not None:
                self.assertEqual(plan.locations, expected)
            expected = plan.locations

    def test_unselected_frame_does_not_include_unselected_siblings(self):
        nodes = [node('frame', kind='FRAME', selected=False),
                 node('a', parent='frame'), node('b', parent='frame', selected=False)]
        effective, _ = expand(nodes)
        self.assertEqual({n.key for n in effective if n.selected}, {'a'})

    def test_multiple_frames_include_reroutes_but_not_outside_nodes(self):
        nodes = [node('f', kind='FRAME'), node('g', kind='FRAME'),
                 node('a', parent='f', selected=False),
                 node('r', parent='f', kind='REROUTE', selected=False),
                 node('b', parent='g', selected=False), node('fixed', selected=False)]
        effective, _ = expand(nodes[::-1])
        self.assertEqual({n.key for n in effective if n.selected}, {'f', 'g', 'a', 'r', 'b'})


if __name__ == '__main__':
    unittest.main()
