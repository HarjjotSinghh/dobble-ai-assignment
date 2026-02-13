# Doctor Appointment Assistant - MCP-Powered AI Agent

A smart doctor appointment and reporting assistant that uses **MCP (Model Context Protocol)** to expose APIs and tools dynamically discovered and invoked by an AI agent (LLM). The system demonstrates agentic behavior where the AI decides what tools to use, when to use them, and how to combine them to fulfill user prompts.

---

## Architecture Overview

```
┌─────────────────┐     HTTP/WS      ┌────────────────────┐
│  React Frontend │ ◄──────────────► │   FastAPI Server   │
│  (Patient/Doctor│                  │                    │
│   Dashboards)   │                  │  ┌──────────────┐  │
└─────────────────┘                  │  │  LLM Agent   │  │
                                     │  │(Orchestrator)│  │
                                     │  └──────┬───────┘  │
                                     │         │          │
                                     │  ┌──────▼──────┐   │
                                     │  │  MCP Server │   │
                                     │  │ (Tools/     │   │
                                     │  │  Resources/ │   │
                                     │  │  Prompts)   │   │
                                     │  └─────────────┘   │
                                     │        │           │
                                     └────────┼───────────┘
                                              │
                    ┌─────────────┬───────────┼──────────┬─────────────┐
                    │             │           │          │             │
              ┌─────▼─────┐ ┌─────▼─────┐ ┌───▼───┐ ┌────▼─────┐ ┌─────▼────┐
              │ PostgreSQL│ │  Google   │ │ Email │ │  Slack   │ │  In-App  │
              │ Database  │ │  Calendar │ │ SMTP  │ │  Webhook │ │  Notifs  │
              └───────────┘ └───────────┘ └───────┘ └──────────┘ └──────────┘
```

### MCP Architecture (Client–Server–Tool/Prompt/Resource)

The MCP server (`backend/app/mcp_server/`) exposes:

| Component | Description |
|-----------|-------------|
| **Tools** (10) | Executable actions: `list_doctors`, `check_doctor_availability`, `book_appointment`, `cancel_appointment`, `get_appointment_stats`, `get_patient_appointments`, `send_email_notification`, `send_slack_notification`, `send_inapp_notification`, `find_alternative_slots` |
| **Resources** (2) | Data endpoints: `doctor://list`, `appointment://today` |
| **Resource Templates** (1) | Dynamic: `doctor://{doctor_id}/schedule/{date}` |
| **Prompts** (2) | Templates: `book_appointment`, `doctor_daily_summary` |

The LLM Agent acts as the **MCP Client**, dynamically discovering available tools and deciding which to invoke based on the user's natural language input.

---

## Features

### Scenario 1: Patient Appointment Scheduling (LLM + Agent Flow)
- Natural language appointment booking ("I want to book with Dr. Ahuja tomorrow morning")
- AI agent automatically: parses intent → checks availability → books appointment → creates Google Calendar event → sends email confirmation
- Auto-rescheduling when preferred slot is unavailable (suggests alternatives)
- Multi-turn conversation support (context maintained across prompts)

### Scenario 2: Doctor Summary Reports & Notifications
- Natural language queries ("How many patients visited yesterday?", "How many patients with fever?")
- AI-generated summary reports with statistics
- Dashboard button-triggered reports
- Notifications sent via **Slack** (different from email used in Scenario 1)
- In-app notification system with real-time WebSocket delivery

### Bonus Features
- Role-based login (patient vs doctor) with JWT authentication
- LLM-powered auto-rescheduling when doctor is unavailable
- Prompt/chat history tracking
- Real-time in-app notifications via WebSocket

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | FastAPI (async) + Python 3.11+ |
| Database | PostgreSQL 16 + SQLAlchemy (async) |
| MCP | Python MCP SDK (`mcp` package) |
| LLM | OpenAI GPT-4o-mini / Anthropic Claude (configurable) |
| Calendar | Google Calendar API |
| Email | SMTP (Gmail) / any transactional service |
| Notifications | Slack Webhooks + In-App (WebSocket) |
| Auth | JWT + bcrypt |

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 16+ (or Docker)
- OpenAI API key or Anthropic API key

### 1. Clone & Setup

```bash
git clone <repo-url>
cd dobble-ai-assignment
```

