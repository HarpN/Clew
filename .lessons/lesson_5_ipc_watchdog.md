# Lesson 5: Cross-Platform IPC & Watchdog Integrity

## 🧠 Core Concept: High-Speed IPC & Active Watchdogs

In production-grade AI agent systems, components (such as a CLI tool, a Streamlit dashboard, a mobile server, and background daemons) must communicate with the core brain orchestrator quickly.

1. **Inter-Process Communication (IPC)**:
   - **Unix Domain Sockets (UDS)**: Sockets created within the filesystem. They bypass the networking stack (loopback adapters, TCP handshake), reducing overhead and communication latency.
   - **Cross-Platform Fallback**: Since Windows does not natively support POSIX Unix sockets in the same way (or standard Python versions lacks socket-level configuration support for Windows), the system must dynamically check the platform and fall back to localhost TCP connections (`127.0.0.1`) to ensure compatibility.
2. **Active State Watchdog**:
   - A background thread or loop that continuously verifies that the in-memory graph CRDT, the serialized database tables, and the cryptographic Merkle DAG remain in-sync.
   - If drift (uncommitted states) or corruption is detected, the system triggers self-healing logic (auto-rollback) to check out the last known cryptographically signed commit.

---

## 🔍 Code Breakdown

Let's examine the platform check and fallback implementation in [ipc_socket.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ipc_socket.py).

### Sockets Platform Fallback (`start_async`)

In [ipc_socket.py:L41-57](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ipc_socket.py#L41-L57), the socket server initializes based on platform capabilities:

```python
    async def start_async(self):
        """Starts the IPC server listening on either Unix Domain Socket or TCP fallback."""
        use_unix = hasattr(socket, "AF_UNIX") and sys.platform != "win32"
        if use_unix:
            # Ensure path directory exists
            dir_name = os.path.dirname(self.socket_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
            # Remove old socket file if exists
            if os.path.exists(self.socket_path):
                try:
                    os.unlink(self.socket_path)
                except OSError:
                    pass
            self.server = await asyncio.start_unix_server(self._handle_client, path=self.socket_path)
        else:
            self.server = await asyncio.start_server(self._handle_client, host=self.host, port=self.port)
```

By checking `hasattr(socket, "AF_UNIX") and sys.platform != "win32"`, the server avoids crashing on Windows startup and configures an `asyncio.start_server` fallback bound to `127.0.0.1:9876`.

---

### Drift Check & Healing Loop (`watchdog.py`)

The watchdog verifies three verification phases in [watchdog.py:L24-52](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/watchdog.py#L24-L52):
1. **Ledger Check**: Verifies that the append-only event log hash chain is unbroken.
2. **Merkle DAG Check**: Verifies that the Merkle tree commit structure is intact.
3. **Replay Validation**: Applies all events from the ledger onto a temporary, clean memory space and verifies that its computed root hash matches the active state root hash.

```python
    def verify_state_integrity(self) -> Tuple[bool, str]:
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
```

If `verify_state_integrity()` fails or if `detect_drift()` identifies uncommitted changes, `auto_recover()` triggers a commit rollback to restore operational health:

```python
    def auto_recover(self) -> Tuple[bool, str]:
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
```

---

## 🔬 Deep Dives

### Socket IPC Message Framing
Because sockets transmit stream-based TCP/UDS byte sequences rather than discrete packet boundaries, clients must frame their calls. In Clew, this is handled using **newline separation** (`\n`). `ClewIPCServer._handle_client` processes inputs line-by-line via `reader.readline()`, which detects the trailing `\n` sequence. Each line is parsed as a standalone JSON request dictionary.

---

## 📝 Interactive Quiz

### Question 1: How does Clew handle IPC socket binding on a Windows machine?
- **A)** It fails to start and outputs a fatal error.
- **B)** It falls back to standard HTTP/2 over gRPC.
- **C)** It checks the platform and initializes a TCP local server on `127.0.0.1:9876`.
- **D)** It falls back to SQLite file polling.

<details>
<summary>Reveal Answer & Explanation</summary>

**Correct Answer: C**

**Explanation**: 
If Unix Domain Sockets (`AF_UNIX`) are not supported or if the OS is Windows (`sys.platform == "win32"`), `start_async` falls back to `asyncio.start_server(..., host=self.host, port=self.port)` where `self.host` defaults to `127.0.0.1` and `port` defaults to `9876`.
</details>

### Question 2: In the State Watchdog, what does "Replay Validation" verify?
- **A)** That the database dialect supports Postgres.
- **B)** That replaying the append-only ledger on a fresh CRDT instance yields the exact same state root hash as the current running CRDT.
- **C)** That the local voice agent response time is under 500ms.
- **D)** That the user's manual override keys are loaded.

<details>
<summary>Reveal Answer & Explanation</summary>

**Correct Answer: B**

**Explanation**: 
Replay validation checks for bugs in the active memory footprint by instantiating a clean GraphCRDT, applying all ledger events sequentially, and comparing the resulting serialized state hash with the active CRDT root hash.
</details>

---

## 🛠️ Coding Exercise / Challenge

### Challenge: Adding Heartbeat Reporting to IPC
Open [ipc_socket.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ipc_socket.py). In `_dispatch_command`, add a command case `"get_watchdog_status"` that queries `self.watchdog.verify_state_integrity()` and returns the status tuple as a JSON response. Test your implementation by running:
`pytest tests/test_watchdog_ipc.py`
