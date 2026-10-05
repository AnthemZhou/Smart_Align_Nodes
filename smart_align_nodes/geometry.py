from dataclasses import dataclass

from .debug import (
    node_identity,
    node_kind_flags,
    normalized_node_box,
    normalized_reroute_box,
    reference_geometry_scale,
)


@dataclass(frozen=True)
class Box:
    left: float
    right: float
    top: float
    bottom: float
    name: str = ""
    is_reroute: bool = False
    socket_ys: tuple = ()
    is_frame: bool = False

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.top - self.bottom

    @property
    def center_x(self):
        return (self.left + self.right) / 2.0

    @property
    def center_y(self):
        return (self.top + self.bottom) / 2.0

    def translated(self, x, y):
        return Box(
            self.left + x,
            self.right + x,
            self.top + y,
            self.bottom + y,
            self.name,
            self.is_reroute,
            tuple((name, value + y) for name, value in self.socket_ys),
            self.is_frame,
        )


def box_from_mapping(
    mapping,
    name="",
    is_reroute=False,
    socket_ys=(),
    is_frame=False,
):
    if mapping is None:
        return None
    return Box(
        float(mapping["left"]),
        float(mapping["right"]),
        float(mapping["top"]),
        float(mapping["bottom"]),
        name,
        is_reroute,
        tuple(socket_ys),
        is_frame,
    )


def _visible_sockets(node, attribute):
    return [
        socket
        for socket in getattr(node, attribute, [])
        if getattr(socket, "enabled", True)
        and not getattr(socket, "hide", False)
        and not getattr(socket, "is_unavailable", False)
    ]


def _socket_y_anchors(node, box):
    sockets = []
    for direction in ("outputs", "inputs"):
        for index, socket in enumerate(_visible_sockets(node, direction)):
            identifier = getattr(socket, "identifier", "") or getattr(
                socket, "name", str(index)
            )
            if getattr(node, "hide", False):
                y = box.center_y
            else:
                # Blender does not expose final socket draw coordinates. The
                # first-row center is calibrated from Blender 5.1 at UI scale 2.
                y = box.top - 37.0 - index * 22.0
                y = min(box.top - 8.0, max(box.bottom + 8.0, y))
            sockets.append((f"socket:{direction}:{identifier}:{index}", y))
    return tuple(sockets)



def layout_socket_y_anchors(node, box):
    """Layout-only estimates; leave interactive snapping calibration unchanged.

    Blender 5.2 node_draw.cc/node_intern.hh: collapsed sockets use 10-unit
    rows around the center. Conventional inputs follow outputs and controls,
    ending 15 units above the bottom (17 with hidden trailing inputs).
    Unknown custom/panel/vector widgets keep the original conservative estimate.
    """
    conventional = getattr(node, 'bl_idname', '') in {
        'GeometryNodeSwitch', 'ShaderNodeSeparateXYZ', 'FunctionNodeCombineTransform',
        'FunctionNodeSeparateTransform', 'ShaderNodeMath', 'ShaderNodeVectorMath',
    }
    shared_rows = getattr(node, 'bl_idname', '') in {
        'FunctionNodeTransformPoint', 'FunctionNodeInvertMatrix', 'GeometryNodeInputPosition',
    }
    anchors = dict(_socket_y_anchors(node, box))
    for direction in ('inputs', 'outputs'):
        visible = _visible_sockets(node, direction)
        simple = all(not getattr(s, 'is_multi_input', False) and
                     (getattr(s, 'is_linked', False) or getattr(s, 'hide_value', False)
                      or getattr(s, 'type', '') not in {'VECTOR', 'ROTATION', 'MATRIX'})
                     for s in visible)
        for i, socket in enumerate(visible):
            identifier = getattr(socket, 'identifier', '') or getattr(socket, 'name', str(i))
            key = f'socket:{direction}:{identifier}:{i}'
            if getattr(node, 'hide', False):
                anchors[key] = box.center_y + 10.0*((len(visible)-1)/2-i)
            elif shared_rows:
                anchors[key] = max(box.bottom+8, box.top-34.0-22.0*i)
            elif direction == 'outputs' and conventional:
                anchors[key] = max(box.bottom+8, box.top-35.0-22.0*i)
            elif direction == 'inputs' and conventional and simple:
                # The conventional loop adds spacing if a socket has a next
                # RNA socket, even when that following socket is hidden.
                all_inputs = list(node.inputs)
                trailing_gap = 2.0 if visible[-1] != all_inputs[-1] else 0.0
                anchors[key] = min(box.top-8, box.bottom+15.0+trailing_gap+22.0*(len(visible)-1-i))
    return tuple(anchors.items())

