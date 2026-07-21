# Walkthrough - Amygdala Real-Time Friction Engine Integration

We have successfully integrated the **Amygdala Real-Time Friction Engine** into the Clew assistant workspace. This engine monitors user stress levels dynamically across messaging cadence, input repetition, punctuation intensity, and lexical sentiment, shunting to a hyper-terse persona when stress crosses the predefined threshold.

## Changes Made

### 1. Neuromorphic Subsystems Class
- **[NEW] [neuromorphic_subsystems.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/neuromorphic_subsystems.py)**: Contains the `Amygdala` class. It performs:
  - Lexical sentiment checks strictly mapping values between `-1.0` and `1.0`.
  - Friction calculation $F_{\text{user}}$ using typing cadence deltas (or falling back to inter-message duration in database logs), linguistic repetition, exclamation spam, and sentiment.
  - Stress threshold comparison against $\theta_{\text{stress}} = 0.75$.

### 2. Cognitive Brain Orchestrator
- **[MODIFY] [brain_orchestrator.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/brain_orchestrator.py)**:
  - Instantiated `Amygdala` inside `CognitiveBrain.__init__`.
  - Added the friction assessment pass at the start of `process_thought_cycle` to compute $F_{\text{user}}$ and set `self.terse_mode_active` state.
  - Dynamically injected `"terse_mode": True` into the factual payload and passed the state down to the semantic translation stream.

### 3. Broca Area & Persona Registry
- **[MODIFY] [persona_manager.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/persona_manager.py)**: Added the `"terse"` persona definition to the registry.
- **[MODIFY] [broca_translator.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/broca_translator.py)**:
  - Intercepts `terse_mode` flag in `compile_response` and `compile_response_stream`.
  - Bypasses standard registry prompts, forcing the hyper-minimalist, safe engineering instructions.
  - Caps LLM generation ceiling options (`max_tokens` / `num_predict`) to exactly `64` tokens.
  - Relaxes semantic divergence check (Broca Guard) under Terse Mode to prevent value error vetos on minimal answers.
- **[MODIFY] [router.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/router.py)**: Extended `query_ollama_chat` signature to accept custom LLM options (like `max_tokens` limit).

### 4. Streamlit UI Command Center
- **[MODIFY] [ui/app.py](file:///c:/Users/Giraffe/Documents/Projects/Clew/Clew/ui/app.py)**:
  - Tracks user submission intervals using `st.session_state` to calculate interval latency.
  - Passes the latency delta list to `process_thought_cycle`.
  - Detects if `terse_mode` was tripped during execution and displays a subtle adaptive warning banner at the top of the chat area:
    🛡️ **Terse Mode active:** Silencing advice to minimize cognitive load.

---

## Verification Results

### Automated Unit and Integration Tests
We created a comprehensive test suite in `tests/test_amygdala.py` validating:
1. Lexical sentiment check scores and clamping.
2. Calm input vs. stressed input friction scores and thresholds.
3. Full integration path shunting to Terse Mode, capping LLM generation parameters, and system instructions injection.

All 40 unit and integration tests (36 existing + 4 new) pass cleanly:

```bash
python -m unittest discover -s tests
...
Ran 40 tests in 6.501s

OK
```

### Manual Verification
1. Open the Streamlit Command Center.
2. Enter repetitive, angry inputs rapidly, e.g., `"No! Stop! That is completely wrong!"` twice within a few seconds.
3. Observe in terminal logs:
   `[AMYGDALA] Stress threshold crossed. Shunting to Terse Mode.`
4. The Streamlit UI will display the custom styled banner `🛡️ Terse Mode active: Silencing advice to minimize cognitive load` at the top of the timeline.
5. The generated output is a single-sentence or terminal code response returned with extremely low latency.
