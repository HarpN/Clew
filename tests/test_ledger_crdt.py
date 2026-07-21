"""
tests/test_ledger_crdt.py - Test suite for Event Ledger & Graph CRDT Engine
Verifies ClewLedgerEvent HLC timestamp ordering, tamper-evident hash chain integrity,
Add-Wins OR-Sets for topology, LWW Registers for scalars, Multi-Value Registers (MVR)
for divergent semantic attributes, and multi-node GraphCRDT merging.
"""

import time
import unittest
from ledger import ClewLedgerEvent, ClewEventLedger
from crdt_engine import (
    AddWinsORSet,
    LWWRegister,
    MultiValueRegister,
    GraphCRDT
)

class TestClewEventLedger(unittest.TestCase):

    def test_ledger_append_and_hash_chain_integrity(self):
        """Verifies event creation, monotonic HLC timestamps, and tamper-evident hash chain integrity."""
        ledger = ClewEventLedger(node_id="node_a")
        e1 = ledger.append("NODE_ADD", target_id="node_1", payload={"name": "Task A"})
        e2 = ledger.append("SET_SCALAR", target_id="node_1", payload={"property": "priority", "value": "P1"})
        e3 = ledger.append("EDGE_ADD", target_id="edge_1", payload={"source": "node_1", "dest": "node_2", "label": "DEPENDS_ON"})

        self.assertEqual(len(ledger.events), 3)
        self.assertEqual(e1.prev_hash, "0" * 64)
        self.assertEqual(e2.prev_hash, e1.event_hash)
        self.assertEqual(e3.prev_hash, e2.event_hash)
        self.assertTrue(ledger.verify_integrity())

    def test_ledger_integrity_failure_on_tampering(self):
        """Verifies verify_integrity() returns False when an event payload is tampered with."""
        ledger = ClewEventLedger(node_id="node_a")
        ledger.append("NODE_ADD", target_id="node_1")
        ledger.append("NODE_ADD", target_id="node_2")

        self.assertTrue(ledger.verify_integrity())
        
        # Tamper with first event's payload
        ledger.events[0].payload["tampered"] = True
        self.assertFalse(ledger.verify_integrity())

    def test_get_events_since_filtering(self):
        """Verifies get_events_since returns events strictly after a specified HLC timestamp."""
        ledger = ClewEventLedger(node_id="node_a")
        t0 = time.time()
        e1 = ledger.append("NODE_ADD", target_id="n1", physical_time=t0)
        e2 = ledger.append("NODE_ADD", target_id="n2", physical_time=t0 + 1.0)
        e3 = ledger.append("NODE_ADD", target_id="n3", physical_time=t0 + 2.0)

        events_after_e1 = ledger.get_events_since(e1.hlc_key)
        self.assertEqual(len(events_after_e1), 2)
        self.assertEqual(events_after_e1[0].target_id, "n2")
        self.assertEqual(events_after_e1[1].target_id, "n3")

class TestAddWinsORSet(unittest.TestCase):

    def test_add_wins_semantics_on_concurrent_add_remove(self):
        """Verifies Add-Wins OR-Set retains elements when concurrent additions and removals occur."""
        set_a = AddWinsORSet()
        set_b = AddWinsORSet()

        # Node A adds element 'node_1' with tag_1
        set_a.add("node_1", "tag_1")

        # Sync A -> B
        set_b.merge(set_a)
        self.assertTrue(set_b.contains("node_1"))

        # Node B observes tag_1 and removes 'node_1'
        set_b.remove("node_1")
        self.assertFalse(set_b.contains("node_1"))

        # Concurrently, Node A adds 'node_1' again with new tag_2
        set_a.add("node_1", "tag_2")

        # Merge B into A
        set_a.merge(set_b)
        
        # Add Wins: tag_2 was not observed by Node B during remove, so 'node_1' remains active!
        self.assertTrue(set_a.contains("node_1"))

class TestLWWRegister(unittest.TestCase):

    def test_lww_register_conflict_resolution(self):
        """Verifies LWWRegister resolves updates by highest HLC timestamp."""
        reg1 = LWWRegister("old_val", (100.0, 1, "node_a"))
        reg2 = LWWRegister("new_val", (100.0, 2, "node_b"))

        reg1.merge(reg2)
        self.assertEqual(reg1.value, "new_val")

        # Out of order earlier timestamp update ignored
        reg1.set("stale_val", (99.0, 5, "node_c"))
        self.assertEqual(reg1.value, "new_val")

class TestMultiValueRegister(unittest.TestCase):

    def test_mvr_divergent_value_retention_and_resolution(self):
        """Verifies MultiValueRegister retains concurrent split-brain updates and allows resolution."""
        mvr_a = MultiValueRegister()
        mvr_b = MultiValueRegister()

        # Node A & Node B set divergent semantic attributes concurrently
        ts_a = (100.0, 1, "node_a")
        ts_b = (100.0, 1, "node_b")

        mvr_a.set("Summary by Node A", ts_a)
        mvr_b.set("Summary by Node B", ts_b)

        mvr_a.merge(mvr_b)
        self.assertTrue(mvr_a.is_divergent())
        self.assertEqual(len(mvr_a.read_values()), 2)
        self.assertIn("Summary by Node A", mvr_a.read_values())
        self.assertIn("Summary by Node B", mvr_a.read_values())

        # Resolve divergent entry via LLM Arbiter decision
        res_ts = (101.0, 1, "node_a")
        mvr_a.resolve("Reconciled Unified Summary", res_ts)
        self.assertFalse(mvr_a.is_divergent())
        self.assertEqual(mvr_a.read_values(), ["Reconciled Unified Summary"])

class TestGraphCRDT(unittest.TestCase):

    def test_graph_crdt_ledger_replay_and_merge(self):
        """Verifies GraphCRDT ledger replay and convergence across two independent nodes."""
        ledger_a = ClewEventLedger(node_id="node_a")
        ledger_b = ClewEventLedger(node_id="node_b")

        # Node A events
        ledger_a.append("NODE_ADD", target_id="task_101")
        ledger_a.append("SET_SCALAR", target_id="task_101", payload={"property": "priority", "value": "P1"})
        ledger_a.append("SET_SEMANTIC_MVR", target_id="task_101", payload={"property": "notes", "value": "Draft by Node A"})

        # Node B events (concurrent)
        ledger_b.append("NODE_ADD", target_id="task_101")
        ledger_b.append("SET_SEMANTIC_MVR", target_id="task_101", payload={"property": "notes", "value": "Draft by Node B"})

        graph_a = GraphCRDT()
        graph_b = GraphCRDT()

        graph_a.apply_ledger(ledger_a)
        graph_b.apply_ledger(ledger_b)

        # Merge graph B into graph A
        graph_a.merge(graph_b)

        self.assertTrue(graph_a.nodes.contains("task_101"))
        self.assertEqual(graph_a.scalars[("task_101", "priority")].value, "P1")

        # Check semantic MVR divergence
        divergent = graph_a.get_divergent_mvr_entries()
        self.assertIn(("task_101", "notes"), divergent)
        mvr = divergent[("task_101", "notes")]
        self.assertTrue(mvr.is_divergent())
        self.assertEqual(len(mvr.read_values()), 2)

if __name__ == "__main__":
    unittest.main()
