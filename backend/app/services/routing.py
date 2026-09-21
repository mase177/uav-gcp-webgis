"""Lightweight field-route ordering (nearest neighbour plus 2-opt refinement)."""

from __future__ import annotations

from .spatial import distance_m


def route_distance(route):
    return sum(distance_m(a, b) for a, b in zip(route, route[1:]))


def plan_route(points, start=None, return_to_start=True):
    coordinates = [tuple(point) for point in points]
    origin = tuple(start) if start else coordinates[0]
    remaining = coordinates.copy()
    if origin in remaining:
        remaining.remove(origin)
    route = [origin]
    while remaining:
        nearest = min(remaining, key=lambda item: distance_m(route[-1], item))
        route.append(nearest)
        remaining.remove(nearest)
    if return_to_start:
        route.append(origin)

    # Preserve start and final return while improving intermediate visit order.
    best_distance = route_distance(route)
    changed = True
    while changed:
        changed = False
        for left in range(1, len(route) - 2):
            for right in range(left + 1, len(route) - 1):
                candidate = route[:left] + route[left : right + 1][::-1] + route[right + 1 :]
                candidate_distance = route_distance(candidate)
                if candidate_distance + 0.1 < best_distance:
                    route, best_distance, changed = candidate, candidate_distance, True
                    break
            if changed:
                break
    return route, best_distance

