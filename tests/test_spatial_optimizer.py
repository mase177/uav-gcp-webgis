import unittest

from backend.app.schemas import OptimizationRequest
from backend.app.core.config import NO_FLY_KMZ_PATH
from backend.app.services.no_fly_zones import load_no_fly_zones
from backend.app.services.optimizer import genetic_optimize
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

    def test_candidates_are_accessible_and_ga_selects_requested_count(self):
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

    def test_local_cambay_kmz_is_read_as_airspace_geojson(self):
        zones = load_no_fly_zones(NO_FLY_KMZ_PATH)
        self.assertEqual(len(zones["features"]), 2)
        self.assertEqual({feature["properties"]["zone_type"] for feature in zones["features"]}, {"prohibited", "restricted"})


if __name__ == "__main__":
    unittest.main()
