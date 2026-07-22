# ⚡ Clew: Distributed Neuromorphic Personal AI Assistant & LifeOS

> **A decoupled, context-aware AI assistant built on a split-brain neuromorphic cognitive architecture, 3-tier compute topology, binary edge framing, append-only event ledgers, and real-time WebRTC voice modulation.**

---

## 📸 System Architecture & Overview

Clew unifies real-time voice streaming, desktop command control, mobile web interactions, and background cognitive processing over a resilient multi-tier infrastructure:

```
                                  ┌─────────────────────────────────────────┐
                                  │    Desktop Command Center (Streamlit)   │
                                  │       http://localhost:8501 (Native)    │
                                  │       http://localhost:8502 (Docker)    │
                                  └────────────────────┬────────────────────┘
                                                       │
                                                       ▼
┌──────────────────────────┐      ┌─────────────────────────────────────────┐      ┌──────────────────────────┐
│     Mobile Web Hub       │      │   Split-Brain Cognitive Architecture    │      │   WebRTC Voice Agent     │
│   FastAPI (Port 8000)    │ ────►│   - Frontal Lobe & Broca Translator     │◄──── │   LiveKit Voice Node     │
│   Day-at-a-Glance View   │      │   - Amygdala, Cerebellum, Hippocampus   │      │  Sub-500ms Dynamic TTS   │
└──────────────────────────┘      │   - Limbic Quadrant & Constraint Guard  │      └──────────────────────────┘
                                  └────────────────────┬────────────────────┘
                                                       │
                                                       ▼
┌──────────────────────────┐      ┌─────────────────────────────────────────┐      ┌──────────────────────────┐
│ Hivemind Edge Proxy      │      │ Decentralized State & Ledgering         │      │ Database Dual Backend    │
│ 128-Byte Binary Frames   │ ────►│ Append-Only Ledger & Graph CRDTs       │ ────►│ SQLite (WAL Mode) V1     │
│ microsecond Rust Proxy   │      │ BLAKE3 Merkle DAG & Split-Brain Arbiter │      │ PostgreSQL + pgvector V2 │
└──────────────────────────┘      └─────────────────────────────────────────┘      └──────────────────────────┘
                                                       ▲
                                                       │
                                  ┌────────────────────┴────────────────────┐
                                  │   Resilience & Telemetry Layer          │
                                  │ - Heartbeat Daemon & Duty-Cycling       │
                                  │ - Cross-Platform IPC Socket & Watchdog  │
                                  └─────────────────────────────────────────┘
```

---

## 🌟 Core Capabilities & Neuromorphic Architecture

### 1. Split-Brain Cognitive Architecture (`brain_orchestrator.py`, `broca_translator.py`)
- **0ms Latency Fast-Path**: Bypasses LLM generation for high-frequency static greetings and status queries (`hello`, `status`, `wake up`).
- **Broca's Area (Semantic Translator)**: Synthesizes responses based on grounded database execution, maintaining strict control flow and performing mathematical semantic divergence checks.
- **Deterministic Pre-Flight Safety Veto (Option A)** (`constraint_guard.py`): Enforces system rules and financial/energy constraints *before* streaming token sockets open, preventing "stutter" UX failures.

### 2. Neuromorphic Subsystems (`neuromorphic_subsystems.py`, `personality_quadrant.py`)
- **Amygdala Friction Engine**: Computes real-time user friction ($F_{user}$) from keystroke dynamics and message cadence. Automatically shunts system responses to **Terse Mode** when stress thresholds ($0.75$) are breached.
- **Cerebellum Hot-Path Caching**: Executes habitual tasks directly from muscle memory, bypassing the frontal lobe for sub-millisecond execution.
- **Hippocampus Memory Consolidator**: Runs background memory decay, consolidation, and semantic graph indexing.
- **2D Limbic Personality Quadrant**: Dynamically maps agent mood across Empathy vs Rigor ($x$) and Energy vs Calm ($y$). Modulates LLM temperature via inverse-distance weighting and adapts WebRTC Voice TTS speech rate and pitch factor in real time.

### 3. 3-Tier Compute Topology & Heartbeat Daemon (`heartbeat_daemon.py`)
- **Tier 1 (Local Brain Stem)**: Sub-15ms intent classification, Pydantic validation, and graph queries on local compute/Ollama.
- **Tier 2 (Cloud Warm Standby)**: Sub-second complex reasoning on Together AI serverless endpoints.
- **Tier 3 (Cloud Cold Async & Sandboxed)**: 50% discounted batch distillation and sandboxed gVisor container execution on Modal.
- **Heartbeat Daemon**: Transmits 64–128 byte payloads containing Hybrid Logical Clock (HLC) timestamps and node nonces every 5s. Auto-promotes to Tier 2 on 15s timeout and duty-cycles sync intervals (5s active vs 30m idle).

