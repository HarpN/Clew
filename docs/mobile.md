# 📱 Mobile Web Hub & REST API

The Clew Mobile Web Hub offers a responsive, touch-optimized PWA experience for managing tasks and interacting with the voice assistant on the go.

---

## REST API Endpoints (`mobile_server.py`)

The FastAPI application serves both static assets from `mobile/` and REST API routes:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/tasks` | `GET` | Retrieve task lists filtered by active energy level & priority |
| `/api/tasks` | `POST` | Create a new task with energy cost and priority tags |
| `/api/tasks/{task_id}/status` | `PUT` | Mutate task status (`Complete`, `Start Focus`, `Defer`) |
| `/api/chat` | `GET` | Fetch real-time chat & audio interaction timeline |
| `/api/livekit/token` | `POST` | Mint ephemeral access tokens for LiveKit WebRTC sessions |

---

## Mobile Interface Highlights

- **Day-at-a-Glance Dashboard**: High-level overview of immediate focus blocks.
- **Micro-Animations & Glassmorphic Design**: Sleek dark mode visual feedback.
- **One-Tap Task Mutations**: Quick inline controls for state transitions.
- **Floating Mic Button**: Instant WebRTC audio streaming to the LiveKit voice agent node.
