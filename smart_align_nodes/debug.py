from statistics import median


TEXT_BLOCK_NAME = "Smart Align Debug"


def value_to_tuple(value):
    if value is None:
        return None
    if hasattr(value, "x") and hasattr(value, "y"):
        return (float(value.x), float(value.y))
    try:
        items = list(value)
    except TypeError:
        return None
    if len(items) < 2:
        return None
    return (float(items[0]), float(items[1]))


def format_pair(value):
    pair = value_to_tuple(value)
    if pair is None:
        return "None"
    return f"x={pair[0]:.3f}, y={pair[1]:.3f}"


def raw_number(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def raw_box(location, width, height):
    origin = value_to_tuple(location)
    box_width = raw_number(width)
    box_height = raw_number(height)
    if origin is None or box_width is None or box_height is None:
        return None
    left, top = origin
    return {
        "left": left,
        "right": left + box_width,
        "top": top,
        "bottom": top - box_height,
        "width": box_width,
        "height": box_height,
    }


def centered_box(location, width, height):
    center = value_to_tuple(location)
    box_width = raw_number(width)
    box_height = raw_number(height)
    if center is None or box_width is None or box_height is None:
        return None
    center_x, center_y = center
    half_width = box_width / 2.0
    half_height = box_height / 2.0
    return {
        "left": center_x - half_width,
        "right": center_x + half_width,
        "top": center_y + half_height,
        "bottom": center_y - half_height,
        "width": box_width,
        "height": box_height,
    }


def format_box(box):
    if box is None:
        return "None"
    return (
        f"left={box['left']:.3f}, right={box['right']:.3f}, "
        f"top={box['top']:.3f}, bottom={box['bottom']:.3f}, "
        f"width={box['width']:.3f}, height={box['height']:.3f}"
    )


def node_kind_flags(node):
    bl_idname = getattr(node, "bl_idname", "")
    node_type = getattr(node, "type", "")
    return {
        "is_frame": bl_idname == "NodeFrame" or node_type == "FRAME",
        "is_reroute": bl_idname == "NodeReroute" or node_type == "REROUTE",
    }


def geometry_scale_ratio(node):
    if node_kind_flags(node)["is_reroute"]:
        return None
    dimensions = value_to_tuple(getattr(node, "dimensions", None))
    width = raw_number(getattr(node, "width", None))
    if dimensions is None or width is None or width <= 0.0 or dimensions[0] <= 0.0:
        return None
    return dimensions[0] / width


def normalized_node_box(node, reference_scale=None):
    flags = node_kind_flags(node)
    if flags["is_reroute"]:
        return None
    location = getattr(node, "location_absolute", None)
    if location is None:
        location = getattr(node, "location", None)
    dimensions = value_to_tuple(getattr(node, "dimensions", None))
    ratio = reference_scale or geometry_scale_ratio(node)
    if dimensions is None or ratio is None or ratio <= 0.0:
        return None
    return raw_box(
        location,
        dimensions[0] / ratio,
        dimensions[1] / ratio,
    )


def normalized_reroute_box(node, reference_scale):
    if not node_kind_flags(node)["is_reroute"]:
        return None
    dimensions = value_to_tuple(getattr(node, "dimensions", None))
    if dimensions is None or reference_scale is None or reference_scale <= 0.0:
        return None
    location = getattr(node, "location_absolute", None)
    if location is None:
        location = getattr(node, "location", None)
    return centered_box(
        location,
        dimensions[0] / reference_scale,
        dimensions[1] / reference_scale,
    )


def node_identity(node):
    if node is None:
        return None
    as_pointer = getattr(node, "as_pointer", None)
    if callable(as_pointer):
        try:
            return ("pointer", int(as_pointer()))
        except (ReferenceError, TypeError, ValueError):
            pass
    name = getattr(node, "name", None)
    if name is not None:
        return ("name", str(name))
    return ("python", id(node))


def nodes_match(first, second):
    return node_identity(first) == node_identity(second)


def endpoint_text(node, socket):
    node_name = getattr(node, "name", "<none>")
    socket_name = getattr(socket, "name", "<none>")
    socket_identifier = getattr(socket, "identifier", "")
    if socket_identifier and socket_identifier != socket_name:
        return f"{node_name}.{socket_name}[{socket_identifier}]"
    return f"{node_name}.{socket_name}"


def socket_lines(socket, index):
    is_unavailable = getattr(socket, "is_unavailable", None)
    enabled = getattr(socket, "enabled", None)
    hidden = getattr(socket, "hide", None)
    visible_candidate = enabled is not False and hidden is not True and is_unavailable is not True
    lines = [
        (
            f"    [{index}] name={getattr(socket, 'name', '')!r}, "
            f"identifier={getattr(socket, 'identifier', '')!r}, "
            f"bl_idname={getattr(socket, 'bl_idname', '')!r}, "
            f"type={getattr(socket, 'type', '')!r}, "
            f"is_output={getattr(socket, 'is_output', None)}, "
            f"enabled={enabled}, hide={hidden}, "
            f"hide_value={getattr(socket, 'hide_value', None)}, "
            f"is_unavailable={is_unavailable}, "
            f"is_multi_input={getattr(socket, 'is_multi_input', None)}, "
            f"visible_candidate={visible_candidate}, "
            f"is_linked={getattr(socket, 'is_linked', None)}, "
            f"link_limit={getattr(socket, 'link_limit', None)}, "
            f"display_shape={getattr(socket, 'display_shape', None)!r}"
        ),
        f"      location_attribute_present: {hasattr(socket, 'location')}",
        f"      location: {format_pair(getattr(socket, 'location', None))}",
    ]
    links = list(getattr(socket, "links", []))
    if not links:
        lines.append("      links: none")
        return lines

    for link_index, link in enumerate(links):
        lines.append(
            "      "
            f"link[{link_index}]: "
            f"{endpoint_text(getattr(link, 'from_node', None), getattr(link, 'from_socket', None))} "
            "-> "
            f"{endpoint_text(getattr(link, 'to_node', None), getattr(link, 'to_socket', None))}, "
            f"is_valid={getattr(link, 'is_valid', None)}, "
            f"is_muted={getattr(link, 'is_muted', None)}"
        )
    return lines


def node_link_lines(tree, node):
    lines = ["  node_links:"]
    count = 0
    for link in getattr(tree, "links", []):
        from_node = getattr(link, "from_node", None)
        to_node = getattr(link, "to_node", None)
        if nodes_match(from_node, node) or nodes_match(to_node, node):
            count += 1
            lines.append(
                "    "
                f"{endpoint_text(from_node, getattr(link, 'from_socket', None))} "
                "-> "
                f"{endpoint_text(to_node, getattr(link, 'to_socket', None))}, "
                f"is_valid={getattr(link, 'is_valid', None)}, "
                f"is_muted={getattr(link, 'is_muted', None)}"
            )
    if count == 0:
        lines.append("    none")
    return lines


def parent_chain(node):
    chain = []
    parent = getattr(node, "parent", None)
    seen = set()
    while parent is not None:
        identity = node_identity(parent)
        if identity in seen:
            chain.append("<cycle>")
            break
        seen.add(identity)
        chain.append(getattr(parent, "name", "<unnamed>"))
        parent = getattr(parent, "parent", None)
    chain.reverse()
    return chain


def selected_move_root(node, selected_nodes):
    selected = {node_identity(item) for item in selected_nodes}
    root = node
    parent = getattr(node, "parent", None)
    while parent is not None:
        if node_identity(parent) in selected and node_kind_flags(parent)["is_frame"]:
            root = parent
        parent = getattr(parent, "parent", None)
    return root


def reference_geometry_scale(nodes):
    nodes = list(nodes)
    visible_ratios = [
        ratio
        for node in nodes
        if not getattr(node, "hide", False)
        for ratio in (geometry_scale_ratio(node),)
        if ratio is not None
    ]
    if visible_ratios:
        return median(visible_ratios)
    ratios = [
        ratio
        for ratio in (geometry_scale_ratio(node) for node in nodes)
        if ratio is not None
    ]
    return median(ratios) if ratios else None


def _runtime_value(source, name):
    return getattr(source, name, None) if source is not None else None


def _window_region(context):
    area = getattr(context, "area", None)
    for region in getattr(area, "regions", []):
        if getattr(region, "type", None) == "WINDOW":
            return region
    return None


def _view2d_scale(region):
    view2d = getattr(region, "view2d", None)
    if view2d is None:
        return None
    try:
        origin = view2d.view_to_region(0.0, 0.0, clip=False)
        x_sample = view2d.view_to_region(100.0, 0.0, clip=False)
        y_sample = view2d.view_to_region(0.0, 100.0, clip=False)
    except (AttributeError, OverflowError, RuntimeError, TypeError, ValueError):
        return None
    return (
        (float(x_sample[0]) - float(origin[0])) / 100.0,
        (float(y_sample[1]) - float(origin[1])) / 100.0,
    )


def collect_runtime_info(context, bpy_module):
    preferences = getattr(context, "preferences", None)
    system = getattr(preferences, "system", None)
    area = getattr(context, "area", None)
    region = getattr(context, "region", None)
    window_region = _window_region(context)
    return {
        "blender_version": _runtime_value(getattr(bpy_module, "app", None), "version_string"),
        "blender_version_tuple": _runtime_value(getattr(bpy_module, "app", None), "version"),
        "ui_scale": _runtime_value(system, "ui_scale"),
        "pixel_size": _runtime_value(system, "pixel_size"),
        "dpi": _runtime_value(system, "dpi"),
        "area_type": _runtime_value(area, "type"),
        "invoking_region_type": _runtime_value(region, "type"),
        "window_region_width": _runtime_value(window_region, "width"),
        "window_region_height": _runtime_value(window_region, "height"),
        "view2d_scale": _view2d_scale(window_region),
    }


def runtime_lines(runtime_info):
    runtime = runtime_info or {}
    lines = ["runtime:"]
    for key in (
        "blender_version",
        "blender_version_tuple",
        "ui_scale",
        "pixel_size",
        "dpi",
        "area_type",
        "invoking_region_type",
        "window_region_width",
        "window_region_height",
    ):
        lines.append(f"  {key}: {runtime.get(key)!r}")
    lines.append(f"  view2d_scale: {format_pair(runtime.get('view2d_scale'))}")
    return lines


def build_debug_report(tree, nodes, runtime_info=None):
    reference_scale = reference_geometry_scale(nodes)
    lines = [
        "Smart Align Nodes Debug",
        "=" * 24,
        "report_version: 0.4.2",
        f"node_tree: {getattr(tree, 'name', '<none>')}",
        f"selected_count: {len(nodes)}",
        f"tree_link_count: {len(getattr(tree, 'links', []))}",
        f"reference_geometry_scale: {reference_scale!r}",
        "reference_geometry_scale_basis: median(dimensions.x / width), excluding hidden nodes and Reroute when possible",
    ]
    lines.extend(runtime_lines(runtime_info))
    lines.append("")

    if not nodes:
        lines.append("No selected nodes.")
        return "\n".join(lines)

    for index, node in enumerate(nodes, 1):
        dimensions = getattr(node, "dimensions", None)
        dimensions_pair = value_to_tuple(dimensions)
        width = getattr(node, "width", None)
        height = getattr(node, "height", None)
        parent = getattr(node, "parent", None)
        location = getattr(node, "location", None)
        absolute = getattr(node, "location_absolute", None)
        box_origin = absolute if absolute is not None else location
        box_from_width_height = raw_box(box_origin, width, height)
        box_from_dimensions = None
        if dimensions_pair is not None:
            box_from_dimensions = raw_box(box_origin, dimensions_pair[0], dimensions_pair[1])
        flags = node_kind_flags(node)
        scale_ratio = geometry_scale_ratio(node)
        normalized_box = normalized_node_box(node)
        reroute_box = normalized_reroute_box(node, reference_scale)
        chain = parent_chain(node)
        move_root = selected_move_root(node, nodes)

        lines.extend(
            [
                f"[{index}] {getattr(node, 'name', '<unnamed>')}",
                "-" * 24,
                f"  label: {getattr(node, 'label', '')!r}",
                f"  bl_idname: {getattr(node, 'bl_idname', '')!r}",
                f"  type: {getattr(node, 'type', '')!r}",
                f"  select: {getattr(node, 'select', None)}",
                f"  hide: {getattr(node, 'hide', None)}",
                f"  mute: {getattr(node, 'mute', None)}",
                f"  show_options: {getattr(node, 'show_options', None)}",
                f"  show_preview: {getattr(node, 'show_preview', None)}",
                f"  parent: {getattr(parent, 'name', None)!r}",
                f"  parent_chain: {chain!r}",
                f"  frame_depth: {len(chain)}",
                f"  selected_move_root: {getattr(move_root, 'name', '<unnamed>')!r}",
                f"  is_frame: {flags['is_frame']}",
                f"  is_reroute: {flags['is_reroute']}",
                f"  location: {format_pair(location)}",
                f"  location_absolute: {format_pair(absolute)}",
                f"  width: {width}",
                f"  height: {height}",
                f"  dimensions: {format_pair(dimensions)}",
                f"  geometry_scale_ratio: {scale_ratio!r}",
                f"  raw_box_from_width_height: {format_box(box_from_width_height)}",
                f"  raw_box_from_dimensions: {format_box(box_from_dimensions)}",
                f"  normalized_box_candidate: {format_box(normalized_box)}",
                "  normalized_box_basis: location_absolute + dimensions / "
                "geometry_scale_ratio",
                f"  reroute_anchor_absolute: {format_pair(absolute) if flags['is_reroute'] else 'None'}",
                f"  reroute_box_candidate: {format_box(reroute_box)}",
                "  reroute_box_basis: centered dimensions / reference_geometry_scale",
                "  inputs:",
            ]
        )

        for socket_index, socket in enumerate(getattr(node, "inputs", [])):
            lines.extend(socket_lines(socket, socket_index))

        lines.append("  outputs:")
        for socket_index, socket in enumerate(getattr(node, "outputs", [])):
            lines.extend(socket_lines(socket, socket_index))

        lines.extend(node_link_lines(tree, node))
        lines.append("")

    return "\n".join(lines)


def write_report_to_text_block(bpy_module, report):
    text = bpy_module.data.texts.get(TEXT_BLOCK_NAME)
    if text is None:
        text = bpy_module.data.texts.new(TEXT_BLOCK_NAME)
    text.clear()
    text.write(report)
    return text
