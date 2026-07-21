# Clew V5: Strategic Implementation Plan

This implementation plan covers the design and execution details for the three strategic horizons of Clew V5.

## User Review Required

> [!NOTE]
> All changes will be deployed to the `v2` branch. Automated tests are configured to run locally.

> [!WARNING]
> We will add the `VISION` tier to `router.py` and register the `pgvector` extension if operating in PostgreSQL mode, with a clean SQLite fallback. No database schema breaking changes are introduced.

## Proposed Changes

---

### Component 1: Horizon 1 - Limbic Momentum (Vector-Smooth Transitions)

#### [MODIFY] [personality_quadrant.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/personality_quadrant.py)
- Add rolling coordinate tracking to `__init__`: `self.current_coords = {"x": -0.5, "y": -0.5}`.
- Update signature of `resolve_limbic_tone(..., alpha: float = 0.25)`.
- Smooth transitions to target coordinates:
  - If `manual_override_key` is set or reason is `"Amygdala Stress Emergency Shunt"`, set `effective_alpha = 1.0`.
  - Otherwise, use `effective_alpha = alpha`.
  - Calculate `x_new` and `y_new` via EMA.
  - Update `self.current_coords` and round coordinates to 3 decimal places in the returned payload.
- Dynamically interpolate `temperature` based on distance to the 4 quadrant centroids (Inverse Distance Weighting).

#### [MODIFY] [brain_orchestrator.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/brain_orchestrator.py)
- Ensure the orchestrator's `PersonalityQuadrant` instance persists active coordinates across thoughts.
- Pass resolved coordinates to downstream handlers.

#### [MODIFY] [tests/test_personality_quadrant.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_personality_quadrant.py)
- Add unit test `test_limbic_momentum_ema` to assert that consecutive turns smoothly approach target coordinates without instantaneous snapping when `alpha < 1.0`.

---

### Component 2: Horizon 2 - WebRTC LiveKit Voice Tone Modulation

#### [MODIFY] [agent/agent.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/agent/agent.py)
- Import `PersonalityQuadrant` to evaluate incoming speech prompts on the LiveKit worker.
- Replace deprecated `JobProcess.run(...)` call with `cli.run_app(...)` per project guidelines.
- Add helper method `resolve_voice_synthesis_options(coords: dict) -> dict` returning:
  - `speed` (WPM / 165.0) and `temperature` (interpolated dynamic temperature).
- Under `user_speech_committed`, run the prompt against the Limbic intercept, log acoustic options, and dynamically update the TTS & LLM configuration via `assistant.update_options(tts=..., llm=...)`.
- Wrap TTS `synthesize` and `stream` methods to strip inter-clause commas when $y < -0.3$ (Punctuation Damping).

#### [NEW] [tests/test_voice_modulation.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_voice_modulation.py)
- Test coordinate-to-acoustic parameter mapping logic for all 4 profiles and extreme stress shunts.

---

### Component 3: Horizon 3 - Multi-Modal Visual Ingestion (pgvector Expansion)

#### [MODIFY] [database.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/database.py)
- Update `init_db()` to register the PostgreSQL `vector` extension if operating in Postgres mode.
- Create `visual_memories` table:
  - Supports SQLite nullable fallback for the `embedding` column.
- Implement database helpers:
  - `store_visual_memory(...)`
  - `query_visual_memories_by_vector(...)` (PostgreSQL `pgvector` <=> cosine distance query with SQLite math fallback in Python).

#### [MODIFY] [router.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/router.py)
- Add `ModelTier.VISION` representing visual inputs.
- Add `process_image_input(image_bytes_or_path, prompt) -> str` querying local vision model `qwen2.5-vl`.

#### [MODIFY] [ui/app.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ui/app.py)
- Add `st.file_uploader` for image uploads.
- Route attachments through vision processing, save visual memory, and prepend context to the Stage 2 thought cycle.

#### [NEW] [tests/test_multimodal.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_multimodal.py)
- Add tests for image summary extraction, visual memory storage/retrieval, and SQLite vector cosine distance fallback verification.

---

### Component 4: Late-Night Testing Fixes

#### [MODIFY] [tests/test_cognitive_brain.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_cognitive_brain.py)
- Mock the system datetime in `setUp` and `tearDown` to ensure tests run successfully at any time of day/night.

## Verification Plan

### Automated Tests
- Run `python -m unittest discover tests` to ensure all tests pass with 100% success.

### Manual Verification
- Launch Streamlit interface via `streamlit run ui/app.py` and verify image attachment processing, coordinate updates on the Limbic Compass, and database entry persistence.
