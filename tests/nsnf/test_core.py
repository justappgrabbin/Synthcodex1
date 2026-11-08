import json
import sqlite3
import tempfile
import unittest
import numpy as np
from nsnf import hexagram as h
from nsnf.address import Address, FIELDS, evaluate_transition
from nsnf.runtime import Runtime
from nsnf.components import MLP
from nsnf.schema import ContactEvent, TIERS


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(self.temp.name)

    def tearDown(self):
        self.runtime.store.db.close()
        self.temp.cleanup()

    def test_all_hexagrams(self):
        for code in range(64):
            self.assertEqual(h.encode(h.lines(code)), code)
            self.assertEqual(h.complement(h.complement(code)), code)
            self.assertEqual(h.reverse(h.reverse(code)), code)
            self.assertEqual(h.exchange_trigrams(h.exchange_trigrams(code)), code)
            values = h.lines(code)
            self.assertEqual(h.lines(h.nuclear(code)), [values[i-1] for i in (2,3,4,3,4,5)])
            for line in range(1,7):
                self.assertEqual(h.flip(h.flip(code,[line]),[line]),code)

    def test_budgets_masks_and_slots(self):
        self.assertEqual(len(self.runtime.topology()["slots"]),320)
        for tier in range(1,6):
            run = self.runtime.execute([1.,.1,.2,.3,.4,.5,.6,.7],tier)
            self.assertLessEqual(len(run["selected"]), TIERS[tier].max_components)
            self.assertLessEqual(run["macs"],TIERS[tier].max_macs)
            self.assertEqual(sum(int(m).bit_count() for m in self.runtime.state["active_masks"]),len(run["selected"]))
            self.assertEqual(run["meso"]["nine_center_mapping"],"UNRESOLVED")

    def test_restart_restore_and_exact_replay_after_learning(self):
        run = self.runtime.execute([1.,0,0,0,0,0,0,0])
        checkpoint = self.runtime.checkpoint()
        before = self.runtime.state.copy()
        self.runtime.feedback(run["id"],1,"synthetic-label",steps=15)
        restarted = Runtime(self.temp.name)
        self.assertTrue(restarted.replay(run["id"])["exact"])
        restarted.restore(checkpoint["id"])
        self.assertEqual(restarted.state,before)
        self.assertTrue(restarted.store.verify()["valid"])
        restarted.store.db.close()

    def test_learning_changes_parameters_and_heldout_behavior(self):
        model = MLP(2)
        rng = np.random.default_rng(4)
        train = rng.normal(size=(100,8))
        heldout = rng.normal(size=(100,8))
        labels = (heldout[:,0] > 0).astype(int)
        def accuracy():
            return np.mean([model.forward(x).argmax() == y for x,y in zip(heldout,labels)])
        before = accuracy()
        for _ in range(15):
            for x in train:
                model.update(x,int(x[0]>0))
        self.assertGreater(accuracy(),.9)
        self.assertGreater(accuracy(),before+.2)

    def test_append_only_and_integrity(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.runtime.store.db.execute("DELETE FROM journal")
        record = self.runtime.store.records()[0]
        path = self.runtime.store.blobs / record["state_hash"]
        path.write_text("tampered")
        with self.assertRaisesRegex(ValueError,"integrity"):
            self.runtime.store.verify()

    def test_concurrent_writer_conflict(self):
        stale = Runtime(self.temp.name)
        self.runtime.checkpoint()
        with self.assertRaisesRegex(ValueError,"concurrent"):
            stale.checkpoint()
        stale.store.db.close()

    def test_cache_and_invalidation(self):
        features = [1.,0,0,0,0,0,0,0]
        self.runtime.execute(features)
        cached = self.runtime.execute(features)
        self.assertGreater(cached["cache_hits"],0)
        self.assertEqual(cached["macs"],0)
        self.runtime.feedback(cached["id"],1,"label")
        new = self.runtime.execute(features)
        self.assertEqual(new["cache_hits"],0)

    def test_typed_messages_affect_receiving_computation(self):
        features = [1.,0,0,0,0,0,0,0]
        baseline = self.runtime.execute(features,3)
        a,b = [s["component_id"] for s in baseline["selected"][:2]]
        self.runtime.topology([{"src":a,"dst":b,"type":"neural-state","weight":.9,
             "rule_version":"experiment-v1","evidence_ref":"test","disposition":"ENGINEERING HYPOTHESIS"}])
        changed = self.runtime.execute(features,3)
        self.assertTrue(changed["messages"])
        self.assertNotEqual(changed["micro"][b],baseline["micro"][b])
        self.assertTrue(self.runtime.replay(changed["id"])["exact"])
        self.assertEqual(changed["topology_version"],self.runtime.topology()["version"])

    def test_behavioral_parameter_transfer_persists(self):
        run = self.runtime.execute([1.,0,0,0,0,0,0,0],candidates=[0])
        self.runtime.feedback(run["id"],1,"verified synthetic label",steps=100)
        heldout = [.9,.01,0,0,0,0,0,0]
        source = self.runtime.model(0).forward(heldout)
        before = self.runtime.model(1).forward(heldout)
        self.runtime.transfer(0,1,"test-transfer-001")
        after = self.runtime.model(1).forward(heldout)
        self.assertGreater(after[1],before[1])
        np.testing.assert_array_equal(source,after)
        restarted = Runtime(self.temp.name)
        np.testing.assert_array_equal(after,restarted.model(1).forward(heldout))
        restarted.store.db.close()

    def test_nonverbal_investigation_correction_and_private_scope(self):
        event = ContactEvent(actor_ref="local-owner",modality="gesture",timestamp="2026-11-08T00:00:00Z",
                             observed_features={"hand":"raised"},source_ref="test-video-frame:1")
        result = self.runtime.contact(event)
        self.assertEqual(result["action"],"request_clarification")
        self.assertEqual(result["missing_modalities"]["audio"],"UNKNOWN")
        self.assertGreater(result["investigation"]["retrieved"],-1)
        self.runtime.correct_contact(result["id"],"request to pause","owner-confirmed")
        corrected = self.runtime.contact(event)
        self.assertEqual(corrected["interpretation"],"request to pause")
        with self.assertRaisesRegex(ValueError,"another owner"):
            Runtime(self.temp.name,"someone-else")

    def test_address_precision_and_unresolved_rules(self):
        values = {k:"1" for k in FIELDS}
        values["Degree"] = "1.123456789012"
        data = dict(values=values,dimensional_context="source-context",source_ref="source-page",
                    calculation_method="user-supplied; not derived",uncertainty={})
        address = Address.parse(data)
        self.assertIn("1.123456789012",address.serialize())
        self.assertEqual(list(address.shared_contact()),list(FIELDS[:4]))
        self.assertIsNone(evaluate_transition(address,address)["permitted"])
        self.assertTrue(all(c["equal"] for c in address.compare(address)))

    def test_invalid_execution_is_not_persisted(self):
        head = self.runtime.head
        for bad in ([float("nan")]*8,[1]*7,[float("inf")]*8):
            with self.assertRaises(ValueError):
                self.runtime.execute(bad)
        self.assertEqual(self.runtime.head,head)


if __name__ == "__main__":
    unittest.main()
