# Clew V5: Strategic Roadmap Implementation Walkthrough

This document outlines the design, implementation, and successful testing of Strategic Horizons 1, 2, and 3 for the Clew V5 LifeOS on branch `v2`.

---

## 🧭 Horizon 1: Vector-Smooth Coordinate Transitions (Limbic Momentum)

Currently, Clew snapped instantly between discrete personality centroids. Horizon 1 introduces smooth physical inertia to coordinate transitions across the 2D Limbic plane.

### 1. Implementation
- **Rolling state tracking**: Initialized active coordinates state tracking: `self.current_coords = {"x": -0.5, "y": -0.5}` in `PersonalityQuadrant` ([personality_quadrant.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/personality_quadrant.py)).
- **Limbic Inertia Coefficient**: Implemented Exponential Moving Average (EMA) transitions:
  $$\mathbf{x}_t = \alpha \cdot \mathbf{x}_{\text{target}} + (1 - \alpha) \cdot \mathbf{x}_{t-1}$$
  - Default $\alpha = 0.25$.
  - When an Amygdala Stress Emergency Shunt occurs ($F_{\text{user}} \ge 0.75$) or a Manual Override is selected, $\alpha_{\text{shunt}} = 1.0$ (coordinates snap instantly).
- **Dynamic Temperature Interpolation**: Replaced hardcoded temperature values with distance-based Inverse Distance Weighting (IDW) interpolation between centroids to smoothly blend prompt temperatures based on physical compass location.

---

## 🎙️ Horizon 2: LiveKit Voice Tone & Acoustic Modulation

Horizon 2 maps visual coordinate states directly to the audio processing pipeline inside the LiveKit voice worker node.

### 1. Implementation
- **Acoustic Transform Matrix**: Implemented `resolve_voice_synthesis_options(coords)` in `agent/agent.py` ([agent.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/agent/agent.py)):
  - Speaking Rate (WPM): $WPM(y) = 165 - (y \cdot 25)$
  - Speed Ratio: $Speed(y) = WPM(y) / 165.0$
  - Pitch Shift: $Pitch(x, y) = 1.0 + (0.08 \cdot x) + (0.04 \cdot y)$
- **Dynamic TTS Updates**: On every response turn (`user_speech_committed`), evaluated user prompt against Limbic intercept and dynamically updated TTS and LLM configurations using `assistant.update_options(tts=..., llm=...)`.
- **Punctuation Damping**: Wrapped TTS `synthesize` and `stream` methods to strip inter-clause commas when $y < -0.3$ (Terse / Analyst / Critic profiles) to enforce tight, rapid token playback.
- **App Startup Modernization**: Replaced deprecated `JobProcess.run(...)` with `cli.run_app(...)` per project guidelines.

---

## 🖼️ Horizon 3: Multi-Modal Visual Ingestion (pgvector Expansion)

Horizon 3 adds visual input (receipts, architecture diagrams, screenshots) capabilities to the assistant, indexing summaries in PostgreSQL via `pgvector` with a robust SQLite math fallback.

### 1. Implementation
- **Schema & DB Helpers**: Created `visual_memories` table in `database.py` ([database.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/database.py)) registering pgvector in Postgres mode and fallback columns in SQLite.
- **Cosine Distance Math Fallback**: Wrote high-fidelity SQLite fallback calculation doing pure Python cosine distance math matching:
  $$\text{Distance}(\mathbf{u}, \mathbf{v}) = 1 - \frac{\mathbf{u} \cdot \mathbf{v}}{\Vert{}\mathbf{u}\Vert{} \Vert{}\mathbf{v}\Vert{}}$$
- **VISION Tier & Processing**: Added `ModelTier.VISION` and `process_image_input` to `router.py` ([router.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/router.py)) to process base64-encoded visual payloads.
- **UI File Uploader**: Added `st.file_uploader` to [app.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ui/app.py). Image attachments are analyzed, stored in database visual memories, and injected into the prompt context.

---

## 🧪 Validation and Testing

### 1. Unit Tests
All new capabilities are fully covered by a robust test suite:
- **Limbic Momentum**: Verified smooth sequential transitions and instant shunts in [test_personality_quadrant.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_personality_quadrant.py).
- **Voice Modulation**: Verified coordinate-to-acoustic mapping and comma-stripping callbacks in [test_voice_modulation.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_voice_modulation.py).
- **Multimodal Visual Ingestion**: Verified vision fallback behavior and math fallback cosine vector search in [test_multimodal.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_multimodal.py).
- **Fatigue Policy Fix**: Mocked system datetime in [test_cognitive_brain.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_cognitive_brain.py) to prevent late-night policy failures.

### 2. Execution Run
The test suite completed with **100% success**:

```bash
Ran 59 tests in 23.543s

OK
```
All capabilities are fully integrated on branch `v2`.
