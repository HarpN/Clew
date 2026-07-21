# Neuromorphic Memory & UI Safety Optimizations Implementation Plan

This plan details the implementation of four key system patches across the persistence layer, background optimizations, model routing, and command UI.

## User Review Required

> [!IMPORTANT]
> - The database schema for `ai_adaptations` is updated to include an `expires_at` timestamp. To handle existing databases, the `init_db()` migration step dynamically executes an `ALTER TABLE` to inject this column if it does not already exist.
> - High-impact commands entered in the chat UI (`delete all tasks`, `drop table`, `alter adaptation`) will trigger a warning and require manual confirmation before they are processed.

## Proposed Changes

### Persistence Layer

#### [MODIFY] [database.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/database.py)
- Update `init_db()` to:
  - Check for and dynamically invalidate the `cerebellum_cache.json` file.
  - Perform a dynamic migration on `ai_adaptations` to add the `expires_at` column if it is missing.
- Update `get_behavioral_adaptations()` to filter out expired adaptations automatically by comparing `expires_at` to `CURRENT_TIMESTAMP`.

### Neuromorphic Subsystems & Optimization

#### [MODIFY] [neuromorphic_subsystems.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/neuromorphic_subsystems.py)
- Update `consolidate_experience_loop` in the `Hippocampus` class:
  - Add a 7-day TTL expiration to new distilled rules during experience replay rule consolidation.

#### [MODIFY] [cron/optimize.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/cron/optimize.py)
- Implement `prune_expired_rules()` to clean up expired unlocked database rules during the nightly optimization job.

### Model Routing & VRAM Bounds

#### [MODIFY] [router.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/router.py)
- Update the default `OLLAMA_OPTIONS` configuration to append `"num_thread": 4` and document VRAM bounding constraints.

### Desktop Command Center UI

#### [MODIFY] [ui/app.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ui/app.py)
- Integrate a Human-in-the-Loop (HITL) panel:
  - Detect high-impact prompts before processing.
  - Display confirmation/abort prompt panel for pending high-impact mutations.
  - Define `execute_tool_call` to handle confirmed commands.

---

## Verification Plan

### Automated Tests
We will run:
- `python -m unittest discover -s tests` to ensure existing and updated tests pass cleanly.
- We will add new unit tests in `tests/test_hippocampus.py` or `tests/test_cerebellum.py` if needed to cover rule expiration and invalidation behavior.

### Manual Verification
- Verify that restarting the database triggers Cerebellum cache deletion.
- Verify that entering "delete all tasks" in the Streamlit UI displays the HITL Interceptor.
