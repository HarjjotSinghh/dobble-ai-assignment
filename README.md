<img width="1230" height="937" alt="image" src="https://github.com/user-attachments/assets/ae2db3c7-7c77-4ba9-9556-2b565a9c513f" />

# Doctor Appointment Assistant - MCP-Powered AI Agent

A smart doctor appointment and reporting assistant built with **true MCP (Model Context Protocol) architecture**. The system implements the full MCP Host–Client–Server design pattern where the LLM agent discovers tools dynamically from the MCP server via the protocol and routes all tool calls through the MCP client-server channel.

## Screenshots:

![Doctor Dashboard](screenshots/doctor_notification.png)
![Patient Dashboard](screenshots/patient_booking.png)

---

## MCP Architecture (Host–Client–Server)

This implementation follows the official MCP specification with clear separation between Host, Client, and Server layers:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HOST APPLICATION (FastAPI - main.py)                                   │
│                                                                         │
│  ┌────────────────┐      ┌───────────────────────────────────────────┐  │
│  │  React Frontend│ HTTP │  Chat Router (routers/chat.py)            │  │
│  │  (Patient/     │◄────►│                                           │  │
│  │   Doctor UI)   │      │  ┌─────────────────────────────────────┐  │  │
│  └────────────────┘      │  │  LLM Agent (agent/agent.py)         │  │  │
│                          │  │  - Orchestrates multi-step workflows│  │  │
│                          │  │  - Discovers tools dynamically      │  │  │
│                          │  │  - Routes calls through MCP client  │  │  │
│                          │  └───────────┬─────────────────────────┘  │  │
│                          └──────────────┼────────────────────────────┘  │
│                                         │                               │
│                          ┌──────────────▼───────────────────────────┐   │
│                          │  MCP CLIENT (mcp_client/client.py)       │   │
│                          │  - connect()         [initialize]        │   │
│                          │  - discover_tools()   [tools/list]       │   │
│                          │  - call_tool()        [tools/call]       │   │
│                          │  - list_resources()   [resources/list]   │   │
│                          │  - list_prompts()     [prompts/list]     │   │
│                          │  - get_tools_for_llm() [schema convert]  │   │
│                          └──────────────┬───────────────────────────┘   │
└─────────────────────────────────────────┼───────────────────────────────┘
                                          │ stdio transport
                                          │ (JSON-RPC 2.0)
