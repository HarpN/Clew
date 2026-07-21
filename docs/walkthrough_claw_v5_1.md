# Walkthrough - Clew 3-Tier Compute Architecture & Heartbeat Daemon

We have successfully implemented and integrated the **Clew 3-Tier Compute Architecture**, **Heartbeat Daemon**, and **Adaptive Sync Cadence (Duty-Cycling)** into the Clew system.

---

## ⚡ 1. 3-Tier Compute Architecture Topology

### Protocol & Routing Updates
- **`protocol.py`**: Added `ComputeTier` enum to formalize execution targets across:
  - `TIER_1_LOCAL_BRAIN_STEM`: Local GPU + System RAM (Qwen 2.5 7B / Llama 3.2 3B) for sub-15ms intent routing, graph memory queries, and Pydantic validation.
  - `TIER_2_CLOUD_WARM`: Together AI Serverless APIs (Llama 3.3 70B, Qwen 2.5 Coder 32B, DeepSeek V3) for sub-second active reasoning.
  - `TIER_3A_CLOUD_COLD_BATCH`: Together AI Batch API for non-real-time operations (nightly memory re-indexing, prompt distillation) at a 50% discount.
  - `TIER_3B_CLOUD_COLD_SANDBOX`: Modal Serverless Containers for scale-to-zero, gVisor-sandboxed secure code execution.
- **`router.py`**:
  - Expanded `ModelTier` enum and added compute tier routing metadata via `AgenticRouter.route_compute_tier()`.
  - Defined model defaults (`LOCAL_BRAIN_STEM_MODEL`, `CLOUD_WARM_MODEL`, `CLOUD_COLD_BATCH_MODEL`, `CLOUD_COLD_SANDBOX_MODEL`).

---

## 💓 2. Heartbeat Daemon & Adaptive Sync Cadence

### Dedicated Heartbeat Module ([heartbeat_daemon.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/heartbeat_daemon.py))
- **Heartbeat Payload**: `HeartbeatPayload` Pydantic model (`node_id`, `sequence_nonce`, `hlc_timestamp`, `status_flags`) producing compact 64 to 128 byte payloads via `.to_compact_bytes()`.
- **Failover Promotion**: Pings every 5 seconds. Missing 3 consecutive heartbeats (15 seconds) automatically triggers `promote_to_cloud_standby()`, upgrading execution to Cloud Warm Standby (Together AI Tier 2).
- **Adaptive Sync Cadence (Duty-Cycling)**:
  - `ACTIVE_SESSION`: 5 - 15 second micro-batches when IDE/Terminal is active.
  - `IDLE_BACKGROUND`: 15 - 30 minute duty-cycling interval when system is idle > 10 min.
  - `PRE_SLEEP_FLUSH`: Triggers immediate pre-sleep full state sync flush, then shifts into a 60-second ping state.

---

## 🧪 3. Verification & Unit Tests

### Automated Unit Test Suite ([tests/test_compute_tiering_heartbeat.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_compute_tiering_heartbeat.py))
- `test_01_compute_tier_enums_and_routing`: Validated provider mappings, latency targets, and sandboxing flags for all 4 compute tiers.
- `test_02_heartbeat_payload_byte_size`: Verified that `HeartbeatPayload` compact bytes payload stays strictly within 64 to 128 bytes.
- `test_03_heartbeat_failover_threshold`: Verified failover promotion triggers after 3 consecutive missed pings (15s threshold).
- `test_04_adaptive_sync_cadence_duty_cycling`: Tested transitions between `ACTIVE_SESSION`, `IDLE_BACKGROUND`, and `PRE_SLEEP_FLUSH`.

### Architectural Documentation
- Updated [docs/architecture.md](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/docs/architecture.md) with full compute tier topology tables and heartbeat specifications.
