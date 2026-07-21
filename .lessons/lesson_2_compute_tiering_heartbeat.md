# Lesson 2: Compute Tiering & Heartbeat Orchestration

## 🧠 Core Concept: Hybrid Topologies & Failover Detection

Decentralized AI assistants need to be resilient to network failures, local resource restrictions, and device state changes. Clew addresses this with two mechanisms:
1. **3-Tier Compute Topology**:
   - **Tier 1 (Local Brain Stem)**: Low-latency local processing (e.g., local intent parsing, simple checks) on device system RAM.
   - **Tier 2 (Cloud Warm)**: High-performance cloud LLMs (Together AI) for active reasoning.
   - **Tier 3 (Cloud Cold)**: Async batch processing (Tier 3A) or sandboxed isolated code runtimes (Tier 3B).
2. **Duty-Cycled Sync Cadence**: To conserve bandwidth and battery, Clew changes its state sync speed dynamically depending on user activity.

If the local agent is disconnected or experiences high latency, Clew needs a way to detect it. The **Heartbeat Daemon** sends status pings regularly. If it misses 3 consecutive pings (15s total), it automatically promotes execution to **Cloud Warm Standby (Tier 2)**.

---

## 🔍 Code Breakdown

Let's examine how this logic is implemented in [heartbeat_daemon.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/heartbeat_daemon.py).

### Failover Promotion (`record_missed_heartbeat`)

In [heartbeat_daemon.py:L87-93](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/heartbeat_daemon.py#L87-L93), the daemon tracks consecutive missed pings:

```python
    def record_missed_heartbeat(self):
        """Increments missed pings counter. Triggers cloud promotion on threshold (15s / 3 missed pings)."""
        self.missed_pings += 1
        logger.warning(f"Heartbeat missed! Count: {self.missed_pings}/{FAILOVER_MISSED_PINGS_THRESHOLD}")
        if self.missed_pings >= FAILOVER_MISSED_PINGS_THRESHOLD and not self.is_cloud_promoted:
            self.promote_to_cloud_standby()
```

When `self.promote_to_cloud_standby()` is called, Clew flips its state to redirect cognitive tasks to cloud infrastructure so services are not interrupted.

### Adaptive Sync Cadence (`set_sync_cadence`)

To prevent battery drain on idle mobile devices or server resource hogging, the daemon cycles its sync cadence in [heartbeat_daemon.py:L105-123](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/heartbeat_daemon.py#L105-L123):

```python
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
```

When transitioning to `PRE_SLEEP_FLUSH`, the daemon triggers a synchronous commit of all dirty local state changes before entering a low-power mode.

---

## 🔬 Deep Dives

### 1. Hybrid Logical Clock (HLC) Timestamps
Standard physical timestamps (`time.time()`) are vulnerable to clock skew (where two machines have slightly different times) and clock adjustments.
To build a total ordering of events without a centralized clock server, the daemon constructs HLC timestamps in [heartbeat_daemon.py:L42-46](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/heartbeat_daemon.py#L42-L46):
```python
    def get_hlc_timestamp(self) -> float:
        """Generates a Hybrid Logical Clock timestamp combining physical epoch & logical counter."""
        physical_time = time.time()
        self.hlc_logical_counter += 1
        return physical_time + (self.hlc_logical_counter * 1e-6)
```
By appending a fractional logical counter (`logical_counter * 1e-6`) to the physical epoch, Clew guarantees that even if multiple events happen in the exact same microsecond physical slice, their causal order is strictly maintained.

---

## 📝 Interactive Quiz

### Question 1: What is the failover timeout threshold to promote Clew to Tier 2 (Cloud Warm)?
- **A)** 5 seconds (1 missed ping)
- **B)** 10 seconds (2 missed pings)
- **C)** 15 seconds (3 missed pings)
- **D)** 60 seconds (12 missed pings)

<details>
<summary>Reveal Answer & Explanation</summary>

**Correct Answer: C**

**Explanation**: 
According to `FAILOVER_MISSED_PINGS_THRESHOLD = 3` and a `PING_INTERVAL_SECONDS = 5.0`, a total of 15 seconds must elapse without a successful heartbeat response before promotion triggers.
</details>

### Question 2: What optimization occurs during the `PRE_SLEEP_FLUSH` cadence?
- **A)** All AI reasoning switches to local GPU only.
- **B)** The daemon performs an immediate local state commit and switches the sync cycle to a slow 60-second frequency.
- **C)** The SQLite database drops the HNSW indexes.
- **D)** The program exits immediately without saving.

<details>
<summary>Reveal Answer & Explanation</summary>

**Correct Answer: B**

**Explanation**: 
`PRE_SLEEP_FLUSH` forces a state sync via the `on_flush_callback` and duty-cycles the ping interval to 60.0 seconds to prevent unnecessary wakeups while the device is sleeping.
</details>

---

## 🛠️ Coding Exercise / Challenge

### Challenge: Dynamic Sync Scaling
Open [heartbeat_daemon.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/heartbeat_daemon.py). Implement a method `dynamically_scale_sync(battery_percent: float)` that automatically changes the sync state to `IDLE_BACKGROUND` if the battery falls below `20.0` percent. Validate your design by running:
`pytest tests/test_compute_tiering_heartbeat.py`
