"""Deterministic, bpy-free one-shot layout in normalized canvas coordinates.

Socket offsets are estimates supplied by the adapter, never draw coordinates.
The solver returns absolute targets for all nodes so Frame rebasing is harmless.
"""
from dataclasses import dataclass, field, replace
from collections import Counter, defaultdict, deque
from bisect import bisect_left, bisect_right
from functools import lru_cache
from math import ceil, sqrt, isfinite, hypot
from statistics import median
from time import perf_counter

from .geometry import Box, union_boxes


@dataclass(frozen=True)
class LayoutNode:
    key: str
    box: Box
    location: tuple
    selected: bool = True
    parent: str = None
    kind: str = "NODE"
    shrink: bool = True
    protected: bool = False
    collapsed: bool = False


@dataclass(frozen=True)
class LayoutLink:
    source: str
    target: str
    output: int = 0
    input: int = 0
    sort_id: int = 0
    source_offset: float = 37.0
    target_offset: float = 37.0
    valid: bool = True
    muted: bool = False
    hidden: bool = False
    source_socket: str = ""
    target_socket: str = ""
    multi_input: bool = False
    reroutes: tuple = ()


@dataclass(frozen=True)
class LayoutSettings:
    horizontal_gap: float = 100.0
    vertical_gap: float = 50.0
    component_gap: float = 100.0
    avoid_fixed: bool = True
    sweeps: int = 4
    # Deterministic operation budget rather than machine-dependent early exits.
    curve_pair_budget: int = 100000
    # "socket" is a reference mode for regression comparisons.
    alignment_style: str = "adaptive"


@dataclass
class LayoutPlan:
    locations: dict
    boxes: dict
    warnings: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    reasons: dict = field(default_factory=dict)
    alignment_decisions: dict = field(default_factory=dict)
    partial_results: list = field(default_factory=list)


def frame_redraw_tolerance(geometry_scale, tolerance=0.1):
    """One measured draw unit for auto-sized containers, in canvas units."""
    if geometry_scale is None or not isfinite(geometry_scale) or geometry_scale <= 0:
        return tolerance
    return max(tolerance, 1.0 / geometry_scale)


def geometry_matches_plan(snapshot, links, plan, expected_links, tolerance=0.1,
                          geometry_scale=None):
    """A draw with unchanged target geometry needs no second layout solve."""
    # Rewiring through reroutes may reorder Blender's physical links without
    # changing any logical edge or port. Preserve duplicate-edge multiplicity.
    if Counter(links) != Counter(expected_links) or len(snapshot) != len(plan.locations):
        return False
    for node in snapshot:
        # Auto-size rebases unselected containers without affecting any child's
        # absolute target; those containers were not outer layout units.
        if node.kind == 'FRAME' and not node.selected:
            continue
        box = plan.boxes.get(node.key)
        target = plan.locations.get(node.key)
        if box is None or target is None:
            return False
        # Blender rounds auto-sized Frame bounds during drawing. Accept only
        # that container's measured rounding error; every child's absolute
        # location and dimensions still have to match the strict tolerance.
        allowed = (frame_redraw_tolerance(geometry_scale, tolerance)
                   if node.kind == 'FRAME' and node.shrink else tolerance)
        if any(abs(node.location[i]-target[i]) > allowed+1e-6 for i in (0,1)):
            return False
        if any(abs(getattr(node.box,attr)-getattr(box,attr)) > allowed+1e-6
               for attr in ('left','right','top','bottom')):
            return False
    return True


def overlaps(a, b, margin=0.0):
    return (a.left < b.right + margin and a.right > b.left - margin
            and a.bottom < b.top + margin and a.top > b.bottom - margin)


def _components(keys, links):
    adjacency = {key: set() for key in keys}
    for link in links:
        adjacency[link.source].add(link.target)
        adjacency[link.target].add(link.source)
    result, visited = [], set()
    for key in sorted(keys):
        if key in visited:
            continue
        queue, component = [key], []
        visited.add(key)
        while queue:
            current = queue.pop()
            component.append(current)
            for other in sorted(adjacency[current]):
                if other not in visited:
                    queue.append(other)
                    visited.add(other)
        result.append(sorted(component))
    return result


def _port_y(box, offset):
    return box.top - offset


@lru_cache(maxsize=4096)
def _curve_samples(x0, x3, y0, y3):
    """Reuse a wire's samples across obstacles, candidates and diagnostics."""
    handle = max(20.0, abs(x3 - x0) * 0.5)
    samples = []
    for step in range(1, 32):
        t = step / 32.0
        u = 1.0 - t
        x = u**3*x0 + 3*u*u*t*(x0+handle) + 3*u*t*t*(x3-handle) + t**3*x3
        y = (u**3+3*u*u*t)*y0 + (3*u*t*t+t**3)*y3
        samples.append((x, y))
    return (min(x for x,y in samples)-8, max(x for x,y in samples)+8,
            min(y for x,y in samples)-8, max(y for x,y in samples)+8, samples)


def _curve_hits(link, boxes, obstacle):
    """Sample an approximate cubic; no claim about Blender's exact wire shape."""
    a, b = boxes[link.source], boxes[link.target]
    left, right, bottom, top, samples = _curve_samples(
        a.right, b.left, a.top-link.source_offset, b.top-link.target_offset)
    if obstacle.left >= right or obstacle.right <= left or obstacle.bottom >= top or obstacle.top <= bottom:
        return False
    ol, or_, ob, ot = obstacle.left-8, obstacle.right+8, obstacle.bottom-8, obstacle.top+8
    return any(ol < x < or_ and ob < y < ot for x,y in samples)


def _alignment_rule(edge, nodes, boxes, settings):
    """Return source-top minus target-top and a deterministic visual rule.

    The decision depends on geometry and ports, never existing coordinates.
    This prevents invocation/redraw from switching alignment back and forth.
    """
    a, b = boxes[edge.source], boxes[edge.target]
    socket_delta = edge.source_offset-edge.target_offset
    if settings.alignment_style == "socket":
        return socket_delta, "socket"
    if (nodes[edge.source].kind != "NODE" or nodes[edge.target].kind != "NODE"
            or nodes[edge.source].collapsed or nodes[edge.target].collapsed
            or min(a.height, b.height) <= 40):
        return socket_delta, "socket"
    top_error = abs(socket_delta)
    bottom_delta = a.height-b.height
    bottom_error = abs(bottom_delta-socket_delta)
    # Bottom edges are useful for lower-port connections between unequal cards.
    if (edge.source_offset >= a.height*.55 and edge.target_offset >= b.height*.55
            and bottom_error <= 16 and top_error > bottom_error+8):
        return bottom_delta, "bottom"
    similar_cards = abs(a.height-b.height) <= max(24, max(a.height,b.height)*.25)
    # Permit a short sloped link to gain a clean row of similarly sized cards.
    # Opposite-end sockets and very different heights retain socket alignment.
    if similar_cards and top_error <= min(30, min(a.height,b.height)*.4):
        return 0.0, "top"
    return socket_delta, "socket"


def _column_rule(layer, successors, settings):
    """Unequal-width siblings feeding one consumer align their output edges."""
    if settings.alignment_style == "socket" or len(layer) < 2:
        return "left"
    consumers = [set(e.target for e in successors[k]) for k in layer]
    return "right" if set.intersection(*consumers) else "left"


