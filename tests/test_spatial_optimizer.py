import unittest
from unittest.mock import patch

from backend.app.schemas import OptimizationRequest
from backend.app.core.config import NO_FLY_KMZ_PATH
from backend.app.services.no_fly_zones import load_no_fly_zones
from backend.app.services.optimizer import genetic_optimize
from backend.app.services.osm import _query_tiles, overpass_to_geojson
from backend.app.services.routing import OSRMRoutingError, plan_osm_route, plan_route
from backend.app.services.spatial import generate_candidates


class OptimizerTests(unittest.TestCase):
    def setUp(self):
        self.aoi = {
            "type": "Feature",
            "properties": {},
            "geometry": {"type": "Polygon", "coordinates": [[[106.7800, 10.8700], [106.7820, 10.8700], [106.7820, 10.8720], [106.7800, 10.8720], [106.7800, 10.8700]]]},
        }
        self.roads = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {}, "geometry": {"type": "LineString", "coordinates": [[106.7800, 10.8710], [106.7820, 10.8710]]}},
                {"type": "Feature", "properties": {}, "geometry": {"type": "LineString", "coordinates": [[106.7810, 10.8700], [106.7810, 10.8720]]}},
            ],
        }

    def test_candidates_cover_aoi_and_ga_selects_requested_count(self):
        candidates, ring = generate_candidates(self.aoi, self.roads, 45, 80, 750)
        request = OptimizationRequest(
            aoi=self.aoi,
            roads=self.roads,
            candidate_spacing_m=45,
            access_radius_m=80,
            gcp_count=6,
            population_size=16,
            generations=12,
            seed=7,
        )
        selected, score = genetic_optimize(candidates, ring, request)
        self.assertGreaterEqual(len(candidates), 6)
        self.assertEqual(len(selected), 6)
        self.assertGreaterEqual(score["fitness"], 0)
        self.assertLessEqual(score["fitness"], 1)

    def test_sparse_or_outside_roads_do_not_remove_aoi_candidates(self):
        distant_roads = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {}, "geometry": {"type": "LineString", "coordinates": [[106.8000, 10.8900], [106.8020, 10.8900]]}},
            ],
        }
        candidates, _ = generate_candidates(self.aoi, distant_roads, 45, 20, 750)
        self.assertGreaterEqual(len(candidates), 6)
        self.assertTrue(all("access_point" in candidate for candidate in candidates))
        self.assertTrue(all(candidate["access_distance_m"] > 20 for candidate in candidates))
        self.assertTrue(all(candidate["accessibility_score"] > 0 for candidate in candidates))

    def test_local_cambay_kmz_is_read_as_airspace_geojson(self):
        zones = load_no_fly_zones(NO_FLY_KMZ_PATH)
        self.assertEqual(len(zones["features"]), 2)
        self.assertEqual({feature["properties"]["zone_type"] for feature in zones["features"]}, {"prohibited", "restricted"})

    def test_overpass_roads_are_converted_to_geojson_lines(self):
        roads = overpass_to_geojson(
            {
                "elements": [
                    {
                        "id": 123,
                        "tags": {"name": "Đường thử", "highway": "residential"},
                        "geometry": [{"lon": 106.78, "lat": 10.87}, {"lon": 106.781, "lat": 10.871}],
                    }
                ]
            }
        )
        self.assertEqual(roads["type"], "FeatureCollection")
        self.assertEqual(roads["features"][0]["id"], "osm-way-123")
        self.assertEqual(roads["features"][0]["properties"]["source"], "OpenStreetMap via Overpass")

    def test_wide_aoi_is_split_into_multiple_osm_query_tiles(self):
        ring = [tuple(point) for point in self.aoi["geometry"]["coordinates"][0]]
        tiles = _query_tiles(ring, 39.3)
        self.assertEqual(len(tiles), 6)
        self.assertTrue(all(west < east and south < north for west, south, east, north in tiles))

    @patch("backend.app.services.routing._osrm_json")
    def test_osrm_route_uses_travel_time_matrix_then_returns_road_geometry(self, request_osrm):
        request_osrm.side_effect = [
            {"code": "Ok", "durations": [[0, 60, 300], [60, 0, 60], [300, 60, 0]]},
            {"code": "Ok", "routes": [{"distance": 3200, "duration": 300, "geometry": {"type": "LineString", "coordinates": [[106.78, 10.87], [106.781, 10.871]]}}]},
        ]
        route = plan_osm_route([[106.78, 10.87], [106.781, 10.871], [106.782, 10.872]])
        self.assertFalse(route["properties"]["is_estimate"])
        self.assertEqual(route["properties"]["distance_m"], 3200)
        self.assertEqual(route["geometry"]["type"], "LineString")

    @patch("backend.app.services.routing._osrm_json", side_effect=OSRMRoutingError("offline"))
    def test_route_fallback_is_explicitly_marked_as_estimate(self, _request_osrm):
        route = plan_route([[106.78, 10.87], [106.781, 10.871]])
        self.assertTrue(route["properties"]["is_estimate"])
        self.assertIn("ước lượng", route["properties"]["note"])


if __name__ == "__main__":
    unittest.main()
