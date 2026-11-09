import itertools
import tempfile
import unittest
from fastapi.testclient import TestClient
from api.server import create_app
from nsnf.perception import eligibility, perceive
from nsnf.runtime import Runtime


def edge(src, dst):
    return {"src": src, "dst": dst, "type": "neural-state", "weight": .5,
            "rule_version": "perception-experiment-v1", "evidence_ref": "test-perception",
            "disposition": "ENGINEERING HYPOTHESIS"}


class PerceptionTests(unittest.TestCase):
    def test_all_dimension_combinations(self):
        for count in range(6):
            for expressed in itertools.combinations(range(1, 6), count):
                for current in (3, 4, 5):
                    result = eligibility(expressed, current)
                    self.assertEqual(result["perceptible"],
                        current in expressed and sum(d <= current for d in expressed) >= 3)
        self.assertTrue(eligibility([1, 2, 3], 3)["perceptible"])
        self.assertTrue(eligibility([2, 3, 4], 4)["perceptible"])
        self.assertTrue(eligibility([1, 3, 5], 5)["perceptible"])

    def test_duplicates_current_and_later_dimensions(self):
        self.assertFalse(eligibility([1, 1, 3], 3)["perceptible"])
        self.assertFalse(eligibility([1, 2, 3], 4)["perceptible"])
        self.assertFalse(eligibility([3, 4, 5], 3)["perceptible"])
        for invalid in (0, 1, 2, 6, True):
            with self.assertRaises(ValueError): eligibility([1, 2, 3], invalid)

    def test_unrelated_activity_does_not_create_shared_expression(self):
        micro = {"d0:g0": [.2, .8], "d1:g0": [.4, .6], "d2:g0": [.6, .4]}
        # Even equal gate-slot numbers across three dimensions do not invent channels.
        self.assertIsNone(perceive(micro, [])["perceived_outputs"]["3"])
        connected = perceive(micro, [{"src": "d0:g0", "dst": "d1:g0"},
                                    {"src": "d1:g0", "dst": "d2:g0"}])
        self.assertAlmostEqual(connected["perceived_outputs"]["3"][0], .4)
        self.assertIsNone(connected["perceived_outputs"]["4"])

    def test_real_execution_threshold_restore_and_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(directory)
            features = [1., 0, 0, 0, 0, 0, 0, 0]
            runtime.topology([edge("d0:g0", "d1:g0"), edge("d1:g0", "d2:g0")])
            # D3 is present, but only two distinct dimensions participate.
            blocked = runtime.execute(features, 3, candidates=[64, 128])
            self.assertIsNone(blocked["perception"]["perceived_outputs"]["3"])
            allowed = runtime.execute(features, 3, candidates=[0, 64, 128])
            self.assertIsNotNone(allowed["perception"]["perceived_outputs"]["3"])
            # No messages have passed in a one-round run: configured edges alone don't suffice.
            unexpressed = runtime.execute(features, 1, candidates=[0, 64, 128])
            self.assertIsNone(unexpressed["perception"]["perceived_outputs"]["3"])
            self.assertTrue(runtime.replay(allowed["id"])["checks"]["perception"])
            runtime.restore(allowed["id"])
            restarted = Runtime(directory)
            self.assertEqual(restarted.state["perception"], allowed["perception"])
            self.assertTrue(restarted.replay(allowed["id"])["exact"])
            restarted.store.db.close(); runtime.store.db.close()

    def test_http_path_carries_perception_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(directory)
            with TestClient(app) as client:
                response = client.post('/topology', json=[edge("d0:g0", "d1:g0"), edge("d1:g0", "d2:g0")])
                self.assertEqual(response.status_code, 200)
                run = client.post('/execute', json={"features": [1,0,0,0,0,0,0,0],
                    "tier": 3, "candidates": [0,64,128]}).json()
                self.assertIsNotNone(run["perception"]["perceived_outputs"]["3"])
                saved = client.get('/runs/' + run['id']).json()
                self.assertEqual(saved['payload']['perception'], run['perception'])
            app.state.runtime.store.db.close()
