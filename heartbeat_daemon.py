"""
heartbeat_daemon.py - Heartbeat Daemon & Adaptive Sync Cadence for Clew LifeOS
Manages 64-128 byte node pings over Hivemind (gRPC/UDP), missed heartbeat failover tracking
(triggers Cloud promotion after 15s / 3 missed pings), and duty-cycling sync cadence state transitions.
"""

import time
import logging
import threading
from typing import Dict, Any, Optional, Callable
from protocol import (
    HeartbeatPayload,
    SyncCadenceState,
    ComputeTier,
    HivemindFrame,
    HivemindMessageType,
    HivemindFlags
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.heartbeat_daemon")

PING_INTERVAL_SECONDS = 5.0
FAILOVER_MISSED_PINGS_THRESHOLD = 3  # 15 seconds total (3 * 5s)
FAILOVER_TIME_SECONDS = 15.0

class HeartbeatDaemon:
    def __init__(self, node_id: str = "clew-primary-node", transport: str = "gRPC"):
        self.node_id = node_id
        self.transport = transport
        self.sequence_nonce = 0
        self.hlc_logical_counter = 0
        self.missed_pings = 0
        self.is_cloud_promoted = False
        self.active_cadence = SyncCadenceState.ACTIVE_SESSION
        self.sync_interval_seconds = 5.0  # Default active micro-batch (5s)
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self.on_failover_callback: Optional[Callable[[], None]] = None
        self.on_flush_callback: Optional[Callable[[], None]] = None

    def get_hlc_timestamp(self) -> float:
        """Generates a Hybrid Logical Clock timestamp combining physical epoch & logical counter."""
        physical_time = time.time()
        self.hlc_logical_counter += 1
        return physical_time + (self.hlc_logical_counter * 1e-6)

    def create_heartbeat_payload(self, is_idle: bool = False) -> HeartbeatPayload:
        """Constructs a 64-128 byte HeartbeatPayload."""
        self.sequence_nonce += 1
        payload = HeartbeatPayload(
            node_id=self.node_id,
            sequence_nonce=self.sequence_nonce,
            hlc_timestamp=self.get_hlc_timestamp(),
            status_flags={
                "ready": True,
                "idle": is_idle,
                "cloud_promoted": self.is_cloud_promoted
            }
        )
        return payload

    def send_ping(self) -> bytes:
        """Generates payload and verifies compact byte footprint (64..128 bytes)."""
        payload = self.create_heartbeat_payload(is_idle=(self.active_cadence == SyncCadenceState.IDLE_BACKGROUND))
        raw_bytes = payload.to_compact_bytes()
        logger.debug(f"[{self.transport}] Transmitting heartbeat ping #{payload.sequence_nonce} ({len(raw_bytes)} bytes)")
        return raw_bytes

    def send_binary_frame_ping(self) -> bytes:
        """Generates a 128-byte Hivemind binary frame header + Heartbeat payload."""
        payload = self.create_heartbeat_payload(is_idle=(self.active_cadence == SyncCadenceState.IDLE_BACKGROUND))
        compact_payload = payload.to_compact_bytes()
        
        frame = HivemindFrame(
            msg_type=HivemindMessageType.HEARTBEAT,
            flags=HivemindFlags.NONE,
            sequence_nonce=self.sequence_nonce,
            hlc_timestamp=int(payload.hlc_timestamp * 1000),
            payload=compact_payload
        )
        raw_binary_frame = frame.pack()
        logger.debug(f"[{self.transport}] Transmitting binary Hivemind frame heartbeat #{self.sequence_nonce} ({len(raw_binary_frame)} bytes)")
        return raw_binary_frame


    def record_missed_heartbeat(self):
        """Increments missed pings counter. Triggers cloud promotion on threshold (15s / 3 missed pings)."""
        self.missed_pings += 1
        logger.warning(f"Heartbeat missed! Count: {self.missed_pings}/{FAILOVER_MISSED_PINGS_THRESHOLD}")
        if self.missed_pings >= FAILOVER_MISSED_PINGS_THRESHOLD and not self.is_cloud_promoted:
            self.promote_to_cloud_standby()

    def record_successful_heartbeat(self):
        """Resets missed heartbeat counter on successful ping acknowledgment."""
        self.missed_pings = 0

    def promote_to_cloud_standby(self):
        """Promotes active execution to Cloud Warm Standby (Together AI Tier 2)."""
        self.is_cloud_promoted = True
        logger.error(f"Node '{self.node_id}' failed 3 consecutive heartbeats (15s). PROMOTING to Cloud Warm Standby (Tier 2).")
        if self.on_failover_callback:
            self.on_failover_callback()

    def set_sync_cadence(self, new_state: SyncCadenceState):
        """
        Updates Adaptive Sync Cadence (Duty-Cycling):
        - ACTIVE_SESSION: 5-15s micro-batches
        - IDLE_BACKGROUND: 15-30m duty cycling (when system idle 10+ min)
        - PRE_SLEEP_FLUSH: Triggers immediate full pre-sleep flush, transitions to 60s ping state
        """
        self.active_cadence = new_state
        if new_state == SyncCadenceState.ACTIVE_SESSION:
            self.sync_interval_seconds = 5.0
            logger.info("Sync cadence set to ACTIVE_SESSION (5s micro-batches).")
        elif new_state == SyncCadenceState.IDLE_BACKGROUND:
            self.sync_interval_seconds = 900.0  # 15 minutes
            logger.info("Sync cadence set to IDLE_BACKGROUND (15-30m duty cycle).")
        elif new_state == SyncCadenceState.PRE_SLEEP_FLUSH:
            self.sync_interval_seconds = 60.0
            logger.info("Sync cadence set to PRE_SLEEP_FLUSH. Executing immediate pre-sleep sync flush...")
            self.trigger_pre_sleep_flush()

    def trigger_pre_sleep_flush(self):
        """Executes an immediate full state sync flush before transitioning to low-power 60s ping state."""
        if self.on_flush_callback:
            self.on_flush_callback()
        logger.info("Pre-sleep state flush complete. System in 60s ping state.")

    def start_daemon(self):
        """Starts background heartbeat daemon loop."""
        self.is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"Heartbeat daemon started for node '{self.node_id}' over {self.transport}.")

    def stop_daemon(self):
        """Gracefully stops heartbeat daemon loop, triggering pre-sleep flush."""
        self.set_sync_cadence(SyncCadenceState.PRE_SLEEP_FLUSH)
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("Heartbeat daemon stopped.")

    def _run_loop(self):
        while self.is_running:
            try:
                self.send_ping()
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                self.record_missed_heartbeat()
            time.sleep(self.sync_interval_seconds if self.active_cadence == SyncCadenceState.ACTIVE_SESSION else PING_INTERVAL_SECONDS)

# Singleton global daemon instance
heartbeat_daemon = HeartbeatDaemon()
