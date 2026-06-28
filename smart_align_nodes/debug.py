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


def endpoint_text(node, socket):
    node_name = getattr(node, "name", "<none>")
    socket_name = getattr(socket, "name", "<none>")
    return f"{node_name}.{socket_name}"


def socket_lines(socket, index):
    lines = [
        (
            f"    [{index}] name={getattr(socket, 'name', '')!r}, "
            f"identifier={getattr(socket, 'identifier', '')!r}, "
            f"bl_idname={getattr(socket, 'bl_idname', '')!r}, "
            f"type={getattr(socket, 'type', '')!r}, "
            f"enabled={getattr(socket, 'enabled', None)}, "
            f"hide={getattr(socket, 'hide', None)}, "
            f"is_linked={getattr(socket, 'is_linked', None)}, "
            f"link_limit={getattr(socket, 'link_limit', None)}, "
            f"location={format_pair(getattr(socket, 'location', None))}"
        )
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
        if getattr(link, "from_node", None) is node or getattr(link, "to_node", None) is node:
            count += 1
            lines.append(
                "    "
                f"{endpoint_text(getattr(link, 'from_node', None), getattr(link, 'from_socket', None))} "
                "-> "
                f"{endpoint_text(getattr(link, 'to_node', None), getattr(link, 'to_socket', None))}"
            )
    if count == 0:
        lines.append("    none")
    return lines


def build_debug_report(tree, nodes):
    lines = [
        "Smart Align Nodes Debug",
        "=" * 24,
        f"node_tree: {getattr(tree, 'name', '<none>')}",
        f"selected_count: {len(nodes)}",
        "",
    ]

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
        box_from_width_height = raw_box(absolute or location, width, height)
        box_from_dimensions = None
        if dimensions_pair is not None:
            box_from_dimensions = raw_box(absolute or location, dimensions_pair[0], dimensions_pair[1])
        flags = node_kind_flags(node)

        lines.extend(
            [
                f"[{index}] {getattr(node, 'name', '<unnamed>')}",
                "-" * 24,
                f"  label: {getattr(node, 'label', '')!r}",
                f"  bl_idname: {getattr(node, 'bl_idname', '')!r}",
                f"  type: {getattr(node, 'type', '')!r}",
                f"  select: {getattr(node, 'select', None)}",
                f"  parent: {getattr(parent, 'name', None)!r}",
                f"  is_frame: {flags['is_frame']}",
                f"  is_reroute: {flags['is_reroute']}",
                f"  location: {format_pair(location)}",
                f"  location_absolute: {format_pair(absolute)}",
                f"  width: {width}",
                f"  height: {height}",
                f"  dimensions: {format_pair(dimensions)}",
                f"  raw_box_from_width_height: {format_box(box_from_width_height)}",
                f"  raw_box_from_dimensions: {format_box(box_from_dimensions)}",
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