┌─────────────────────────────────────────▼─────────────────────────────┐
│  MCP SERVER (subprocess - mcp_server/server.py)                       │
│  Built with FastMCP (Python MCP SDK)                                  │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  TOOLS (10) - Registered via @mcp.tool() decorator              │  │
│  │  list_doctors, check_doctor_availability, book_appointment,     │  │
│  │  cancel_appointment, get_appointment_stats,                     │  │
│  │  get_patient_appointments, send_email_notification,             │  │
│  │  send_slack_notification, send_inapp_notification,              │  │
│  │  find_alternative_slots                                         │  │
│  ├─────────────────────────────────────────────────────────────────┤  │
│  │  RESOURCES (1+1) - @mcp.resource()                              │  │
│  │  doctor://list, doctor://{id}/schedule/{date}                   │  │
│  ├─────────────────────────────────────────────────────────────────┤  │
│  │  PROMPTS (2) - @mcp.prompt()                                    │  │
│  │  book_appointment_prompt, doctor_daily_summary_prompt           │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌───────┐  ┌──────────┐      │
│  │PostgreSQL│  │ Google   │  │ Email  │  │ Slack │  │ In-App   │      │
│  │ Database │  │ Calendar │  │ SMTP   │  │Webhook│  │WebSocket │      │
│  └──────────┘  └──────────┘  └────────┘  └───────┘  └──────────┘      │
└───────────────────────────────────────────────────────────────────────┘
```

### Key MCP Design Principles Implemented

1. **Dynamic Tool Discovery**: The agent discovers available tools at runtime by calling `tools/list` on the MCP server via the client. Tool schemas are NOT hardcoded in the agent — they are fetched through the MCP protocol.

2. **Client–Server–Tool Separation**: Three distinct layers:
   - **Host** (`main.py`): Manages MCP lifecycle, serves the web application
   - **Client** (`mcp_client/client.py`): Protocol-level communication with the server
   - **Server** (`mcp_server/server.py`): Standalone process exposing tools, resources, prompts

3. **Protocol-Driven Tool Calls**: All tool execution flows through the MCP protocol:
   ```
   Agent → MCP Client [tools/call] → MCP Server → Tool Handler → Database/APIs
   ```
   The agent never directly calls tool handlers.

4. **stdio Transport**: The MCP server runs as an independent subprocess. The client communicates via stdin/stdout using JSON-RPC 2.0 messages, following the MCP specification.

5. **Agent-Driven Orchestration**: The LLM agent loop:
   ```
   1. Discover tools from MCP server     [tools/list]
   2. Convert schemas to LLM format      [openai/anthropic]
   3. Send prompt + tools to LLM
   4. LLM decides which tool to call
   5. Route tool call through MCP client  [tools/call]
   6. Feed result back to LLM
   7. Repeat until final answer
   ```

6. **Multi-Tool Chaining**: The agent naturally chains multiple tool calls in a single conversation turn (e.g., `list_doctors → check_availability → book_appointment → send_email`).

7. **Structured Session Management**: Sessions track:
   - Message history (last 20 messages)
   - Entity tracking (doctors, dates, appointments mentioned)
   - Action history (MCP tools called per turn)
   - Turn counter and timestamps

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
- Prompt/chat history tracking with structured context
- Real-time in-app notifications via WebSocket

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | FastAPI (async) + Python 3.11+ |
| Database | PostgreSQL 16 + SQLAlchemy (async) |
| MCP | Python MCP SDK (`mcp` package) with FastMCP |
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
- Start the MCP server subprocess
- Connect the MCP client and discover tools dynamically
- Print discovered tool count and capabilities

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
| GET | `/api/chat/sessions` | Get chat history with context |

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

### Health / MCP Status
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check with MCP server capabilities (dynamically discovered) |
| GET | `/api/health` | Detailed health check including MCP connection status |

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
│   │   ├── main.py              # HOST: FastAPI entry + MCP lifecycle management
│   │   ├── config.py            # Environment configuration
│   │   ├── database.py          # Async SQLAlchemy setup
│   │   ├── models/
│   │   │   └── models.py        # Database models (User, Doctor, Appointment, etc.)
│   │   ├── schemas/
│   │   │   └── schemas.py       # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── auth.py          # JWT authentication routes
│   │   │   ├── chat.py          # AI agent chat endpoint (uses MCP client)
│   │   │   ├── appointments.py  # Appointment CRUD routes
│   │   │   └── notifications.py # Notification routes + WebSocket
│   │   ├── mcp_server/          # MCP SERVER (runs as subprocess)
│   │   │   ├── server.py        # FastMCP server with @mcp.tool() registration
│   │   │   └── tool_handlers.py # Tool execution logic (DB + external APIs)
│   │   ├── mcp_client/          # MCP CLIENT (protocol communication)
│   │   │   └── client.py        # MCPClient: connect, discover, call_tool
│   │   ├── agent/
│   │   │   ├── agent.py         # LLM agent (uses MCPClient for all tool access)
│   │   │   └── session.py       # Multi-turn session with structured context
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

1. **True MCP Client–Server–Tool Separation**: The MCP server runs as a standalone subprocess (via FastMCP) and communicates with the host application through stdio transport using JSON-RPC 2.0. The MCP client discovers tools dynamically via the `tools/list` protocol method — tool definitions are never hardcoded in the agent.

2. **Protocol-Driven Tool Execution**: All tool calls flow through the MCP protocol: `Agent → MCPClient.call_tool() → [tools/call JSON-RPC] → MCP Server → ToolHandler`. The agent has no direct access to the database or tool handlers.

3. **Agentic Loop with Dynamic Tool Discovery**: The LLM agent runs in a loop where it first discovers available tools from the MCP server, then the LLM decides which tools to call based on user intent. Multiple tools can be chained in a single turn (e.g., check availability → book → notify).

4. **Structured Multi-Turn Sessions**: Sessions persist not just message history but also structured context: entities mentioned (doctors, dates), action history (tools called per turn), and turn counters. This enables the agent to resolve references across conversation turns.

5. **Dual Notification Channels**: Email (SMTP) is used for patient appointment confirmations (Scenario 1), while Slack webhooks + in-app notifications are used for doctor reports (Scenario 2), as required.

6. **Graceful Degradation**: All external services (Google Calendar, Email, Slack) fall back to demo mode when credentials aren't configured, so the core functionality works without external API setup.

7. **Async Everything**: The entire backend is async (FastAPI + asyncpg + aiosmtplib) for high concurrency and non-blocking I/O.

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
| MCP Architecture | True Host–Client–Server with FastMCP, stdio transport, dynamic tool discovery via protocol |
| Client–Server–Tool Separation | MCPClient (protocol), MCP Server (subprocess), ToolHandlers (execution) — three distinct layers |
| Dynamic Tool Discovery | Agent calls `tools/list` at runtime — schemas NOT hardcoded in agent code |
| Protocol-Driven Execution | All tool calls route through `MCPClient.call_tool()` → JSON-RPC → MCP Server |
| Multi-Tool Chaining | Agent loop supports chaining: check_availability → book → send_email in one turn |
| Multi-Turn Memory | Structured sessions with entity tracking, action history, turn counting |
| LLM Workflow Orchestration | Agentic loop with multi-step tool calling (check → book → notify) |
| API Integration | Google Calendar, SMTP Email, Slack Webhooks, WebSocket |
| Full-Stack Fluency | React ↔ FastAPI ↔ PostgreSQL with async throughout |
| Code Readability | Modular structure, typed schemas, comprehensive docstrings |
| Scalability | Async architecture, connection pooling, session management |