### 4. Hivemind Binary Edge Proxy & Frame Validation (`hivemind_proxy.py`, `src/hivemind.rs`)
- High-throughput Rust proxy utilizing a **128-Byte Binary Frame Layout**.
- Includes Ed25519 signature verification, BLAKE3 payload digests, SIMD CRC32C header validation, monotonic sequence nonces, and a strict 16MB payload ceiling.

### 5. Append-Only Event Ledger & Graph CRDT Engine (`ledger.py`, `crdt_engine.py`, `merkle_dag.py`)
- **Append-Only Event Ledger**: Tamper-evident transaction logging ordered by HLC timestamps `(physical_time, logical_counter, node_id)` with BLAKE3 hash chaining.
- **Graph CRDT Engine**: Resolves state conflicts using Add-Wins OR-Sets for membership, LWW Registers for scalar properties, and Multi-Value Registers (MVR) for concurrent semantic updates.
- **BLAKE3 Merkle DAG & Rollback**: Content-addressable versioning tree supporting zero-data-loss atomic state rollbacks.
- **Split-Brain Recovery Arbiter**: LLM-assisted semantic arbiter (`reconciliation.py`) that reconciles divergent MVR branches after network partition heal.

### 6. Socket IPC & Active Watchdog Recovery (`ipc_socket.py`, `watchdog.py`)
- **Cross-Platform Socket IPC**: Unix Domain Socket transport with seamless TCP localhost (`127.0.0.1`) fallback for Windows compatibility.
- **Integrity Watchdog Daemon**: Actively checks process health, monitors file integrity hashes, and triggers auto-recovery routines upon subsystem failure.

### 7. Sub-500ms WebRTC Voice Agent (`agent/agent.py`)
- LiveKit Agents integration with OpenAI STT/TTS and Silero VAD.
- Modulates TTS speed and pitch dynamically in response to Limbic quadrant coordinate shifts.

### 8. Interactive Training Syllabus & Lessons (`SYLLABUS.md`, `.lessons/`)
- Built-in interactive code reviews and lessons covering binary frame validation, compute tiering, CRDT ledgers, limbic quadrants, and IPC watchdogs.

---

## 🏗️ Technical Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Desktop UI** | Streamlit | Visual command center & limbic governance dashboard |
| **Mobile UI & API** | FastAPI + React (JSX) / Vanilla HTML5 | Mobile web client, Day-at-a-Glance hub & REST API |
| **Voice Pipeline** | LiveKit Agents + OpenAI + Silero VAD | Sub-500ms WebRTC voice agent with acoustic modulation |
| **Cognitive Orchestrator** | Python 3.11 + Pydantic v2 + Jinja2 | Neuromorphic multi-quadrant brain model & constraint veto |
| **Edge Proxy** | Rust (Hivemind) + Python `hivemind_proxy.py` | 128-byte binary frame parser & bit-level validation |
| **State & Ledgers** | Hybrid Logical Clocks + BLAKE3 + CRDTs | Append-only event ledgering, Add-Wins OR-Sets, Merkle DAG |
| **Resilience & IPC** | Unix Sockets / TCP 127.0.0.1 Fallback | Cross-platform IPC & active integrity watchdog daemon |
| **V1 Storage** | SQLite (WAL Mode) | Write-Ahead Logging for ultra-low latency local persistence |
| **V2 Storage** | PostgreSQL + `pgvector` | Scalable multi-node cluster with 1536d HNSW vector memory |
| **Deployment** | Docker & Kubernetes (Helm) | Multi-container orchestration & Helm chart specifications |

---

## 📁 Repository Structure

