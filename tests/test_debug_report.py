import unittest

from smart_align_nodes.debug import build_debug_report, node_kind_flags, raw_box


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
        self.enabled = True
        self.hide = False
        self.is_linked = False
        self.link_limit = 1
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

    def test_report_contains_links_and_raw_geometry(self):
        first = Node("First")
        second = Node("Second")
        link = Link(first, first.outputs[0], second, second.inputs[0])
        first.outputs[0].links = [link]
        second.inputs[0].links = [link]
        tree = Tree([first, second], [link])

        report = build_debug_report(tree, [first, second])

        self.assertIn("Smart Align Nodes Debug", report)
        self.assertIn("raw_box_from_width_height", report)
        self.assertIn("raw_box_from_dimensions", report)
        self.assertIn("First.Output -> Second.Input", report)


if __name__ == "__main__":
    unittest.main()