def _layered(keys, links, nodes, boxes, settings, warnings):
    """Lay out one connected component, compressing unbranched reroutes."""
    incoming, outgoing = defaultdict(list), defaultdict(list)
    for edge in links:
        incoming[edge.target].append(edge)
        outgoing[edge.source].append(edge)
    chain_nodes = {key for key in keys if nodes[key].kind == "REROUTE"
                   and len(incoming[key]) == len(outgoing[key]) == 1}
    active = set(keys) - chain_nodes
    chains, edges = [], []
    for edge in links:
        if edge.source not in active:
            continue
        path, end, seen = [], edge, set()
        while end.target in chain_nodes and end.target not in seen:
            seen.add(end.target)
            path.append(end.target)
            end = outgoing[end.target][0]
        if end.target in active:
            edges.append(replace(edge, target=end.target, input=end.input,
                                 sort_id=end.sort_id, target_offset=end.target_offset))
            if path:
                chains.append((edges[-1], path))
    # Kahn's algorithm is iterative, including for 1000+ node chains.
    indegree = {key: 0 for key in active}
    successors = defaultdict(list)
    for edge in edges:
        indegree[edge.target] += 1
        successors[edge.source].append(edge.target)
    queue = deque(sorted(key for key in active if indegree[key] == 0))
    rank = dict.fromkeys(active, 0)
    ordered = []
    while queue:
        key = queue.popleft()
        ordered.append(key)
        for other in sorted(successors[key]):
            rank[other] = max(rank[other], rank[key] + 1)
            indegree[other] -= 1
            if indegree[other] == 0:
                queue.append(other)
    if len(ordered) != len(active) or not active or any(n.protected for n in (nodes[k] for k in keys)):
        warnings.append("Cycle or unverified zone: preserved connected component internally.")
        return {key: boxes[key] for key in keys}

    layers = defaultdict(list)
    for key in ordered:
        layers[rank[key]].append(key)
    for layer in layers.values():
        # A fresh canonical order prevents bounded sweeps from continuing the
        # previous invocation's partial sort (and gradually moving nodes).
        layer.sort()
    max_rank = max(layers)
    in_edges, out_edges = defaultdict(list), defaultdict(list)
    for edge in edges:
        in_edges[edge.target].append(edge)
        out_edges[edge.source].append(edge)
    # Port ordinal + multi-input order breaks ties before the original order.
    for sweep in range(settings.sweeps):
        forward = sweep % 2 == 0
        indices = range(1, max_rank+1) if forward else range(max_rank-1, -1, -1)
        positions = {key: i for layer in layers.values() for i, key in enumerate(layer)}
        for level in indices:
            def score(key):
                relevant = in_edges[key] if forward else out_edges[key]
                if not relevant:
                    return (positions[key], 0, 0, key)
                if forward:
                    values = [(positions[e.source], e.output, -e.sort_id) for e in relevant]
                else:
                    values = [(positions[e.target], e.input, -e.sort_id) for e in relevant]
                return (sum(v[0] for v in values)/len(values),
                        sum(v[1] for v in values)/len(values),
                        sum(v[2] for v in values)/len(values), key)
            layers[level].sort(key=score)
            positions.update({key: i for i, key in enumerate(layers[level])})

    result, x = {}, 0.0
    for level in range(max_rank+1):
        top = float('inf')
        column_width = max(boxes[key].width for key in layers[level])
        horizontal = _column_rule(layers[level], out_edges, settings)
        for key in layers[level]:
            box = boxes[key]
            # Prefer a common card edge or a straight wire, subject to lane spacing.
            desired = [result[e.source].top - _alignment_rule(e, nodes, boxes, settings)[0]
                       for e in in_edges[key] if e.source in result]
            y = min(top, median(desired)) if desired else min(top, 0.0)
            node_x = x + (column_width-box.width if horizontal == "right" else 0)
            result[key] = box.translated(node_x-box.left, y-box.top)
            top = y - box.height - settings.vertical_gap
        chain_length = max((len(path) for edge, path in chains
                            if rank[edge.source] == level), default=0)
        x += max(boxes[key].width for key in layers[level]) + max(
            settings.horizontal_gap, (chain_length+1)*24.0)

    # Reserve a lane for long edges bypassing an intermediate column. Two
    # bounded passes; moving a blocker down cannot cause same-column overlap.
    checks = 0
    for _pass in range(2):
        for edge in edges:
            if rank[edge.target] - rank[edge.source] < 2:
                continue
            for level in range(rank[edge.source]+1, rank[edge.target]):
                for key in layers[level]:
                    checks += 1
                    if checks > settings.curve_pair_budget:
                        break
                    if _curve_hits(edge, result, result[key]):
                        ceiling = min(_port_y(result[edge.source], edge.source_offset),
                                      _port_y(result[edge.target], edge.target_offset)) - settings.vertical_gap
                        dy = min(0.0, ceiling - result[key].top)
                        start = layers[level].index(key)
                        for following in layers[level][start:]:
                            result[following] = result[following].translated(0, dy)
                if checks > settings.curve_pair_budget:
                    break
            if checks > settings.curve_pair_budget:
                warnings.append("Curve avoidance budget reached; residual wire obstructions may remain.")
                break
        if checks > settings.curve_pair_budget:
            break
    for edge, path in chains:
        a, b = result[edge.source], result[edge.target]
        ay, by = _port_y(a, edge.source_offset), _port_y(b, edge.target_offset)
        for index, key in enumerate(path, 1):
            t = index / (len(path)+1)
            x = a.right + (b.left-a.right)*t
            y = ay + (by-ay)*t
            box = boxes[key]
            candidate = box.translated(x-box.center_x, y-box.center_y)
            # Reroutes are tiny obstacles, not a full extra layer.
            for _attempt in range(len(result)+1):
                blockers = [other for other in result.values() if overlaps(candidate, other, 8.0)]
                if not blockers:
                    break
                candidate = candidate.translated(0, min(other.bottom-16-candidate.top for other in blockers))
            result[key] = candidate
    return result



def _within_neighborhood(keys, original, targets, settings):
    """Bound translation as well as growth; a compact block can still jump far."""
    before = union_boxes(original[k] for k in keys)
    after = union_boxes(targets[k] for k in keys)
    pad_x = max(2 * settings.horizontal_gap, before.width * .35)
    pad_y = max(2 * settings.component_gap, before.height * .5)
    return (abs(after.center_x-before.center_x) <= pad_x
            and abs(after.center_y-before.center_y) <= pad_y
            and after.width <= max(before.width*1.35, before.width+2*settings.horizontal_gap)
            and after.height <= max(before.height*1.5, before.height+2*settings.component_gap))


