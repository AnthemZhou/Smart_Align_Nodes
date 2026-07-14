import unittest

from smart_align_nodes.geometry import Box, node_box, selected_move_roots, union_boxes
from smart_align_nodes.snapping import find_snaps, guide_segments


class SnappingTest(unittest.TestCase):
    def test_collapsed_node_box_uses_rendered_dimensions(self):
        vector = type("Vector", (), {})
        location = vector()
        location.x = 40.0
        location.y = -140.0
        dimensions = vector()
        dimensions.x = 280.0
        dimensions.y = 56.0
        node = type(
            "Node",
            (),
            {
                "name": "Collapsed",
                "bl_idname": "GeometryNodeSetPosition",
                "type": "SET_POSITION",
                "hide": True,
                "width": 140.0,
                "location_absolute": location,
                "dimensions": dimensions,
            },
        )()

        result = node_box(node, 2.0)

        self.assertEqual(result.left, 40.5)
        self.assertEqual(result.right, 180.5)
        self.assertEqual(result.top, -136.5)
        self.assertEqual(result.bottom, -164.5)

    def test_selected_frame_is_only_movement_root_for_its_child(self):
        frame = type(
            "Node",
            (),
            {"name": "Frame", "bl_idname": "NodeFrame", "type": "FRAME", "parent": None},
        )()
        child = type(
            "Node",
            (),
            {
                "name": "Child",
                "bl_idname": "ShaderNodeValue",
                "type": "VALUE",
                "parent": frame,
            },
        )()

        self.assertEqual(selected_move_roots([frame, child]), [frame])

    def test_union_boxes_wraps_selection(self):
        result = union_boxes(
            [
                Box(0, 50, 100, 40, "A"),
                Box(80, 120, 80, 20, "B"),
            ]
        )

        self.assertEqual(result, Box(0, 120, 100, 20, "Selection"))

    def test_left_edges_snap_within_threshold(self):
        moving = Box(97, 147, 100, 50, "Moving")
        target = Box(100, 150, 20, -30, "Target")

        result = find_snaps(moving, [target], 5, 5, equal_spacing=False)

        self.assertEqual(result.correction_x, 3)
        self.assertEqual(result.x_candidate.kind, "alignment")
        self.assertEqual(result.x_candidate.moving_anchor, "left")

    def test_top_edges_snap_vertically(self):
        moving = Box(0, 50, 103, 53, "Moving")
        target = Box(100, 150, 100, 50, "Target")

        result = find_snaps(moving, [target], 5, 5, equal_spacing=False)

        self.assertEqual(result.correction_y, -3)
        self.assertEqual(result.y_candidate.moving_anchor, "top")

    def test_spacing_continues_existing_horizontal_gap(self):
        first = Box(0, 50, 100, 50, "First")
        second = Box(70, 120, 100, 50, "Second")
        moving = Box(137, 187, 100, 50, "Moving")

        result = find_snaps(moving, [first, second], 5, 5, equal_spacing=True)

        self.assertEqual(result.correction_x, 3)
        self.assertEqual(result.x_candidate.kind, "spacing")
        self.assertEqual(result.x_candidate.placement, "after")
        self.assertEqual(result.x_candidate.gap, 20)

    def test_spacing_centers_node_between_two_neighbors(self):
        first = Box(0, 50, 100, 50, "First")
        second = Box(150, 200, 100, 50, "Second")
        moving = Box(78, 118, 100, 50, "Moving")

        result = find_snaps(moving, [first, second], 5, 5, equal_spacing=True)

        self.assertEqual(result.correction_x, 2)
        self.assertEqual(result.x_candidate.kind, "spacing")
        self.assertEqual(result.x_candidate.placement, "between")
        self.assertEqual(result.x_candidate.gap, 30)

    def test_spacing_continues_existing_vertical_gap(self):
        first = Box(0, 50, 100, 50, "First")
        second = Box(0, 50, 30, -20, "Second")
        moving = Box(0, 50, -37, -87, "Moving")

        result = find_snaps(moving, [first, second], 5, 5, equal_spacing=True)

        self.assertEqual(result.correction_y, -3)
        self.assertEqual(result.y_candidate.kind, "spacing")
        self.assertEqual(result.y_candidate.placement, "after")
        self.assertEqual(result.y_candidate.gap, 20)

    def test_axis_constraint_disables_other_axis(self):
        moving = Box(97, 147, 103, 53, "Moving")
        target = Box(100, 150, 100, 50, "Target")

        result = find_snaps(
            moving,
            [target],
            5,
            5,
            equal_spacing=False,
            axis_constraint="x",
        )

        self.assertEqual(result.correction_x, 3)
        self.assertEqual(result.correction_y, 0)
        self.assertIsNone(result.y_candidate)

    def test_reroute_does_not_snap_to_normal_node_center(self):
        moving = Box(95, 105, 55, 45, "Reroute", True)
        target = Box(100, 150, 100, 50, "Node")

        result = find_snaps(moving, [target], 30, 30, equal_spacing=False)

        self.assertIsNone(result.x_candidate)
        self.assertIsNone(result.y_candidate)

    def test_reroute_snaps_vertically_to_normal_node_socket(self):
        moving = Box(95, 105, 55, 45, "Reroute", True)
        target = Box(
            120,
            170,
            100,
            0,
            "Node",
            False,
            (("socket:inputs:Vector:0", 55),),
        )

        result = find_snaps(moving, [target], 5, 5, equal_spacing=False)

        self.assertEqual(result.correction_y, 5)
        self.assertEqual(result.y_candidate.moving_anchor, "middle")
        self.assertEqual(
            result.y_candidate.target_anchor,
            "socket:inputs:Vector:0",
        )

    def test_reroutes_snap_by_center(self):
        moving = Box(95, 105, 55, 45, "Moving Reroute", True)
        target = Box(120, 130, 60, 50, "Target Reroute", True)

        result = find_snaps(moving, [target], 30, 10, equal_spacing=False)

        self.assertEqual(result.x_candidate.moving_anchor, "center")
        self.assertEqual(result.x_candidate.target_anchor, "center")
        self.assertEqual(result.correction_x, 25)

    def test_normal_nodes_do_not_snap_by_center(self):
        moving = Box(45, 95, 100, 50, "Moving")
        target = Box(20, 120, 20, -30, "Target")

        result = find_snaps(moving, [target], 5, 5, equal_spacing=False)

        self.assertIsNone(result.x_candidate)

    def test_alignment_guide_includes_all_collinear_targets(self):
        moving = Box(200, 250, 103, 53, "Moving")
        first = Box(0, 50, 100, 50, "First")
        second = Box(100, 150, 100, 20, "Second")

        result = find_snaps(moving, [first, second], 5, 5, equal_spacing=False)
        final_box = moving.translated(result.correction_x, result.correction_y)
        segments = guide_segments(result, final_box)

        self.assertEqual(len(result.y_candidate.references), 2)
        self.assertEqual(segments[0].start[0], -8.0)
        self.assertEqual(segments[0].end[0], 258.0)

    def test_spacing_requires_real_orthogonal_overlap(self):
        first = Box(0, 50, 100, 50, "First")
        second = Box(70, 120, 100, 50, "Second")
        moving = Box(137, 187, 45, -5, "Moving")

        result = find_snaps(moving, [first, second], 5, 5, equal_spacing=True)

        self.assertIsNone(result.x_candidate)

    def test_spacing_result_builds_two_measurement_guides(self):
        first = Box(0, 50, 100, 50, "First")
        second = Box(70, 120, 100, 50, "Second")
        moving = Box(137, 187, 100, 50, "Moving")
        result = find_snaps(moving, [first, second], 5, 5, equal_spacing=True)
        final_box = moving.translated(result.correction_x, result.correction_y)

        segments = guide_segments(result, final_box)
        horizontal_measurements = [
            segment
            for segment in segments
            if segment.kind == "spacing" and segment.start[1] == segment.end[1]
        ]

        self.assertEqual(len(horizontal_measurements), 2)
        self.assertTrue(all(segment.start[1] == 75 for segment in horizontal_measurements))
        self.assertTrue(all(segment.fade for segment in horizontal_measurements))
        ticks = [
            segment
            for segment in segments
            if segment.kind == "spacing" and segment.start[0] == segment.end[0]
        ]
        self.assertTrue(ticks)
        self.assertTrue(all(not segment.fade for segment in ticks))


if __name__ == "__main__":
    unittest.main()
