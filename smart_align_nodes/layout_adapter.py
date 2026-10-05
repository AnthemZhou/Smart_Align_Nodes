"""Read Blender once, solve without bpy, write absolute targets parent-first."""
import json
from time import perf_counter

from .debug import node_identity, node_kind_flags, reference_geometry_scale
from .context import layout_selected_names
from .geometry import node_box, local_location_for_absolute, layout_socket_y_anchors
from .layout import LayoutNode, LayoutLink
from .layout_route_adapter import routing_nodes, logical_links, link_index


def capture_layout(tree):
    started = perf_counter()
    link_data = link_index(tree)
    selected = layout_selected_names(tree)
    generated, reusable = routing_nodes(tree, link_data, selected)
    live = [n for n in tree.nodes if n.name not in generated | reusable]
    scale = reference_geometry_scale(live)
    if scale is None:
        raise ValueError("Node dimensions are not ready. Draw the nodes before arranging.")
    identities = {node_identity(node): node.name for node in live}
    snapshot, sockets = [], {}
    raw = []
    for node in live:
        key = node.name
        box = node_box(node, scale)
        if box is None:
            raise ValueError("Node dimensions are not ready: " + key)
        flags = node_kind_flags(node)
        kind = "FRAME" if flags["is_frame"] else "REROUTE" if flags["is_reroute"] else "NODE"
        location = tuple(float(v) for v in node.location_absolute)
        snapshot.append(LayoutNode(
            key, box, location, key in selected,
            identities.get(node_identity(node.parent)), kind,
            getattr(node, "shrink", True),
            any(word in node.bl_idname for word in ("Simulation", "Repeat", "Foreach")),
            bool(node.hide),
        ))
        raw.append({"name": key, "local": list(node.location), "absolute": location,
                    "dimensions_raw": list(node.dimensions), "width_raw": node.width,
                    "parent": node.parent.name if node.parent else None,
                    "kind": kind, "selected": bool(node.select), "hide": bool(node.hide),
                    "normalized_box": [box.left, box.right, box.top, box.bottom]})
        layout_anchors = dict(layout_socket_y_anchors(node, box))
        for direction in ("outputs", "inputs"):
            visible_index = 0
            for index, socket in enumerate(getattr(node, direction)):
                visible = socket.enabled and not socket.hide and not getattr(socket, "is_unavailable", False)
                identifier = socket.identifier or socket.name
                anchor_key = f"socket:{direction}:{identifier}:{visible_index}"
                anchor = layout_anchors.get(anchor_key, box.center_y)
                if kind == "REROUTE":
                    anchor = box.center_y
                sockets[node_identity(socket)] = (index, box.top-anchor, identifier)
                if visible:
                    visible_index += 1
    links = []
    for source, target, sort_id, path in logical_links(tree, generated | reusable, link_data):
        out_index, source_offset, source_socket = sockets[node_identity(source)]
        in_index, target_offset, target_socket = sockets[node_identity(target)]
        links.append(LayoutLink(
            identities[node_identity(source.node)], identities[node_identity(target.node)],
            out_index, in_index, int(sort_id), source_offset, target_offset,
            all(e.is_valid for e in path), any(e.is_muted for e in path),
            any(getattr(e, "is_hidden", False) for e in path), source_socket, target_socket,
            bool(getattr(target, 'is_multi_input', False)),
            tuple(e.to_node.name for e in path[:-1] if e.to_node.name in reusable),
        ))
    return snapshot, links, {"geometry_scale": scale, "raw_nodes": raw,
                             "explicit_selection": sorted(n.name for n in tree.nodes if n.select),
                             "layout_selection": sorted(selected),
                             "generated_reroutes": sorted(generated),
                             "reusable_reroutes": sorted(reusable),
                             "snapshot_ms": (perf_counter()-started)*1000}


def parent_first(tree):
    def depth(node):
        count, parent = 0, node.parent
        while parent is not None:
            count += 1
            parent = parent.parent
        return count
    return sorted(tree.nodes, key=lambda node: (depth(node), node.name))


def apply_locations(tree, locations):
    """Absolute targets include followers and fixed nodes; never add old deltas."""
    written = 0
    for node in parent_first(tree):
        if node.name in locations:
            target = locations[node.name]
            if any(abs(node.location_absolute[i]-target[i]) > 0.001 for i in (0,1)):
                node.location = local_location_for_absolute(node, *target)
                written += 1
    # Location RNA updates plus the operator's redraw are sufficient. Explicitly
    # tagging the entire tree would also invalidate unrelated evaluated geometry.
    return written


def capture_restore_state(tree):
    return {node.name: {"absolute": tuple(node.location_absolute),
                        "width": node.width, "height": node.height,
                        "shrink": getattr(node, "shrink", None)} for node in tree.nodes}


def restore_state(tree, state):
    for node in parent_first(tree):
        saved = state.get(node.name)
        if saved is None:
            continue
        if saved["shrink"] is not None:
            node.shrink = saved["shrink"]
            node.width = saved["width"]
            node.height = saved["height"]
    apply_locations(tree, {key: saved["absolute"] for key, saved in state.items()})


def format_layout_report(snapshot, links, plan, metadata):
    from dataclasses import asdict
    return json.dumps({"feature": "Smart Align Layout Preview", "metadata": metadata,
                       "links": [asdict(link) for link in links],
                       "target_absolute_locations": plan.locations,
                       "move_reasons": plan.reasons, "alignment_decisions": plan.alignment_decisions,
                       "partial_results": plan.partial_results, "warnings": plan.warnings,
                       "metrics": plan.metrics}, ensure_ascii=False, indent=2)
