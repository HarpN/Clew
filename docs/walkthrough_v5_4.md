# Walkthrough: Task 4: Drift & Corruption Watchdog + Local IPC Layer

This document summarizes the changes introduced for Task 4 to implement active state integrity/drift monitoring and the local high-speed inter-process communication transport.

## Changes Made

### 1. State Watchdog
- **[watchdog.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/watchdog.py)**: Created the `StateWatchdog` class which:
  - Validates ledger continuous chain hash-chain integrity via `verify_integrity()`.
  - Validates Merkle DAG structural links via `verify_dag_integrity()`.
  - Replays ledger events on a clean temporary `GraphCRDT` instance and compares its state root hash against the active `GraphCRDT` state root to detect discrepancies.
  - Exposes `detect_drift()` to compare the current in-memory CRDT against the head commit snapshot.
  - Exposes `auto_recover()` to roll back to the last known cryptographically verified Merkle commit in the event of drift or corruption.

### 2. IPC Layer
- **[ipc_socket.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ipc_socket.py)**: Created the `ClewIPCServer` and `ClewIPCClient` classes:
  - Uses `asyncio` socket streams.
  - Automatically binds to Unix Domain Sockets (`/tmp/clew_ipc.sock`) where supported, and falls back to TCP localhost socket (`127.0.0.1:9876`) on Windows/unsupported platforms.
  - Implements line-delimited message framing (`\n`-terminated JSON).
  - Handles command dispatching for `COMMIT`, `CHECKOUT`, `RECONCILE`, `HEALTH_CHECK`, and `INSPECT_STATE`.

### 3. Unit Tests
- **[test_watchdog_ipc.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_watchdog_ipc.py)**: Added a comprehensive unit test suite:
  - `test_watchdog_drift_detection_and_auto_recovery`: Verifies that direct memory mutations on the active CRDT are correctly identified as drift, and that `auto_recover()` successfully rolls back the CRDT to a safe commit state.
  - `test_ipc_socket_command_dispatch`: Boots `ClewIPCServer` asynchronously, connects via `ClewIPCClient`, sends `HEALTH_CHECK` and `COMMIT` commands, and asserts correct responses.
  - `test_ipc_state_inspection`: Validates querying `INSPECT_STATE` retrieves a complete serialized layout of active nodes and edges.

---

## Verification Results

### Automated Tests
- Running the watchdog and IPC specific unit tests:
  ```bash
  python -m unittest tests/test_watchdog_ipc.py
  ```
  Result: **Passed (3 tests in 0.073s)**
- Running the full workspace test discovery:
  ```bash
  python -m unittest discover tests
  ```
  Result: **Passed (88 tests in 23.713s with OK status)**
