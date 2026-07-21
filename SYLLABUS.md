# Architecting Clew LifeOS: Deep Dive into Distributed AI Coordination & Neuromorphic Brain Engines

Welcome to the interactive training syllabus for **Clew LifeOS**. This course walks through the core architectural pillars that drive Clew's low-latency, decentralized, and adaptive cognitive architecture.

---

## 🎯 Learning Objectives

By completing these lessons, you will master the following engineering concepts implemented in Clew:
1. **Binary Framing & Serialization Integrity**: Understand fixed binary headers, CRC32C, and BLAKE3 cryptopackage designs.
2. **Execution Topology & Sync Cadences**: Learn how Clew routes work through a 3-tier compute model, keeps heartbeats alive, and duty-cycles connection synching.
3. **Decentralized State Consistency**: Master Hybrid Logical Clock (HLC) total ordering, Append-Only Event Ledgers, and Conflict-Free Replicated Data Types (CRDTs).
4. **Cognitive State Orchestration**: Understand the Limbic Personality Quadrant and dynamic inverse-distance weighted temperature interpolation.
5. **IPC & Operational Resilience**: Dive into cross-platform Inter-Process Communication socket bounds and active watchdog recovery.

---

## 📚 Table of Contents & Lessons

Explore the modules sequentially:

### 🧩 Module 1: Binary Frame Layout & Signature Integrity
- **Topic**: Hivemind binary communication protocol.
- **Link**: [Lesson 1: Binary Frame Layout & Cryptographic Integrity](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/.lessons/lesson_1_protocol_frames.md)
- **Key Files**:
  - [protocol.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/protocol.py)

### ⚡ Module 2: 3-Tier Compute & Heartbeat Orchestration
- **Topic**: Active/Idle sync transitions, heartbeat failover, and local-to-cloud promotion.
- **Link**: [Lesson 2: Compute Tiering & Heartbeat Orchestration](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/.lessons/lesson_2_compute_tiering_heartbeat.md)
- **Key Files**:
  - [heartbeat_daemon.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/heartbeat_daemon.py)
  - [protocol.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/protocol.py)

### 📜 Module 3: Event Ledgering & Graph CRDTs
- **Topic**: Tamper-evident ledger chaining, Add-Wins OR-Sets, LWW-Registers, and Multi-Value Registers (MVR) for split-brain sync.
- **Link**: [Lesson 3: State Chaining & Graph CRDTs](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/.lessons/lesson_3_crdt_ledger.md)
- **Key Files**:
  - [ledger.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ledger.py)
  - [crdt_engine.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/crdt_engine.py)

### 🎭 Module 4: Limbic Personality Quadrant
- **Topic**: Direct linguistic prompt intercepts, friction mapping, and dynamic temperature interpolation across 2D mood space coordinates.
- **Link**: [Lesson 4: Limbic Personality Quadrants](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/.lessons/lesson_4_personality_quadrant.md)
- **Key Files**:
  - [personality_quadrant.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/personality_quadrant.py)

### 🛡️ Module 5: Socket IPC & watchdog recovery
- **Topic**: Unix domain socket fallbacks for cross-platform compatibility and system watchdog integrity loop.
- **Link**: [Lesson 5: Cross-Platform IPC & Watchdog Integrity](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/.lessons/lesson_5_ipc_watchdog.md)
- **Key Files**:
  - [ipc_socket.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ipc_socket.py)
  - [watchdog.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/watchdog.py)
