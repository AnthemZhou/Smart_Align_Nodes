import unittest

from smart_align_nodes.debug import (
    build_debug_report,
    centered_box,
    geometry_scale_ratio,
    node_kind_flags,
    node_link_lines,
    normalized_node_box,
    normalized_reroute_box,
    raw_box,
    selected_move_root,
)


class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Socket:
    def __init__(self, name):
        self.name = name
        self.identifier = name
        self.bl_idname = "NodeSocketFloat"
        self.type = "VALUE"
        self.is_output = False
        self.enabled = True
        self.hide = False
        self.hide_value = False
        self.is_unavailable = False
        self.is_multi_input = False
        self.is_linked = False
        self.link_limit = 1
        self.display_shape = "CIRCLE"
        self.location = None
        self.links = []


class Link:
    def __init__(self, from_node, from_socket, to_node, to_socket):
        self.from_node = from_node
        self.from_socket = from_socket
        self.to_node = to_node
        self.to_socket = to_socket
        self.is_valid = True
        self.is_muted = False


class Node:
    def __init__(self, name, bl_idname="ShaderNodeValue", node_type="VALUE"):
        self.name = name
        self.label = ""
        self.bl_idname = bl_idname
        self.type = node_type
        self.select = True
        self.hide = False
        self.mute = False
        self.show_options = True
        self.show_preview = False
        self.parent = None
        self.location = Vector(10, 20)
        self.location_absolute = Vector(30, 40)
        self.width = 120
        self.height = 80
        self.dimensions = Vector(130, 90)
        self.inputs = [Socket("Input")]
        self.outputs = [Socket("Output")]


class Tree:
    def __init__(self, nodes, links):
        self.name = "Tree"
        self.nodes = nodes
        self.links = links


class DebugReportTest(unittest.TestCase):
    def test_raw_box_uses_top_left_origin(self):
        box = raw_box(Vector(10, 20), 100, 50)

        self.assertEqual(box["left"], 10)
        self.assertEqual(box["right"], 110)
        self.assertEqual(box["top"], 20)
        self.assertEqual(box["bottom"], -30)

    def test_node_kind_flags_identify_frame_and_reroute(self):
        self.assertTrue(node_kind_flags(Node("Frame", "NodeFrame", "FRAME"))["is_frame"])
        self.assertTrue(node_kind_flags(Node("Reroute", "NodeReroute", "REROUTE"))["is_reroute"])

    def test_centered_box_uses_anchor_as_center(self):
        box = centered_box(Vector(20, 30), 10, 6)

        self.assertEqual(box["left"], 15)
        self.assertEqual(box["right"], 25)
        self.assertEqual(box["top"], 33)
        self.assertEqual(box["bottom"], 27)

    def test_normalized_box_derives_height_from_observed_ratio(self):
        node = Node("Scaled")
        node.location_absolute = Vector(40, -140)
        node.width = 140
        node.dimensions = Vector(280, 352)

        self.assertEqual(geometry_scale_ratio(node), 2)
        self.assertEqual(
            normalized_node_box(node),
            {
                "left": 40,
                "right": 180,
                "top": -140,
                "bottom": -316,
                "width": 140,
                "height": 176,
            },
        )

    def test_reroute_box_uses_reference_scale_and_center_anchor(self):
        node = Node("Reroute", "NodeReroute", "REROUTE")
        node.location_absolute = Vector(100, 50)
        node.dimensions = Vector(20, 20)

        self.assertEqual(
            normalized_reroute_box(node, 2),
            {
                "left": 95,
                "right": 105,
                "top": 55,
                "bottom": 45,
                "width": 10,
                "height": 10,
            },
        )

    def test_selected_move_root_uses_outermost_selected_frame(self):
        outer = Node("Outer", "NodeFrame", "FRAME")
        inner = Node("Inner", "NodeFrame", "FRAME")
        child = Node("Child")
        inner.parent = outer
        child.parent = inner

        self.assertIs(selected_move_root(child, [outer, inner, child]), outer)

    def test_node_links_match_blender_wrappers_by_stable_name(self):
        selected = Node("First")
        wrapped_from_node = Node("First")
        second = Node("Second")
        link = Link(wrapped_from_node, wrapped_from_node.outputs[0], second, second.inputs[0])
        tree = Tree([selected, second], [link])

        lines = node_link_lines(tree, selected)

        self.assertIn("First.Output -> Second.Input", lines[1])

    def test_report_contains_links_and_raw_geometry(self):
        first = Node("First")
        second = Node("Second")
        link = Link(first, first.outputs[0], second, second.inputs[0])
        first.outputs[0].links = [link]
        second.inputs[0].links = [link]
        tree = Tree([first, second], [link])

        report = build_debug_report(
            tree,
            [first, second],
            {
                "blender_version": "5.1.2",
                "ui_scale": 1.0,
                "pixel_size": 2,
                "view2d_scale": (1.5, 1.5),
            },
        )

        self.assertIn("Smart Align Nodes Debug", report)
        self.assertIn("report_version: 0.3.1", report)
        self.assertIn("tree_link_count: 1", report)
        self.assertIn("pixel_size: 2", report)
        self.assertIn("  hide: False", report)
        self.assertIn("reference_geometry_scale", report)
        self.assertIn("raw_box_from_width_height", report)
        self.assertIn("raw_box_from_dimensions", report)
        self.assertIn("normalized_box_candidate", report)
        self.assertIn("location_attribute_present", report)
        self.assertIn("First.Output -> Second.Input", report)


if __name__ == "__main__":
    unittest.main()
