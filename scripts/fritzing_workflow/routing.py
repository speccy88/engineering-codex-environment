"""Conservative, single-layer orthogonal routing for generated Fritzing projects.

This is a bounded grid router and geometric checker, not Fritzing's native DRC.
All dimensions are millimetres. Failure raises ValueError; no partial route is
returned as a successful design. Rectangular obstacles represent keepouts.
"""

from __future__ import annotations

import heapq
import itertools
import math
from collections import defaultdict

EPS = 1e-7
MAX_GRID_NODES = 300_000
MAX_SEARCH_VISITS = 600_000


def _point_segment(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    d2 = dx * dx + dy * dy
    if d2 == 0:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / d2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(a, b, c, d):
    if max(a[0], b[0]) + EPS < min(c[0], d[0]) or max(c[0], d[0]) + EPS < min(a[0], b[0]):
        return False
    if max(a[1], b[1]) + EPS < min(c[1], d[1]) or max(c[1], d[1]) + EPS < min(a[1], b[1]):
        return False
    return _cross(a, b, c) * _cross(a, b, d) <= EPS and _cross(c, d, a) * _cross(c, d, b) <= EPS


def _segment_distance(a, b, c, d):
    if _segments_intersect(a, b, c, d):
        return 0.0
    return min(_point_segment(a, c, d), _point_segment(b, c, d), _point_segment(c, a, b), _point_segment(d, a, b))


def _segment_rect(a, b, rect, margin):
    x0, y0, x1, y1 = rect
    if x0 <= a[0] <= x1 and y0 <= a[1] <= y1:
        return True
    if x0 <= b[0] <= x1 and y0 <= b[1] <= y1:
        return True
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return any(_segment_distance(a, b, corners[i], corners[(i + 1) % 4]) < margin - EPS for i in range(4)) or any(
        _segments_intersect(a, b, corners[i], corners[(i + 1) % 4]) for i in range(4)
    )


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _input_errors(pins, width, height, clearance, trace_width, edge_clearance, obstacles):
    errors = []
    for name, value in (("width", width), ("height", height), ("trace_width", trace_width)):
        if not _finite(value) or value <= 0:
            errors.append(f"{name} must be finite and positive")
    for name, value in (("clearance", clearance), ("edge_clearance", edge_clearance)):
        if not _finite(value) or value < 0:
            errors.append(f"{name} must be finite and nonnegative")
    for name, pin in pins.items():
        if not all(_finite(pin.get(k)) for k in ("x", "y", "radius")) or pin.get("radius", -1) < 0:
            errors.append(f"{name}: invalid pad geometry")
        if not isinstance(pin.get("net"), str) or not pin["net"]:
            errors.append(f"{name}: missing net identity")
    for rect in obstacles:
        if len(rect) != 4 or not all(_finite(v) for v in rect) or rect[0] > rect[2] or rect[1] > rect[3]:
            errors.append("invalid obstacle rectangle")
    return errors


def validate_geometry(pins, segments, width, height, clearance, trace_width, edge_clearance, obstacles=()):
    """Return errors for pad/trace clearance, outline, keepouts and connectivity.

    Geometric connectivity means every centre of a multi-pin net is joined by
    that net's segments. Fritzing XML connectivity is checked by the caller.
    """
    errors = _input_errors(pins, width, height, clearance, trace_width, edge_clearance, obstacles)
    if errors:
        return errors
    half = trace_width / 2
    for name, pin in pins.items():
        x, y, r = pin["x"], pin["y"], pin["radius"]
        if min(x, y, width - x, height - y) < r + edge_clearance - EPS:
            errors.append(f"pad {name} violates board edge clearance")
        if any(math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1)) < r + clearance - EPS for x0, y0, x1, y1 in obstacles):
            errors.append(f"pad {name} violates a keepout")
    for (na, a), (nb, b) in itertools.combinations(pins.items(), 2):
        if a["net"] != b["net"] and math.hypot(a["x"] - b["x"], a["y"] - b["y"]) < a["radius"] + b["radius"] + clearance - EPS:
            errors.append(f"pads {na}/{nb} violate clearance")
    checked = []
    known_nets = {pin["net"] for pin in pins.values()}
    for i, segment in enumerate(segments):
        a, b, net = segment.get("a", ()), segment.get("b", ()), segment.get("net")
        if len(a) != 2 or len(b) != 2 or not all(_finite(v) for v in (*a, *b)) or not isinstance(net, str):
            errors.append(f"segment {i}: invalid geometry")
            continue
        if math.dist(a, b) < EPS or (abs(a[0] - b[0]) > EPS and abs(a[1] - b[1]) > EPS):
            errors.append(f"segment {i}: must be nonzero and orthogonal")
            continue
        if net not in known_nets:
            errors.append(f"segment {i}: unknown net {net}")
            continue
        checked.append(segment)
        if min(*(p[0] for p in (a, b)), *(p[1] for p in (a, b)), *(width - p[0] for p in (a, b)), *(height - p[1] for p in (a, b))) < half + edge_clearance - EPS:
            errors.append(f"segment {i}: violates board edge clearance")
        if any(_segment_rect(a, b, rect, half + clearance) for rect in obstacles):
            errors.append(f"segment {i}: intersects a keepout")
        for name, pin in pins.items():
            if pin["net"] != net and _point_segment((pin["x"], pin["y"]), a, b) < pin["radius"] + half + clearance - EPS:
                errors.append(f"segment {i}/pad {name}: violates clearance")
    for i, a in enumerate(checked):
        for j, b in enumerate(checked[:i]):
            if a["net"] != b["net"] and _segment_distance(a["a"], a["b"], b["a"], b["b"]) < trace_width + clearance - EPS:
                errors.append(f"segments {j}/{i}: violate clearance")
    groups = defaultdict(list)
    for name, pin in pins.items():
        groups[pin["net"]].append((name, (pin["x"], pin["y"])))
    for net, net_pins in groups.items():
        if len(net_pins) < 2:
            continue
        net_segments = [s for s in checked if s["net"] == net]
        # Segment connectivity includes same-net T junctions and crossings.
        connected = set()
        pending = [i for i, s in enumerate(net_segments) if _point_segment(net_pins[0][1], s["a"], s["b"]) <= EPS]
        while pending:
            i = pending.pop()
            if i in connected:
                continue
            connected.add(i)
            a = net_segments[i]
            pending.extend(j for j, b in enumerate(net_segments) if j not in connected and _segments_intersect(a["a"], a["b"], b["a"], b["b"]))
        for name, point in net_pins:
            if not any(_point_segment(point, net_segments[i]["a"], net_segments[i]["b"]) <= EPS for i in connected):
                errors.append(f"net {net}: pin {name} is unrouted")
    return errors


