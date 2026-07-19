# ⚡ Clew: Personal AI Assistant

Welcome to the documentation for **Clew** — a decoupled, context-aware AI assistant built for personal logistics, fluid task management, real-time voice streaming, and autonomous behavioral adaptation.

---

## 🌟 Key Capabilities

### 1. Dynamic Context Engine
Rather than relying on rigid calendar alarms, Clew evaluates your fluid **Working State** against real-time variables:
- **Time of Day & Energy Level**: Matches tasks (`low`, `medium`, `high` energy) to your cognitive bandwidth.
- **Priority Pacing**: Categorizes tasks by priority (`P1`, `P2`, `P3`) and tags context (`#voice`, `#office`, `#research`).

### 2. Dual Operational Interfaces
- **Desktop Command Center (`ui/app.py`)**: Visual dashboard built in Streamlit. Split-screen layout displaying active working state, focus blocks, proactive logistics, calendar events, unified chat timeline, and friction analytics.
- **Mobile Voice & Web Hub (`mobile/` & `mobile_server.py`)**: Responsive mobile PWA hub powered by FastAPI. Features a "Day-at-a-Glance" task view, single-tap status mutations (`Complete`, `Start Focus`, `Defer`), and a floating WebRTC microphone activator.

### 3. Sub-500ms Hands-Free Voice Node (`agent/agent.py`)
- Built on the **LiveKit Agents** WebRTC framework.
- Uses OpenAI LLM, Speech-to-Text (STT), Text-to-Speech (TTS), and Silero Voice Activity Detection (VAD).
- Non-blocking database execution via `asyncio.to_thread()`.
- AI tool context (`@ai_callable`) allowing Clew to query and mutate tasks while streaming audio.

### 4. Autonomous Behavioral Memory & Friction Analytics
- Ephemeral background jobs evaluate execution telemetry (e.g., tasks deferred after 9:00 PM).
- Automatically extracts semantic rules and populates `ai_adaptations`.
- Administrative **System Governance Panel** allowing users to lock specific AI strategies to shield them from cron modifications or revert AI adaptation history with one click.