def _existing_alignment(keys, links, nodes, boxes, tolerance=1.0):
    """Remember visible rows/columns and repeated gaps before local edits.

    Only separated, expanded cards sharing a parent participate. Either edge
    may represent an alignment, so adaptive left/right or top/bottom choices
    remain possible. Frames and reroutes are not ordinary card boundaries.
    """
    cards = sorted(k for k in keys if nodes[k].kind == 'NODE' and not nodes[k].collapsed)
    # A vertical stack of successive computation stages is not a column to
    # preserve. Only peers at the same downstream depth share an X constraint.
    moving = set(keys)
    outgoing, degree = defaultdict(list), dict.fromkeys(keys, 0)
    for edge in links:
        if edge.valid and not edge.muted and edge.source in moving and edge.target in moving:
            outgoing[edge.source].append(edge.target)
            degree[edge.target] += 1
    queue = deque(k for k in keys if not degree[k])
    order = []
    while queue:
        key = queue.popleft()
        order.append(key)
        for target in outgoing[key]:
            degree[target] -= 1
            if not degree[target]:
                queue.append(target)
    rank = {}
    for key in reversed(order):
        rank[key] = max((rank[target]+(nodes[target].kind != 'REROUTE')
                         for target in outgoing[key] if target in rank), default=0)
    aligned, spacing = [], []
    for axis, edges in (('x', ('left', 'right')), ('y', ('top', 'bottom'))):
        neighbors = defaultdict(set)
        for i, a in enumerate(cards):
            for b in cards[i+1:]:
                if nodes[a].parent != nodes[b].parent:
                    continue
                if axis == 'x' and (a not in rank or b not in rank or rank[a] != rank[b]):
                    continue
                first, second = boxes[a], boxes[b]
                separated = (first.bottom >= second.top or second.bottom >= first.top
                             if axis == 'x' else
                             first.right <= second.left or second.right <= first.left)
                error = min(abs(getattr(first, edge)-getattr(second, edge)) for edge in edges)
                if separated and error <= tolerance:
                    aligned.append((a, b, edges, error))
                    neighbors[a].add(b)
                    neighbors[b].add(a)
        # Check consecutive cards on an existing row/column without enumerating
        # every possible triple in a large partial selection.
        for center, peers in neighbors.items():
            ordered = sorted(peers | {center}, key=lambda k: (
                boxes[k].left if axis == 'y' else -boxes[k].top, k))
            index = ordered.index(center)
            if not 0 < index < len(ordered)-1:
                continue
            a, b, c = ordered[index-1:index+2]
            if c not in neighbors[a]:
                continue
            gaps = ((boxes[b].left-boxes[a].right, boxes[c].left-boxes[b].right)
                    if axis == 'y' else
                    (boxes[a].bottom-boxes[b].top, boxes[b].bottom-boxes[c].top))
            if min(gaps) >= 8 and abs(gaps[0]-gaps[1]) <= tolerance:
                spacing.append((a, b, c, axis, abs(gaps[0]-gaps[1])))
    return aligned, spacing


def _preserves_alignment(constraints, boxes):
    aligned, spacing = constraints
    for a, b, edges, error in aligned:
        if min(abs(getattr(boxes[a], edge)-getattr(boxes[b], edge))
               for edge in edges) > max(1.0, error)+.01:
            return False
    for a, b, c, axis, error in spacing:
        gaps = ((boxes[b].left-boxes[a].right, boxes[c].left-boxes[b].right)
                if axis == 'y' else
                (boxes[a].bottom-boxes[b].top, boxes[b].bottom-boxes[c].top))
        if min(gaps) < 8 or abs(gaps[0]-gaps[1]) > max(1.0, error)+.01:
            return False
    return True


def _partial_layout(keys, links, nodes, boxes, settings, decisions=None, status=None,
                    bounded=False, accept=None):
    """Keep independent successes; try bounded local edits for a rejected block."""
    moving = set(keys)
    internal = [e for e in links if e.valid and not e.muted
                and e.source in moving and e.target in moving]
    result, complete = dict(boxes), True
    for component in _components(keys, internal):
        choices, failure = {}, []
        target, ok = _partial_candidate(component, links, nodes, result, settings, choices, failure)
        if ok and bounded and not _within_neighborhood(component, boxes, target, settings):
            ok = False
            failure.append('displacement_limit')
        if ok and accept is not None and not accept({**result, **target}):
            ok = False
            failure.append('frame_clearance')
        if (ok and bounded and not _preserves_alignment(
                _existing_alignment(component, links, nodes, result), {**result, **target})):
            ok = False
            failure.append('alignment_regression')
        reason = failure[-1] if failure else 'local_search_limit'
        method = 'structured'
        if not ok and reason not in {'search_budget', 'diagnostic_budget', 'reroute_budget'}:
            # A compact, monotonic local pass changes only nodes it can improve.
            # It keeps the existing extent and checks internal wires/rectangles.
            target, ok = _conservative_partial_layout(component, links, nodes, result, settings,
                                                      preserve_anchor=bounded)
            method = 'local' if ok else 'preserved'
            choices.clear()
        elif not ok:
            method = 'preserved'
        if ok and bounded and not _within_neighborhood(component, boxes, target, settings):
            ok, method, reason = False, 'preserved', 'displacement_limit'
        if ok and accept is not None and not accept({**result, **target}):
            ok, method, reason = False, 'preserved', 'frame_clearance'
        if ok:
            result.update(target)
            if decisions is not None:
                decisions.update(choices)
        else:
            complete = False
        if status is not None:
            status.append({'nodes': component, 'method': method,
                           'reason': reason if failure or not ok else None,
                           'moved': sum(result[k] != boxes[k] for k in component)})
    return {k: result[k] for k in keys}, complete


def _floating_junctions(keys, links, nodes):
    moving = set(keys)
    result = set()
    for key in moving:
        if nodes[key].kind != 'REROUTE':
            continue
        ins = [e for e in links if e.target == key]
        outs = [e for e in links if e.source == key]
        if (len(ins) == 1 and outs and ins[0].source in moving
                and nodes[ins[0].source].kind == 'NODE'
                and all(e.target in moving and nodes[e.target].kind == 'NODE' for e in outs)):
            result.add(key)
    return result


