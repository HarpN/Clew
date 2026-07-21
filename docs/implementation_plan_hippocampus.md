# Implementation Plan - Hippocampus Offline Memory Consolidator

This plan outlines the integration of the Hippocampus offline memory consolidation background task into Clew's V2 workspace. The Hippocampus clusters recent user corrections, distills them into active system strategies using local low-temperature LLM queries, and cleans up the chat history context to minimize LLM prompt bloat.

## User Review Required

> [!IMPORTANT]
> **Database Schema & SQL Mapping:** The database schema uses `content` and `timestamp` columns in the `chat_timeline` table instead of the `message` and `created_at` fields in the originally suggested SQL. We will use SQL aliases (`content AS message`, `timestamp AS created_at`) in our queries to bridge this difference without breaking downstream python code.

## Proposed Changes

### Component 1: Neuromorphic Subsystems Layer

#### [MODIFY] [neuromorphic_subsystems.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/neuromorphic_subsystems.py)
* Append the `Hippocampus` class implementing:
  * Word-frequency vectorization and TF-based cosine similarity computations.
  * Semantic correction clustering (with threshold $\ge 0.85$).
  * Corrections querying from `chat_timeline` (`speaker = 'user'`), mapping database columns `content` to `message` and `timestamp` to `created_at`.
  * Nightly consolidation loop calling the generalist LLM via `ModelRouter` to distill rules.
  * Integration with the Governance Panel rules: checking if the strategy exists and is locked (`is_locked = 1`) before modifying or writing, strictly skipping locked ones.
  * Dialect-safe insertion into `ai_adaptations` and logging of audits into `adaptation_audit_log`.
  * Context timeline compaction (deleting highly noisy timeline records).

---

### Component 2: Multi-Model Router

#### [MODIFY] [router.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/router.py)
* Update `ModelRouter.execute_completion` to accept a `tier` string parameter (e.g. `"GENERALIST"`) and optionally an `options` dict.
* If a tier is specified or if raw string completion is requested, execute a raw Ollama query using `query_ollama_chat` and return the plain-text completion directly instead of a `CommandResult` object.

---

### Component 3: Database & Telemetry

#### [MODIFY] [database.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/database.py)
* Update `get_adaptation_audit_log` to include `l.triggering_telemetry` in its SELECT statement so it can be displayed in the UI.

---

### Component 4: Nightly Cron Optimizer Task

#### [NEW] [optimize.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/cron/optimize.py)
* Create `cron/optimize.py` to instantiate `Hippocampus` and run the `consolidate_experience_loop` using the active `ModelRouter`.
* Add logic to ensure locked adaptations are ignored, and output execution statistics:
  `[HIPPOCAMPUS] Nightly memory consolidation loop finished. Consolidated N new system strategies.`

---

### Component 5: Streamlit Interface

#### [MODIFY] [app.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ui/app.py)
* Convert the bottom expanders in the "System Insights" panel into `st.tabs` layout:
  * `st.tabs(["📅 Calendar Events", "🧠 Behavioral Memory Engine Strategy Locks", "👁️ Audit Telemetry Logs", "⚙️ System Governance"])`
* In the **System Governance** tab:
  * Fetch live audit logs using `database.get_adaptation_audit_log()`.
  * Render a vertical timeline feed showing:
    * The distilled strategy adaptation.
    * The original user cluster telemetry that triggered it.
    * The specific reasoning or timestamp details.
  * Render "Revert" action buttons next to each audit card, enabling instant rollbacks by calling `database.revert_adaptation(audit_log_id)`.

---

### Component 6: Tests

#### [NEW] [test_hippocampus.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_hippocampus.py)
* Add a dedicated integration test that:
  * Pre-seeds the database with user correction entries (e.g., *"No, don't use absolute paths"*, *"Stop using absolute paths"*).
  * Runs the clustering logic and validates similarity scores are above the threshold.
  * Mocks local LLM completion to return a distilled rule.
  * Verifies rules are inserted in `ai_adaptations` and audit logs are written in `adaptation_audit_log`.
  * Verifies matched messages are successfully purged from `chat_timeline`.

## Verification Plan

### Automated Tests
* Run existing test suites:
  `python -m unittest discover tests`
* Run the new Hippocampus integration test:
  `python -m unittest tests/test_hippocampus.py`

### Manual Verification
* Run the manual consolidation command to verify the loop finishes without error:
  `python -c "import asyncio, neuromorphic_subsystems, router; r=router.ModelRouter(); h=neuromorphic_subsystems.Hippocampus(); asyncio.run(h.consolidate_experience_loop(r))"`
* Start the Streamlit UI and check that the "System Governance" tab displays historical audits and handles reverting adaptations correctly.
