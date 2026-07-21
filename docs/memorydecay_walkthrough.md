# Memory Decay & UI Safety Walkthrough

All memory systems and safety optimizations have been successfully implemented, tested, and validated.

## Changes Made

### 1. Database Temporal Decay & Migration
- **Files Modified**: [database.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/database.py)
- **Modifications**:
  - Injected dynamic cache invalidation on database restart (`init_db()` deletes `cerebellum_cache.json` if it exists).
  - Setup `ai_adaptations` table schema with `expires_at TIMESTAMP` (and defaults to standard values).
  - Added a dynamic database migration inside `init_db()` which uses `ALTER TABLE` to inject the `expires_at` column if it is missing from an existing database.
  - Refactored `get_behavioral_adaptations()` to automatically exclude expired rules (`expires_at < CURRENT_TIMESTAMP`).

### 2. Hippocampus Memory Decay TTL
- **Files Modified**: [neuromorphic_subsystems.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/neuromorphic_subsystems.py)
- **Modifications**:
  - Distilled rules consolidated via Hippocampus experience replay now receive a dynamic `expires_at` value set to exactly 7 days from creation.

### 3. Nightly Expired Rules Pruning
- **Files Modified**: [cron/optimize.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/cron/optimize.py)
- **Modifications**:
  - Implemented `prune_expired_rules()` which sweeps and deletes expired unlocked adaptations (`is_locked = 0`).
  - Added `prune_expired_rules()` execution inside the nightly optimization main script.

### 4. GPU VRAM Thread Guard
- **Files Modified**: [router.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/router.py)
- **Modifications**:
  - Updated default `OLLAMA_OPTIONS` to include `"num_thread": 4` constraint to avoid system CPU and CUDA resource starvation.

### 5. Human-In-The-Loop UI Interceptor
- **Files Modified**: [ui/app.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ui/app.py)
- **Modifications**:
  - Added `execute_tool_call(prompt_to_run)` helper to process approved mutations.
  - Integrated safety check in active chat column: intercepts commands containing high-impact actions (`delete all tasks`, `drop table`, `alter adaptation`).
  - Shows warning panel with confirmation controls: committing runs command via `execute_tool_call()`; aborting cancels.

---

## Verification & Testing

We verified the changes by executing the unit tests with Python's unittest discover tool.

### Added Unit Tests
We added two new integration test cases to `tests/test_hippocampus.py`:
1. `test_06_prune_expired_rules`: Asserts that `prune_expired_rules()` sweeps out expired unlocked adaptations while keeping future and locked adaptations intact in the database.
2. `test_07_temporal_decay_filter`: Asserts that `get_behavioral_adaptations()` automatically filters out expired adaptations from client queries even if they haven't been actively swept by the optimizer yet.

### Validation Results
All 48 unit tests executed and passed successfully.
```bash
python -m unittest discover -s tests
...
Ran 48 tests in 20.405s
OK
```
