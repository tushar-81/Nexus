<p align="center">
  <img src="static/nexus-logo.svg" alt="Nexus logo" width="120">
</p>

<h1 align="center">Nexus</h1>

<p align="center">
  A real-time collaborative AI workspace where teams brainstorm together and summon an AI assistant on demand.<br>
  Multiple users share a live chat room — the AI only activates when someone types <code>@AI</code>.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-WebSockets-009688" alt="FastAPI">
  <img src="https://img.shields.io/badge/LangGraph-multi--agent-purple" alt="LangGraph">
</p>

---

## Architecture

![Nexus Architecture](output.png)

---

## Project Demo

[![Watch the Nexus demo](https://img.youtube.com/vi/wNY4m6hDNo4/maxresdefault.jpg)](https://youtu.be/wNY4m6hDNo4)

---
## What it does

Nexus is a multi-user WebSocket chat application backed by a LangGraph multi-agent system. Teams can discuss ideas freely, and when they are ready, any user can trigger the AI with `@AI` to perform tasks like drafting emails, scheduling meetings, generating insight reports, searching the web, or creating Trello boards — all without leaving the conversation.

Every action that involves real-world consequences (sending an email, creating a calendar event, pushing to Trello) requires **human approval** before it executes. All connected users must vote to approve before the action proceeds.

---

## Agents

| Agent | Trigger | What it does |
|---|---|---|
| **Orchestrator** | Every `@AI` message | Reads intent, selects the right agent, writes a detailed instruction |
| **Email Agent** | `@AI` + email intent | Drafts a professional email, shows it for review before sending |
| **Meet Scheduler** | `@AI` + meeting intent | Extracts meeting details, creates Google Calendar event with Meet link |
| **Task Assign Agent** | `@AI` + project/task intent | Breaks project into tasks, assigns to team members, creates Trello board |
| **PDF / Report Agent** | `@AI` + report intent | Analyses conversation, generates a visual PDF insight report |
| **Search Agent** | `@AI` + search intent | Searches the web using DuckDuckGo, ranks results with BM25 + embeddings |
| **General Agent** | Everything else | Handles general questions and conversation |

---

## Human-in-the-Loop (HITL)

Three agents pause for human review before taking action:

- **Email Review** — shows a Gmail-style draft with editable From, To, CC, Subject, and Body fields
- **Meeting Review** — shows scheduled meeting details and the Google Meet link
- **Trello Board Review** — shows an interactive Kanban board with editable cards and checklists

All users in the room must vote **Approve** before the action proceeds. A single **Reject** vote immediately sends it back for regeneration with feedback.

---

## Project Structure

```
Nexus/
├── backend/
│   ├── main.py                   # FastAPI app + WebSocket handler
│   ├── Graph.py                  # LangGraph graph definition
│   ├── condition_edge.py         # Pass_AI router + orchestrator router
│   ├── render_charts.py          # Chart rendering + HTML → PDF (wkhtmltopdf)
│   └── Agents/
│       ├── Common_State.py       # Shared TypedDict state
│       ├── Orchestrator_Agent.py
│       ├── Email_agent.py
│       ├── Meet_scheduler_agent.py
│       ├── Assign_task.py
│       ├── PDF_create.py
│       ├── Search_Agent.py
│       └── general_agent.py
├── frontend/
│   └── nexus.html                # Single-file frontend
├── static/
│   ├── nexus-logo.svg            # App logo + favicon
│   └── nexus-letterhead.svg      # Source for pdf_image.png
├── pdf_image.png                 # PDF report letterhead (footer wave + badge)
├── Helvetica.ttf                 # Font embedded in generated reports
├── output.png                    # Architecture diagram
├── .env.example                  # Template for API keys
└── requirements.txt
```

Created at runtime (git-ignored): `.env`, `credentials.json`, `token.json`, `checkpoints.db*`, `PDF/report.pdf`.

---

## Setup

### Prerequisites

- **Python 3.12+**
- **[wkhtmltopdf](https://wkhtmltopdf.org/downloads.html)**, which the PDF report agent needs. Install it and either add it to `PATH` or set `WKHTMLTOPDF_PATH` in `.env`.
- **Google Chrome**, which the search agent uses through Selenium to fetch pages that block plain HTTP requests.
- API access for **OpenAI**, **Trello**, **Gmail** (app password) and **Google Calendar** (OAuth client).

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/tushar-81/Nexus.git
cd Nexus
python -m venv venv
venv\Scripts\activate         # Windows
source venv/bin/activate      # Mac/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the template and fill in your keys:

```bash
cp .env.example .env          # Windows: copy .env.example .env
```

```env
OPENAI_API_KEY=sk-...
TRELLO_API=your_trello_api_key
TRELLO_TOKEN=your_trello_token
GOOGLE_MAIL=your_gmail_app_password
# WKHTMLTOPDF_PATH=C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe   (optional)
```

### 4. Google Calendar setup

1. In [Google Cloud Console](https://console.cloud.google.com/), enable the **Google Calendar API**.
2. Create an **OAuth client ID** of type *Desktop app* and download the JSON.
3. Save it as `credentials.json` in the project root.

On the first meeting request, a browser window opens for OAuth consent. After that, `token.json` is created and reused automatically.

> `.env`, `credentials.json` and `token.json` contain secrets. They are git-ignored, so never commit them.

### 5. Run

Run this from the project root, because paths like `static/`, `pdf_image.png` and `checkpoints.db` are resolved relative to it:

```bash
uvicorn backend.main:app --reload
```

Open `http://localhost:8000` in your browser. To try multi-user collaboration, open it in a second tab or on another device on your network (use `--host 0.0.0.0`).

---

## Usage

### Joining a room

Open the app, enter your name and a Room ID. Share the same Room ID with teammates — everyone who joins the same room shares one conversation and one LangGraph state.

### Chatting

Type normally to send messages to the room. All messages are visible to everyone and stored in the AI's memory.

### Triggering the AI

Include `@AI` anywhere in your message:

```
@AI write an email to the team about tomorrow's standup
@AI schedule a 1 hour meeting tomorrow at 3pm
@AI what are the latest trends in AI tooling
@AI create a trello board for our new mobile app project
@AI generate an insight report from our discussion
```

### Approving HITL actions

When the AI needs your sign-off, an overlay appears for all users in the room. Everyone must click **Approve** for the action to proceed. Any user can **Reject** with feedback to regenerate.

### Agent progress tracker

While the AI is working, the sidebar shows a live step-by-step progress tracker:

```
PROGRESS
● Orchestrator      ✓
● Email Agent       ✓
● Email Review      ⏸
```

---

## Key Design Decisions

**Shared LangGraph state** — all users write to the same `thread_id` in the checkpointer. Plain chat messages are stored via `update_state()` without triggering the graph, giving the AI full conversation context when `@AI` is called.

**Conditional graph entry** — `Pass_AI` is the first conditional edge. If the message contains `@AI` it routes to the Orchestrator. Otherwise the graph goes directly to `END` — no agent runs, the message is just stored.

**HITL voting** — the `WebSocket_Manager` tracks votes per interrupt. The graph only resumes via `Command(resume=...)` once all users approve, or immediately if anyone rejects.

**Agent streaming** — the server uses `graph.astream(stream_mode="updates")` so each node completion is broadcast to the frontend in real time as it happens.

---

## Environment Variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key for all LLM calls |
| `TRELLO_API` | Trello API key |
| `TRELLO_TOKEN` | Trello OAuth token |
| `GOOGLE_MAIL` | Gmail app password for sending email |
| `WKHTMLTOPDF_PATH` | *(optional)* Path to `wkhtmltopdf` if it is not on `PATH` |

---

## Dependencies

| Package | Purpose |
|---|---|
| `fastapi` + `uvicorn` | WebSocket server |
| `langgraph` | Multi-agent graph runtime |
| `langchain-openai` | LLM calls |
| `langgraph-checkpoint-sqlite` | Conversation memory persistence |
| `google-api-python-client` | Google Calendar integration |
| `trafilatura` + `selenium` | Web content extraction |
| `rank-bm25` | Keyword-based search ranking |
| `ddgs` | DuckDuckGo search |
| `scikit-learn` | Semantic similarity scoring |
| `pdfkit` + `matplotlib` | PDF insight reports with charts |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `OSError: No wkhtmltopdf executable found` | Install wkhtmltopdf and add it to `PATH`, or set `WKHTMLTOPDF_PATH` |
| `FileNotFoundError: credentials.json` when scheduling | Complete [Google Calendar setup](#4-google-calendar-setup) |
| Google OAuth `invalid_grant` / expired token | Delete `token.json` and re-authorize |
| Email fails with `SMTPAuthenticationError` | `GOOGLE_MAIL` must be a Gmail **app password**, with 2-Step Verification enabled |
| Want to wipe the AI's conversation memory | Stop the server and delete `checkpoints.db*` |
| `RuntimeError: Directory 'static' does not exist` | Run `uvicorn` from the project root, not from `backend/` |