def _partial_candidate(keys, links, nodes, boxes, settings, decisions=None, failure=None):
    """Pack a partial DAG into columns measured backwards from its consumers.

    Short externally-fed branches stay beside their consumer. Reroutes remain
    anchors; they do not consume columns. Socket alignment is subordinate to
    branch separation and fixed-node clearance. Each column is solved as a unit,
    not subsequently pulled apart by a wire-length optimizer.
    """
    def reject(reason):
        if failure is not None:
            failure.append(reason)
        return {k: boxes[k] for k in keys}, False

    moving = set(keys)
    flow = sorted((e for e in links if e.valid and not e.muted),
                  key=lambda e: (e.source, e.target, e.input, -e.sort_id, e.output))
    relevant = [e for e in flow if e.source in moving or e.target in moving]
    internal = [e for e in relevant if e.source in moving and e.target in moving]
    floating = _floating_junctions(keys, flow, nodes)
    scored_internal = [e for e in internal if e.source not in floating and e.target not in floating]
    if len(internal) > 128 or len(keys)*len(internal) > 100000:
        return reject("search_budget")
    snapshot = [replace(n, selected=n.key in moving) for n in nodes.values()]
    quality = layout_diagnostics(snapshot, scored_internal, boxes, settings.curve_pair_budget)
    if not all(quality[k] for k in ("node_overlap_check_complete", "wire_check_complete", "crossing_check_complete")):
        return reject("diagnostic_budget")
    active = {k for k in keys if nodes[k].kind != "REROUTE"}
    outgoing = defaultdict(list)
    for e in internal:
        outgoing[e.source].append(e)
    edges = []
    expansions = 0
    # Follow selected reroutes without moving boundary junctions or adding ranks.
    for key in sorted(active):
        pending = [(e, frozenset()) for e in outgoing[key]]
        while pending:
            expansions += 1
            if expansions > 10000:
                return reject("reroute_budget")
            edge, seen = pending.pop()
            if edge.target in active:
                edges.append(edge)
            elif edge.target in moving and edge.target not in seen:
                for other in outgoing[edge.target]:
                    pending.append((replace(edge, target=other.target, input=other.input,
                                            target_offset=other.target_offset, sort_id=other.sort_id),
                                    seen | {edge.target}))
    if not edges:
        return reject("no_internal_chain")
    # Selected boundary reroutes still own an input slot. Respect that slot
    # when choosing a main chain, even though the reroute takes no column.
    supplied_reroutes = {k for k in moving-active if not any(e.target == k for e in internal)}
    pending_reroutes = list(supplied_reroutes)
    while pending_reroutes:
        for e in outgoing[pending_reroutes.pop()]:
            if e.target in moving-active and e.target not in supplied_reroutes:
                supplied_reroutes.add(e.target)
                pending_reroutes.append(e.target)
    pinned_inputs = [e for e in internal if e.source in supplied_reroutes and e.target in active]
    incoming, successors = defaultdict(list), defaultdict(list)
    degree = dict.fromkeys(active, 0)
    for e in edges:
        incoming[e.target].append(e)
        successors[e.source].append(e)
        degree[e.target] += 1
    queue = deque(sorted(k for k in active if not degree[k]))
    order = []
    while queue:
        key = queue.popleft()
        order.append(key)
        for e in successors[key]:
            degree[e.target] -= 1
            if not degree[e.target]:
                queue.append(e.target)
    if len(order) != len(active):
        return reject("cycle")

    result = dict(boxes)
    alignment_choices = {}
    # Components retain their existing spatial relationship; a distant external
    # source is never treated as an extra leftmost column.
    for component in _components(active, edges):
        if len(component) < 2:
            continue
        members = set(component)
        rank = {}
        for key in reversed(order):
            if key in members:
                rank[key] = max((rank[e.target]+1 for e in successors[key]), default=0)
        layers = defaultdict(list)
        for key in component:
            layers[rank[key]].append(key)
        last = max(layers)
        widths = {r: max(boxes[k].width for k in layer) for r, layer in layers.items()}
        # Preserve terminal and left-edge anchors when there is already room.
        # A minimum readable gap may expand a cramped selection moderately.
        right_x = max(boxes[k].left for k in layers[0])
        left_x = min(boxes[k].left for k in component)
        available = (right_x-left_x-sum(widths[r] for r in range(1,last+1)))/last
        gap = min(settings.horizontal_gap, max(24.0, available))
        xs = {0: right_x}
        for r in range(1,last+1):
            xs[r] = xs[r-1]-widths[r]-gap

        # Boundary junctions retain X. Respect their direction while projecting
        # columns forward; a short gap may expand, but a branch cannot go back
        # across its fixed incoming reroute.
        for r in range(last, -1, -1):
            lower = max((boxes[e.source].right+24.0 for e in internal
                         if e.target in layers[r] and e.source not in active and e.source not in floating
                         and boxes[e.source].right <= boxes[e.target].left+.1),
                        default=float('-inf'))
            if r < last:
                lower = max(lower, xs[r+1]+widths[r+1]+24.0)
            xs[r] = max(xs[r], lower)

        horizontal = {r: _column_rule(layer, successors, settings) for r, layer in layers.items()}
        node_x = {k: xs[rank[k]] + (widths[rank[k]]-boxes[k].width
                                   if horizontal[rank[k]] == "right" else 0)
                  for k in component}
        # A port path gives deterministic branch order independent of current Y
        # and node names. At a merge input 0 precedes input 1, etc.
        paths, primary = {}, {}
        sinks = sorted(layers[0])
        for i, key in enumerate(sinks):
            paths[key] = (i,)
        for key in reversed(order):
            if key not in members or not successors[key]:
                continue
            # Prefer the nearest downstream stage over a long bypass connection.
            edge = max(successors[key], key=lambda e: (rank[e.target], tuple(-v for v in paths[e.target]), -e.input, e.sort_id, -e.output))
            primary[key] = edge
            paths[key] = paths[edge.target]+(edge.input, -edge.sort_id, edge.output)
        # Make one main chain per branch. A target accepts one aligned
        # connection; other inputs get their own lane. Shift whole chains when
        # clearing obstacles so fixing an upstream node cannot break alignment.
        main_input = {}
        for key in component:
            choices = ([e for e in incoming[key] if primary.get(e.source) == e]
                       + [e for e in pinned_inputs if e.target == key])
            if choices:
                main_input[key] = min(choices, key=lambda e: (e.input, -e.sort_id, e.output, e.source))
        chain_of, chains, relative = {}, {}, {}
        for key in reversed(order):
            if key not in members:
                continue
            edge = primary.get(key)
            if edge and main_input.get(edge.target) == edge:
                chain = chain_of[edge.target]
                relative[key] = relative[edge.target]+_alignment_rule(edge, nodes, boxes, settings)[0]
            else:
                chain, relative[key] = key, 0.0
                chains[chain] = []
            chain_of[key] = chain
            chains[chain].append(key)
        # A bypass can cross a card in its own main chain. Relax that card's
        # alignment before anchoring the chain, so avoidance stays deterministic
        # across invocations instead of shifting one node after the fact.
        for _pass in range(2):
            for e in edges:
                if chain_of[e.source] != chain_of[e.target] or rank[e.source]-rank[e.target] < 2:
                    continue
                chain = chains[chain_of[e.source]]
                trial = {k: boxes[k].translated(node_x[k]-boxes[k].left,
                                                relative[k]-boxes[k].top) for k in chain}
                for k in chain:
                    if rank[e.target] < rank[k] < rank[e.source] and _curve_hits(e, trial, trial[k]):
                        relative[k] = min(relative[e.source]-e.source_offset,
                                          relative[e.target]-e.target_offset)-16.0
                        trial[k] = boxes[k].translated(node_x[k]-boxes[k].left,
                                                       relative[k]-boxes[k].top)
        fixed = [box for k, box in boxes.items() if k not in moving and nodes[k].kind != "FRAME"]
        pinned = [boxes[k] for k in moving-active-floating]
        placed = set()
        # Consumer chains are placed first. This order also preserves input
        # socket order at forks and merges, including multi-input sort IDs.
        for tip in sorted(chains, key=lambda k: (paths[k], rank[k], k)):
            chain = chains[tip]
            edge = primary.get(tip)
            # Anchor a terminal chain at its consumer's original height. Taking
            # a median over upstream cards lets a distant helper/input branch
            # drag the main flow (and every lane below it) across the canvas.
            desired = (result[edge.target].top+_alignment_rule(edge, nodes, boxes, settings)[0]
                       if edge else boxes[tip].top)
            # Already placed parallel branches define the lane above this one.
            ceiling = min((result[other].bottom-settings.vertical_gap-relative[k]
                           for k in chain for other in placed if rank[k] == rank[other]),
                          default=float('inf'))
            y = min(ceiling, desired)
            def translated(top):
                return {k: boxes[k].translated(node_x[k]-boxes[k].left,
                                               top+relative[k]-boxes[k].top) for k in chain}
            obstacles = fixed + pinned + [result[k] for k in placed]
            candidates = ({y + step*settings.vertical_gap/2 for step in range(-4, 5)}
                          if edge else {y})
            for k in chain:
                probe = translated(y)[k]
                for b in obstacles:
                    if probe.left < b.right+8 and probe.right > b.left-8:
                        candidates.add(b.bottom-settings.vertical_gap-relative[k])
                        upper = b.top+boxes[k].height+settings.vertical_gap-relative[k]
                        if upper <= ceiling:
                            candidates.add(upper)
            safe = []
            for top in sorted(candidates):
                if top > ceiling:
                    continue
                candidate = translated(top)
                if not any(overlaps(b, o, 8) for b in candidate.values() for o in obstacles):
                    trial = {**result, **candidate}
                    known = placed | set(chain) | (moving-active-floating)
                    local_edges = [e for e in internal if not e.hidden
                                   and e.source in known and e.target in known]
                    hits = 0
                    for e in local_edges:
                        if e.source in candidate or e.target in candidate:
                            hits += sum(_curve_hits(e, trial, b) for k, b in trial.items()
                                        if k not in (e.source, e.target) and nodes[k].kind != "FRAME"
                                        and (k not in moving or k in known))
                        else:
                            hits += sum(_curve_hits(e, trial, b) for b in candidate.values())
                    safe.append((hits, abs(top-y), abs(top-desired), -top, candidate))
            if not safe:
                return reject("no_clearance")
            target = min(safe, key=lambda entry: entry[:4])[4]
            result.update(target)
            placed.update(chain)
        for key in component:
            edge = primary.get(key)
            delta, rule = _alignment_rule(edge, nodes, boxes, settings) if edge else (0, "anchor")
            error = abs(result[key].top-result[edge.target].top-delta) if edge else 0.0
            alignment_choices[key] = {
                "horizontal": horizontal[rank[key]], "vertical": rule,
                "target": edge.target if edge else None,
                "vertical_error": error, "vertical_satisfied": error < .1,
            }

    # Preserve an internal reroute's position along its own edge, rather than
    # leaving a detour behind when both of its endpoints were rearranged.
    for key in moving-active:
        ins = [e for e in flow if e.target == key]
        outs = [e for e in flow if e.source == key]
        if len(ins) == len(outs) == 1 and ins[0].source in active and outs[0].target in active:
            a, b = result[ins[0].source], result[outs[0].target]
            x = (a.right+b.left)/2
            y = (a.top-ins[0].source_offset+b.top-outs[0].target_offset)/2
            candidate = boxes[key].translated(x-boxes[key].center_x, y-boxes[key].center_y)
            if not any(overlaps(candidate, box, 8) for k, box in result.items()
                       if k != key and nodes[k].kind != "FRAME"):
                result[key] = candidate
    from .layout_routing import align_internal_junctions
    result = align_internal_junctions(snapshot, flow, result)
    original = union_boxes(boxes[k] for k in keys)
    bounds = union_boxes(result[k] for k in keys)
    if (bounds.width > max(original.width*1.35, original.width+2*settings.horizontal_gap)
            or bounds.height > max(original.height*1.5, original.height+2*settings.component_gap)):
        return reject("extent")
    after = layout_diagnostics(snapshot, scored_internal, result, settings.curve_pair_budget)
    before_back = sum(boxes[e.target].left < boxes[e.source].right-.1 for e in scored_internal)
    after_back = sum(result[e.target].left < result[e.source].right-.1 for e in scored_internal)
    if after['node_overlaps'] > quality['node_overlaps']:
        return reject('node_overlap')
    if after_back > before_back:
        return reject('backward_internal_links')
    if after['estimated_wire_node_hits'] > quality['estimated_wire_node_hits']:
        from .layout_routing import plan_internal_routes
        routes = plan_internal_routes(snapshot, scored_internal, result)
        routed_quality = layout_diagnostics(snapshot, scored_internal, result,
                                            settings.curve_pair_budget, routes=routes)
        if routed_quality['estimated_wire_node_hits'] > quality['estimated_wire_node_hits']:
            return reject('internal_wire_obstruction')
    if decisions is not None:
        decisions.update(alignment_choices)
    return {k: result[k] for k in keys}, True


