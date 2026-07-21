# Walkthrough - Option A (Pre-Computation Veto & Strict Context Pinning)

We have successfully implemented **Option A (Pre-Computation Veto / Deterministic State-Validation)**. This approach eliminates LLM-on-LLM latency by running pure Python guardrail validation checks prior to initialization of streaming or code execution, and enforces factual alignment via Jinja2 prompt injection for context pinning.

---

## 🛠️ Changes Made

### 1. Guardrail Layer (`orchestrator.py`)
- Created [ConstraintGuard.verify_pre_flight](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/orchestrator.py#L60-L70) static method.
- Evaluates constraints (Late-Night Tech Fatigue, Budget cost limit exceeding $500, and Goal-Tether Alignment) directly on the Pydantic-validated `IntentCommand` objects with $0\text{ ms}$ of additional LLM overhead.

### 2. Context Pinning (`router.py` & Prompts)
- Added `sql_results_json` parameter to [get_system_prompt](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/router.py#L39-L66) and [get_templated_prompt](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/router.py#L304-L315) to pass pre-flight database query results to prompt templates.
- Appended the Ground Truth section and the Groundedness Mandate to:
  - [prompts/lifeos_system_prompt.j2](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/prompts/lifeos_system_prompt.j2#L43-L50)
  - [prompts/coder_system_prompt.j2](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/prompts/coder_system_prompt.j2#L42-L49)
- Enforces strict factual reliance and blocks the AI from hallucinating details (e.g. budgets).

### 3. Orchestration & Interfaces
- Refactored `process_thought_cycle` in [brain_orchestrator.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/brain_orchestrator.py#L20-L80) and [brain.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/brain.py#L27-L80) to run the pre-flight veto checks. If a constraint is violated, it intercepts the cycle and returns the veto response instantly.
- Handled `QUERY_STATE` pre-flight queries by running the database query and caching it inside the prompt templating context.
- Streamlined [ui/app.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ui/app.py#L270-L290) to delegate all prompt flows to the central `process_thought_cycle` orchestrator, which returns a streaming async generator for chitchat/queries or a structured command result for mutations/vetoes.

---

## 📈 Verification Results

### 1. Automated Tests
All 21 unit tests in the suite were executed and passed successfully:
```powershell
python -m unittest discover -s tests
```
**Result**: `Ran 21 tests in 6.133s - OK`.

### 2. Pre-Flight Veto Integrity
When a task is misaligned or violates constraints (e.g., tether mismatch), it triggers the veto immediately:
```
WARNING:clew.graph_memory:Goal-Tether Alignment Failure: Specified goal_tether_id 'unregistered_tether_id_xyz' does not exist in graph_memory.
WARNING:clew.brain:Pre-Flight Veto Triggered: Goal-Tether Alignment Failure: ...
INFO:clew.event_store:Recorded event #310: [PROJECTS] Blocked ADD_TASK
```
This reduces local GPU load and returns the static warning payload in $<10\text{ ms}$.
