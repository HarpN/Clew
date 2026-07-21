"""
tests/test_watchdog_ipc.py - Unit test suite for watchdog and local IPC layer.
Verifies state drift detection, auto-recovery, IPC server/client asynchronous command dispatching,
and active state inspection.
"""

import asyncio
import unittest
import sys
import os

from crdt_engine import GraphCRDT
from ledger import ClewEventLedger
from version_engine import VersionEngine
from watchdog import StateWatchdog
from ipc_socket import ClewIPCServer, ClewIPCClient
from reconciliation import ReconciliationEngine
from merkle_dag import serialize_graph_crdt

class TestWatchdogIPC(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Synchronous setup for state objects
        self.crdt = GraphCRDT()
        self.ledger = ClewEventLedger(node_id="test-node")
        self.version_engine = VersionEngine(crdt_instance=self.crdt, node_id="test-node")
        self.watchdog = StateWatchdog(
            crdt_instance=self.crdt,
            ledger_instance=self.ledger,
            version_engine=self.version_engine
        )
        self.reconciler = ReconciliationEngine(crdt_instance=self.crdt)

    def test_watchdog_drift_detection_and_auto_recovery(self):
        """
        Creates a valid commit state C_1, manually tampers with crdt_instance state outside of the ledger/DAG,
        asserts detect_drift() returns True, executes auto_recover(), and verifies that GraphCRDT is restored to C_1.
        """
        # 1. Setup valid state C_1
        self.ledger.append("NODE_ADD", target_id="node_1")
        self.ledger.append("SET_SCALAR", target_id="node_1", payload={"property": "val", "value": "init"})
        self.crdt.apply_ledger(self.ledger)
        
        c1 = self.version_engine.commit(message="Commit C1")
        
        # Verify initial consistency
        is_valid, msg = self.watchdog.verify_state_integrity()
        self.assertTrue(is_valid, f"Initial state should be valid: {msg}")
        self.assertFalse(self.watchdog.detect_drift(), "Should detect no drift initially")

        # 2. Tamper with crdt_instance directly (outside ledger and version engine)
        self.crdt.nodes.add("tampered_node", "tamper_tag")
        
        # Verify drift is detected
        self.assertTrue(self.watchdog.detect_drift(), "Should detect drift after tampering")
        
        # Verify state integrity check fails due to mismatch between replayed ledger state and active state
        is_valid, msg = self.watchdog.verify_state_integrity()
        self.assertFalse(is_valid, "State integrity should be invalid after tampering")
        self.assertIn("State root mismatch", msg)

        # 3. Execute auto_recover()
        recovered, recover_msg = self.watchdog.auto_recover()
        self.assertTrue(recovered, f"Should recover successfully: {recover_msg}")
        
        # 4. Verify restored state matches C1
        self.assertFalse(self.crdt.nodes.contains("tampered_node"), "Tampered node should be purged after recovery")
        self.assertTrue(self.crdt.nodes.contains("node_1"), "Original node_1 should still exist")
        self.assertFalse(self.watchdog.detect_drift(), "Should detect no drift after recovery")
        is_valid, msg = self.watchdog.verify_state_integrity()
        self.assertTrue(is_valid, f"State integrity should be clean: {msg}")

    async def test_ipc_socket_command_dispatch(self):
        """
        Boots a test ClewIPCServer, connects via ClewIPCClient, sends HEALTH_CHECK and COMMIT commands,
        and asserts that structured JSON responses are returned correctly over the socket.
        """
        # Use a high port number to prevent conflict
        test_port = 19876
        test_socket_path = "/tmp/clew_ipc_test.sock"
        
        server = ClewIPCServer(
            version_engine=self.version_engine,
            reconciliation_engine=self.reconciler,
            watchdog=self.watchdog,
            socket_path=test_socket_path,
            host="127.0.0.1",
            port=test_port
        )
        
        await server.start_async()
        
        client = ClewIPCClient(
            socket_path=test_socket_path,
            host="127.0.0.1",
            port=test_port
        )
        
        try:
            # 1. HEALTH_CHECK command
            hc_resp = await client.send_command("HEALTH_CHECK")
            self.assertEqual(hc_resp.get("status"), "success")
            data = hc_resp.get("data", {})
            self.assertTrue(data.get("is_valid"))
            self.assertFalse(data.get("drift_detected"))

            # 2. COMMIT command
            # Mutate slightly so there's something to commit
            self.ledger.append("NODE_ADD", target_id="node_2")
            self.crdt.apply_ledger(self.ledger)
            
            commit_resp = await client.send_command("COMMIT", {"message": "IPC Commit Test"})
            self.assertEqual(commit_resp.get("status"), "success")
            c_data = commit_resp.get("data", {})
            self.assertIsNotNone(c_data.get("commit_hash"))
            self.assertIsNotNone(c_data.get("state_root_hash"))
            
            # Verify version engine head reflects the committed state
            self.assertEqual(self.version_engine.head_commit_hash, c_data.get("commit_hash"))

            # 3. RECONCILE command (empty test case)
            rec_resp = await client.send_command("RECONCILE")
            self.assertEqual(rec_resp.get("status"), "success")
            self.assertEqual(rec_resp.get("data", {}).get("resolved_count"), 0)
            
        finally:
            await server.stop()

    async def test_ipc_state_inspection(self):
        """
        Executes state inspection queries over IPC and verifies that the returned JSON payload
        reflects the active CRDT nodes and edges.
        """
        test_port = 19877
        test_socket_path = "/tmp/clew_ipc_test_inspect.sock"
        
        server = ClewIPCServer(
            version_engine=self.version_engine,
            reconciliation_engine=self.reconciler,
            watchdog=self.watchdog,
            socket_path=test_socket_path,
            host="127.0.0.1",
            port=test_port
        )
        
        await server.start_async()
        
        client = ClewIPCClient(
            socket_path=test_socket_path,
            host="127.0.0.1",
            port=test_port
        )
        
        try:
            # Add nodes and edges
            self.ledger.append("NODE_ADD", target_id="vertex_a")
            self.ledger.append("NODE_ADD", target_id="vertex_b")
            self.ledger.append("EDGE_ADD", target_id="link_a_b", payload={"source": "vertex_a", "dest": "vertex_b", "label": "KNOWS"})
            self.crdt.apply_ledger(self.ledger)
            
            # Send INSPECT_STATE command
            inspect_resp = await client.send_command("INSPECT_STATE")
            self.assertEqual(inspect_resp.get("status"), "success")
            
            state_data = inspect_resp.get("data", {})
            nodes_add_set = state_data.get("nodes", {}).get("add_set", {})
            edges_add_set = state_data.get("edges", {}).get("add_set", {})
            
            # Assert that the serialized representation reflects our active CRDT state
            self.assertIn("vertex_a", nodes_add_set.values())
            self.assertIn("vertex_b", nodes_add_set.values())
            
            # Check edge exists (edges are list-of-lists in serialized JSON format: [source, dest, label])
            edges_list = list(edges_add_set.values())
            self.assertTrue(any(e == ["vertex_a", "vertex_b", "KNOWS"] for e in edges_list))

        finally:
            await server.stop()

if __name__ == "__main__":
    unittest.main()