def _conservative_partial_layout(keys, links, nodes, boxes, settings, preserve_anchor=False):
    """Improve a readable partial selection without rebuilding its columns.

    Boundary reroutes remain anchors. Only internal wires are scored. Every accepted step
    keeps overlaps, backwards links and estimated obstructions from increasing,
    stays within the original width/height, and reduces wire length/crossing cost.
    Iterate to a fixed point so redraw verification and repeated invocation do
    not continue an unfinished optimization. On budget exhaustion keep the input.
    Anchored Frame scopes also retain existing rows, peer columns, equal gaps
    and their top-left envelope instead of trading them for shorter wires.
    """
    moving = set(keys)
    ordering_edges = sorted((e for e in links if e.valid and not e.muted
                    and e.source in moving and e.target in moving),
                   key=lambda e: (e.source, e.target, e.output, e.input, e.sort_id,
                                  e.source_socket, e.target_socket, e.source_offset, e.target_offset))
    edges = [e for e in ordering_edges if not e.hidden]
    if len(ordering_edges) > 128 or len(keys)*len(ordering_edges) > 100000:
        return {k: boxes[k] for k in keys}, False
    # Anchored groups already have a readable neighborhood to retain. Other
    # scopes keep their existing free arrangement/repeated-reroute behavior.
    constraints = _existing_alignment(keys, links, nodes, boxes) if preserve_anchor else ([], [])
    row_members = {key for a, b, edges, _error in constraints[0]
                   if edges == ('top', 'bottom') for key in (a, b)}
    boundary = {k for e in links if e.valid and not e.muted and (e.source in moving) != (e.target in moving)
                for k in (e.source, e.target) if k in moving}
    pinned = {k for k in boundary if nodes[k].kind == "REROUTE"}
    # Cyclic components keep their internal arrangement, as in full layout.
    internal = [e for e in ordering_edges if e.source in moving and e.target in moving]
    for component in _components(keys, internal):
        members = set(component)
        indegree = dict.fromkeys(component, 0)
        successors = defaultdict(list)
        for edge in internal:
            if edge.source in members:
                indegree[edge.target] += 1
                successors[edge.source].append(edge.target)
        queue = deque(k for k in component if not indegree[k])
        count = 0
        while queue:
            key = queue.popleft()
            count += 1
            for other in successors[key]:
                indegree[other] -= 1
                if not indegree[other]:
                    queue.append(other)
        if count != len(component):
            pinned.update(component)
    original = union_boxes(boxes[k] for k in keys)
    work = dict(boxes)
    # Every accepted candidate stays inside the original selection envelope.
    # Even backwards cubic handles cannot reach fixed bodies beyond this padded
    # region; prune them once instead of revisiting the whole tree per candidate.
    pad_x = max(20, original.width/2)+8
    pad_y = max((abs(v) for e in edges for v in (e.source_offset,e.target_offset)), default=0)+8
    local_keys = [k for k,b in boxes.items() if k in moving or
                  (b.right >= original.left-pad_x and b.left <= original.right+pad_x
                   and b.top >= original.bottom-pad_y and b.bottom <= original.top+pad_y)]
    body_keys = [k for k in local_keys if nodes[k].kind != 'FRAME']
    snapshot = [replace(n, selected=n.key in moving) for n in nodes.values()]
    incoming, outgoing = defaultdict(list), defaultdict(list)
    for edge in ordering_edges:
        incoming[edge.target].append(edge)
        outgoing[edge.source].append(edge)

    def wire_cost(candidate):
        points = [(e, (candidate[e.source].right, candidate[e.source].top-e.source_offset),
                   (candidate[e.target].left, candidate[e.target].top-e.target_offset)) for e in edges]
        length = sum(hypot(b[0]-a[0], b[1]-a[1]) for _, a, b in points)
        backwards = sum(candidate[e.target].left < candidate[e.source].right-0.1 for e in ordering_edges)
        crossings = 0
        def orient(a, b, c):
            return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        for i, (edge, a, b) in enumerate(points):
            for other, c, d in points[i+1:]:
                if {edge.source, edge.target} & {other.source, other.target}:
                    continue
                crossings += int(orient(a,b,c)*orient(a,b,d)<0 and orient(c,d,a)*orient(c,d,b)<0)
        return length + settings.horizontal_gap*2*crossings, backwards

    ancestors = {}
    for key in moving:
        lineage, parent = set(), nodes[key].parent
        while parent in nodes:
            lineage.add(parent)
            parent = nodes[parent].parent
        ancestors[key] = lineage

    def local_counts(key):
        # Only these pairs change when one node moves; avoid rescanning the
        # whole graph for every candidate in a large tree with a small selection.
        overlap_count = sum(overlaps(work[key], work[other]) for other in local_keys
                            if other != key and other not in ancestors[key])
        hits = 0
        for edge in edges:
            if key in (edge.source, edge.target):
                hits += sum(_curve_hits(edge, work, work[other]) for other in body_keys
                            if other not in (edge.source, edge.target))
            else:
                hits += int(_curve_hits(edge, work, work[key]))
        return overlap_count, hits

    quality = layout_diagnostics(snapshot, edges, work, settings.curve_pair_budget)
    if not all(quality[k] for k in ("node_overlap_check_complete", "wire_check_complete", "crossing_check_complete")):
        return {k: boxes[k] for k in keys}, False
    cost, backwards = wire_cost(work)
    evaluations = 0
    for _pass in range(16):
        changed = False
        for key in sorted(moving - pinned):
            current = work[key]
            old_overlaps, old_hits = local_counts(key)
            xs, ys = {current.left}, {current.top}
            # Bring short branches towards their selected consumers. External
            # endpoints never constrain this local wire cost or alignment.
            for edge in incoming[key]:
                other = work[edge.source]
                if edge.source in moving:
                    xs.add(other.right + settings.horizontal_gap)
                ys.add(other.top-edge.source_offset+edge.target_offset)
                if edge.source in row_members:
                    ys.add(other.top-_alignment_rule(edge, nodes, work, settings)[0])
            for edge in outgoing[key]:
                other = work[edge.target]
                if edge.target in moving:
                    xs.add(other.left-current.width-settings.horizontal_gap)
                ys.add(other.top-edge.target_offset+edge.source_offset)
                if edge.target in row_members:
                    ys.add(other.top+_alignment_rule(edge, nodes, work, settings)[0])
            if len(ys) > 1:
                ys.add(median(ys - {current.top}))
            # Limit high-degree nodes to the nearest useful alternatives.
            xs = sorted(xs, key=lambda x: (abs(x-current.left), x))[:5]
            ys = sorted(ys, key=lambda y: (abs(y-current.top), y))[:6]
            best, best_cost, best_backwards, best_quality = current, cost, backwards, quality
            for x in xs:
                for y in ys:
                    if abs(x-current.left)+abs(y-current.top) < 0.1:
                        continue
                    evaluations += 1
                    if evaluations > 5000:
                        return {k: boxes[k] for k in keys}, False
                    candidate = current.translated(x-current.left, y-current.top)
                    work[key] = candidate
                    if not _preserves_alignment(constraints, work):
                        continue
                    bounds = union_boxes(work[k] for k in keys)
                    if preserve_anchor and (abs(bounds.left-original.left) > .1
                                            or abs(bounds.top-original.top) > .1):
                        continue
                    if bounds.width > original.width+0.1 or bounds.height > original.height+0.1:
                        continue
                    new_cost, new_backwards = wire_cost(work)
                    if new_cost >= best_cost-0.1 or new_backwards > best_backwards:
                        continue
                    new_overlaps, new_hits = local_counts(key)
                    report = dict(quality,
                                  node_overlaps=quality["node_overlaps"]-old_overlaps+new_overlaps,
                                  estimated_wire_node_hits=quality["estimated_wire_node_hits"]-old_hits+new_hits)
                    if any(report[k] > best_quality[k]
                           for k in ("node_overlaps", "estimated_wire_node_hits")):
                        continue
                    best, best_cost, best_backwards, best_quality = candidate, new_cost, new_backwards, report
            work[key] = best
            if best != current:
                changed = True
                cost, backwards, quality = best_cost, best_backwards, best_quality
        if not changed:
            return {k: work[k] for k in keys}, True
    return {k: boxes[k] for k in keys}, False


