# Implementation Plan - Clew 3-Tier Compute Architecture & Heartbeat Daemon

Integrate the **3-Tier Compute Architecture** (Local Brain Stem, Cloud Warm, Cloud Cold Batch & Sandboxed) and the **Heartbeat Daemon & Adaptive Sync Cadence** into Clew's core engine, protocols, and documentation.

## User Review Required

> [!NOTE]
> - **Compute Topology**: Tier 1 handles local sub-15ms intent routing & graph memory reads. Tier 2 delegates active reasoning to Together AI Serverless APIs (Llama 3.3 70B, Qwen 2.5 Coder 32B, DeepSeek V3). Tier 3 splits into Tier 3A (Together AI Batch API for 50% cost reduction on nightly tasks) and Tier 3B (Modal gVisor-sandboxed containers for isolated code execution).
> - **Heartbeat & Failover**: 64-128 byte heartbeats sent every 5 seconds. Missing 3 consecutive heartbeats (15 seconds) triggers promotion to Cloud Warm Standby.
> - **Duty Cycling**: Micro-batches (5-15s) during active sessions, 15-30 minute sync during idle periods (10+ min idle), and immediate full flush + 60s ping state during pre-sleep/graceful shutdown.

## Open Questions

- None. All specifications and performance targets are defined in the user request.

---

## Proposed Changes

### Core Protocols & Schemas

#### [MODIFY] [protocol.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/protocol.py)
- Expand `ComputeTier` enum to represent:
  - `TIER_1_LOCAL_BRAIN_STEM`
  - `TIER_2_CLOUD_WARM`
  - `TIER_3A_CLOUD_COLD_BATCH`
  - `TIER_3B_CLOUD_COLD_SANDBOX`
- Add `HeartbeatPayload` Pydantic model (`node_id`, `sequence_nonce`, `hlc_timestamp`, `status_flags`).
- Add helper method `to_compact_bytes()` to ensure payload stays within 64-128 bytes.
- Add `SyncCadenceState` enum (`ACTIVE_SESSION`, `IDLE_BACKGROUND`, `PRE_SLEEP_FLUSH`).

---

### Compute Tier Router

#### [MODIFY] [router.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/router.py)
- Align `ModelTier` with the 3-Tier Compute Architecture:
  - Tier 1: Local GPU + System RAM (Qwen 2.5 7B / Llama 3.2 3B) with sub-15ms target.
  - Tier 2: Cloud Warm Serverless (Together AI API with Llama 3.3 70B, Qwen 2.5 Coder 32B, DeepSeek V3).
  - Tier 3A: Cloud Cold Async Batch (Together AI Batch API for distillation/graph re-indexing).
  - Tier 3B: Cloud Cold Sandboxed Execution (Modal gVisor containers).
- Add router execution stubs and provider routing configurations for Together AI Serverless/Batch and Modal Container execution.

---

### Heartbeat Daemon & Duty Cycling

#### [NEW] [heartbeat_daemon.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/heartbeat_daemon.py)
- Implement `HeartbeatDaemon`:
  - Heartbeat generator producing 64-128 byte `HeartbeatPayload` objects.
  - 5-second interval heartbeat dispatch via Hivemind gRPC/UDP.
  - Failover monitor: tracks missing heartbeats and triggers Cloud promotion after 3 consecutive failures (15s).
  - Adaptive Sync Duty-Cycling controller:
    - Active Session: micro-batches (5-15s).
    - Idle / Background: duty-cycle interval (15-30m) when system idle > 10 min.
    - Pre-Sleep / Shutdown: immediate full pre-sleep flush, transitioning to 60s ping state.

---

### Documentation

#### [MODIFY] [docs/architecture.md](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/docs/architecture.md)
#### [MODIFY] [README.md](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/README.md)
- Update architectural diagrams and tables with 3-Tier Compute Architecture, Together AI / Modal roles, and Heartbeat / Adaptive Sync Cadence specs.

---

### Automated Unit Tests

#### [NEW] [tests/test_compute_tiering_heartbeat.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_compute_tiering_heartbeat.py)
- Test suite verifying:
  - 3-Tier compute classification and router target provider mapping.
  - `HeartbeatPayload` serialization and byte size compliance (64-128 bytes).
  - Failover promotion trigger upon missing 3 consecutive heartbeats (15s threshold).
  - Adaptive Sync Cadence state transitions (`ACTIVE_SESSION` -> `IDLE_BACKGROUND` -> `PRE_SLEEP_FLUSH`).

---

## Verification Plan

### Automated Tests
- Run `python -m unittest tests/test_compute_tiering_heartbeat.py`
- Run all workspace tests to verify zero regressions: `python -m unittest discover tests`

### Manual Verification
- Validate Heartbeat payload byte size using `HeartbeatPayload.to_compact_bytes()`.
- Test duty-cycling interval switching and pre-sleep flush execution.
