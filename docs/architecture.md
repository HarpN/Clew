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
