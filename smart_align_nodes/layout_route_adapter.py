"""Blender routing transaction; preserve logical links and rollback on failure."""
from .layout_routing import ROUTE_TAG
from .geometry import local_location_for_absolute
from .context import layout_selected_names


def link_index(tree):
    # NodeSocket.links scans the complete tree in Blender. Index once instead.
    from collections import defaultdict
    links = list(tree.links)
    incoming, outgoing = defaultdict(list), defaultdict(list)
    for edge in links:
        incoming[edge.to_node.name].append(edge)
        outgoing[edge.from_node.name].append(edge)
    return links, incoming, outgoing


def generated_nodes(tree, index=None):
    """Only intact addon-owned one-in/one-out nodes are disposable routes."""
    links, incoming, outgoing = index or link_index(tree)
    candidates = {n.name for n in tree.nodes if n.type == 'REROUTE' and n.get(ROUTE_TAG, False)
                  and not n.label and not n.use_custom_color and set(n.keys()) <= {ROUTE_TAG}
                  and len(incoming[n.name]) == len(outgoing[n.name]) == 1}
    intact = set()
    for link in links:
        if link.from_node.name in candidates or link.to_node.name not in candidates:
            continue
        end, path = link, set()
        while end.to_node.name in candidates and end.to_node.name not in path:
            path.add(end.to_node.name)
            end = outgoing[end.to_node.name][0]
        if end.to_node.name not in candidates:
            intact.update(path)
    return intact


def logical_links(tree, generated, index=None):
    links, incoming, outgoing = index or link_index(tree)
    for link in links:
        if link.from_node.name in generated:
            continue
        end, seen = link, set()
        path = [link]
        while end.to_node.name in generated:
            key = end.to_node.name
            if key in seen:
                raise ValueError('Generated reroute cycle; layout cancelled.')
            seen.add(key)
            end = outgoing[key][0]
            path.append(end)
        yield link.from_socket, end.to_socket, end.multi_input_sort_id, path


def routing_nodes(tree, index=None, selected=None):
    """Collapse selected internal serial points, retaining their identity for reuse."""
    index = index or link_index(tree)
    selected = layout_selected_names(tree) if selected is None else selected
    _, incoming, outgoing = index
    generated = generated_nodes(tree, index)
    serial = {n.name for n in tree.nodes if n.type == 'REROUTE' and n.name in selected
              and n.name not in generated and len(incoming[n.name]) == len(outgoing[n.name]) == 1}
    reusable = set()
    for source, target, _, path in logical_links(tree, generated | serial, index):
        manual = [e.to_node.name for e in path[:-1] if e.to_node.name in serial]
        if (manual and len(manual) <= 16 and source.node.name in selected and target.node.name in selected
                and source.node != target.node and not target.is_multi_input
                and not any(word in n.bl_idname for n in (source.node,target.node)
                            for word in ('Simulation','Repeat','Foreach'))
                and all(e.is_valid and not e.is_muted and not e.is_hidden for e in path)):
            reusable.update(manual)
    return generated, reusable


def socket_index(socket):
    collection = socket.node.outputs if socket.is_output else socket.node.inputs
    return next(i for i,s in enumerate(collection) if s == socket)


def link_record(link):
    return (link.from_node.name, socket_index(link.from_socket),
            link.to_node.name, socket_index(link.to_socket), bool(link.is_muted))


