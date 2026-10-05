import json
import unittest
from pathlib import Path
from dataclasses import replace
from test_layout import node, repeat
from smart_align_nodes.layout import Box, LayoutNode, LayoutLink, solve_layout, layout_diagnostics
from smart_align_nodes.layout_routing import plan_internal_routes, align_internal_junctions
from smart_align_nodes.layout import LayoutPlan, geometry_matches_plan, frame_redraw_tolerance


class RoutingTests(unittest.TestCase):
    def test_existing_serial_points_are_used_before_adding_points(self):
        ns=[node('a'),node('b',800),node('fixed',350,30,width=200,height=180,selected=False)]
        es=[LayoutLink('a','b',reroutes=('old_1','old_2','old_3','old_4'))]
        routes=plan_internal_routes(ns,es,{n.key:n.box for n in ns})
        self.assertEqual(routes[0]['reuse'],list(es[0].reroutes))
        self.assertEqual(len(routes[0]['points']),4)
        self.assertEqual(layout_diagnostics(ns,es,{n.key:n.box for n in ns},routes=routes)['estimated_wire_node_hits'],0)

    def test_clear_path_keeps_existing_manual_point_without_adding(self):
        ns=[node('a'),node('b',400)]
        routes=plan_internal_routes(ns,[LayoutLink('a','b',reroutes=('labelled',))],{n.key:n.box for n in ns})
        self.assertEqual(len(routes[0]['points']),1)
        self.assertEqual(routes[0]['points'][0][1],-37)

    def test_junction_does_not_get_duplicate_lead_in(self):
        ns=[node('r',140,-32,width=10,height=10,kind='REROUTE'),node('b',800),
            node('fixed',350,30,width=200,height=180,selected=False)]
        edge=LayoutLink('r','b',source_offset=5)
        routes=plan_internal_routes(ns,[edge],{n.key:n.box for n in ns})
        self.assertTrue(routes)
        self.assertLessEqual(len(routes[0]['points']),3)
        self.assertNotIn((150,-37),routes[0]['points'])

    def test_redraw_fast_path_requires_unchanged_geometry_and_ports(self):
        ns=[node('a'),node('b',400)];es=[LayoutLink('a','b')]
        plan=solve_layout(ns,es);drawn=repeat(ns,plan)
        self.assertTrue(geometry_matches_plan(drawn,es,plan,es))
        self.assertFalse(geometry_matches_plan(drawn,[replace(es[0],target_offset=60)],plan,es))
        self.assertFalse(geometry_matches_plan([replace(drawn[0],box=Box(0,500,0,-100)),drawn[1]],es,plan,es))
        self.assertFalse(geometry_matches_plan([replace(drawn[0],location=(10,10)),drawn[1]],es,plan,es))

    def test_rewired_link_order_needs_no_second_solve(self):
        ns=[node('a'),node('b',400),node('c',800)]
        es=[LayoutLink('a','b'),LayoutLink('b','c')]
        plan=solve_layout(ns,es);drawn=repeat(ns,plan)
        self.assertTrue(geometry_matches_plan(drawn,list(reversed(es)),plan,es))
        self.assertFalse(geometry_matches_plan(drawn,[es[0],es[0]],plan,es))

    def test_auto_frame_draw_rounding_uses_measured_geometry_scale(self):
        # Auto-size rounds the Frame, rebasing child locals but leaving their
        # absolute positions unchanged. This must not trigger a fresh solve.
        frame=node('frame',10.25,-2302.79833984375,width=450.25,height=310.3,kind='FRAME')
        child=node('child',40.3,-2370.2,parent='frame')
        ns=[frame,child]
        plan=LayoutPlan({n.key:n.location for n in ns},{n.key:n.box for n in ns})
        for scale in (1,1.25,2,3):
            with self.subTest(scale=scale):
                rounded=replace(frame,location=tuple(round(v*scale)/scale for v in frame.location),
                                box=replace(frame.box,**{k:round(getattr(frame.box,k)*scale)/scale
                                            for k in ('left','right','top','bottom')}))
                self.assertTrue(geometry_matches_plan([rounded,child],[],plan,[],geometry_scale=scale))

    def test_frame_rounding_never_relaxes_child_or_manual_frame_checks(self):
        frame=node('frame',10,-20,width=450,height=300,kind='FRAME')
        child=node('child',40,-70,parent='frame')
        ns=[frame,child]
        plan=LayoutPlan({n.key:n.location for n in ns},{n.key:n.box for n in ns})
        rounded=replace(frame,location=(10,-19.7),box=replace(frame.box,top=-19.7))
        self.assertTrue(geometry_matches_plan([rounded,child],[],plan,[],geometry_scale=2))
        for moved in (replace(child,location=(40,-69.8)),
                      replace(child,box=replace(child.box,bottom=child.box.bottom-.2))):
            self.assertFalse(geometry_matches_plan([rounded,moved],[],plan,[],geometry_scale=2))
        self.assertFalse(geometry_matches_plan([replace(rounded,shrink=False),child],[],plan,[],geometry_scale=2))
        self.assertFalse(geometry_matches_plan([rounded,child],[],plan,[]))

    def test_frame_geometry_changes_larger_than_draw_unit_still_need_solve(self):
        frame=node('frame',kind='FRAME')
        plan=LayoutPlan({'frame':frame.location},{'frame':frame.box})
        for changed in (replace(frame,location=(0,.6)),
                        replace(frame,box=replace(frame.box,right=frame.box.right+.6))):
            self.assertFalse(geometry_matches_plan([changed],[],plan,[],geometry_scale=2))

    def test_unknown_draw_scale_keeps_strict_tolerance(self):
        for scale in (None,0,-1,float('inf'),float('nan')):
            self.assertEqual(frame_redraw_tolerance(scale),.1)
        self.assertEqual(frame_redraw_tolerance(2),.5)
        self.assertEqual(frame_redraw_tolerance(20),.1)

    def test_route_clears_fixed_body_and_keeps_horizontal_end_legs(self):
        ns=[node('a'),node('b',800),node('fixed',350,30,width=200,height=180,selected=False)]
        es=[LayoutLink('a','b')];boxes={n.key:n.box for n in ns}
        routes=plan_internal_routes(ns,es,boxes)
        self.assertEqual(len(routes),1)
        self.assertEqual(routes[0]['points'][0][1],-37)
        self.assertEqual(routes[0]['points'][-1][1],-37)
        self.assertEqual(layout_diagnostics(ns,es,boxes,routes=routes)['estimated_wire_node_hits'],0)
        self.assertEqual(routes,plan_internal_routes(ns[::-1],es[::-1],boxes))

    def test_external_muted_hidden_and_multi_input_links_are_not_rewired(self):
        ns=[node('a'),node('b',800),node('fixed',350,30,width=200,height=180,selected=False)]
        boxes={n.key:n.box for n in ns}
        for kwargs in ({'muted':True},{'hidden':True},{'valid':False},{'multi_input':True}):
            self.assertEqual(plan_internal_routes(ns,[LayoutLink('a','b',**kwargs)],boxes),[])
        ns[1]=replace(ns[1],selected=False)
        self.assertEqual(plan_internal_routes(ns,[LayoutLink('a','b')],boxes),[])

    def test_clear_wire_adds_no_reroutes(self):
        ns=[node('a'),node('b',400,-100)]
        self.assertEqual(plan_internal_routes(ns,[LayoutLink('a','b')],{n.key:n.box for n in ns}),[])

    def test_routing_budget_is_bounded_and_reported(self):
        ns=[node('a'),node('b',800),node('fixed',350,30,width=200,height=180,selected=False)]
        stats={}
        routes=plan_internal_routes(ns,[LayoutLink('a','b')],{n.key:n.box for n in ns},budget=1,stats=stats)
        self.assertEqual(routes,[])
        self.assertFalse(stats['check_complete'])
        self.assertEqual(stats['pair_checks'],1)

    def test_boundary_junction_keeps_position(self):
        ns=[node('a'),node('r',250,-400,width=10,height=10,kind='REROUTE'),
            node('b',600),node('external',900,selected=False)]
        es=[LayoutLink('a','r',target_offset=5),LayoutLink('r','b',source_offset=5),LayoutLink('r','external',source_offset=5)]
        boxes={n.key:n.box for n in ns}
        self.assertEqual(align_internal_junctions(ns,es,boxes),boxes)

    def test_reported_frame_toggle_and_junctions(self):
        f=json.loads((Path(__file__).parent/'fixtures/frame_routing_layout.json').read_text())
        ns=[LayoutNode(**dict(n,box=Box(*n['box'],n['key']),location=tuple(n['location']))) for n in f['nodes']]
        es=[LayoutLink(**e) for e in f['links']]
        off=solve_layout(ns,es)
        on=solve_layout([replace(n,selected=True) if n.key=='Frame.020' else n for n in ns],es)
        for n in ns:
            if n.kind!='FRAME':self.assertEqual(on.locations[n.key],off.locations[n.key])
            if not n.selected and n.kind!='FRAME':self.assertEqual(off.locations[n.key],n.location)
        self.assertEqual(off.locations,solve_layout(repeat(ns,off),es).locations)
        for key in ('Reroute.097','Reroute.197'):
            edge=next(e for e in es if e.target==key)
            self.assertAlmostEqual(off.boxes[key].center_y,off.boxes[edge.source].top-edge.source_offset)
        routes=plan_internal_routes(ns,es,off.boxes)
        self.assertTrue(routes)
        before=layout_diagnostics(ns,es,{n.key:n.box for n in ns})
        after=layout_diagnostics(ns,es,off.boxes,routes=routes)
        self.assertLessEqual(after['estimated_wire_node_hits'],before['estimated_wire_node_hits'])
        self.assertEqual(after['node_overlaps'],0)


if __name__=='__main__':unittest.main()
