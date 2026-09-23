"""Field-route ordering using OpenStreetMap travel costs with a clear fallback."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .spatial import distance_m

OSRM_BASE_URL = "https://router.project-osrm.org"


class OSRMRoutingError(ValueError):
    """The external OpenStreetMap routing service could not produce a route."""


def route_distance(route):
    return sum(distance_m(a, b) for a, b in zip(route, route[1:]))


def plan_route_estimate(points, start=None, return_to_start=True):
    """Return an explicitly labelled straight-line fallback route."""
    coordinates = [tuple(point) for point in points]
    if len(coordinates) < 2:
        raise ValueError("At least two control points are required")
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


def _coordinate_string(coordinates):
    return ";".join(f"{longitude:.7f},{latitude:.7f}" for longitude, latitude in coordinates)


def _osrm_json(path: str):
    request = Request(f"{OSRM_BASE_URL}{path}", headers={"User-Agent": "uav-gcp-webgis/0.1"})
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise OSRMRoutingError(f"OSRM returned HTTP {error.code}") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise OSRMRoutingError("Không thể kết nối dịch vụ định tuyến OSM/OSRM.") from error
    if result.get("code") != "Ok":
        raise OSRMRoutingError(result.get("message", "OSRM không tìm được tuyến đường phù hợp."))
    return result


def _matrix_cost(matrix, route):
    cost = 0.0
    for index in range(len(route) - 1):
        value = matrix[route[index]][route[index + 1]]
        if not _is_valid_cost(value):
            return float("inf")
        cost += value
    return cost


def _is_valid_cost(value):
    return value is not None and value != float("inf")


def _optimize_order(duration_matrix, return_to_start=True):
    """Nearest-neighbour plus 2-opt over OSM travel-time costs, starting at index 0."""
    count = len(duration_matrix)
    route = [0]
    remaining = set(range(1, count))
    while remaining:
        next_index = min(
            remaining,
            key=lambda index: duration_matrix[route[-1]][index]
            if _is_valid_cost(duration_matrix[route[-1]][index])
            else float("inf"),
        )
        if not _is_valid_cost(duration_matrix[route[-1]][next_index]):
            raise OSRMRoutingError("Một hoặc nhiều điểm không kết nối được qua mạng đường OSM.")
        route.append(next_index)
        remaining.remove(next_index)
    if return_to_start:
        if not _is_valid_cost(duration_matrix[route[-1]][0]):
            raise OSRMRoutingError("Không thể quay về điểm xuất phát qua mạng đường OSM.")
        route.append(0)

    best_cost = _matrix_cost(duration_matrix, route)
    improved = True
    # Preserve origin and, when requested, the final return to origin.
    last_reversible = len(route) - 1 if return_to_start else len(route)
    while improved:
        improved = False
        for left in range(1, last_reversible - 1):
            for right in range(left + 1, last_reversible):
                candidate = route[:left] + route[left : right + 1][::-1] + route[right + 1 :]
                candidate_cost = _matrix_cost(duration_matrix, candidate)
                if candidate_cost + 0.1 < best_cost:
                    route, best_cost, improved = candidate, candidate_cost, True
                    break
            if improved:
                break
    return route, best_cost


def plan_osm_route(points, start=None, return_to_start=True, vehicle="car"):
    """Optimize stop order by OSRM travel time and return OSM road geometry."""
    controls = [tuple(point) for point in points]
    if len(controls) < 2:
        raise ValueError("At least two control points are required")
    origin = tuple(start) if start else controls[0]
    coordinates = [origin] + [point for point in controls if point != origin]
    if len(coordinates) < 2:
        raise ValueError("At least two different control points are required")
    if len(coordinates) > 25:
        raise ValueError("OSM routing supports a maximum of 25 control points per run")

    coordinate_string = _coordinate_string(coordinates)
    matrix = _osrm_json(f"/table/v1/driving/{coordinate_string}?{urlencode({'annotations': 'duration,distance'})}")
    order, estimated_duration = _optimize_order(matrix["durations"], return_to_start)
    ordered_coordinates = [coordinates[index] for index in order]
    geometry_query = urlencode({"overview": "full", "geometries": "geojson", "steps": "false"})
    route = _osrm_json(f"/route/v1/driving/{_coordinate_string(ordered_coordinates)}?{geometry_query}")["routes"][0]
    distance_meters = round(route["distance"], 1)
    # The public OSRM endpoint offers a driving profile.  Motorcycle uses the
    # same passable-road geometry with a conservative field-speed estimate;
    # restrictions that are specific to motorcycles still need checking on site.
    is_motorcycle = vehicle == "motorcycle"
    duration_seconds = round(distance_meters / (35_000 / 3600), 1) if is_motorcycle else round(route["duration"], 1)
    return {
        "type": "Feature",
        "properties": {
            "method": "osrm_travel_time_nearest_neighbour_2opt",
            "distance_m": distance_meters,
            "duration_s": duration_seconds,
            "estimated_matrix_duration_s": round(estimated_duration, 1),
            "stops": len(controls),
            "stop_order": order,
            "vehicle": vehicle,
            "is_estimate": False,
            "source": "OpenStreetMap routing via OSRM",
            "note": (
                "Thứ tự ghé điểm tối ưu theo thời gian di chuyển trên mạng đường OSM; khoảng cách và thời gian là ước lượng theo hồ sơ lái xe của OSRM."
                if not is_motorcycle
                else "Tuyến xe máy dùng cùng mạng đường có thể đi như hồ sơ lái xe; thời gian được ước tính 35 km/h. Cần kiểm tra biển cấm xe máy và điều kiện thực địa."
            ),
        },
        "geometry": route["geometry"],
    }


def plan_route(points, start=None, return_to_start=True, vehicle="car"):
    """Return a road route when OSM/OSRM is available, otherwise an honest fallback."""
    try:
        return plan_osm_route(points, start, return_to_start, vehicle)
    except OSRMRoutingError as error:
        route, total_distance = plan_route_estimate(points, start, return_to_start)
        return {
            "type": "Feature",
            "properties": {
                "method": "nearest_neighbour_2opt_straight_line_fallback",
                "distance_m": round(total_distance, 1),
                "duration_s": round(total_distance / ((35_000 if vehicle == "motorcycle" else 45_000) / 3600), 1),
                "stops": len(points),
                "stop_order": [list(map(tuple, points)).index(point) for point in route],
                "vehicle": vehicle,
                "is_estimate": True,
                "source": "Không có tuyến OSM/OSRM",
                "note": f"Tuyến ước lượng bằng khoảng cách thẳng vì OSM/OSRM chưa sẵn sàng: {error}",
            },
            "geometry": {"type": "LineString", "coordinates": route},
        }