class RouteTransaction:
    def __init__(self, tree, plans, selected):
        self.tree = tree
        index = link_index(tree)
        generated, reusable = routing_nodes(tree, index)
        self.plans = [p for p in plans if not tree.nodes[p['target']].inputs[p['input']].is_multi_input]
        by_edge = {(p['source'],p['output'],p['target'],p['input']):p for p in self.plans}
        self.operations = []
        self.removed = set()
        affected = set()
        self.reused = 0
        self.touched = set()
        for source, target, _, path in logical_links(tree, generated | reusable, index):
            key = (source.node.name,socket_index(source),target.node.name,socket_index(target))
            if (source.node.name not in selected or target.node.name not in selected
                    or target.is_multi_input
                    or not all(e.is_valid and not e.is_muted and not e.is_hidden for e in path)):
                continue
            existing = [e.to_node.name for e in path[:-1]]
            manual = [k for k in existing if k in reusable]
            plan = by_edge.get(key)
            # An unsuccessful search must not discard an existing manual path.
            if manual and plan is None:
                continue
            points = plan['points'] if plan else []
            pool = manual + [k for k in existing if k in generated]
            names = pool[:len(points)]
            names += [None] * (len(points)-len(names))
            if len(manual) > len(points):
                continue
            self.reused += sum(k is not None for k in names)
            if (names == existing and all(k is not None and
                    max(abs(tree.nodes[k].location_absolute[i]-point[i]) for i in (0,1)) < .01
                    for k,point in zip(names,points))):
                continue
            if not points and not existing:
                continue
            self.operations.append((key,points,names))
            affected.update(existing)
            self.removed.update(k for k in existing if k not in names and k in generated)
            self.touched.add((target.node.name,socket_index(target)))
        self.old_nodes = [dict(name=n.name,parent=n.parent.name if n.parent else None,
                               location=tuple(n.location_absolute),select=n.select,
                               socket_idname=n.socket_idname,generated=bool(n.get(ROUTE_TAG,False)))
                          for n in tree.nodes if n.name in affected]
        self.old_links = [link_record(e) for e in index[0]
                          if e.from_node.name in affected or e.to_node.name in affected
                          or (e.to_node.name,socket_index(e.to_socket)) in self.touched]
        self.created = []
        self.started = False
        self.existing_edges = {record[:4] for record in (link_record(e) for e in index[0])}
        self.link_writes = 0

    def apply(self):
        tree = self.tree
        self.started = True
        def connect(out, inp):
            key = (out.node.name,socket_index(out),inp.node.name,socket_index(inp))
            if key not in self.existing_edges:
                tree.links.new(out,inp)
                self.link_writes += 1
        for (source_key,out_index,target_key,in_index),points,names in self.operations:
            source, target = tree.nodes[source_key], tree.nodes[target_key]
            out, inp = source.outputs[out_index], target.inputs[in_index]
            parent = source.parent if source.parent == target.parent else None
            for (x,y),name in zip(points,names):
                if name is None:
                    n = tree.nodes.new('NodeReroute')
                    self.created.append(n.name)
                    n[ROUTE_TAG] = True
                    n.socket_idname = out.bl_idname
                    n.parent = parent
                    n.select = False
                else:
                    n = tree.nodes[name]
                n.location = local_location_for_absolute(n,x,y)
                connect(out,n.inputs[0])
                out = n.outputs[0]
            connect(out,inp)
        for name in self.removed:
            tree.nodes.remove(tree.nodes[name])
        if self.created or self.removed or self.link_writes:
            tree.update_tag()
        return len(self.created)

    def rollback(self):
        if not self.started or not self.operations:
            return
        tree = self.tree
        for name in self.created:
            if name in tree.nodes:
                tree.nodes.remove(tree.nodes[name])
        for saved in self.old_nodes:
            n = tree.nodes.get(saved['name'])
            if n is None:
                n = tree.nodes.new('NodeReroute'); n.name = saved['name']
                n[ROUTE_TAG] = saved['generated']; n.socket_idname = saved['socket_idname']
                n.parent = tree.nodes.get(saved['parent']) if saved['parent'] else None
            n.location = local_location_for_absolute(n,*saved['location'])
            n.select = saved['select']
        restore_inputs = self.touched | {(n['name'],0) for n in self.old_nodes}
        for e in list(tree.links):
            if (e.to_node.name,socket_index(e.to_socket)) in restore_inputs:
                tree.links.remove(e)
        for source,out,target,inp,muted in self.old_links:
            e = tree.links.new(tree.nodes[source].outputs[out],tree.nodes[target].inputs[inp])
            e.is_muted = muted
        tree.update_tag()
        self.started = False
