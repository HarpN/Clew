# Implementation Plan: Task 4: Drift & Corruption Watchdog + Local IPC Layer

This plan designs the active integrity monitoring layer (`watchdog.py`), the local inter-process communication transport (`ipc_socket.py`), and the corresponding test suite (`tests/test_watchdog_ipc.py`).

## User Review Required

> [!IMPORTANT]
> - **Windows Localhost Socket Fallback**: On Windows/unsupported Unix environments, the server will bind to `127.0.0.1:9876` instead of the Unix Domain Socket path.
> - **Communication Protocol**: Commands and responses over the socket will be framed using newline-terminated (`\n`) JSON strings to ensure robust framing and parsing in asynchronous tests and client interactions.

## Proposed Changes

---

### Watchdog and State Verification

#### [NEW] [watchdog.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/watchdog.py)
Implement `StateWatchdog` class:
- **Initialization**:
  - `crdt_instance: GraphCRDT`
  - `ledger_instance: ClewEventLedger`
  - `version_engine: VersionEngine`
- **`verify_state_integrity()`**:
  - Checks `self.ledger.verify_integrity()`.
  - Checks `self.version_engine.dag.verify_dag_integrity()`.
  - Replays `self.ledger` onto a temporary clean `GraphCRDT`, serializes both, and compares their state roots using BLAKE3/SHA256 hex digest.
  - Returns `(is_valid: bool, status_message: str)`.
- **`detect_drift()`**:
  - Compares active `crdt_instance` against the commit snapshot at `version_engine.head_commit_hash`.
  - Returns `True` if a difference is detected (or if active state exists with no commits), else `False`.
- **`auto_recover()`**:
  - If drift or corruption is detected, rolls back `crdt_instance` by triggering `checkout(head_commit_hash)`.
  - Returns `(recovered: bool, message: str)`.

---

### Local IPC Layer

#### [NEW] [ipc_socket.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ipc_socket.py)
Implement local IPC transport:
- **`ClewIPCServer`**:
  - Listens on Unix Domain Socket or falls back to TCP `127.0.0.1:9876`.
  - Handles incoming JSON connections. Reads commands line-by-line (`\n` terminated).
  - Supported commands: `COMMIT`, `CHECKOUT`, `RECONCILE`, `HEALTH_CHECK`, `INSPECT_STATE`.
  - Dispatches to the underlying `VersionEngine`, `ReconciliationEngine`, and `StateWatchdog`.
  - Sends a JSON response with status, data, and optional error.
  - Exposes `start_async()` and `stop()` methods.
- **`ClewIPCClient`**:
  - Connects to Unix Domain Socket or TCP fallback.
  - Exposes `send_command(command, payload)` to transmit a command, read the `\n`-terminated JSON response, and parse it.

---

### Tests

#### [NEW] [test_watchdog_ipc.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_watchdog_ipc.py)
- **`test_watchdog_drift_detection_and_auto_recovery`**:
  - Performs mutations, commits them (generating commit $C_1$), manually tampers with `crdt_instance` state outside of the ledger/DAG, verifies `detect_drift()` is True, calls `auto_recover()`, and asserts that the state is successfully rolled back to $C_1$.
- **`test_ipc_socket_command_dispatch`**:
  - Boots `ClewIPCServer` in an async loop task, connects via `ClewIPCClient`, sends `HEALTH_CHECK` and `COMMIT` commands, and verifies the structured JSON responses.
- **`test_ipc_state_inspection`**:
  - Queries `INSPECT_STATE` over the client and asserts that it matches the active `GraphCRDT` serialization.

---

## Verification Plan

### Automated Tests
- Run the new test module:
  `python -m unittest tests/test_watchdog_ipc.py`
- Run full test discovery to ensure no regressions:
  `python -m unittest discover tests`

### Manual Verification
- Verify socket binding behaviors on Windows platform.
