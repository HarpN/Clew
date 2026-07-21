"""
tests/test_merkle_versioning.py - Unit test suite for BLAKE3 Merkle DAG Versioning & Atomic Rollback.
Verifies commit creation, hash chaining, atomic rollback, diff computation, and integrity verification.
"""

import unittest
from crdt_engine import GraphCRDT
from ledger import ClewEventLedger
from merkle_dag import MerkleDAG, MerkleCommit
from version_engine import VersionEngine

class TestMerkleVersioning(unittest.TestCase):

    def test_commit_creation_and_hash_chaining(self):
        """
        Performs graph mutations, creates two sequential commits via VersionEngine,
        and verifies that the second commit references the first commit's hash in parent_hashes.
        """
        crdt = GraphCRDT()
        engine = VersionEngine(crdt_instance=crdt, node_id="node_a")

        # Mutate 1: Add a node
        ledger = ClewEventLedger(node_id="node_a")
        ledger.append("NODE_ADD", target_id="node_1")
        crdt.apply_ledger(ledger)

        # Commit 1
        c1 = engine.commit(message="Initial commit")
        self.assertIsNotNone(c1.commit_hash)
        self.assertEqual(c1.parent_hashes, [])
        self.assertEqual(engine.head_commit_hash, c1.commit_hash)

        # Mutate 2: Add scalar and edge
        ledger2 = ClewEventLedger(node_id="node_a")
        ledger2.append("SET_SCALAR", target_id="node_1", payload={"property": "priority", "value": "P1"})
        ledger2.append("EDGE_ADD", target_id="edge_1", payload={"source": "node_1", "dest": "node_2", "label": "DEP"})
        crdt.apply_ledger(ledger2)

        # Commit 2
        c2 = engine.commit(message="Second commit")
        self.assertIsNotNone(c2.commit_hash)
        self.assertEqual(c2.parent_hashes, [c1.commit_hash])
        self.assertEqual(engine.head_commit_hash, c2.commit_hash)

        # Verify history structure
        history = engine.get_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["commit_hash"], c1.commit_hash)
        self.assertEqual(history[1]["commit_hash"], c2.commit_hash)

    def test_atomic_rollback(self):
        """
        Adds nodes/edges to GraphCRDT, commits state (C1), adds more nodes (C2),
        and executes checkout(C1.commit_hash).
        Asserts that the GraphCRDT state is restored exactly to C1's state, purging items added in C2.
        """
        crdt = GraphCRDT()
        engine = VersionEngine(crdt_instance=crdt, node_id="node_a")

        # Create state C1
        ledger1 = ClewEventLedger(node_id="node_a")
        ledger1.append("NODE_ADD", target_id="n1")
        ledger1.append("NODE_ADD", target_id="n2")
        crdt.apply_ledger(ledger1)

        c1 = engine.commit("Commit C1")

        # Verify initial state
        self.assertTrue(crdt.nodes.contains("n1"))
        self.assertTrue(crdt.nodes.contains("n2"))
        self.assertFalse(crdt.nodes.contains("n3"))

        # Create state C2
        ledger2 = ClewEventLedger(node_id="node_a")
        ledger2.append("NODE_ADD", target_id="n3")
        crdt.apply_ledger(ledger2)

        c2 = engine.commit("Commit C2")

        # Verify secondary state
        self.assertTrue(crdt.nodes.contains("n1"))
        self.assertTrue(crdt.nodes.contains("n2"))
        self.assertTrue(crdt.nodes.contains("n3"))

        # Rollback to C1
        success = engine.checkout(c1.commit_hash)
        self.assertTrue(success)
        self.assertEqual(engine.head_commit_hash, c1.commit_hash)

        # Assert C1 state is restored, C2 items purged
        self.assertTrue(crdt.nodes.contains("n1"))
        self.assertTrue(crdt.nodes.contains("n2"))
        self.assertFalse(crdt.nodes.contains("n3"))

        # Rollback to C2 again
        success = engine.checkout(c2.commit_hash)
        self.assertTrue(success)
        self.assertEqual(engine.head_commit_hash, c2.commit_hash)
        self.assertTrue(crdt.nodes.contains("n3"))

        # Test checkout with invalid commit hash raises ValueError
        with self.assertRaises(ValueError):
            engine.checkout("invalid-hash")

    def test_dag_diff_computation(self):
        """
        Computes the diff between two commits and asserts that newly added/removed properties
        are accurately identified.
        """
        crdt = GraphCRDT()
        engine = VersionEngine(crdt_instance=crdt, node_id="node_a")

        # Commit 1: base
        ledger1 = ClewEventLedger(node_id="node_a")
        ledger1.append("NODE_ADD", target_id="n1")
        ledger1.append("SET_SCALAR", target_id="n1", payload={"property": "priority", "value": "P2"})
        crdt.apply_ledger(ledger1)
        c1 = engine.commit("Base State")

        # Commit 2: modified/added
        ledger2 = ClewEventLedger(node_id="node_a")
        ledger2.append("NODE_ADD", target_id="n2")
        ledger2.append("SET_SCALAR", target_id="n1", payload={"property": "priority", "value": "P1"})
        ledger2.append("SET_SCALAR", target_id="n1", payload={"property": "tags", "value": "critical"})
        crdt.apply_ledger(ledger2)
        c2 = engine.commit("Updated State")

        # Calculate diff from C1 -> C2
        diff = engine.dag.diff_commits(c1.commit_hash, c2.commit_hash)

        # Check nodes
        self.assertIn("n2", diff["nodes"]["added"])
        self.assertEqual(diff["nodes"]["removed"], [])

        # Check properties
        # added property: tags
        added_props = diff["properties"]["added"]
        self.assertEqual(len(added_props), 1)
        self.assertEqual(added_props[0]["target"], "n1")
        self.assertEqual(added_props[0]["property"], "tags")
        self.assertEqual(added_props[0]["value"], "critical")

        # modified property: priority
        modified_props = diff["properties"]["modified"]
        self.assertEqual(len(modified_props), 1)
        self.assertEqual(modified_props[0]["target"], "n1")
        self.assertEqual(modified_props[0]["property"], "priority")
        self.assertEqual(modified_props[0]["old_value"], "P2")
        self.assertEqual(modified_props[0]["new_value"], "P1")

        self.assertEqual(diff["properties"]["removed"], [])

    def test_dag_integrity_verification(self):
        """
        Asserts that verify_dag_integrity() returns True for valid commits and detects
        tampered or corrupted commit hashes.
        """
        crdt = GraphCRDT()
        engine = VersionEngine(crdt_instance=crdt, node_id="node_a")

        # Generate some history
        ledger1 = ClewEventLedger(node_id="node_a")
        ledger1.append("NODE_ADD", target_id="n1")
        crdt.apply_ledger(ledger1)
        c1 = engine.commit("Commit 1")

        ledger2 = ClewEventLedger(node_id="node_a")
        ledger2.append("NODE_ADD", target_id="n2")
        crdt.apply_ledger(ledger2)
        c2 = engine.commit("Commit 2")

        # Initially valid
        self.assertTrue(engine.dag.verify_dag_integrity())

        # Tamper with the message of C1, which changes its computed hash
        c1.message = "Tampered message"
        
        # Now integrity verification should fail
        self.assertFalse(engine.dag.verify_dag_integrity())

        # Restore message
        c1.message = "Commit 1"
        self.assertTrue(engine.dag.verify_dag_integrity())

        # Now tamper with parent hashes link in C2
        c2.parent_hashes = ["corrupted-hash"]
        self.assertFalse(engine.dag.verify_dag_integrity())


if __name__ == "__main__":
    unittest.main()
