# Desktop Command Center (Streamlit UI)

This Streamlit application serves as the Desktop Command Center for the Personal AI Assistant, reading from and writing to the local SQLite database (`assistant.db`).

## Features

- **Split-Screen Dashboard Layout**:
  - **Left Column (Active Working State)**:
    - Interactive Fluid Task Manager (filter by status, energy level, priority; mutate status with direct buttons).
    - Focus Blocks scheduler & status tracker.
    - Proactive Logistics monitor with direct action buttons.
    - Task & Logistic creation tools.
  - **Right Column (Unified Chat Timeline)**:
    - Combined chat feed of desktop text inputs and mobile WebRTC voice logs (tagged with 🎙️ icons).
    - Real-time text messaging input box.
- **System Insights Panels**:
  - Calendar Events (Hard Landscape table).
  - Behavioral Memory Engine (Active friction analytics rules).
  - Execution Telemetry Log (Friction analytics audit trail).
- **SQLite WAL Mode Integration**: Monitored in real-time in the system status header.

## Running the App

From the repository root (`PersonalAssistant/`):

```bash
streamlit run ui/app.py
```

Or specify custom port / host:

```bash
streamlit run ui/app.py --server.port 8501
```
