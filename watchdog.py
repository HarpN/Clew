"""
watchdog.py - Drift & Corruption Watchdog for Clew V5 Architecture
Continuously verifies state consistency between the ClewEventLedger, GraphCRDT, and MerkleDAG,
triggering automated rollbacks if memory corruption or state drift occurs.
"""

import json
from typing import Tuple, Optional
from crdt_engine import GraphCRDT
from ledger import ClewEventLedger, compute_hash_hex
from version_engine import VersionEngine
from merkle_dag import serialize_graph_crdt

class StateWatchdog:
    """
    Active integrity monitoring watchdog for GraphCRDT and MerkleDAG state consistency.
    """

    def __init__(self, crdt_instance: GraphCRDT, ledger_instance: ClewEventLedger, version_engine: VersionEngine):
        self.crdt = crdt_instance
        self.ledger = ledger_instance
        self.version_engine = version_engine

    def verify_state_integrity(self) -> Tuple[bool, str]:
        """
        Validates the ledger integrity and Merkle DAG integrity.
        Replays the ledger onto a temporary clean GraphCRDT and compares state root hashes.
        Returns a tuple (is_valid, status_message).
        """
        # 1. Validate ledger integrity
        if not self.ledger.verify_integrity():
            return False, "Ledger integrity verification failed"

        # 2. Validate Merkle DAG integrity
        if not self.version_engine.dag.verify_dag_integrity():
            return False, "Merkle DAG integrity verification failed"

        # 3. Replay ledger onto clean GraphCRDT
        temp_crdt = GraphCRDT()
        temp_crdt.apply_ledger(self.ledger)

        # 4. Compare active CRDT state root with temp replayed CRDT state root
        active_snapshot = serialize_graph_crdt(self.crdt)
        active_root = compute_hash_hex(json.dumps(active_snapshot, sort_keys=True, separators=(',', ':')).encode('utf-8'))

        temp_snapshot = serialize_graph_crdt(temp_crdt)
        temp_root = compute_hash_hex(json.dumps(temp_snapshot, sort_keys=True, separators=(',', ':')).encode('utf-8'))

        if active_root != temp_root:
            return False, f"State root mismatch: active ({active_root}) vs replayed ({temp_root})"

        return True, "State integrity verified successfully"

    def detect_drift(self) -> bool:
        """
        Compares current crdt_instance properties against the snapshot stored at head_commit_hash.
        Returns True if uncommitted mutations or out-of-order state corruptions exist, otherwise False.
        """
        head_hash = self.version_engine.head_commit_hash
        active_snapshot = serialize_graph_crdt(self.crdt)
        active_root = compute_hash_hex(json.dumps(active_snapshot, sort_keys=True, separators=(',', ':')).encode('utf-8'))

        if head_hash is None:
            # Check if active CRDT is non-empty
            empty_snapshot = serialize_graph_crdt(GraphCRDT())
            empty_root = compute_hash_hex(json.dumps(empty_snapshot, sort_keys=True, separators=(',', ':')).encode('utf-8'))
            return active_root != empty_root

        commit = self.version_engine.dag.get_commit(head_hash)
        if not commit:
            return True  # Commit doesn't exist in DAG: drift/corruption

        return active_root != commit.state_root_hash

    def auto_recover(self) -> Tuple[bool, str]:
        """
        If drift or corruption is detected, automatically triggers rollback to the last known
        cryptographically verified Merkle commit.
        Returns (recovered, message).
        """
        is_valid, status_msg = self.verify_state_integrity()
        has_drift = self.detect_drift()

        if not is_valid or has_drift:
            head_hash = self.version_engine.head_commit_hash
            if not head_hash:
                return False, "Cannot recover: No head commit exists in Merkle DAG"
            try:
                self.version_engine.checkout(head_hash)
                return True, f"State successfully rolled back to last known commit: {head_hash}"
            except Exception as e:
                return False, f"Recovery failed: {str(e)}"

        return False, "No drift or corruption detected"
