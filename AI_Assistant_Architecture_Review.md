Personal AI Assistant: Architecture Review & Roadmap

1. The Core Vision (What We Established)

We are building a highly decoupled, context-aware AI assistant focused on personal logistics and dynamic task management. Unlike traditional CRUD-based task managers that rely on rigid alarms, this system utilizes a Dynamic Context Engine. It evaluates a fluid "Working State" against real-time variables (time, location, energy level, and calendar commitments) to execute tasks and offer suggestions conversationally.

The system bridges two distinct environments:

Home Office: A visually dense desktop command center.

On-the-Go: A hands-free, ultra-low-latency voice interface for when you are driving around Lakeland or walking outside.

2. Functional Capabilities (What It Does)

The assistant shifts from being a passive repository to an active, reasoning partner.

Continuous Synchronization: Whether you log a thought via text on your PC or dictate it to your phone while driving, it writes to a unified local database.

Temporal Awareness (The Hard Landscape): By integrating Google Calendar, the AI differentiates between fixed events (meetings, dinners) and fluid goals (research, coding). It plays "Tetris" with your goals, slotting them into the white space of your day.

Proactive Logistics: It anticipates needs based on fixed dates (e.g., an upcoming Chewy autoship for the cats) and proactively brings them up in natural conversation before the deadline.

Behavioral Adaptation (Friction Analytics): A nightly background job analyzes your execution telemetry (what tasks you deferred, what time of day you failed to complete goals). It extracts semantic rules and injects them into a vector database, permanently altering the AI's future pacing and tone to match your actual habits.

3. User Experience & Interface (How It Looks)

The UI is decoupled to serve the specific needs of the device being used.

The Desktop Command Center (Streamlit)

Split-Screen Layout:

Left Column: The Active Working State. This displays a kanban-style or list view of fluid tasks, current focus blocks, and active logistics. It includes direct-action buttons to instantly resolve or mutate tasks without chatting.

Right Column: The Unified Chat Timeline. A scrolling chat history showing text inputs from the desktop interspersed with transcribed audio logs (marked with a 🎙️ icon) from your mobile sessions.

Data Density: Clean, tabular displays of upcoming calendar events, recent telemetry summaries, and system status.

The Mobile Voice Node (LiveKit WebRTC PWA)

Minimalist UI: A simple Progressive Web App (PWA) pinned to your phone's home screen. It likely features a single, pulsing "listening" orb or waveform.

Conversational Speed: No text fields, no lists. It relies entirely on sub-500ms audio streaming.

Interruptible: If the AI is talking and you have a new thought, you can simply speak over it. The AI stops, listens, and pivots instantly.

4. Current Infrastructure (The Engine Room)

The system is designed for a local Kubernetes (K8s) cluster using a unified Helm chart.

Microservices Architecture:

ui/: Streamlit pod (Port 8501).

agent/: LiveKit Voice Worker pod (WebRTC).

cron/: Ephemeral Optimization Engine pod.

Storage Layer:

A shared PersistentVolumeClaim (PVC) backed by local NVMe storage.

SQLite (WAL Mode): Handles high-frequency, concurrent read/writes for state and chat logs.

Note: Strict K8s Pod Affinity ensures all pods run on the same physical node to prevent SQLite file-locking issues over network filesystems.

5. Roadmap: Areas for Improvement & Security

To elevate this from a functional prototype to a secure, resilient daily driver, the following areas must be addressed.

A. Security & Trust Boundaries (Critical)

Dual-LLM Guardrails: Currently, external data (like a calendar invite description) flows directly into the main agent's context. This invites Indirect Prompt Injection. We must implement a cheaper, isolated LLM (e.g., Llama 3 8B locally) to sanitize and extract data from external APIs before handing structured JSON to the main reasoning agent.

The "Human-in-the-Loop" Switch: The AI should have read-only access by default. Any mutating action (e.g., "Cancel my 3 PM meeting" or "Order cat food") must require an explicit user confirmation (a button click or a verbal "Yes, authorize") before executing the API call.

Secret Management: Move Google API tokens, OpenAI keys, and LiveKit secrets out of container environment variables and into a localized HashiCorp Vault or Kubernetes Secrets implementation.

B. Infrastructure & Scalability

Database Migration Path: While SQLite WAL mode is brilliant for single-node setups, it traps your deployment to one physical machine. As the system grows, migrating to PostgreSQL with the pgvector extension will allow you to scale your pods across multiple physical nodes while combining your relational logs and semantic behavioral memory into one database cluster.

Network Resilience (Mobile): Cellular handoffs (e.g., switching from 5G to LTE) can drop WebRTC packets. The frontend PWA must be improved to buffer audio locally during micro-disconnects and bulk-send it to the LiveKit server upon reconnection, ensuring no thoughts are lost while driving.

C. Capability Enhancements

Multi-Modal Ingestion: Allow the Streamlit app to accept image drops (e.g., a screenshot of an email or a tracking number). The AI can parse the image via vision models and automatically log the logistic details into the Working State.

Webhooks & Automation: Integrate webhooks (e.g., via n8n or local Node-RED) so the system isn't just checking your calendar, but actively receiving push notifications from your bank, Amazon, or smart home devices (Home Assistant) to trigger proactive voice alerts.