# HW5: Campus Customs agent team + Night Desk dashboard

Five PydanticAI agents (Boss, Inventory, Accounting, Facilities, Customer Service) work the shop's open tickets. They get every shop fact from a FastMCP server over SQLite, prepare payments for a human to approve, and are run and watched from a React "Night Desk" board.

- **Model:** `gpt-5.6-luna` via Portkey
- **Backend:** FastAPI
- **Frontend:** React + Vite + TypeScript

| Folder / file | What it is |
|---|---|
| `data/campus_customs.db` | Original database. **Never modified.** |
| `data/campus_customs_new.db` | Working copy that the MCP tools read and write. Committed in its state after the Task 9 run (checking $1,000, all tickets resolved). |
| `mcp_server/server.py` | FastMCP server: 14 tools (11 read, 3 write). See `mcp_server/README.md`. |
| `backend/` | Agents (`agents/`, one file per role), prompts (`prompts/*.md`), data types (`models.py`), the MCP gate (`mcp_client.py`), FastAPI routes (`main.py`). |
| `frontend/` | The React Night Desk board. |
| `output/` | Harness, MCP smoke test, ticket plan vs actual + cash + reflection (`desk_tickets.html`), design notes, resolved tickets, board screenshots (`board_screens/`), audit trail, the approvals queue (`pending_approvals.json`), GitHub URL. |
| `AI_prompts.md` | Every prompt used to build this, task by task. |

## Setup (once)

Requires Python 3.11+ and Node 20+.

```bash
python -m venv .venv
```

Activate it: Windows `.venv\Scripts\activate`, macOS/Linux `source .venv/bin/activate`.

```bash
pip install -r requirements.txt
```

Then add your API key:

```bash
cp .env.example .env
```

Put your `PORTKEY_API_KEY` in `.env`. It is git-ignored; never commit it.

```bash
cd frontend
npm install
cd ..
```

## 1. Start from a clean database (copy the original over the working copy)

`data/campus_customs_new.db` is the copy the agents change. For a clean run, overwrite it with the original:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

On Windows PowerShell: `Copy-Item data\campus_customs.db data\campus_customs_new.db -Force`. Once the backend is running you can also reset from the board (**↺ Fresh shift**) or with `POST http://localhost:8000/api/reset`, which does the same copy and also clears the approvals queue.

## 2. The MCP server

```bash
python mcp_server/server.py
```

That command starts it on stdio, which is useful for testing it alone. You **don't** need to start it separately for the app: the backend launches it as a subprocess, with the same Python, when it starts. To use the tools from Claude Code, open this folder with the venv activated; `.mcp.json` registers `campus-customs` → `python mcp_server/server.py`.

## 3. Start the FastAPI backend (http://localhost:8000)

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Interactive API docs are at http://localhost:8000/docs. The main routes:

| Route | What it does |
|---|---|
| `GET /api/tickets` | Every ticket, marked open or resolved |
| `POST /api/tickets/{id}/run` | Runs the agent team on that ticket |
| `GET /api/events` | What each agent said and which tools it used |
| `GET /api/approvals` | Payments, purchases and discounts the agents prepared |
| `POST /api/approvals/{id}/approve` | The human's Approve click: the only thing that changes cash |
| `GET /api/cash` | Checking balance |
| `POST /api/reset` | Restore the working database from the original |

The full list is in `output/harness.md`.

> Don't edit backend files while a ticket is running: `--reload` restarts the server and the run is lost.

## 4. Start the React board (http://localhost:5173)

In a second terminal:

```bash
cd frontend
npm run dev
```

The board opens in your browser and calls the backend at http://localhost:8000. To change that, copy `frontend/.env.example` to `frontend/.env`.

## 5. A full three-ticket run

1. **Reset first:** click **↺ Fresh shift**, or run `POST /api/reset`. Checking goes back to **$3,400.00** and tickets 101–103 reopen.
2. On the board, pick **#101** and click **Wake the team ✦**. Watch the desks and the live feed. When the run ends, the ticket is resolved, or *waiting* if agents prepared something that needs a signature.
3. Type your name under **Signing as**, then **Approve** or **Decline** each cheque in the sign-off tray. An approved payment rolls the cash register down.
4. Repeat for **#102** and **#103**.

What happened in our run (checking **$3,400 → $1,000**: rent of $2,400 paid on 102, nothing else moved) is documented in `output/desk_tickets.html` (Actual, Cash and Reflection tabs), `output/resolved_tickets.json`, `output/resolved_board.html` and `output/audit_trail.json`. The audit trail is append-only, so new runs add to it. Entries before the `db_reset` at 2026-10-14T21:44:12Z are setup tests (route tests, an early 102 run and a run killed by a server reload); the graded run comes after it.

There is also a command-line runner: `python -m backend.run --ticket 101`, with `--dry-run` to block every write.

## Safety, in one paragraph

- **No agent can pay.** Agents prepare payments, and only the human Approve route calls MCP `record_payment`, which re-checks the exact amount, the balance and double payment.
- **Least privilege.** Each agent sees only its own MCP tools.
- **Limits.** Team-wide caps of 30 model requests, 60 tool calls and 250k tokens per ticket, with delegation depth 3 and at most 8 hand-offs.
- **Full audit.** Every agent step, tool call, block, delegation and human decision is written to `output/audit_trail.json`.

Details: `output/harness.md`.