def _compress(edges, terminals, grid, net):
    neighbors = defaultdict(set)
    for a, b in edges:
        neighbors[a].add(b)
        neighbors[b].add(a)
    breaks = set(terminals)
    for point, adjacent in neighbors.items():
        if len(adjacent) != 2:
            breaks.add(point)
        else:
            a, b = sorted(adjacent)
            if a[0] != b[0] and a[1] != b[1]:
                breaks.add(point)
    used = set()
    result = []
    for start in sorted(breaks):
        for nxt in sorted(neighbors[start]):
            edge = tuple(sorted((start, nxt)))
            if edge in used:
                continue
            used.add(edge)
            previous, current = start, nxt
            while current not in breaks:
                following = next(p for p in neighbors[current] if p != previous)
                used.add(tuple(sorted((current, following))))
                previous, current = current, following
            result.append({"net": net, "a": [round(v * grid, 10) for v in start], "b": [round(v * grid, 10) for v in current]})
    return result


def route_view(pins, nets, width, height, grid, clearance, trace_width, edge_clearance, obstacles=()):
    """Route nets on one layer with deterministic A* and exact segment checks.

    Pads must be on the selected grid. Net permutations are tried for small
    designs, but rip-up, vias and multilayer routing are intentionally absent.
    """
    errors = _input_errors(pins, width, height, clearance, trace_width, edge_clearance, obstacles)
    if not _finite(grid) or grid <= 0:
        errors.append("grid must be finite and positive")
    if errors:
        raise ValueError("; ".join(errors))
    nx, ny = math.floor(width / grid), math.floor(height / grid)
    if (nx + 1) * (ny + 1) > MAX_GRID_NODES:
        raise ValueError(f"routing grid exceeds {MAX_GRID_NODES} nodes; enlarge grid or reduce board")
    points = {}
    for name, pin in pins.items():
        point = (round(pin["x"] / grid), round(pin["y"] / grid))
        if abs(point[0] * grid - pin["x"]) > 1e-6 or abs(point[1] * grid - pin["y"]) > 1e-6:
            raise ValueError(f"pin {name} is not on the {grid:g} mm routing grid")
        points[name] = point
    seen = set()
    net_names = set()
    for net in nets:
        if not isinstance(net.get("name"), str) or not net["name"] or net["name"] in net_names:
            raise ValueError("net names must be unique nonempty strings")
        net_names.add(net["name"])
        for name in net.get("pins", []):
            if name not in pins or name in seen or pins[name]["net"] != net["name"]:
                raise ValueError(f"invalid or duplicated net assignment for pin {name}")
            seen.add(name)
    if seen != set(pins):
        raise ValueError("every pad must appear in exactly one net (singleton nets represent unconnected pins)")
    pad_errors = [e for e in validate_geometry(pins, [], width, height, clearance, trace_width, edge_clearance, obstacles) if "is unrouted" not in e]
    if pad_errors:
        raise ValueError("; ".join(pad_errors))
    routable = [n for n in nets if len(n["pins"]) > 1]
    def span(net):
        ps = [points[n] for n in net["pins"]]
        return max(p[0] for p in ps) - min(p[0] for p in ps) + max(p[1] for p in ps) - min(p[1] for p in ps)
    first = sorted(routable, key=lambda n: (-len(n["pins"]), span(n), n["name"]))
    orders = [first]
    if len(first) > 1:
        orders.append(list(reversed(first)))
        orders.extend(first[i:] + first[:i] for i in range(1, min(len(first), 4)))
    total_visits = 0
    last_failure = "unroutable design"
    half = trace_width / 2
    for attempt, order in enumerate(orders, 1):
        segments = []
        failed = False
        for net in order:
            name = net["name"]
            terminals = [points[p] for p in net["pins"]]
            tree = {terminals[0]}
            edges = set()
            other_pads = [(p["x"], p["y"], p["radius"]) for p in pins.values() if p["net"] != name]
            other_segments = [s for s in segments if s["net"] != name]
            edge_cache = {}
            def clear(a, b):
                key = tuple(sorted((a, b)))
                if key in edge_cache:
                    return edge_cache[key]
                aa = (a[0] * grid, a[1] * grid)
                bb = (b[0] * grid, b[1] * grid)
                allowed = min(aa[0], aa[1], width - aa[0], height - aa[1], bb[0], bb[1], width - bb[0], height - bb[1]) >= half + edge_clearance - EPS
                if allowed:
                    allowed = not any(_point_segment((x, y), aa, bb) < radius + half + clearance - EPS for x, y, radius in other_pads)
                if allowed:
                    allowed = not any(_segment_rect(aa, bb, r, half + clearance) for r in obstacles)
                if allowed:
                    allowed = not any(_segment_distance(aa, bb, s["a"], s["b"]) < trace_width + clearance - EPS for s in other_segments)
                edge_cache[key] = allowed
                return allowed
            pending_terminals = set(terminals[1:])
            while pending_terminals:
                start = min(pending_terminals, key=lambda p: (min(abs(p[0] - q[0]) + abs(p[1] - q[1]) for q in tree), p))
                pending_terminals.remove(start)
                if start in tree:
                    continue
                tx0, tx1 = min(p[0] for p in tree), max(p[0] for p in tree)
                ty0, ty1 = min(p[1] for p in tree), max(p[1] for p in tree)
                def h(p):
                    return max(tx0 - p[0], 0, p[0] - tx1) + max(ty0 - p[1], 0, p[1] - ty1)
                # Direction is part of the search state. Lexicographic cost
                # minimizes length first, then bends; equally short paths do
                # not form a staircase around a circular pad's grid boundary.
                start_state = (start, -1)
                queue = [(h(start), 0, 0, start, -1)]
                costs = {start_state: (0, 0)}
                parents = {}
                goal = None
                while queue:
                    _, turns, cost, current, direction = heapq.heappop(queue)
                    state = (current, direction)
                    if (cost, turns) != costs[state]:
                        continue
                    total_visits += 1
                    if total_visits > MAX_SEARCH_VISITS:
                        raise ValueError(f"routing exceeded {MAX_SEARCH_VISITS} search visits; simplify layout or increase grid")
                    if current in tree:
                        goal = state
                        break
                    for next_direction, (dx, dy) in enumerate(((1, 0), (0, 1), (-1, 0), (0, -1))):
                        nxt = (current[0] + dx, current[1] + dy)
                        nxt_state = (nxt, next_direction)
                        next_turns = turns + int(direction != -1 and direction != next_direction)
                        next_cost = (cost + 1, next_turns)
                        if not (0 <= nxt[0] <= nx and 0 <= nxt[1] <= ny) or next_cost >= costs.get(nxt_state, (float("inf"), float("inf"))) or not clear(current, nxt):
                            continue
                        costs[nxt_state] = next_cost
                        parents[nxt_state] = state
                        heapq.heappush(queue, (cost + 1 + h(nxt), next_turns, cost + 1, nxt, next_direction))
                if goal is None:
                    last_failure = f"net {name} cannot be routed on one layer with the requested clearances"
                    failed = True
                    break
                state = goal
                tree.add(state[0])
                while state != start_state:
                    previous = parents[state]
                    edges.add(tuple(sorted((state[0], previous[0]))))
                    tree.add(previous[0])
                    state = previous
            if failed:
                break
            segments.extend(_compress(edges, terminals, grid, name))
        if failed:
            continue
        errors = validate_geometry(pins, segments, width, height, clearance, trace_width, edge_clearance, obstacles)
        if errors:
            raise ValueError("route validation failed: " + "; ".join(errors))
        return {"segments": segments, "errors": [], "grid_mm": grid, "attempts": attempt, "search_visits": total_visits, "router": "bounded-single-layer-orthogonal-a-star", "native_drc": "not_run"}
    raise ValueError(last_failure)
