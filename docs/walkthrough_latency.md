# Walkthrough - GPU Acceleration, Model Migration, State Query Bug Fix & Chat Token Streaming

We have successfully migrated the Clew assistant stack to NVIDIA GPU-accelerated local execution, transitioned the primary model to `qwen2.5:3b-instruct`, resolved a bug where list queries returned generic telemetry, and implemented async token-by-token streaming on the desktop timeline to eliminate perceived conversational latency.

---

## Changes Made

### Docker Compose
- **GPU Passthrough**: Configured the `ollama` service in [docker-compose.yml](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/docker-compose.yml) to reserve NVIDIA GPU capabilities using the `deploy.resources.reservations` structure.
- **Service Environment**: Added `OLLAMA_NUM_PARALLEL=1` and `OLLAMA_NOPRUNE=1` environment variables to the `ollama` container.
- **Model Bootstrap Sync**: Updated the `ollama-bootstrap` service to pull the `qwen2.5:3b-instruct` model and block until it is successfully downloaded and verified via the Ollama `/api/tags` endpoint.
- **Model Settings**: Updated the `LOCAL_MODEL` environment variable to target `qwen2.5:3b-instruct` across the `clew-ui`, `clew-mobile`, and `clew-agent` containers.

### Python Codebase
- **Router Fallback**: Configured `CODER_MODEL` and `GENERALIST_MODEL` default fallbacks in [router.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/router.py) to target `qwen2.5:3b-instruct`.
- **KV Cache Optimization**: Injected `OLLAMA_OPTIONS` (with `num_ctx: 2048`, `temperature: 0.2`, and `num_predict: 256` boundaries) inside [router.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/router.py) to maximize local GPU KV cache utilization and bound output generation.
- **Chit-Chat Fallbacks**: Modified the fast chit-chat bypass handlers in [brain.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/brain.py) and [brain_orchestrator.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/brain_orchestrator.py) to dynamically reference the `GENERALIST_MODEL` instead of hardcoded `"llama3"`.
- **PostgreSQL V2 Compatibility**: Fixed two dialect compatibility bugs in [memory_service.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/memory_service.py) where psycopg2's `RealDictCursor` returned row dictionaries:
  1. Extracted `COUNT(*)` via a named alias (`AS count`) and lookup (`dict(cursor.fetchone())["count"]`).
  2. Simplified the boolean query filter from `a.is_active = 1 OR a.is_active = TRUE` to `WHERE a.is_active` to prevent PG errors comparing booleans to integer literals.
- **Test Integrity**: Mocked `datetime` inside [tests/test_lifeos_pipeline.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_lifeos_pipeline.py) and [tests/test_multi_model_router.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/tests/test_multi_model_router.py) to prevent late-night constraints from failing test assertions.
- **State Query Bug Fix**: Enhanced the `QUERY_STATE` action handling in [orchestrator.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/orchestrator.py):
  1. Updated `_execute_command` to retrieve active database tasks and filter them by checking if the queried domain matches any value in `context_tags`.
  2. Configured `friendly_message` generation to format and display the list of filtered tasks directly in the response chat bubble (e.g. `"Here is what is currently on your Projects list: \n- Task A ..."`), falling back to the standard snapshot message only if no specific domain tasks exist.
- **Token-by-Token Streaming Integration**: 
  1. Created `execute_streaming_completion` asynchronous generator method in [router.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/router.py) to parse chunk lines from Ollama's stream.
  2. Adjusted `process_thought_cycle` in [brain_orchestrator.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/brain_orchestrator.py) to return the streaming generator directly when a `CHITCHAT` intent is matched.
  3. Replaced the static iframe wrapper in [ui/app.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ui/app.py) with a fully native Streamlit dashboard implementation supporting `st.write_stream` and active tethers/WAL mode integrations.

---

## Verification Results

### 1. Automated Unit Tests
Executed the entire unittest suite inside the `clew-agent` container:
```powershell
docker exec clew-agent python -m unittest discover -s tests
```
**Result**: `Ran 21 tests - OK` (All tests successfully passing).

### 2. GPU Passthrough Allocation Logs
Checked Ollama container execution logs to confirm discrete GPU offloading:
```
time=2026-07-20T01:59:38.688Z level=INFO source=types.go:32 msg="inference compute" id=0 filter_id=0 library=CUDA compute=12.0 name=CUDA0 description="NVIDIA GeForce RTX 5070" libdirs=ollama,cuda_v13 driver=13.1 pci_id=0000:01:00.0 type=discrete total="11.9 GiB" available="10.8 GiB"
```

### 3. Manual Operational Cycle
Ran end-to-end routing queries inside the `clew-agent` container to verify latency and classification mapping.

#### Cycle 1: Greeting Pre-Classifier Bypass
- **Input**: `"hi"`
- **Intent**: `CHITCHAT - CHITCHAT`
- **Latency**: **1.60 ms** (pre-classifier bypass works perfectly)

#### Cycle 2: Compound Chores Command
- **Input**: `"Add review the database pooling logs to my chores with high priority."`
- **Intent**: `CHORES - ADD_TASK` (successfully classified)
- **Execution**: Correctly inserted task `Review Database Pooling Logs` to database chores table.
- **Latency**: **773.01 ms** (achieves sub-second conversational latency using GPU acceleration)

#### Cycle 3: State Query Task Retrieval
- **Input**: `"what is currently on my projects list?"`
- **Intent**: `PROJECTS - QUERY_STATE` (successfully classified)
- **Execution**: Fetches all projects tasks and formats them dynamically.
- **Output**: `"Here is what is currently on your PROJECTS list:\n- Refactor protocol middleware engine (Priority: P1, Energy: high)\n..."` (rendered correctly inside chat)

#### Cycle 4: Asynchronous Token-by-Token Streaming
- **Input**: `"Tell me a joke in one sentence."`
- **Intent**: `CHITCHAT - CHITCHAT`
- **Time to First Token**: **308.79 ms** (instant feedback)
- **Generation Duration**: **80.00 ms** (170+ tokens/second inference rate on discrete GPU)
- **Output**: Streams dynamically token-by-token directly inside Streamlit via `st.write_stream` and only persists final output to history after stream completion.
