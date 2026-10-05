import unittest
from dataclasses import replace

from smart_align_nodes.geometry import Box
from smart_align_nodes.layout import LayoutNode, LayoutLink, LayoutSettings, solve_layout, overlaps, layout_diagnostics


def node(key, x=0, y=0, width=140, height=100, **kwargs):
    return LayoutNode(key, Box(x, x+width, y, y-height, key), (x, y), **kwargs)


def repeat(snapshot, plan):
    return [replace(n, box=plan.boxes[n.key], location=plan.locations[n.key]) for n in snapshot]


class LayoutTests(unittest.TestCase):
    def test_horizontal_gap_setting_changes_columns_without_repeat_drift(self):
        nodes=[node('a'),node('b',600),node('c',1200)]
        links=[LayoutLink('a','b'),LayoutLink('b','c')]
        for gap in (24,60,100,200,400):
            plan=self.assert_stable(nodes,links,settings=LayoutSettings(horizontal_gap=gap))
            self.assertAlmostEqual(plan.boxes['b'].left-plan.boxes['a'].right,gap)
            self.assertAlmostEqual(plan.boxes['c'].left-plan.boxes['b'].right,gap)

    def assert_stable(self, nodes, links, **kwargs):
        first = solve_layout(nodes, links, **kwargs)
        second = solve_layout(repeat(nodes, first), links, **kwargs)
        for key in first.locations:
            for i in (0, 1):
                self.assertAlmostEqual(first.locations[key][i], second.locations[key][i], places=5, msg=key)
        return first

    def test_chain_sizes_and_original_anchor(self):
        nodes = [node('a', 40, 50, width=400), node('b', 0, 100), node('c', 90, -5)]
        plan = self.assert_stable(nodes, [LayoutLink('a','b'), LayoutLink('b','c')])
        self.assertEqual(plan.boxes['a'].left, 0)
        self.assertEqual(plan.boxes['a'].top, 100)
        self.assertGreaterEqual(plan.boxes['b'].left, plan.boxes['a'].right+100)
        self.assertGreaterEqual(plan.boxes['c'].left, plan.boxes['b'].right+100)

    def test_output_order_beats_name_and_initial_y(self):
        nodes = [node('a'), node('b', y=100), node('c', y=-300)]
        plan = self.assert_stable(nodes, [LayoutLink('a','b',output=2), LayoutLink('a','c',output=0)])
        self.assertGreater(plan.boxes['c'].bottom, plan.boxes['b'].top)

    def test_input_order_and_variable_heights(self):
        nodes = [node('a', height=900), node('b'), node('c')]
        plan = self.assert_stable(nodes, [LayoutLink('a','c',input=2), LayoutLink('b','c',input=0)])
        self.assertGreaterEqual(plan.boxes['b'].bottom-plan.boxes['a'].top, 50)

    def test_multi_input_high_sort_id_is_top(self):
        nodes = [node('a'), node('b'), node('c')]
        links = [LayoutLink('a','c',sort_id=0), LayoutLink('b','c',sort_id=9)]
        plan = self.assert_stable(nodes, links)
        self.assertGreater(plan.boxes['b'].top, plan.boxes['a'].top)
        self.assertEqual([e.sort_id for e in links], [0,9])

    def test_components_and_isolated_below(self):
        nodes = [node('a', y=500), node('b'), node('c', y=-900), node('d'), node('e')]
        plan = self.assert_stable(nodes, [LayoutLink('a','b'), LayoutLink('c','d')])
        self.assertGreaterEqual(min(plan.boxes[k].bottom for k in ('a','b'))-max(plan.boxes[k].top for k in ('c','d')), 100)
        self.assertGreaterEqual(min(plan.boxes[k].bottom for k in ('c','d'))-plan.boxes['e'].top, 100)

    def test_no_path_through_unselected_node(self):
        nodes = [node('a'), node('fixed', 300, selected=False), node('b')]
        plan = solve_layout(nodes, [LayoutLink('a','fixed'), LayoutLink('fixed','b')], LayoutSettings(avoid_fixed=False))
        self.assertEqual(plan.boxes['a'].top, plan.boxes['b'].top)
        self.assertEqual(plan.locations['fixed'], (300,0))

    def test_cycle_preserves_internal_offsets(self):
        nodes = [node('a', 10, 20), node('b', 400, -200)]
        plan = self.assert_stable(nodes, [LayoutLink('a','b'), LayoutLink('b','a')])
        self.assertEqual(plan.locations['b'][0]-plan.locations['a'][0], 390)
        self.assertTrue(any('Cycle' in warning for warning in plan.warnings))

    def test_frame_only_is_rigid_and_children_provide_external_ports(self):
        nodes = [node('f', width=300, height=300, kind='FRAME'),
                 node('child', 30,-60,selected=False,parent='f'), node('other', -500, 20)]
        plan = self.assert_stable(nodes, [LayoutLink('child','other')])
        self.assertEqual(plan.locations['child'][0]-plan.locations['f'][0],30)
        self.assertEqual(plan.locations['child'][1]-plan.locations['f'][1],-60)
        self.assertGreater(plan.boxes['other'].left,plan.boxes['f'].right)

    def test_only_selected_children_move_and_parent_kept(self):
        nodes = [node('f',width=800,height=800,selected=False,kind='FRAME'),
                 node('a',30,-70,parent='f'), node('b',30,-400,parent='f'),
                 node('fixed',600,-500,parent='f',selected=False)]
        plan = self.assert_stable(nodes,[LayoutLink('a','b')])
        self.assertEqual(plan.locations['f'],(0,0))
        self.assertEqual(plan.locations['fixed'],(600,-500))
        self.assertEqual(nodes[1].parent,'f')
        self.assertGreater(plan.boxes['b'].left,plan.boxes['a'].right)

    def test_selected_frame_and_children_inner_then_outer(self):
        nodes = [node('f', width=240,height=500,kind='FRAME'),
                 node('a',30,-60,parent='f'),node('b',30,-300,parent='f'),node('z',10,0)]
        links = [LayoutLink('a','b'),LayoutLink('b','z')]
        plan = self.assert_stable(nodes,links)
        self.assertGreater(plan.boxes['b'].left,plan.boxes['a'].right)
        self.assertGreater(plan.boxes['f'].width,240)
        self.assertGreater(plan.boxes['z'].left,plan.boxes['f'].right)

    def test_nested_frames_no_double_translation(self):
        nodes = [node('outer', width=400,height=700,kind='FRAME'),
                 node('inner',30,-60,width=250,height=550,kind='FRAME',parent='outer'),
                 node('a',60,-100,parent='inner'),node('b',60,-350,parent='inner'),
                 node('fixed',70,-500,parent='inner',selected=False),node('z',-1000)]
        links=[LayoutLink('a','b'),LayoutLink('b','z')]
        plan=self.assert_stable(nodes,links)
        # A can move inside Inner under scoped boundary alignment. Compare the
        # whole subtree against the same solve without the extra outer wrapper:
        # fixed descendants must receive exactly the same outer translation.
        without_outer=solve_layout([replace(n,selected=False) if n.key=='outer' else n
                                    for n in nodes],links)
        delta=tuple(plan.locations['inner'][i]-without_outer.locations['inner'][i] for i in (0,1))
        for key in ('a','b','fixed'):
            self.assertEqual(tuple(plan.locations[key][i]-without_outer.locations[key][i] for i in (0,1)),delta)

    def test_frame_aggregation_cycle_is_bounded(self):
        nodes=[node('f',width=400,height=500,kind='FRAME'),node('a',30,-50,parent='f',selected=False),
               node('b',30,-250,parent='f',selected=False),node('z',500)]
        plan=solve_layout(nodes,[LayoutLink('a','z'),LayoutLink('z','b')])
        self.assertTrue(plan.warnings)

    def test_manual_frame_does_not_shrink(self):
        nodes=[node('f',width=1000,height=1000,kind='FRAME',shrink=False),
               node('a',30,-60,parent='f'),node('b',300,-400,parent='f')]
        plan=solve_layout(nodes,[LayoutLink('a','b')])
        self.assertGreaterEqual(plan.boxes['f'].width,1000)
        self.assertGreaterEqual(plan.boxes['f'].height,1000)

    def test_reroute_chain_has_no_full_extra_columns(self):
        nodes=[node('a'),node('r',width=10,height=10,kind='REROUTE'),
               node('s',width=10,height=10,kind='REROUTE'),node('b')]
        links=[LayoutLink('a','r'),LayoutLink('r','s',source_offset=5,target_offset=5),LayoutLink('s','b')]
        plan=self.assert_stable(nodes,links)
        self.assertEqual(plan.boxes['b'].left-plan.boxes['a'].right,100)
        self.assertLess(plan.boxes['r'].center_x,plan.boxes['s'].center_x)
        self.assertEqual(plan.boxes['r'].center_y,plan.boxes['a'].top-37)

    def test_reroute_branch_and_fixed_reroute(self):
        nodes=[node('a'),node('r',width=10,height=10,kind='REROUTE'),
               node('b'),node('c'),node('fixed',900,selected=False,kind='REROUTE')]
        links=[LayoutLink('a','r'),LayoutLink('r','b',source_offset=5),
               LayoutLink('r','c',source_offset=5),LayoutLink('c','fixed')]
        plan=self.assert_stable(nodes,links)
        self.assertEqual(plan.locations['fixed'],(900,0))
        self.assertGreater(plan.boxes['b'].left,plan.boxes['r'].right)

    def test_fixed_obstacle_avoidance_is_stable_and_optional(self):
        nodes=[node('a'),node('b'),node('fixed',240,selected=False)]
        links=[LayoutLink('a','b')]
        plan=self.assert_stable(nodes,links)
        self.assertFalse(overlaps(plan.boxes['b'],plan.boxes['fixed']))
        self.assertEqual(plan.locations['fixed'],(240,0))
        disabled=solve_layout(nodes,links,LayoutSettings(avoid_fixed=False))
        self.assertTrue(overlaps(disabled.boxes['b'],disabled.boxes['fixed']))
        self.assertGreater(disabled.metrics['fixed_conflicts'],0)

    def test_selection_order_does_not_change_result(self):
        nodes=[node('a'),node('b'),node('c')]
        links=[LayoutLink('a','b'),LayoutLink('a','c')]
        self.assertEqual(solve_layout(nodes,links).locations,
                         solve_layout(list(reversed(nodes)),list(reversed(links))).locations)

    def test_invalid_muted_links_retained_but_not_used_for_flow(self):
        nodes=[node('a'),node('b')]
        links=[LayoutLink('a','b',muted=True),LayoutLink('b','a',valid=False)]
        plan=solve_layout(nodes,links)
        self.assertEqual(plan.boxes['a'].top,plan.boxes['b'].top)
        self.assertEqual(plan.metrics['links'],2)

    def test_hidden_link_still_contributes_flow(self):
        plan=solve_layout([node('a'),node('b')],[LayoutLink('a','b',hidden=True)])
        self.assertGreater(plan.boxes['b'].left,plan.boxes['a'].right)

    def test_invalid_geometry_cancels_instead_of_using_zero(self):
        for bad in [node('a',height=0),node('a',x=float('nan'))]:
            with self.assertRaises(ValueError):
                solve_layout([bad],[])

    def test_zone_connected_component_is_rigid(self):
        nodes=[node('a',protected=True),node('b',400,-200)]
        plan=solve_layout(nodes,[LayoutLink('a','b')])
        self.assertEqual(plan.locations['b'],(400,-200))
        self.assertTrue(plan.warnings)

    def test_long_edge_reserves_lane_around_middle_node(self):
        nodes=[node('a'),node('b'),node('c')]
        links=[LayoutLink('a','b'),LayoutLink('b','c'),LayoutLink('a','c')]
        plan=self.assert_stable(nodes,links)
        self.assertLess(plan.boxes['b'].top,plan.boxes['a'].top-37)

    def test_1000_node_chain_uses_no_recursive_graph_walk(self):
        nodes=[node(str(i)) for i in range(1000)]
        links=[LayoutLink(str(i),str(i+1)) for i in range(999)]
        plan=solve_layout(nodes,links)
        self.assertGreater(plan.boxes['999'].left,plan.boxes['998'].right)

    def test_random_dags_repeat_without_progressive_sorting(self):
        from random import Random
        random = Random(42)
        for _case in range(100):
            nodes = [node(str(i), x=i*10) for i in range(12)]
            links = [LayoutLink(str(i), str(j), output=random.randrange(4), input=random.randrange(4))
                     for i in range(12) for j in range(i+1, 12) if random.random() < .15]
            self.assert_stable(nodes, links)

    def test_diagnostics_exclude_legal_frame_containment_and_report_budget(self):
        nodes = [node('f',width=400,height=400,kind='FRAME'),
                 node('a',30,-50,parent='f'),node('b',30,-60,parent='f')]
        boxes = {n.key:n.box for n in nodes}
        report = layout_diagnostics(nodes, [], boxes)
        self.assertEqual(report['node_overlaps'], 1)
        limited = layout_diagnostics(nodes, [], boxes, budget=1)
        self.assertFalse(limited['node_overlap_check_complete'])

    def test_many_fixed_obstacles_require_one_stable_downward_sweep(self):
        nodes = [node('a'), node('b')] + [node('fixed'+str(i),240,-150*i,selected=False) for i in range(50)]
        plan = self.assert_stable(nodes, [LayoutLink('a','b')])
        self.assertEqual(plan.metrics['fixed_conflicts'], 0)

    def test_partial_selection_improves_without_rebuilding_columns(self):
        nodes = [node('input', -240, selected=False), node('a'), node('b', 400, -200),
                 node('output', 800, selected=False)]
        links = [LayoutLink('input', 'a'), LayoutLink('a', 'b'), LayoutLink('b', 'output')]
        plan = self.assert_stable(nodes, links)
        self.assertGreater(plan.metrics['moved'], 0)
        self.assertLess(plan.metrics['height'], 300)
        for key in ('input', 'output'):
            self.assertEqual(plan.locations[key], next(n.location for n in nodes if n.key == key))

    def test_partial_external_branches_preserve_readability(self):
        import json
        from pathlib import Path
        from smart_align_nodes.geometry import union_boxes
        fixture = json.loads((Path(__file__).parent/'fixtures/partial_branch_layout.json').read_text())
        nodes = [LayoutNode(**dict(n, box=Box(*n['box'], n['key']), location=tuple(n['location'])))
                 for n in fixture['nodes']]
        links = [LayoutLink(**e) for e in fixture['links']]
        plan = self.assert_stable(nodes, links)
        before = layout_diagnostics(nodes, links, {n.key: n.box for n in nodes})
        after = layout_diagnostics(nodes, links, plan.boxes)
        bounds = union_boxes(n.box for n in nodes if n.selected)
        self.assertGreater(plan.metrics['moved'], 0)
        self.assertLessEqual(plan.metrics['width'], bounds.width + .1)
        self.assertLessEqual(plan.metrics['height'], bounds.height * 1.5)
        for metric in ('node_overlaps', 'endpoint_chord_crossings'):
            self.assertLessEqual(after[metric], before[metric])
        for n in nodes:
            if not n.selected or n.key in ('Reroute.084', 'Reroute.146'):
                self.assertEqual(plan.locations[n.key], n.location)
            if n.key in ('Position.004', 'Math.040', 'Math.041'):
                self.assertLess(abs(plan.locations[n.key][0]-n.location[0]), 150)
        # Structural readability now has priority over the wire-only score.
        self.assertLessEqual(after['estimated_wire_node_hits'], before['estimated_wire_node_hits'])
        for a,b in (('Switch.022','Switch.025'), ('Separate XYZ.002','Separate XYZ.003'),
                    ('Math.040','Math.041'), ('Math.038','Math.051')):
            self.assertAlmostEqual(plan.boxes[a].left, plan.boxes[b].left)
        for source,target in (('Separate XYZ.002','Math.051'),('Math.051','Switch.025')):
            edge=next(e for e in links if e.source==source and e.target==target)
            self.assertAlmostEqual(plan.boxes[source].top-edge.source_offset,
                                   plan.boxes[target].top-edge.target_offset)
        for a,b in (('Position.004','Transform Point'),('Transform Point','Separate XYZ.002'),
                    ('Separate Transform','Combine Transform')):
            self.assertAlmostEqual(plan.boxes[a].top,plan.boxes[b].top)
            self.assertEqual(plan.alignment_decisions[a]['vertical'],'top')
        self.assertEqual(plan.alignment_decisions['Math.051']['vertical'],'socket')
        self.assertAlmostEqual(plan.boxes['Math.040'].bottom-plan.boxes['Math.041'].top,50)
        reversed_plan = solve_layout(list(reversed(nodes)), list(reversed(links)))
        self.assertEqual(plan.locations, reversed_plan.locations)

    def test_adaptive_edges_and_socket_fallback(self):
        # (height, port offset) describes displayed card geometry. External end
        # keeps these cases on the local-layout path used in the user's example.
        cases = [((100,35),(120,60),False,'top'),
                 ((160,140),(100,85),False,'bottom'),
                 ((100,25),(120,95),False,'socket'),
                 ((100,35),(120,60),True,'socket'),
                 ((28,14),(120,70),False,'socket')]
        for a,b,collapsed,rule in cases:
            with self.subTest(rule=rule,collapsed=collapsed,a=a):
                nodes=[node('a',0,100,height=a[0],collapsed=collapsed),
                       node('b',300,40,height=b[0]),node('fixed',700,selected=False)]
                links=[LayoutLink('a','b',source_offset=a[1],target_offset=b[1]),
                       LayoutLink('b','fixed')]
                p=self.assert_stable(nodes,links)
                self.assertEqual(p.alignment_decisions['a']['vertical'],rule)
                self.assertAlmostEqual(p.alignment_decisions['a']['vertical_error'],0)
                if rule=='top': self.assertEqual(p.boxes['a'].top,p.boxes['b'].top)
                elif rule=='bottom': self.assertEqual(p.boxes['a'].bottom,p.boxes['b'].bottom)
                else: self.assertAlmostEqual(p.boxes['a'].top-a[1],p.boxes['b'].top-b[1])
                self.assertEqual(p.locations['fixed'],(700,0))
                self.assertEqual(p.locations,solve_layout(nodes[::-1],links[::-1]).locations)

    def test_full_layout_aligns_bottom_edges_in_both_height_orders(self):
        for a,b in ((100,160),(160,100)):
            with self.subTest(a=a,b=b):
                nodes=[node('a',height=a),node('b',height=b)]
                links=[LayoutLink('a','b',source_offset=a-20,target_offset=b-15)]
                p=self.assert_stable(nodes,links)
                self.assertAlmostEqual(p.boxes['a'].bottom,p.boxes['b'].bottom)

    def test_varied_partial_graphs_repeat_without_alignment_drift(self):
        from random import Random
        random=Random(17)
        for _case in range(100):
            nodes=[node(str(i),i*280,(i%3)*-200,width=random.choice([100,140,220]),
                        height=random.choice([28,80,100,160])) for i in range(8)]
            nodes.append(node('end',2600,selected=False))
            links=[LayoutLink(str(i),str(i+1),source_offset=min(nodes[i].box.height-10,35),
                              target_offset=min(nodes[i+1].box.height-10,60)) for i in range(7)]
            links.append(LayoutLink('7','end'))
            links.extend(LayoutLink(str(i),str(j),input=1) for i in range(6)
                         for j in range(i+2,8) if random.random()<.12)
            self.assert_stable(nodes,links)

    def test_parallel_merge_aligns_right_edges_for_unequal_widths(self):
        for partial in (False,True):
            with self.subTest(partial=partial):
                nodes=[node('a',0,100,width=140),node('b',20,-150,width=240),
                       node('merge',400,100),node('end',750,100,selected=not partial)]
                links=[LayoutLink('a','merge',input=0),LayoutLink('b','merge',input=1),
                       LayoutLink('merge','end')]
                p=self.assert_stable(nodes,links)
                self.assertEqual(p.boxes['a'].right,p.boxes['b'].right)
                self.assertGreaterEqual(p.boxes['a'].bottom-p.boxes['b'].top,50)
                self.assertGreater(p.boxes['merge'].left,p.boxes['a'].right)
                self.assertEqual(p.metrics['fixed_conflicts'],0)
                self.assertEqual(p.locations,solve_layout(nodes[::-1],links[::-1]).locations)
                if partial: self.assertEqual(p.alignment_decisions['a']['horizontal'],'right')

    def test_parallel_fanout_keeps_left_edges(self):
        nodes=[node('source',0,100),node('a',260,100,width=140),
               node('b',290,-150,width=240),node('end',800,selected=False)]
        links=[LayoutLink('source','a',output=0),LayoutLink('source','b',output=1),
               LayoutLink('a','end')]
        p=self.assert_stable(nodes,links)
        self.assertEqual(p.boxes['a'].left,p.boxes['b'].left)
        self.assertEqual(p.alignment_decisions['a']['horizontal'],'left')

    def test_socket_reference_style_retains_straight_main_wire(self):
        nodes=[node('a',0,100,height=100),node('b',300,40,height=120),
               node('end',700,selected=False)]
        links=[LayoutLink('a','b',source_offset=35,target_offset=60),LayoutLink('b','end')]
        p=self.assert_stable(nodes,links,settings=LayoutSettings(alignment_style='socket'))
        self.assertAlmostEqual(p.boxes['a'].top-35,p.boxes['b'].top-60)
        self.assertEqual(p.alignment_decisions['a']['vertical'],'socket')

    def test_partial_short_branch_stays_beside_consumer(self):
        nodes=[node('a',0,100),node('b',240,100),node('short',230,-100,height=28),
               node('merge',480,100),node('fixed',750,selected=False)]
        links=[LayoutLink('a','b'),LayoutLink('b','merge',input=0),
               LayoutLink('short','merge',input=1),LayoutLink('merge','fixed')]
        plan=self.assert_stable(nodes,links)
        self.assertEqual(plan.boxes['b'].left,plan.boxes['short'].left)
        self.assertGreater(plan.boxes['b'].left,plan.boxes['a'].right)
        self.assertGreaterEqual(plan.boxes['b'].bottom-plan.boxes['short'].top,50)

    def test_partial_alignment_survives_main_chain_obstacle(self):
        nodes=[node('a',0,150),node('b',300,-40),node('sink',550,0),
               node('out',850,selected=False),node('blocker',310,30,selected=False)]
        links=[LayoutLink('a','b'),LayoutLink('b','sink'),LayoutLink('sink','out')]
        plan=self.assert_stable(nodes,links)
        self.assertEqual(plan.boxes['a'].top,plan.boxes['b'].top)
        self.assertEqual(plan.boxes['b'].top,plan.boxes['sink'].top)
        self.assertEqual(plan.metrics['fixed_conflicts'],0)
        # A real blocker can override the terminal anchor, without drift.
        self.assertNotEqual(plan.locations['sink'][1],nodes[2].location[1])

    def test_partial_distant_helpers_do_not_pull_main_flow_down(self):
        nodes=[node('input',0,-1000),node('helper',240,-1000),
               node('main',480,0),node('sink',720,0),
               node('branch',480,-200),node('external',1000,selected=False)]
        links=[LayoutLink('input','helper'),LayoutLink('helper','main'),
               LayoutLink('main','sink'),LayoutLink('branch','sink',input=1),
               LayoutLink('sink','external')]
        plan=self.assert_stable(nodes,links)
        self.assertEqual(plan.locations['sink'],nodes[3].location)
        self.assertEqual(plan.boxes['main'].top,0)
        self.assertGreater(plan.boxes['helper'].top,-1000)
        self.assertGreaterEqual(plan.boxes['main'].bottom-plan.boxes['branch'].top,50)
        self.assertEqual(layout_diagnostics(nodes,links,plan.boxes)['node_overlaps'],0)

    def test_reported_uv_selection_preserves_terminal_height(self):
        import json
        from pathlib import Path
        fixture=json.loads((Path(__file__).parent/'fixtures/partial_anchor_layout.json').read_text())
        nodes=[LayoutNode(**dict(n,box=Box(*n['box'],n['key']),location=tuple(n['location'])))
               for n in fixture['nodes']]
        links=[LayoutLink(**dict(e,reroutes=tuple(e.get('reroutes',())))) for e in fixture['links']]
        settings=LayoutSettings(**fixture['settings'])
        plan=self.assert_stable(nodes,links,settings=settings)
        original={n.key:n for n in nodes}
        anchor=fixture['anchor']
        self.assertEqual(plan.locations[anchor],original[anchor].location)
        self.assertFalse(plan.warnings)
        self.assertTrue(all(r['method']=='structured' for r in plan.partial_results))
        for key in ('Switch.021','Math.001','Math.021','Math.039'):
            self.assertLess(abs(plan.locations[key][1]-original[key].location[1]),100)
        for n in nodes:
            if not n.selected:
                self.assertEqual(plan.locations[n.key],n.location)
        self.assertEqual(layout_diagnostics(nodes,links,plan.boxes)['node_overlaps'],0)
        children=[replace(n,selected=False) if n.key==fixture['frame'] else n for n in nodes]
        child_plan=solve_layout(children,links,settings)
        for n in children:
            if n.selected:self.assertEqual(plan.locations[n.key],child_plan.locations[n.key])
        selected={n.key for n in nodes if n.selected}
        slopes=[replace(e,source_offset=e.source_offset+5000) if e.source not in selected
                else replace(e,target_offset=e.target_offset-5000) if e.target not in selected
                else e for e in links]
        self.assertEqual(plan.locations,solve_layout(nodes,slopes,settings).locations)
        self.assertEqual(plan.locations,solve_layout(nodes[::-1],links[::-1],settings).locations)

    def test_partial_budget_exhaustion_keeps_input(self):
        nodes = [node('a'), node('b', 400, -200), node('fixed', 800, selected=False)]
        links = [LayoutLink('a', 'b'), LayoutLink('b', 'fixed')]
        plan = solve_layout(nodes, links, LayoutSettings(curve_pair_budget=0))
        self.assertEqual(plan.locations, {n.key: n.location for n in nodes})
        self.assertTrue(any('search limit' in message for message in plan.warnings))

    def test_partial_cycle_keeps_internal_positions(self):
        nodes = [node('a'), node('b', 400, -200), node('fixed', 800, selected=False)]
        links = [LayoutLink('a', 'b'), LayoutLink('b', 'a'), LayoutLink('b', 'fixed')]
        plan = self.assert_stable(nodes, links)
        self.assertEqual(plan.locations, {n.key: n.location for n in nodes})

    def test_external_wires_do_not_influence_partial_layout(self):
        nodes=[node('a'),node('b',400,-200),node('output',800,selected=False),
               node('wire_left',-240,-50,selected=False),node('wire_right',1000,-50,selected=False)]
        internal=LayoutLink('a','b')
        first=[internal,LayoutLink('b','output',target_offset=35)]
        # Changing boundary routing and adding unrelated wires cannot change
        # the selected layout or its warning diagnostics.
        other=[internal,LayoutLink('b','output',target_offset=900)]
        other += [LayoutLink('wire_left','wire_right',source_offset=i) for i in range(200)]
        a=self.assert_stable(nodes,first)
        b=self.assert_stable(nodes,other)
        self.assertEqual(a.locations,b.locations)
        self.assertEqual(layout_diagnostics(nodes,first,a.boxes),layout_diagnostics(nodes,other,b.boxes))

    def test_diagnostics_only_count_internal_wires_but_all_node_obstacles(self):
        nodes=[node('a',0,0,width=100),node('b',500,0,width=100),
               node('blocker',220,0,selected=False),node('external',800,0,selected=False)]
        boxes={n.key:n.box for n in nodes}
        external=[LayoutLink('a','external'),LayoutLink('blocker','external')]
        report=layout_diagnostics(nodes,external,boxes)
        self.assertEqual(report['estimated_wire_node_hits'],0)
        self.assertEqual(report['endpoint_chord_crossings'],0)
        self.assertEqual(report['internal_links_checked'],0)
        report=layout_diagnostics(nodes,external+[LayoutLink('a','b')],boxes)
        self.assertEqual(report['estimated_wire_node_hits'],1)
        self.assertEqual(report['internal_links_checked'],1)
        self.assertEqual(report['wire_scope'],'selection_internal')

    def test_selected_frame_includes_moving_descendant_wires(self):
        nodes=[node('frame',width=700,height=300,kind='FRAME'),
               node('a',20,-40,selected=False,parent='frame'),
               node('b',400,-40,selected=False,parent='frame')]
        report=layout_diagnostics(nodes,[LayoutLink('a','b')],{n.key:n.box for n in nodes})
        self.assertEqual(report['internal_links_checked'],1)
        self.assertEqual(report['node_overlaps'],0)

    def test_extent_failure_keeps_local_improvements(self):
        positions=[(34,160),(65,100),(-7,160),(-1,160),(5,100)]
        nodes=[node(str(i),i*190,y,height=h) for i,(y,h) in enumerate(positions)]
        nodes.append(node('fixed',1300,selected=False))
        links=[LayoutLink(str(i),str(i+1),source_offset=20,target_offset=positions[i+1][1]-15)
               for i in range(4)]+[LayoutLink('4','fixed')]
        p=self.assert_stable(nodes,links)
        self.assertEqual(p.partial_results[0]['reason'],'extent')
        self.assertEqual(p.partial_results[0]['method'],'local')
        self.assertGreater(p.metrics['moved'],0)
        self.assertLessEqual(p.metrics['height'],232)
        self.assertEqual(p.locations['fixed'],(1300,0))

    def test_one_block_over_budget_does_not_cancel_other_blocks(self):
        nodes=[node('a'),node('b',300,-200),node('c',0,-1000),node('d',300,-1200),
               node('fixed',900,selected=False)]
        links=[LayoutLink('a','b',input=i) for i in range(129)]
        links += [LayoutLink('c','d'),LayoutLink('d','fixed')]
        p=self.assert_stable(nodes,links)
        self.assertEqual(p.locations['a'],nodes[0].location)
        self.assertEqual(p.locations['b'],nodes[1].location)
        self.assertNotEqual(p.locations['c'],nodes[2].location)
        self.assertTrue(any(r['reason']=='search_budget' and r['method']=='preserved' for r in p.partial_results))
        self.assertTrue(any(r['moved']>0 for r in p.partial_results))
        self.assertEqual(p.locations,solve_layout(nodes[::-1],links[::-1]).locations)

    def test_reported_eight_node_selection_now_arranges(self):
        import json
        from pathlib import Path
        fixture=json.loads((Path(__file__).parent/'fixtures/partial_eight_layout.json').read_text())
        nodes=[LayoutNode(**dict(n,box=Box(*n['box'],n['key']),location=tuple(n['location']))) for n in fixture['nodes']]
        links=[LayoutLink(**e) for e in fixture['links']]
        p=self.assert_stable(nodes,links)
        # The terminal is the vertical anchor; arranging need not move it.
        self.assertEqual(p.metrics['moved'],7)
        terminal=next(n for n in nodes if n.key=='Transform Point.001')
        self.assertEqual(p.locations[terminal.key],terminal.location)
        self.assertFalse(p.warnings)
        before=layout_diagnostics(nodes,links,{n.key:n.box for n in nodes})
        after=layout_diagnostics(nodes,links,p.boxes)
        self.assertEqual(after['node_overlaps'],0)
        self.assertLess(after['estimated_wire_node_hits'],before['estimated_wire_node_hits'])
        self.assertEqual(after['internal_links_checked'],9)
        for n in nodes:
            if not n.selected:self.assertEqual(p.locations[n.key],n.location)
        self.assertEqual(p.locations,solve_layout(nodes[::-1],links[::-1]).locations)

    def test_partial_hidden_cycle_is_preserved(self):
        nodes = [node('a'), node('b', 400, -200), node('fixed', 800, selected=False)]
        links = [LayoutLink('a', 'b'), LayoutLink('b', 'a', hidden=True), LayoutLink('b', 'fixed')]
        plan = self.assert_stable(nodes, links)
        self.assertEqual(plan.locations, {n.key: n.location for n in nodes})


if __name__ == '__main__':
    unittest.main()
