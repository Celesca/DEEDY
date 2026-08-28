import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.run_paper_pilot import (
    CampaignProfile,
    SimulationConfig,
    js_distance,
    run_simulation,
)


class PaperPilotTests(unittest.TestCase):
    def setUp(self):
        self.profile = CampaignProfile(
            name="test-campaign",
            positive=0.4,
            neutral=0.4,
            negative=0.2,
            total_comments=10,
            post_counts=(6, 4),
            unique_authors=9,
            reply_links=0,
            likes=(0, 1, 2, 5, 10),
        )

    def test_js_distance_identity_and_bounds(self):
        self.assertEqual(js_distance((0.2, 0.3, 0.5), (0.2, 0.3, 0.5)), 0.0)
        self.assertAlmostEqual(js_distance((1, 0), (0, 1)), 1.0)

    def test_simulation_is_deterministic(self):
        config = SimulationConfig(
            campaign=self.profile.name,
            feed="interest",
            network="post_affiliation_proxy",
            population=60,
            seed=7,
            rounds=5,
        )
        self.assertEqual(
            run_simulation(self.profile, config),
            run_simulation(self.profile, config),
        )

    def test_edge_matched_networks(self):
        common = dict(
            campaign=self.profile.name,
            feed="chronological",
            population=80,
            seed=3,
            rounds=3,
        )
        proxy = run_simulation(
            self.profile,
            SimulationConfig(network="post_affiliation_proxy", **common),
        )
        random_graph = run_simulation(
            self.profile,
            SimulationConfig(network="matched_random", **common),
        )
        self.assertEqual(proxy["edge_count"], random_graph["edge_count"])


if __name__ == "__main__":
    unittest.main()
