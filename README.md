# ⚡ Clew: Personal AI Assistant

> **A decoupled, context-aware AI assistant for personal logistics, fluid task management, and autonomous behavioral adaptation.**

---

## 📸 System Architecture & Overview

Clew bridges two distinct operational environments using a unified, persistent database backend:

```
                          ┌─────────────────────────────────────────┐
                          │    Desktop Command Center (Streamlit)   │
                          │          http://localhost:8501          │
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

## 🌟 Key Capabilities

### 1. Dynamic Context Engine
Rather than relying on rigid calendar alarms, Clew evaluates your fluid **Working State** against real-time variables:
- **Time of Day & Energy Level**: Matches tasks (`low`, `medium`, `high` energy) to your cognitive bandwidth.
- **Priority Pacing**: Categorizes tasks by priority (`P1`, `P2`, `P3`) and tags context (`#voice`, `#office`, `#research`).

### 2. Dual Operational Interfaces
- **Desktop Command Center (`ui/app.py`)**: Visual dashboard built in Streamlit. Split-screen layout displaying the active working state, focus blocks, proactive logistics, calendar events, unified chat timeline, and friction analytics.
- **Mobile Voice & Web Hub (`mobile/` & `mobile_server.py`)**: Responsive mobile PWA hub powered by FastAPI. Features a "Day-at-a-Glance" task view, single-tap status mutations (`Complete`, `Start Focus`, `Defer`), and a floating WebRTC microphone activator.

### 3. Sub-500ms Hands-Free Voice Node (`agent/agent.py`)
- Built on the **LiveKit Agents** WebRTC framework.
- Uses OpenAI LLM, Speech-to-Text (STT), Text-to-Speech (TTS), and Silero Voice Activity Detection (VAD).
- Non-blocking database execution via `asyncio.to_thread()`.
- AI tool context (`@ai_callable`) allowing Clew to query and mutate tasks while streaming audio.

### 4. Autonomous Behavioral Memory & Friction Analytics
- Ephemeral background jobs evaluate execution telemetry (e.g., tasks deferred after 9:00 PM).
- Automatically extracts semantic rules and populates `ai_adaptations`.
- Administrative **System Governance Panel** allowing users to lock specific AI strategies to shield them from cron modifications or revert AI adaptation history with one click.

---

## 🏗️ Technical Stack & Architecture

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Desktop UI** | Streamlit | Visual command center & system governance dashboard |
| **Mobile UI & API** | FastAPI + React (JSX) / Vanilla HTML5 | Mobile web client, Day-at-a-Glance hub & REST API |
| **Voice Pipeline** | LiveKit Agents + OpenAI + Silero VAD | Real-time WebRTC sub-500ms audio streaming node |
| **V1 Storage** | SQLite (WAL Mode) | Write-Ahead Logging for low-latency concurrent local access |
| **V2 Storage** | PostgreSQL + `pgvector` | Scalable multi-node cluster with 1536d vector memory embeddings |
| **Deployment** | Docker & Kubernetes (Helm) | Containerization with strict Pod Affinity rules |

---

## 📁 Repository Structure

```
Clew/
├── database.py                   # Central DB persistence layer (SQLite WAL & Postgres pool)
├── mobile_server.py              # FastAPI REST server for Mobile Web Hub
├── agent.py                      # Root entrypoint bootstrap for Voice Agent
├── agent/
│   └── agent.py                  # LiveKit WebRTC Real-Time Voice Agent Node
├── ui/
│   └── app.py                    # Streamlit Desktop Command Center UI
├── mobile/
│   ├── mobile_app.jsx            # Mobile React component (Day-at-a-Glance UI)
│   └── index.html                # Standalone responsive mobile web client
├── migrations/
│   └── v2_postgres_migration.sql # PostgreSQL schema & pgvector HNSW index migration
├── helm/
│   ├── Chart.yaml                # Helm chart metadata
│   ├── values.yaml               # Config values & LiveKit/Postgres credentials
│   └── templates/
│       ├── secrets.yaml          # K8s Opaque Secrets manifest
│       ├── deployments.yaml      # UI, Voice Agent & Mobile deployment specs
│       ├── cron-and-storage.yaml # PersistentVolumeClaim & Optimizer CronJob
│       └── postgres-deployment.yaml # PostgreSQL StatefulSet with pgvector
├── Dockerfile                    # Multi-service Python container definition
├── AI_Assistant_Architecture_Review.md # Architecture blueprint & roadmap
└── README.md                     # System documentation
```

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10+
- `pip` package manager
- LiveKit & OpenAI API Keys (for voice node)

### 1. Environment Setup
Clone the repository and install dependencies:

```bash
git clone https://github.com/HarpN/Clew.git
cd Clew

# Install core dependencies
pip install streamlit fastapi uvicorn livekit-agents livekit-plugins-openai livekit-plugins-silero python-dotenv psycopg2-binary
```

Configure your environment variables in `.env`:

```env
OPENAI_API_KEY=sk-...
LIVEKIT_URL=wss://your-livekit-instance.livekit.cloud
LIVEKIT_API_KEY=dev_key
LIVEKIT_API_SECRET=dev_secret
```

### 2. Running Locally

#### Desktop Command Center (Streamlit)
```bash
streamlit run ui/app.py
```
*Access at `http://localhost:8501`*

#### Mobile Web Hub (FastAPI)
```bash
python mobile_server.py
```
*Access at `http://localhost:8000`*

#### LiveKit Voice Agent Node
```bash
python agent.py start
```

---

## 🐳 Containerization & Kubernetes Deployment (Helm)

### 1. Building Docker Image
```bash
docker build -t clew-assistant:latest .
```

### 2. Deploying via Helm

#### V1 Mode (SQLite WAL Mode with Strict Pod Affinity)
In V1 mode, all microservices share a single NVMe PersistentVolume (`/data`). The Helm charts enforce **Strict Pod Affinity** on `kubernetes.io/hostname` and utilize `volume-mount-guard` init containers to protect shared memory mapping (`mmap`).

```bash
helm install clew ./helm
```

#### V2 Mode (PostgreSQL + pgvector)
To scale pods across multiple Kubernetes physical worker nodes, enable PostgreSQL parameters in `helm/values.yaml` or set environment variables:

```yaml
POSTGRES_HOST: "clew-postgresql"
POSTGRES_DB: "clew_v2"
POSTGRES_USER: "clew_admin"
POSTGRES_PASSWORD: "clew_secure_pass"
```

---

## 🛢️ V2 PostgreSQL Migration & pgvector

Clew V2 refactors database.py using a dynamic DialectManager and psycopg2 connection pooling (ThreadedConnectionPool with RealDictCursor).

### Running the V2 Database Migration
Execute the migration script against your PostgreSQL instance to enable `pgvector` and HNSW vector similarity search:

```bash
psql -h localhost -U clew_admin -d clew_v2 -f migrations/v2_postgres_migration.sql
```

This enables hybrid relational-semantic AI memory:
- **`behavioral_scenarios`**: `embedding vector(1536)`
- **`ai_adaptations`**: `strategy_embedding vector(1536)`
- **HNSW Cosine Index**: `idx_behavioral_scenarios_embedding`

---

## 🛡️ License

Private & Open Development for personal assistant logistics.
