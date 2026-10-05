"""Bounded, internal-wire routing; generated points are not layout columns."""
from math import hypot

from .geometry import Box
from .layout import LayoutLink, _curve_hits, overlaps

ROUTE_TAG = '_smart_align_layout_route'


def align_internal_junctions(snapshot, links, boxes):
    """Attach selected one-source junctions to their source's output row."""
    nodes = {n.key: n for n in snapshot}
    moving = {n.key for n in snapshot if n.selected and n.kind != 'FRAME'}
    flow = [e for e in links if e.valid and not e.muted and not e.hidden]
    result = dict(boxes)
    for key in sorted(moving):
        if nodes[key].kind != 'REROUTE':
            continue
        ins = [e for e in flow if e.target == key]
        outs = [e for e in flow if e.source == key]
        if (len(ins) != 1 or not outs or ins[0].source not in moving
                or nodes[ins[0].source].kind != 'NODE'
                or any(e.target not in moving or nodes[e.target].kind != 'NODE' for e in outs)):
            continue
        a, b = result[ins[0].source], result[key]
        end = min(result[e.target].left for e in outs)
        if end-a.right < 32:
            continue
        x = a.right + min(30.0, (end-a.right)/2)
        y = a.top-ins[0].source_offset
        candidate = b.translated(x-b.center_x, y-b.center_y)
        if not any(overlaps(candidate, ob, 8) for k, ob in result.items()
                   if k != key and nodes[k].kind != 'FRAME'):
            result[key] = candidate
    return result


def route_segments(edge, boxes, points):
    """Return the virtual boxes and links used to score a routed wire."""
    result = dict(boxes)
    keys = []
    for i, (x, y) in enumerate(points):
        key = ('route', i)
        result[key] = Box(x-5, x+5, y+5, y-5, key, is_reroute=True)
        keys.append(key)
    path = [edge.source] + keys + [edge.target]
    segments = [LayoutLink(a, b, source_offset=edge.source_offset if i == 0 else 5,
                           target_offset=edge.target_offset if i == len(path)-2 else 5)
                for i, (a, b) in enumerate(zip(path, path[1:]))]
    return result, segments


def plan_internal_routes(snapshot, links, boxes, max_routes=24, budget=100000, stats=None):
    """Use two/four corners only when an internal forward wire hits a body.

    First and last legs stay horizontal. Multi-input links are filtered by the
    Blender adapter before application. No route is accepted unless every
    estimated segment clears all ordinary node bodies.
    """
    nodes = {n.key: n for n in snapshot}
    moving = {n.key for n in snapshot if n.selected and n.kind != 'FRAME'}
    flow = sorted((e for e in links if e.valid and not e.muted and not e.hidden and not e.multi_input
                   and e.source in moving and e.target in moving
                   and not nodes[e.source].protected and not nodes[e.target].protected),
                  key=lambda e: (e.source, e.target, e.output, e.input, e.sort_id))
    plans, extra_obstacles = [], {}
    checks = 0
    complete = True
    class SearchLimit(Exception):
        pass
    def check():
        nonlocal checks
        checks += 1
        if checks > budget:
            raise SearchLimit()
    def hits(edge, boxes, obstacle):
        check()
        return _curve_hits(edge, boxes, obstacle)
    def intersects(a, b):
        check()
        return overlaps(a, b, 8)
    try:
        for edge in flow:
            if len(plans) >= max_routes:
                complete = False
                break
            obstacles = {k: b for k, b in boxes.items()
                         if k not in (edge.source, edge.target) and nodes[k].kind != 'FRAME'}
            obstacles.update(extra_obstacles)
            obstructed = any(hits(edge, boxes, b) for b in obstacles.values())
            required = len(edge.reroutes)
            if not obstructed and not required:
                continue
            a, b = boxes[edge.source], boxes[edge.target]
            sx, sy, tx, ty = a.right, a.top-edge.source_offset, b.left, b.top-edge.target_offset
            if tx-sx < 56:
                continue
            # A junction already is a bend. Do not add a duplicate lead-in point.
            left = sx if nodes[edge.source].kind == 'REROUTE' else sx+24
            right = tx if nodes[edge.target].kind == 'REROUTE' else tx-24
            nearby = [ob for ob in obstacles.values() if ob.right >= sx-16 and ob.left <= tx+16]
            columns = {left, right, (left+right)/2}
            columns.update(v for ob in nearby for v in (ob.left-24, ob.right+24) if left <= v <= right)
            columns = sorted(columns, key=lambda x: (abs(x-(left+right)/2), x))[:12]
            lanes = {sy, ty}
            lanes.update(v for ob in nearby for v in (ob.top+24, ob.bottom-24)
                         if min(sy,ty)-240 <= v <= max(sy,ty)+240)
            lanes = sorted(lanes, key=lambda y: (abs(y-sy)+abs(y-ty), y))[:16]
            candidates = [[(x, sy), (x, ty)] for x in columns]
            candidates += [[(left, sy), (left, y), (right, y), (right, ty)] for y in lanes]
            if required and not obstructed:
                candidates.insert(0, [(sx+(tx-sx)*i/(required+1), sy+(ty-sy)*i/(required+1))
                                      for i in range(1,required+1)])
            best = None
            for points in candidates:
                # Remove consecutive duplicate corners without changing direction.
                path = [(sx,sy)] + points + [(tx,ty)]
                compact = [path[0]]
                for p in path[1:]:
                    if p == compact[-1]:
                        continue
                    while len(compact)>1 and ((compact[-2][0]==compact[-1][0]==p[0])
                                             or (compact[-2][1]==compact[-1][1]==p[1])):
                        compact.pop()
                    compact.append(p)
                points = compact[1:-1]
                # Retain user-authored points, placing them along the route. Only
                # addon-generated surplus points may be removed by the adapter.
                while len(points) < required:
                    path = [(sx,sy)] + points + [(tx,ty)]
                    i = max(range(len(path)-1),key=lambda j:hypot(path[j+1][0]-path[j][0],path[j+1][1]-path[j][1]))
                    points.insert(i,tuple((path[i][j]+path[i+1][j])/2 for j in (0,1)))
                virtual, segments = route_segments(edge, boxes, points)
                if any(intersects(virtual[('route',i)], ob) for i in range(len(points)) for ob in nearby):
                    continue
                if any(hits(segment, virtual, ob) for segment in segments for ob in nearby):
                    continue
                path = [(sx,sy)] + points + [(tx,ty)]
                length = sum(hypot(q[0]-p[0],q[1]-p[1]) for p,q in zip(path,path[1:]))
                score = (max(0,len(points)-required), len(points), length, points)
                if best is None or score < best[0]:
                    best = score, points
            if best:
                plans.append({'source': edge.source, 'target': edge.target, 'output': edge.output,
                              'input': edge.input, 'points': best[1], 'reuse': list(edge.reroutes)})
                for i,(x,y) in enumerate(best[1]):
                    extra_obstacles[(len(plans),i)] = Box(x-5,x+5,y+5,y-5,is_reroute=True)
    except SearchLimit:
        complete = False
    if stats is not None:
        stats.update(check_complete=complete, pair_checks=min(checks,budget), pair_budget=budget,
                     max_routes=max_routes, routed_links=len(plans))
    return plans
