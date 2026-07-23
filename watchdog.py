"""
watchdog.py - Drift & Corruption Watchdog for Clew V5 Architecture
Continuously verifies state consistency between the ClewEventLedger, GraphCRDT, and MerkleDAG,
triggering automated rollbacks if memory corruption or state drift occurs.
"""

import json
import logging
import asyncio
from typing import Tuple, Dict, Any, Optional

from crdt_engine import GraphCRDT
from ledger import ClewEventLedger, compute_hash_hex
from version_engine import VersionEngine
from merkle_dag import serialize_graph_crdt

logger = logging.getLogger("clew.watchdog")

class StateWatchdog:
    """
    Active state watchdog monitoring hash-chain continuity and Merkle DAG alignment.
    """
    def __init__(self, crdt_instance: GraphCRDT, ledger_instance: ClewEventLedger, version_engine: VersionEngine):
        self.crdt = crdt_instance
        self.ledger = ledger_instance
        self.version_engine = version_engine

    def verify_state_integrity(self) -> Tuple[bool, str]:
        """
        Validates the ledger integrity, Merkle DAG integrity, and active state consistency against replayed ledger.
        """
        if not self.ledger.verify_integrity():
            return False, "Ledger BLAKE3 hash-chain continuity broken."
        if not self.version_engine.dag.verify_dag_integrity():
            return False, "Merkle DAG parent link integrity verification failed."

        # Replay ledger onto clean GraphCRDT to verify active state consistency
        temp_crdt = GraphCRDT()
        temp_crdt.apply_ledger(self.ledger)
        active_root = self.crdt.get_state_root_hash()
        temp_root = temp_crdt.get_state_root_hash()

        if active_root != temp_root:
            return False, f"State root mismatch: active ({active_root}) vs replayed ({temp_root})"

        return True, "State integrity verified."

    def detect_drift(self) -> bool:
        """
        Compares active state root hash against the HEAD commit's state root hash.
        Returns True if uncommitted mutations or state drift exist.
        """
        head_commit = self.version_engine.get_head_commit()
        if not head_commit:
            empty_root = GraphCRDT().get_state_root_hash()
            return self.crdt.get_state_root_hash() != empty_root
        return self.crdt.get_state_root_hash() != head_commit.state_root_hash

    def auto_recover(self) -> Tuple[bool, str]:
        """
        Triggers atomic rollback/restoration to the HEAD commit in Merkle DAG.
        """
        head_commit = self.version_engine.get_head_commit()
        if not head_commit:
            return False, "No head commit available for auto-recovery."
        try:
            self.version_engine.checkout(head_commit.commit_hash)
            return True, f"State restored cleanly to Merkle commit {head_commit.commit_hash}."
        except Exception as e:
            return False, f"Auto-recovery checkout failed: {e}"

class WatchdogDaemon:
    """
    Asynchronous background daemon that periodically audits state integrity
    and triggers automated recovery if memory drift or corruption is detected.
    """
    def __init__(self, watchdog_instance: StateWatchdog, check_interval: int = 30):
        self.watchdog = watchdog_instance
        self.check_interval = check_interval
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Starts periodic background health auditing loop."""
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._audit_loop())
        logger.info(f"[WATCHDOG_DAEMON] Background integrity polling started (Interval: {self.check_interval}s).")

    async def stop(self):
        """Stops background health auditing loop cleanly."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[WATCHDOG_DAEMON] Background integrity polling stopped.")

    async def _audit_loop(self):
        while self.is_running:
            try:
                await asyncio.sleep(self.check_interval)
                logger.debug("[WATCHDOG_DAEMON] Executing periodic state audit...")
                
                # Check 1: Ledger & DAG Hash-Chain Integrity
                valid, msg = self.watchdog.verify_state_integrity()
                if not valid:
                    logger.error(f"[WATCHDOG_DAEMON] Integrity Compromised: {msg}. Initiating auto-recovery...")
                    rec_ok, rec_msg = self.watchdog.auto_recover()
                    logger.info(f"[WATCHDOG_DAEMON] Auto-recovery result: {rec_ok} - {rec_msg}")
                    continue

                # Check 2: Drift Detection
                has_drift = self.watchdog.detect_drift()
                if has_drift:
                    logger.warning("[WATCHDOG_DAEMON] Memory drift detected against HEAD commit. Re-aligning state...")
                    rec_ok, rec_msg = self.watchdog.auto_recover()
                    logger.info(f"[WATCHDOG_DAEMON] Drift re-alignment result: {rec_ok} - {rec_msg}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[WATCHDOG_DAEMON] Unexpected error in audit loop: {e}")
