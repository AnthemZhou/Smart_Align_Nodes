def node_tree_from_context(context):
    space = getattr(context, "space_data", None)
    if getattr(space, "type", None) == "NODE_EDITOR":
        tree = getattr(space, "edit_tree", None) or getattr(space, "node_tree", None)
        if tree is not None:
            return tree

    area = getattr(context, "area", None)
    if getattr(area, "type", None) == "NODE_EDITOR":
        for space in getattr(area, "spaces", []):
            if getattr(space, "type", None) == "NODE_EDITOR":
                tree = getattr(space, "edit_tree", None) or getattr(space, "node_tree", None)
                if tree is not None:
                    return tree

    return None


def selected_nodes_from_context(context):
    tree = node_tree_from_context(context)
    if tree is None:
        return None, []
    return tree, [node for node in tree.nodes if getattr(node, "select", False)]


def layout_selected_names(tree):
    """Expand selected Frames recursively without changing Blender selection."""
    from collections import defaultdict
    children = defaultdict(list)
    selected, pending = set(), []
    for node in tree.nodes:
        if node.parent is not None:
            children[node.parent.name].append(node.name)
        if node.select:
            selected.add(node.name)
            if node.type == 'FRAME':
                pending.append(node.name)
    visited = set()
    while pending:
        parent = pending.pop()
        if parent in visited:
            continue
        visited.add(parent)
        selected.update(children[parent])
        pending.extend(children[parent])
    return selected