def solve_layout(snapshot, links, settings=None, anchor=None):
    started = perf_counter()
    settings = settings or LayoutSettings()
    nodes = {node.key: node for node in snapshot}
    if len(nodes) != len(snapshot):
        raise ValueError("Duplicate node identity")
    for node in snapshot:
        if (node.box.width <= 0 or node.box.height <= 0 or
                not all(isfinite(v) for v in (*node.location, node.box.left, node.box.right,
                                              node.box.top, node.box.bottom))):
            raise ValueError("Node geometry is not ready: " + node.key)
    boxes = {key: node.box for key, node in nodes.items()}
    locations = {key: node.location for key, node in nodes.items()}
    selected = {key for key, node in nodes.items() if node.selected}
    warnings, reasons = [], {}
    alignment_decisions = {}
    partial_results = []
    if any(nodes[key].protected for key in selected):
        warnings.append("Unverified zone nodes selected; connected components retain internal layout.")
    all_links = [e for e in links if e.source in nodes and e.target in nodes]
    flow = [replace(e,
                    source_offset=boxes[e.source].height/2 if nodes[e.source].kind == 'REROUTE' else e.source_offset,
                    target_offset=boxes[e.target].height/2 if nodes[e.target].kind == 'REROUTE' else e.target_offset)
            for e in all_links if e.valid and not e.muted]
    ancestors, children = {}, defaultdict(list)
    for key, node in nodes.items():
        lineage, parent = [], node.parent
        while parent in nodes:
            if parent == key or parent in lineage:
                raise ValueError("Cyclic Frame hierarchy")
            lineage.append(parent)
            parent = nodes[parent].parent
        ancestors[key] = lineage
        if node.parent in nodes:
            children[node.parent].append(key)
    descendants = defaultdict(list)
    for key, lineage in ancestors.items():
        for parent in lineage:
            descendants[parent].append(key)
    scopes = defaultdict(list)
    for key in sorted(selected):
        owner = next((p for p in ancestors[key] if p in selected and nodes[p].kind == "FRAME"), None)
        scopes[owner].append(key)

    # Editing two sibling containers must not also repack those containers as
    # giant cards. Frame-only selections keep their rigid movement semantics.
    anchored_frames = {}
    bounded_scopes = set()
    for owner, units in scopes.items():
        edited = {k for k in units if nodes[k].kind == 'FRAME' and k in scopes}
        if len(edited) >= 2:
            anchored_frames[owner] = edited
            bounded_scopes.add(owner)
            bounded_scopes.update(k for k in scopes if k in edited
                                  or (k is not None and edited.intersection(ancestors[k])))
    # A selected ancestor must not translate these same groups again together
    # with some unrelated outer node. Carry the anchor through each wrapper.
    for key in {k for group in anchored_frames.values() for k in group}:
        for parent in ancestors[key]:
            if parent in selected and nodes[parent].kind == 'FRAME':
                owner = next((p for p in ancestors[parent] if p in selected
                              and nodes[p].kind == 'FRAME'), None)
                anchored_frames.setdefault(owner, set()).add(parent)
                bounded_scopes.update((parent, owner))

    def move(key, dx, dy, reason):
        affected = [key] + (descendants[key] if nodes[key].kind == "FRAME" else [])
        for child in affected:
            boxes[child] = boxes[child].translated(dx, dy)
            old = locations[child]
            locations[child] = (old[0]+dx, old[1]+dy)
            reasons[child] = reason if child == key else "Frame follower"

    def predicted_frame(owner, candidate):
        old_content = union_boxes([nodes[k].box for k in children[owner]])
        content = union_boxes([candidate[k] for k in children[owner]])
        original = nodes[owner].box
        margins = (max(0, old_content.left-original.left), max(0, original.right-old_content.right),
                   max(0, original.top-old_content.top), max(0, old_content.bottom-original.bottom))
        predicted = Box(content.left-margins[0], content.right+margins[1],
                        content.top+margins[2], content.bottom-margins[3], owner, is_frame=True)
        if not nodes[owner].shrink:
            predicted = union_boxes([original, predicted], owner)
        return predicted

    def resize_owner(owner):
        # Predicted auto-size rebases the Frame, never its children's absolute
        # targets. This also runs for parents containing only anchored Frames.
        if owner is None or not children[owner]:
            return
        original = nodes[owner].box
        predicted = predicted_frame(owner, boxes)
        boxes[owner] = predicted
        locations[owner] = (nodes[owner].location[0]+predicted.left-original.left,
                            nodes[owner].location[1]+predicted.top-original.top)

    fixed_conflicts = 0
    partial_scopes = 0
    for owner in sorted(scopes, key=lambda k: (-(len(ancestors[k])+1) if k else 0, k or "")):
        units = [k for k in scopes[owner] if k not in anchored_frames.get(owner, ())]
        if not units:
            resize_owner(owner)
            continue
        # Selecting just the enclosing container in addition to its children
        # must not re-anchor their newly arranged absolute positions.
        if owner is None and len(units) == 1 and units[0] in scopes:
            continue
        # Capture external anchor before resizing selected child Frames.
        initial = union_boxes([nodes[k].box for k in units])
        left, top = (anchor if owner is None and anchor is not None else (initial.left, initial.top))
        representative = {}
        for key in units:
            representative[key] = key
            if nodes[key].kind == "FRAME":
                representative.update({child: key for child in descendants[key]})
        edges = []
        for e in flow:
            source, target = representative.get(e.source), representative.get(e.target)
            if source is None or target is None or source == target:
                continue
            # Virtual ports retain actual internal endpoint heights in Frames.
            edges.append(replace(e, source=source, target=target,
                                 source_offset=boxes[source].top-boxes[e.source].top+e.source_offset,
                                 target_offset=boxes[target].top-boxes[e.target].top+e.target_offset))
        has_boundary = any(((e.source in representative and e.target not in representative)
                            or (e.target in representative and e.source not in representative))
                           for e in flow)
        bounded = owner in bounded_scopes
        local_eligible = (has_boundary or bounded) and all(nodes[k].kind != "FRAME" and not nodes[k].protected for k in units)
        partial_scopes += int(local_eligible)
        partial = (local_eligible
                   and (bounded or not any(overlaps(boxes[a], boxes[b]) for i, a in enumerate(units) for b in units[i+1:])))
        if partial:
            accept = None
            if bounded and owner is not None:
                # An expanded container must not engulf neighboring groups or
                # their nodes. Try the compact local fallback before moving any
                # entire group, including selected groups solved in another scope.
                unrelated = [k for k in boxes if k != owner and k not in ancestors[owner]
                             and owner not in ancestors[k]]
                def area(a, b):
                    return max(0, min(a.right,b.right)-max(a.left,b.left))*max(0, min(a.top,b.top)-max(a.bottom,b.bottom))
                before_overlap = {k: area(boxes[owner],boxes[k]) for k in unrelated}
                def accept(candidate):
                    predicted = predicted_frame(owner, candidate)
                    return all(area(predicted,candidate[k]) <= before_overlap[k]+.1 for k in unrelated)
            targets, converged = _partial_layout(units, flow, nodes, boxes, settings, alignment_decisions, partial_results,
                                                 bounded=bounded, accept=accept)
        else:
            components = _components(units, edges)
            connected = [c for c in components if len(c) > 1]
            isolated = [c[0] for c in components if len(c) == 1]
            connected.sort(key=lambda c: (-max(nodes[k].box.top for k in c), min(c)))
            targets, cursor = {}, top
            for component in connected:
                members = set(component)
                internal = [e for e in edges if e.source in members and e.target in members]
                result = _layered(component, internal, nodes, boxes, settings, warnings)
                bounds = union_boxes(result.values())
                for key, box in result.items():
                    targets[key] = box.translated(left-bounds.left, cursor-bounds.top)
                cursor -= bounds.height + settings.component_gap
            if isolated:
                isolated.sort(key=lambda k: (-nodes[k].box.top, nodes[k].box.left, k))
                columns = max(1, ceil(sqrt(len(isolated))))
                for start in range(0, len(isolated), columns):
                    row = isolated[start:start+columns]
                    x = left
                    for key in row:
                        box = boxes[key]
                        targets[key] = box.translated(x-box.left, cursor-box.top)
                        x += box.width + settings.horizontal_gap
                    cursor -= max(boxes[k].height for k in row) + settings.component_gap
        # Unselected ordinary nodes remain fixed. Frames are not solid obstacles;
        # their actual children are. Move the scope together to preserve topology.
        excluded = set(representative)
        excluded.update(p for k in units for p in ancestors[k])
        obstacles = [boxes[k] for k in sorted(nodes) if k not in excluded
                     and k not in selected and nodes[k].kind != "FRAME"]
        if settings.avoid_fixed and not partial:
            # One horizontal-range query per unit. Forbidden Y intervals are
            # merged by a downward sweep, avoiding repeated full-canvas scans.
            ordered_obstacles = sorted(obstacles, key=lambda b: b.left)
            left_edges = [b.left for b in ordered_obstacles]
            intervals = []
            for box in targets.values():
                limit = bisect_left(left_edges, box.right+8.0)
                for obstacle in ordered_obstacles[:limit]:
                    if obstacle.right+8.0 > box.left:
                        intervals.append((obstacle.top+8.0-box.bottom,
                                          obstacle.bottom-8.0-box.top))
            delta = 0.0
            for upper, lower in sorted(intervals, reverse=True):
                if lower < delta < upper:
                    delta = lower-settings.vertical_gap
            targets = {key: box.translated(0, delta) for key, box in targets.items()}
            if targets and max(box.top for box in targets.values()) < top-0.01:
                warnings.append("Selection shifted downward to avoid fixed nodes.")
        if local_eligible and not partial:
            targets, _converged = _partial_layout(units, flow, nodes, {**boxes, **targets}, settings, alignment_decisions, partial_results)
        if bounded and not _within_neighborhood(units, {k: nodes[k].box for k in units}, targets, settings):
            targets = {k: boxes[k] for k in units}
            partial_results.append({'nodes': units, 'method': 'preserved',
                                    'reason': 'displacement_limit', 'moved': 0})
        for key, target in targets.items():
            move(key, target.left-boxes[key].left, target.top-boxes[key].top, "Selected layout unit")
        fixed_conflicts += sum(overlaps(boxes[k], obstacle) for k in units for obstacle in obstacles)
        resize_owner(owner)

    # Internally owned junctions follow an output row after card placement.
    # The adapter may add bends for the resulting long bypass wires.
    from .layout_routing import align_internal_junctions
    preserved = {k for r in partial_results if r['method'] == 'preserved' for k in r['nodes']}
    has_protected_component = "Cycle or unverified zone: preserved connected component internally." in warnings
    routing_snapshot = [replace(n, selected=n.selected and n.key not in preserved
                                and not n.protected and not has_protected_component)
                        for n in snapshot]
    routed = align_internal_junctions(routing_snapshot, flow, boxes)
    for key, target in routed.items():
        if target != boxes[key]:
            move(key, target.left-boxes[key].left, target.top-boxes[key].top, "Internal reroute socket alignment")

    for result in partial_results:
        if result['method'] == 'preserved':
            if result['reason'] in {'search_budget', 'diagnostic_budget', 'reroute_budget', 'local_search_limit'}:
                warnings.append("Local layout search limit reached; preserved affected components.")
            else:
                warnings.append("Some components could not fit within layout constraints; other results were kept.")
    bounds = union_boxes([boxes[k] for k in selected])
    moved = sum(abs(locations[k][0]-nodes[k].location[0]) > 1e-5 or
                abs(locations[k][1]-nodes[k].location[1]) > 1e-5 for k in nodes)
    metrics = {"nodes": len(nodes), "selected": len(selected), "links": len(all_links),
               "moved": moved, "fixed_conflicts": fixed_conflicts,
               "partial_scopes": partial_scopes,
               "anchored_frames": sorted(k for group in anchored_frames.values() for k in group),
               "width": bounds.width if bounds else 0, "height": bounds.height if bounds else 0,
               "solve_ms": (perf_counter()-started)*1000,
               "socket_geometry": "estimated; logical port order is authoritative"}
    return LayoutPlan(locations, boxes, list(dict.fromkeys(warnings)), metrics, reasons, alignment_decisions, partial_results)


