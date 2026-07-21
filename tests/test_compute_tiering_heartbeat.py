"""
tests/test_compute_tiering_heartbeat.py - Unit test suite for 3-Tier Compute Architecture,
Heartbeat Daemon payload validation, failover thresholding, and Adaptive Sync Duty-Cycling.
"""

import unittest
import time
from protocol import (
    ComputeTier,
    SyncCadenceState,
    HeartbeatPayload
)
from router import (
    router,
    ModelTier,
    LOCAL_BRAIN_STEM_MODEL,
    CLOUD_WARM_MODEL,
    CLOUD_COLD_BATCH_MODEL,
    CLOUD_COLD_SANDBOX_MODEL
)
from heartbeat_daemon import HeartbeatDaemon, FAILOVER_MISSED_PINGS_THRESHOLD

class TestComputeTieringAndHeartbeat(unittest.TestCase):

    def test_01_compute_tier_enums_and_routing(self):
        """Verify 3-tier compute model routing metadata and provider mapping."""
        # Tier 1 Local Brain Stem
        t1_route = router.route_compute_tier(ModelTier.TIER_1_LOCAL_BRAIN_STEM)
        self.assertEqual(t1_route["hardware"], "Local GPU + System RAM")
        self.assertEqual(t1_route["latency_target"], "<15ms")

        # Tier 2 Cloud Warm
        t2_route = router.route_compute_tier(ModelTier.TIER_2_CLOUD_WARM)
        self.assertEqual(t2_route["provider"], "Together AI Serverless APIs")
        self.assertEqual(t2_route["latency_target"], "<1s")

        # Tier 3A Cloud Cold Batch
        t3a_route = router.route_compute_tier(ModelTier.TIER_3A_CLOUD_COLD_BATCH)
        self.assertEqual(t3a_route["provider"], "Together AI Batch API")
        self.assertTrue(t3a_route.get("async"))

        # Tier 3B Cloud Cold Sandboxed Execution
        t3b_route = router.route_compute_tier(ModelTier.TIER_3B_CLOUD_COLD_SANDBOX)
        self.assertEqual(t3b_route["provider"], "Modal Serverless Containers")
        self.assertTrue(t3b_route.get("sandboxed"))
        self.assertEqual(t3b_route.get("environment"), "gVisor")

    def test_02_heartbeat_payload_byte_size(self):
        """Verify HeartbeatPayload stays within 64 to 128 bytes constraint."""
        payload = HeartbeatPayload(
            node_id="clew-node-alpha",
            sequence_nonce=101,
            hlc_timestamp=1774123456.789123,
            status_flags={"ready": True, "idle": False, "cloud_promoted": False}
        )
        compact_bytes = payload.to_compact_bytes()
        byte_len = len(compact_bytes)
        
        self.assertGreaterEqual(byte_len, 64, f"Payload size {byte_len} bytes < 64 bytes minimum.")
        self.assertLessEqual(byte_len, 128, f"Payload size {byte_len} bytes > 128 bytes maximum.")

        # Test round-trip deserialization
        restored = HeartbeatPayload.from_compact_bytes(compact_bytes)
        self.assertEqual(restored.node_id, "clew-node-alpha")
        self.assertEqual(restored.sequence_nonce, 101)

    def test_03_heartbeat_failover_threshold(self):
        """Verify missing 3 consecutive heartbeats (15s) triggers Cloud promotion to active warm standby."""
        daemon = HeartbeatDaemon(node_id="test-failover-node")
        failover_called = []
        daemon.on_failover_callback = lambda: failover_called.append(True)

        self.assertFalse(daemon.is_cloud_promoted)
        self.assertEqual(daemon.missed_pings, 0)

        # Record 1st missed ping
        daemon.record_missed_heartbeat()
        self.assertFalse(daemon.is_cloud_promoted)

        # Record 2nd missed ping
        daemon.record_missed_heartbeat()
        self.assertFalse(daemon.is_cloud_promoted)

        # Record 3rd missed ping -> threshold met (15 seconds)
        daemon.record_missed_heartbeat()
        self.assertTrue(daemon.is_cloud_promoted)
        self.assertTrue(len(failover_called) > 0)

        # Reset on successful ping
        daemon.record_successful_heartbeat()
        self.assertEqual(daemon.missed_pings, 0)

    def test_04_adaptive_sync_cadence_duty_cycling(self):
        """Verify Adaptive Sync Cadence state transitions and pre-sleep flush execution."""
        daemon = HeartbeatDaemon(node_id="test-cadence-node")
        flush_called = []
        daemon.on_flush_callback = lambda: flush_called.append(True)

        # Active Session state
        daemon.set_sync_cadence(SyncCadenceState.ACTIVE_SESSION)
        self.assertEqual(daemon.active_cadence, SyncCadenceState.ACTIVE_SESSION)
        self.assertEqual(daemon.sync_interval_seconds, 5.0)

        # Idle / Background state (10+ min system idle -> 15-30m duty cycling)
        daemon.set_sync_cadence(SyncCadenceState.IDLE_BACKGROUND)
        self.assertEqual(daemon.active_cadence, SyncCadenceState.IDLE_BACKGROUND)
        self.assertEqual(daemon.sync_interval_seconds, 900.0)

        # Pre-Sleep / Graceful Shutdown state
        daemon.set_sync_cadence(SyncCadenceState.PRE_SLEEP_FLUSH)
        self.assertEqual(daemon.active_cadence, SyncCadenceState.PRE_SLEEP_FLUSH)
        self.assertEqual(daemon.sync_interval_seconds, 60.0)
        self.assertTrue(len(flush_called) > 0, "Pre-sleep flush callback was not executed.")

if __name__ == "__main__":
    unittest.main()