```
Clew/
├── brain_orchestrator.py         # Cognitive multi-quadrant brain orchestrator
├── brain.py                      # Cognitive brain entry point & thought cycle driver
├── broca_translator.py           # Broca's Area semantic translation & stream compiler
├── constraint_guard.py           # Pre-flight Deterministic Safety Veto & Overseer guard
├── neuromorphic_subsystems.py    # Amygdala stress engine, Cerebellum hot-path, Hippocampus
├── personality_quadrant.py       # 2D Limbic Personality Quadrant & mood interpolation
├── personality_validator.py      # Personality profile schema validation
├── protocol.py                   # Protocol definitions, Intent commands & frame types
├── router.py                     # Multi-model router & prompt template engine
├── heartbeat_daemon.py           # 3-Tier compute tiering & heartbeat daemon
├── hivemind_proxy.py             # Hivemind edge proxy 128-byte binary frame parser
├── src/
│   └── hivemind.rs               # Rust microsecond edge proxy implementation
├── ledger.py                     # Append-Only Event Ledger with BLAKE3 hash chaining
├── crdt_engine.py                # Graph CRDT Engine (Add-Wins OR-Sets, LWW, MVR)
├── merkle_dag.py                 # Content-addressable BLAKE3 Merkle DAG engine
├── version_engine.py             # Atomic version control & state rollback engine
├── reconciliation.py             # LLM Semantic Arbiter for split-brain recovery
├── ipc_socket.py                 # Cross-platform socket IPC (Unix Domain + TCP fallback)
├── watchdog.py                   # Active process & integrity monitoring daemon
├── database.py                   # Dual DB layer (SQLite WAL mode & Postgres pgvector pool)
├── graph_memory.py               # Semantic graph memory node & edge query layer
├── distillery.py                 # Prompt & context distillation engine
├── event_store.py                # Telemetry event store recorder
├── memory_service.py             # Memory service facade
├── mobile_server.py              # FastAPI REST server for Mobile Web Hub
├── agent.py                      # Root launcher for LiveKit Voice Agent
├── agent/
│   └── agent.py                  # LiveKit WebRTC Real-Time Voice Agent Node
├── ui/
│   └── app.py                    # Streamlit Desktop Command Center UI
├── mobile/
│   ├── mobile_app.jsx            # Mobile React component
│   └── index.html                # Standalone responsive mobile web client
├── SYLLABUS.md                   # Interactive LifeOS training course syllabus
├── .lessons/                     # Interactive architectural lesson modules
├── docs/                         # Implementation plans and architectural walkthroughs
├── tests/                        # Comprehensive pytest test suite (19 test files)
├── migrations/
│   └── v2_postgres_migration.sql # PostgreSQL schema & pgvector HNSW index migration
├── helm/                         # Kubernetes Helm deployment charts
├── Dockerfile                    # Multi-service Python container definition
└── docker-compose.yml            # Docker Compose orchestration file
```

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10+
- `pip` package manager
- LiveKit & OpenAI API Keys (for WebRTC voice features)
- Docker & Docker Compose (optional for PostgreSQL + Ollama setup)

### 1. Installation & Environment Setup

```bash
git clone https://github.com/HarpN/Clew.git
cd Clew

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the root directory:

```env
LIVEKIT_URL=wss://your-instance.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
OPENAI_API_KEY=sk-...
```

### 2. Running System Services

#### Option A: Docker Compose (Full Stack)
Spin up PostgreSQL (`pgvector`), Ollama local model, Streamlit UI, Mobile API, and Voice Agent:

```bash
docker-compose up --build
```

#### Option B: Native Execution

1. **Desktop Command Center (Streamlit)**:
   ```bash
   streamlit run ui/app.py
   ```
   *Access dashboard at `http://localhost:8501`*

2. **Mobile Web Hub (FastAPI)**:
   ```bash
   python mobile_server.py
   ```
   *Access API / Mobile Hub at `http://localhost:8000`*

3. **LiveKit Voice Agent Node**:
   ```bash
   python agent.py dev
   ```

4. **Heartbeat & Watchdog Daemons**:
   ```bash
   python heartbeat_daemon.py
   python watchdog.py
   ```

---

## 🧪 Running Tests & Interactive Syllabus

### Running Automated Test Suite
Clew includes 19 comprehensive unit test modules covering all cognitive, ledger, CRDT, and socket subsystems:

```bash
pytest
```

To run a specific test suite:
```bash
pytest tests/test_cognitive_brain.py
pytest tests/test_ledger_crdt.py
pytest tests/test_personality_quadrant.py
pytest tests/test_watchdog_ipc.py
```

### Interactive Architectural Lessons
Dive into the engineering details using the interactive lessons:
- [SYLLABUS.md](SYLLABUS.md): Course overview and module index.
- [Lesson 1: Binary Frame Layout](.lessons/lesson_1_protocol_frames.md)
- [Lesson 2: 3-Tier Compute & Heartbeat Orchestration](.lessons/lesson_2_compute_tiering_heartbeat.md)
- [Lesson 3: Event Ledgering & Graph CRDTs](.lessons/lesson_3_crdt_ledger.md)
- [Lesson 4: Limbic Personality Quadrants](.lessons/lesson_4_personality_quadrant.md)
- [Lesson 5: Cross-Platform IPC & Watchdog Integrity](.lessons/lesson_5_ipc_watchdog.md)

---

## 🛢️ Database Backend (V1 SQLite vs V2 PostgreSQL + pgvector)

Clew seamlessly supports both SQLite (WAL mode) for zero-config local development and PostgreSQL (`pgvector`) for cluster deployments:

- **SQLite WAL Mode (V1)**: Fast concurrent local file access with automatic database fallback.
- **PostgreSQL + `pgvector` (V2)**: Enterprise deployment supporting 1536-dimensional OpenAI memory embeddings and HNSW cosine similarity indices (`migrations/v2_postgres_migration.sql`).

---

## 🛡️ License

Private & Open Development for personal assistant logistics.