def layout_diagnostics(snapshot, links, boxes, budget=100000, routes=None):
    """Check internal selected wires against all node bodies; bound each budget.

    Selected Frames include descendants that move with them. External wires
    never contribute hits or crossings, but fixed nodes remain obstacles.
    """
    nodes = {n.key: n for n in snapshot}
    def related(a, b):
        for first, second in ((a, b), (b, a)):
            parent = nodes[first].parent
            while parent in nodes:
                if parent == second:
                    return True
                parent = nodes[parent].parent
        return False
    moving = {n.key for n in snapshot if n.selected}
    for node in snapshot:
        parent = node.parent
        while parent in nodes:
            if parent in moving:
                moving.add(node.key)
                break
            parent = nodes[parent].parent
    overlaps_count, overlap_checks = 0, 0
    items = sorted(boxes)
    moving_items = sorted(moving & boxes.keys())
    for i, a in enumerate(items):
        # Preserve lexicographic check order/budget without walking fixed/fixed pairs.
        targets = items[i+1:] if a in moving else moving_items[bisect_right(moving_items, a):]
        for b in targets:
            overlap_checks += 1
            if overlap_checks > budget:
                break
            if not related(a,b) and overlaps(boxes[a], boxes[b]):
                overlaps_count += 1
        if overlap_checks > budget:
            break
    edges = [e for e in links if e.valid and not e.muted and not e.hidden
             and e.source in boxes and e.target in boxes
             and e.source in moving and e.target in moving]
    wire_hits, wire_checks = 0, 0
    routing = {(r['source'],r['target'],r['output'],r['input']):r['points'] for r in routes or []}
    for edge in edges:
        points = routing.get((edge.source,edge.target,edge.output,edge.input))
        if points:
            from .layout_routing import route_segments
            wire_boxes, segments = route_segments(edge, boxes, points)
        else:
            wire_boxes, segments = boxes, [edge]
        for key in items:
            if key in (edge.source, edge.target) or nodes[key].kind == "FRAME":
                continue
            wire_checks += 1
            if wire_checks > budget:
                break
            wire_hits += int(any(_curve_hits(segment, wire_boxes, boxes[key]) for segment in segments))
        if wire_checks > budget:
            break
    # Endpoint-chord intersections are a cheap ranking diagnostic, separate
    # from sampled-cubic node obstruction checks and actual rendered wires.
    def endpoints(edge):
        a,b=boxes[edge.source],boxes[edge.target]
        return (a.right, a.top-edge.source_offset), (b.left, b.top-edge.target_offset)
    def orient(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    crossings, cross_checks = 0, 0
    for i, edge in enumerate(edges):
        a,b=endpoints(edge)
        for other in edges[i+1:]:
            cross_checks += 1
            if cross_checks > budget:
                break
            if {edge.source,edge.target} & {other.source,other.target}:
                continue
            c,d=endpoints(other)
            crossings += int(orient(a,b,c)*orient(a,b,d)<0 and orient(c,d,a)*orient(c,d,b)<0)
        if cross_checks > budget:
            break
    return {"node_overlaps": overlaps_count, "node_overlap_check_complete": overlap_checks <= budget,
            "estimated_wire_node_hits": wire_hits, "wire_check_complete": wire_checks <= budget,
            "endpoint_chord_crossings": crossings, "crossing_check_complete": cross_checks <= budget,
            "diagnostic_pair_budget": budget, "wire_scope": "selection_internal",
            "internal_links_checked": len(edges)}