def node_box(node, reference_scale=None):
    flags = node_kind_flags(node)
    if flags["is_reroute"]:
        mapping = normalized_reroute_box(node, reference_scale)
    else:
        mapping = normalized_node_box(node, reference_scale)
        if mapping is not None and reference_scale and getattr(node, "hide", False):
            x_offset = 1.0 - 1.0 / reference_scale
            y_offset = 1.0 + 5.0 / reference_scale
            mapping = {
                **mapping,
                "left": mapping["left"] + x_offset,
                "right": mapping["right"] + x_offset,
                "top": mapping["top"] + y_offset,
                "bottom": mapping["bottom"] + y_offset,
            }
    box = box_from_mapping(
        mapping,
        getattr(node, "name", ""),
        flags["is_reroute"],
        is_frame=flags["is_frame"],
    )
    if box is not None and (box.width <= 0.0 or box.height <= 0.0):
        return None
    if box is None or flags["is_reroute"]:
        return box
    return Box(
        box.left,
        box.right,
        box.top,
        box.bottom,
        box.name,
        box.is_reroute,
        _socket_y_anchors(node, box),
        box.is_frame,
    )


def union_boxes(boxes, name="Selection"):
    boxes = list(boxes)
    if not boxes:
        return None
    return Box(
        min(box.left for box in boxes),
        max(box.right for box in boxes),
        max(box.top for box in boxes),
        min(box.bottom for box in boxes),
        name,
        len(boxes) == 1 and boxes[0].is_reroute,
        (),
        len(boxes) == 1 and boxes[0].is_frame,
    )


def selected_move_roots(selected_nodes):
    selected_ids = {node_identity(node) for node in selected_nodes}
    roots = []
    for node in selected_nodes:
        parent = getattr(node, "parent", None)
        moves_with_selected_frame = False
        while parent is not None:
            if (
                node_identity(parent) in selected_ids
                and node_kind_flags(parent)["is_frame"]
            ):
                moves_with_selected_frame = True
                break
            parent = getattr(parent, "parent", None)
        if not moves_with_selected_frame:
            roots.append(node)
    return roots


def has_ancestor(node, ancestor_ids):
    parent = getattr(node, "parent", None)
    while parent is not None:
        if node_identity(parent) in ancestor_ids:
            return True
        parent = getattr(parent, "parent", None)
    return False


def ancestor_ids(nodes):
    result = set()
    for node in nodes:
        parent = getattr(node, "parent", None)
        while parent is not None:
            result.add(node_identity(parent))
            parent = getattr(parent, "parent", None)
    return result


def local_location_for_absolute(node, absolute_x, absolute_y):
    parent = getattr(node, "parent", None)
    if parent is None:
        return absolute_x, absolute_y
    parent_absolute = getattr(parent, "location_absolute", None)
    if parent_absolute is None:
        parent_absolute = getattr(parent, "location", None)
    if parent_absolute is None:
        return absolute_x, absolute_y
    return (
        absolute_x - float(parent_absolute.x),
        absolute_y - float(parent_absolute.y),
    )


def snap_geometry(tree, selected_nodes):
    all_nodes = list(getattr(tree, "nodes", []))
    scale = reference_geometry_scale(all_nodes)
    roots = selected_move_roots(selected_nodes)
    root_boxes = [node_box(node, scale) for node in roots]
    root_boxes = [box for box in root_boxes if box is not None]
    moving_box = union_boxes(root_boxes)

    selected_ids = {node_identity(node) for node in selected_nodes}
    moving_frame_ids = {
        node_identity(node)
        for node in roots
        if node_kind_flags(node)["is_frame"]
    }
    moving_ancestor_ids = ancestor_ids(roots)

    targets = []
    for node in all_nodes:
        if node_identity(node) in selected_ids:
            continue
        if node_identity(node) in moving_ancestor_ids:
            continue
        if has_ancestor(node, moving_frame_ids):
            continue
        box = node_box(node, scale)
        if box is not None:
            targets.append(box)

    return roots, moving_box, targets, scale
