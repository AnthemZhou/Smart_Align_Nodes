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
        )


def box_from_mapping(mapping, name="", is_reroute=False, socket_ys=()):
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
                y = box.top - 32.0 - index * 22.0
                y = min(box.top - 8.0, max(box.bottom + 8.0, y))
            sockets.append((f"socket:{direction}:{identifier}:{index}", y))
    return tuple(sockets)


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
    )
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
    parent_ids = {node_identity(getattr(node, "parent", None)) for node in roots}

    targets = []
    for node in all_nodes:
        if node_identity(node) in selected_ids:
            continue
        if has_ancestor(node, moving_frame_ids):
            continue
        if node_identity(getattr(node, "parent", None)) not in parent_ids:
            continue
        box = node_box(node, scale)
        if box is not None:
            targets.append(box)

    return roots, moving_box, targets, scale