### 2. Start PostgreSQL

**Option A: Docker (Recommended)**
```bash
docker-compose up -d
```

**Option B: Local PostgreSQL**
```bash
createdb doctor_appointment
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../.env.example ../.env
# Edit .env with your API keys
```

**Required `.env` variables:**
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/doctor_appointment
OPENAI_API_KEY=sk-your-key-here  # Required for LLM
LLM_PROVIDER=openai               # or "anthropic"
```

**Optional (for full integration):**
```env
SMTP_USERNAME=your@gmail.com      # Email notifications
SMTP_PASSWORD=your-app-password
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX  # Slack notifications
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json       # Google Calendar
```

### 4. Start Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

The server will:
- Create all database tables automatically
- Seed demo data (doctors, patients, sample appointments)
- Print demo login credentials

### 5. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 6. Open Application

Visit **http://localhost:5173**

Demo Login Credentials:
| Role | Email | Password |
|------|-------|----------|
| Patient | john@email.com | password123 |
| Patient | jane@email.com | password123 |
| Doctor | dr.ahuja@hospital.com | password123 |
| Doctor | dr.sharma@hospital.com | password123 |
| Doctor | dr.patel@hospital.com | password123 |

---

## Sample Prompts

### Patient Prompts (Appointment Booking)

```
"I want to book an appointment with Dr. Ahuja tomorrow morning"
→ Agent: list_doctors → check_doctor_availability → book_appointment → send_email_notification

"Is Dr. Sharma available on Friday?"
→ Agent: list_doctors → check_doctor_availability

"Please book the 3 PM slot"  (multi-turn, after checking availability)
→ Agent: book_appointment → send_email_notification

"Show my upcoming appointments"
→ Agent: get_patient_appointments

"Cancel my appointment #5"
→ Agent: cancel_appointment

"Which doctors are available?"
→ Agent: list_doctors
```

### Doctor Prompts (Summary Reports)

```
"How many patients visited yesterday?"
→ Agent: get_appointment_stats → send_slack_notification

"How many appointments do I have today and tomorrow?"
→ Agent: get_appointment_stats (today) → get_appointment_stats (tomorrow)

"How many patients with fever?"
→ Agent: get_appointment_stats → (filters by reason)

"Send me a summary of this week via Slack"
→ Agent: get_appointment_stats → send_slack_notification
```

### Multi-Turn Conversation Example

```
User: "I want to check Dr. Ahuja's availability for Friday afternoon"
Agent: Checks availability, shows slots like 2:00 PM, 2:30 PM, 3:00 PM...

User: "Please book the 3 PM slot"
Agent: Books the 3:00 PM slot (remembers Dr. Ahuja + Friday from context)
       → Creates Google Calendar event
       → Sends email confirmation
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login (returns JWT) |
| GET | `/api/auth/me` | Get current user |

### Chat (AI Agent)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/` | Send message to AI agent |
| GET | `/api/chat/sessions` | Get chat history |

### Appointments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/appointments/doctors` | List all doctors |
| GET | `/api/appointments/my-appointments` | Get user's appointments |
| GET | `/api/appointments/doctor-stats` | Get doctor statistics |

