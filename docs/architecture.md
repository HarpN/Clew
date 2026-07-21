# 📸 System Architecture

Clew bridges two distinct operational environments using a unified, persistent database backend:

```
                          ┌─────────────────────────────────────────┐
                          │    Desktop Command Center (Streamlit)   │
                          │      http://localhost:8502 (Docker)   │
                          │     http://localhost:8501 (Native)    │
                          └────────────────────┬────────────────────┘
                                               │
                                               ▼
┌──────────────────────────┐      ┌──────────────────────────┐      ┌──────────────────────────┐
│     Mobile Web Hub       │      │   Database Layer (V1/V2) │      │   WebRTC Voice Agent     │
│   FastAPI (Port 8000)    │ ────►│ SQLite WAL / PostgreSQL  │◄──── │   LiveKit Voice Node     │
│   Day-at-a-Glance View   │      │   + pgvector Embeddings  │      │  Sub-500ms Audio Stream  │
└──────────────────────────┘      └──────────────────────────┘      └──────────────────────────┘
                                               ▲
                                               │
                          ┌────────────────────┴────────────────────┐
                          │    Telemetry & Optimizer Cron Engine    │
                          │        Nightly Friction Analytics       │
                          └─────────────────────────────────────────┘
```

---

## 🏗️ Technical Stack & Architecture

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Desktop UI** | Streamlit | Visual command center & system governance dashboard |
| **Mobile UI & API** | FastAPI + React (JSX) / HTML5 | Mobile web client, Day-at-a-Glance hub & REST API |
| **Voice Pipeline** | LiveKit Agents + OpenAI + Silero VAD | Real-time WebRTC sub-500ms audio streaming node |
| **V1 Storage** | SQLite (WAL Mode) | Write-Ahead Logging for low-latency concurrent local access |
| **V2 Storage** | PostgreSQL + `pgvector` | Scalable multi-node cluster with 1536d vector memory embeddings |
| **Deployment** | Docker & Kubernetes (Helm) | Containerization with strict Pod Affinity rules |

---

## 📁 Database Dual Backend (`database.py`)

Clew seamlessly supports both SQLite (WAL mode) for lightweight V1 deployment and PostgreSQL (`pgvector`) for scaled V2 deployment:
- **DialectManager**: Abstraction layer for SQL syntax variations (`?` vs `%s`, `AUTOINCREMENT` vs `SERIAL`).
- **Connection Pooling**: `psycopg2.pool.ThreadedConnectionPool` for concurrent serverless or multi-pod API calls.
- **HNSW Vector Indices**: High-performance semantic similarity lookups across 1536-dimensional OpenAI embeddings stored in `behavioral_scenarios` and `ai_adaptations`.

---

## ⚡ 3-Tier Compute Architecture & Execution Topology

Clew compute and memory operations follow a 3-tiered execution topology:

| Tier | Environment & Provider | Model / Specs | Target Latency / Role |
| :--- | :--- | :--- | :--- |
| **Tier 1: Local Brain Stem** | Local GPU + System RAM | Qwen 2.5 7B / Llama 3.2 3B | **Sub-15ms** intent routing, graph memory queries (Neo4j/Memgraph), Pydantic validation |
| **Tier 2: Cloud Warm** | Together AI Serverless APIs | Llama 3.3 70B, Qwen 2.5 Coder 32B, DeepSeek V3 | **Sub-second** real-time complex reasoning, code generation, zero idle compute cost |
| **Tier 3A: Cloud Cold (Async Batch)** | Together AI Batch API | DeepSeek V3 / Llama 3.3 70B | Nightly memory graph re-indexing, prompt distillation at **50% discount** |
| **Tier 3B: Cloud Cold (Sandboxed)** | Modal Serverless Containers | gVisor Sandbox Container | Scale-to-zero, gVisor-sandboxed secure code execution |

---

## 💓 Heartbeat Daemon & Adaptive Sync Cadence

### Heartbeat Mechanism (`heartbeat_daemon.py`)
- **Payload Footprint**: Compact 64 to 128 bytes containing `node_id`, `sequence_nonce`, `hlc_timestamp` (Hybrid Logical Clock), and `status_flags`.
- **Ping Frequency**: 5-second interval via Hivemind over gRPC or UDP.
- **Failover Threshold**: Missing 3 consecutive heartbeats (15 seconds total) automatically triggers promotion to Cloud Warm Standby (Tier 2).

### Adaptive Sync Cadence (Duty-Cycling)
- **Active Session (IDE / Terminal in use)**: 5 - 15 second micro-batch syncing.
- **Idle / Background (System idle 10+ min)**: 15 - 30 minute duty-cycling interval.
- **Pre-Sleep / Graceful Shutdown**: Triggers an immediate full pre-sleep flush and transitions into a low-power 60-second ping state.

---

## 🛡️ Hivemind Edge Proxy & Bit-Validation Protocol (`hivemind_proxy.py`)

Hivemind is a microsecond-tier Rust edge proxy sitting in front of Clew's cognitive core.
- **128-Byte Binary Frame Layout**: `[0x00-0x03]` magic `"HIVE"`, `[0x04]` version `0x01`, `[0x05]` msg_type (Delta/Heartbeat/Sync), `[0x06-0x07]` flags, `[0x08-0x0F]` monotonic sequence nonce, `[0x10-0x17]` HLC timestamp, `[0x18-0x1B]` payload length (strict **16MB ceiling**), `[0x1C-0x1F]` SIMD CRC32C header checksum, `[0x20-0x5F]` Ed25519 signature, `[0x60-0x7F]` BLAKE3 payload digest.
- **Bit-Validation Pipeline**: Instant rejection of corrupt magic bytes, CRC32C header mismatch, payload length overflow (> 16MB), out-of-order replayed nonces, or BLAKE3 payload digest discrepancies.

---

## 📜 Append-Only Event Ledger & Graph CRDT Engine (`ledger.py`, `crdt_engine.py`)

- **Append-Only Event Ledger (`ledger.py`)**: Stores `ClewLedgerEvent` updates ordered by Hybrid Logical Clocks `(physical_time, logical_counter, node_id)`. Links each event digest via BLAKE3 hash chaining for tamper-evident history auditing.
- **Graph CRDT Engine (`crdt_engine.py`)**:
  - **Add-Wins OR-Sets**: Manages graph node & edge membership. Concurrent additions and removals resolve in favor of additions.
  - **LWW Registers**: Resolves basic scalar property conflicts using highest HLC timestamp.
  - **Multi-Value Registers (MVR)**: Retains concurrent divergent semantic attribute updates across split-brain partitions until reconciled by the LLM Arbiter.