### Notifications
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notifications/` | Get notifications |
| PUT | `/api/notifications/{id}/read` | Mark as read |
| PUT | `/api/notifications/read-all` | Mark all read |
| WS | `/api/notifications/ws/{token}` | Real-time WebSocket |

---

## MCP Tools Reference

| Tool | Input | Description |
|------|-------|-------------|
| `list_doctors` | `{specialization?}` | List doctors, optionally filtered |
| `check_doctor_availability` | `{doctor_id, date}` | Get available 30-min slots |
| `book_appointment` | `{doctor_id, patient_id, date, start_time, reason?}` | Book + Calendar + Email |
| `cancel_appointment` | `{appointment_id}` | Cancel appointment |
| `get_appointment_stats` | `{doctor_id, date_from?, date_to?}` | Appointment statistics |
| `get_patient_appointments` | `{patient_id, status?}` | Patient's appointments |
| `send_email_notification` | `{to_email, subject, body}` | Send email (Scenario 1) |
| `send_slack_notification` | `{message}` | Send Slack message (Scenario 2) |
| `send_inapp_notification` | `{user_id, title, message, type?}` | In-app notification |
| `find_alternative_slots` | `{doctor_id, preferred_date, num_slots?}` | Auto-rescheduling |

---

## Project Structure

```
dobble-ai-assignment/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point + seed data
│   │   ├── config.py            # Environment configuration
│   │   ├── database.py          # Async SQLAlchemy setup
│   │   ├── models/
│   │   │   └── models.py        # Database models (User, Doctor, Appointment, etc.)
│   │   ├── schemas/
│   │   │   └── schemas.py       # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── auth.py          # JWT authentication routes
│   │   │   ├── chat.py          # AI agent chat endpoint
│   │   │   ├── appointments.py  # Appointment CRUD routes
│   │   │   └── notifications.py # Notification routes + WebSocket
│   │   ├── mcp_server/
│   │   │   ├── server.py        # MCP server (tools, resources, prompts)
│   │   │   └── tool_handlers.py # Tool execution logic
│   │   ├── agent/
│   │   │   ├── agent.py         # LLM agent (OpenAI/Anthropic + tool calling)
│   │   │   └── session.py       # Multi-turn session management
│   │   └── services/
│   │       ├── calendar_service.py    # Google Calendar integration
│   │       ├── email_service.py       # SMTP email service
│   │       └── notification_service.py # Slack + WebSocket notifications
│   ├── requirements.txt
│   └── init.sql                 # Database seed data
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Route configuration
│   │   ├── main.jsx             # Entry point
│   │   ├── context/
│   │   │   └── AuthContext.jsx  # Authentication state
│   │   ├── services/
│   │   │   └── api.js           # API client (axios)
│   │   ├── components/
│   │   │   ├── ChatInterface.jsx     # AI chat UI
│   │   │   └── NotificationPanel.jsx # Notification display
│   │   └── pages/
│   │       ├── Login.jsx         # Auth page with role selection
│   │       ├── PatientDashboard.jsx # Patient view
│   │       └── DoctorDashboard.jsx  # Doctor view with stats
│   ├── package.json
│   └── index.html
├── docker-compose.yml           # PostgreSQL container
├── .env.example                 # Environment template
└── README.md                    # This file
```

---

## Design Decisions

1. **MCP Integration**: The MCP server defines tools declaratively with JSON schemas, enabling the LLM to discover and invoke them dynamically. Tool handlers are separated from definitions for clean architecture.

2. **Agentic Loop**: The LLM agent runs in a loop — it can make multiple tool calls per turn (e.g., check availability → book → send email) before returning a final response to the user.

3. **Multi-Turn Context**: Conversation history is persisted in the `chat_sessions` table with JSON fields, allowing the agent to reference previous messages without the user restating context.

4. **Dual Notification Channels**: Email (SMTP) is used for patient appointment confirmations (Scenario 1), while Slack webhooks + in-app notifications are used for doctor reports (Scenario 2), as required.

5. **Graceful Degradation**: All external services (Google Calendar, Email, Slack) fall back to demo mode when credentials aren't configured, so the core functionality works without external API setup.

6. **Async Everything**: The entire backend is async (FastAPI + asyncpg + aiosmtplib) for high concurrency and non-blocking I/O.

---

## Google Calendar Setup (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the Google Calendar API
3. Create OAuth 2.0 credentials (Desktop application)
4. Download `credentials.json` to the `backend/` directory
5. Run the app — it will open a browser for OAuth consent on first use

Without credentials, the system runs in **demo mode** (appointments are still saved to DB, just not synced to Google Calendar).

---

## Evaluation Criteria Coverage

| Criteria | Implementation |
|----------|---------------|
| MCP Architecture | Full MCP server with 10 tools, 2 resources, 1 resource template, 2 prompts |
| LLM Workflow Orchestration | Agentic loop with multi-step tool calling (check → book → notify) |
| API Integration | Google Calendar, SMTP Email, Slack Webhooks, WebSocket |
| Full-Stack Fluency | React ↔ FastAPI ↔ PostgreSQL with async throughout |
| Code Readability | Modular structure, typed schemas, comprehensive docstrings |
| Scalability | Async architecture, connection pooling, session management |
| Agentic Design | Dynamic tool selection, multi-turn context, auto-rescheduling |
