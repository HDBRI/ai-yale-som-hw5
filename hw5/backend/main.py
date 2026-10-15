"""FastAPI backend for the Campus Customs dashboard.

Start it from the backend/ folder:

    uvicorn main:app --reload --port 8000

Shop facts and every change to the shop database go through the MCP server
(mcp_server/server.py), the same tool layer the agents use. The only exception is
POST /api/reset, an admin action that restores the working copy from the original file.
"""

import asyncio
import sqlite3
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# `uvicorn main:app` runs this file as a top-level module; make the backend package importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import approvals, audit  # noqa: E402
from backend.config import HW5_DIR, MODEL_NAME  # noqa: E402
from backend.mcp_client import SHOP_MCP  # noqa: E402
from backend.models import ROLES  # noqa: E402
from backend.team import new_run_id, run_ticket  # noqa: E402

ORIGINAL_DB = HW5_DIR / "data" / "campus_customs.db"
WORKING_DB = HW5_DIR / "data" / "campus_customs_new.db"
PAYMENT_KINDS = {"invoice_payment": "invoice", "rent_payment": "rent"}

runs: dict[str, dict[str, Any]] = {}          # run_id -> {ticket_id, status, report}
running_tickets: set[int] = set()             # one team run per ticket at a time


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with SHOP_MCP:                       # one MCP connection for the server's lifetime
        yield


app = FastAPI(title="Campus Customs agent backend", lifespan=lifespan)
FRONTEND_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]  # the Vite dev page

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",  # any other local port
    allow_methods=["*"],
    allow_headers=["*"],
)


async def mcp(tool: str, args: dict[str, Any] | None = None) -> Any:
    return await SHOP_MCP.direct_call_tool(tool, args or {})


def pending_for(ticket_id: int) -> list[str]:
    return [a.id for a in approvals.load() if a.ticket_id == ticket_id and a.status == "pending"]


async def settle_ticket(ticket_id: int, note: str, author: str) -> str:
    """Desk rule: a ticket is resolved once the team has finished AND nothing is waiting on a
    human. If approvals are still pending, it stays 'waiting' until the last one is decided."""
    waiting_on = pending_for(ticket_id)
    status = "waiting" if waiting_on else "resolved"
    if waiting_on:
        note = f"{note} Waiting on human approval: {', '.join(waiting_on)}."
    await mcp("update_ticket", {"ticket_id": ticket_id, "status": status, "note": note, "author": author})
    return status


# ---------- health ----------


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "model": MODEL_NAME, "running_tickets": sorted(running_tickets)}


# ---------- tickets ----------


@app.get("/api/tickets")
async def list_tickets() -> dict:
    """All tickets, each marked open or resolved (plus the detailed status the agents set)."""
    data = await mcp("list_tickets")
    tickets = [
        {**t, "state": "resolved" if t["status"] == "resolved" else "open",
         "running": t["id"] in running_tickets}
        for t in data["tickets"]
    ]
    return {"date_today": data["date_today"], "tickets": tickets}


class RunRequest(BaseModel):
    dry_run: bool = False


@app.post("/api/tickets/{ticket_id}/run")
async def run_team(ticket_id: int, body: RunRequest | None = None,
                   wait: bool = Query(True, description="false = start in the background and poll /api/runs/{run_id}")) -> dict:
    """Run the agent team (Boss first) on one ticket."""
    body = body or RunRequest()
    ticket = await mcp("get_ticket", {"ticket_id": ticket_id})
    if not ticket.get("found"):
        raise HTTPException(404, f"No ticket {ticket_id}")
    if ticket_id in running_tickets:
        raise HTTPException(409, f"The team is already working on ticket {ticket_id}")

    run_id = new_run_id()
    runs[run_id] = {"run_id": run_id, "ticket_id": ticket_id, "status": "running", "report": None}
    running_tickets.add(ticket_id)

    async def work() -> None:
        try:
            _, report = await run_ticket(ticket_id, dry_run=body.dry_run, run_id=run_id)
            approvals.attach_to_owning_tickets((await mcp("list_tickets"))["tickets"])
            ticket_status = None
            if report.status != "blocked" and not body.dry_run:
                ticket_status = await settle_ticket(
                    ticket_id, f"Team run {run_id} finished ({report.status}).", "desk")
            runs[run_id].update(status="finished", report=report.model_dump(),
                                ticket_status=ticket_status)
        except Exception as exc:  # noqa: BLE001
            runs[run_id].update(status="failed", error=f"{type(exc).__name__}: {exc}")
        finally:
            running_tickets.discard(ticket_id)

    if wait:
        await work()
    else:
        asyncio.create_task(work())
    return runs[run_id]


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    if run_id not in runs:
        raise HTTPException(404, f"No run {run_id} since the server started")
    return runs[run_id]


# ---------- agent events ----------


def _simplify(e: dict[str, Any]) -> dict[str, Any]:
    """Turn one audit entry into what the board shows: who, what they said, which tools."""
    d = e.get("details") or {}
    said, tools = None, []
    ev = e["event"]
    if ev == "model_response":
        parts = d.get("parts", [])
        said = "\n".join(p["text"] for p in parts if "text" in p) or None
        tools = [p["tool_call"] for p in parts if "tool_call" in p and p["tool_call"] != "final_result"]
    elif ev in ("mcp_tool_call", "mcp_tool_blocked"):
        tools = [d.get("tool")]
        said = d.get("reason") if ev == "mcp_tool_blocked" else None
    elif ev in ("delegation", "delegation_refused"):
        tools = ["delegate"]
        said = f"→ {d.get('to')}: {d.get('task')}" + (f" (refused: {d['reason']})" if ev == "delegation_refused" else "")
    elif ev == "final_output":
        said = (d.get("output") or {}).get("summary")
    elif ev in ("run_end", "error"):
        said = d.get("summary") or d.get("message")
    elif ev in ("run_start", "user_prompt"):
        said = d.get("prompt")
    elif ev.startswith("human_") or ev in ("approval_prepared", "db_reset"):
        said = d.get("summary") or d.get("reason")
    return {
        "ts": e["ts"], "run_id": e["run_id"], "ticket_id": e.get("ticket_id"),
        "agent": e["agent"], "chain": e.get("chain", []), "step": e.get("step"),
        "event": ev, "said": said, "tools": tools,
        "args": d.get("args"), "result": d.get("result"),
        "status": d.get("status") or (d.get("output") or {}).get("status"),
    }


@app.get("/api/events")
async def events(limit: int = Query(50, ge=1, le=500), ticket_id: int | None = None,
                 run_id: str | None = None, after: str | None = Query(None, description="only events with ts > this")) -> dict:
    """Recent agent events, newest first: what each agent said and which tools it used."""
    entries = audit.read_all()
    if ticket_id is not None:
        entries = [e for e in entries if e.get("ticket_id") == ticket_id]
    if run_id:
        entries = [e for e in entries if e["run_id"] == run_id]
    if after:
        entries = [e for e in entries if e["ts"] > after]
    entries = [e for e in entries if e["event"] not in ("model_request", "tool_results", "ticket_run_start")]
    recent = [_simplify(e) for e in entries[-limit:]][::-1]
    return {"count": len(recent), "events": recent}


@app.get("/api/tickets/{ticket_id}/summary")
async def ticket_summary(ticket_id: int, run_id: str | None = None) -> dict:
    """What each agent did on this ticket's latest run (or the run given): its final status
    and summary, the MCP tools it called, and who it delegated to. Also returns the Boss's
    full report (customer message, approvals, facts)."""
    entries = [e for e in audit.read_all() if e.get("ticket_id") == ticket_id]
    agent_runs = [e for e in entries if e["agent"] in ROLES]
    if not run_id:
        starts = [e["run_id"] for e in agent_runs if e["event"] == "run_start" and e["depth"] == 0]
        run_id = starts[-1] if starts else None
    if not run_id:
        return {"ticket_id": ticket_id, "run_id": None, "agents": [], "boss_report": None}

    agents: dict[str, dict[str, Any]] = {}
    boss_report = None
    for e in (x for x in agent_runs if x["run_id"] == run_id):
        a = agents.setdefault(e["agent"], {"agent": e["agent"], "status": None, "summary": None,
                                           "tools": [], "delegated_to": [], "blocked": [], "first_ts": e["ts"]})
        d = e.get("details") or {}
        if e["event"] == "mcp_tool_call":
            a["tools"].append(d.get("tool"))
        elif e["event"] == "mcp_tool_blocked":
            a["blocked"].append(d.get("tool"))
        elif e["event"] == "delegation":
            a["delegated_to"].append(d.get("to"))
        elif e["event"] == "final_output":
            out = d.get("output") or {}
            a["status"], a["summary"] = out.get("status"), out.get("summary")
            if e["agent"] == "boss" and e["depth"] == 0:
                boss_report = out
    ordered = sorted(agents.values(), key=lambda a: a["first_ts"])
    return {"ticket_id": ticket_id, "run_id": run_id, "agents": ordered, "boss_report": boss_report}


# ---------- approvals (agents prepare, a human approves) ----------


@app.get("/api/approvals")
async def list_approvals(status: str | None = Query("pending", description="pending | approved | rejected | failed | all")) -> dict:
    items = approvals.load()
    if status and status != "all":
        items = [a for a in items if a.status == status]
    return {"approvals": [a.model_dump() for a in items]}


class Decision(BaseModel):
    decided_by: str = Field(min_length=1, description="Name of the human clicking the button")
    note: str | None = None


@app.post("/api/approvals/{approval_id}/approve")
async def approve(approval_id: str, body: Decision) -> dict:
    """The human's Approve click. For a payment this is the ONLY code path that changes cash:
    it calls the MCP record_payment tool, which re-checks the amount, balance and double payment."""
    item = approvals.get(approval_id)
    if item is None or item.status != "pending":
        raise HTTPException(404, f"No pending approval '{approval_id}'")
    who = body.decided_by.strip()

    result: dict[str, Any]
    if item.kind in PAYMENT_KINDS:
        result = await mcp("record_payment", {
            "kind": PAYMENT_KINDS[item.kind], "ref_id": item.ref_id, "amount": item.amount,
            "account": "checking", "approved_by": who,
        })
        if not result.get("ok"):
            approvals.decide(approval_id, "failed", who, result)
            audit.record_action(f"human:{who}", "human_approval_failed",
                                {"approval_id": approval_id, "summary": "Payment refused by the MCP tool",
                                 "result": result}, ticket_id=item.ticket_id)
            raise HTTPException(409, {"error": result.get("error"), "approval_id": approval_id})
        summary = (f"{who} approved {item.kind.replace('_', ' ')} {item.ref_id}: paid "
                   f"${result['amount']:,.2f} from checking, ${result['balance_after']:,.2f} left.")
    else:
        result = {"ok": True, "note": "Approved; no cash moves for this kind."}
        summary = f"{who} approved {item.kind} {item.ref_id}" + (f": {body.note}" if body.note else ".")

    decided = approvals.decide(approval_id, "approved", who, result)
    ticket_status = None
    if item.ticket_id is not None:
        ticket_status = await settle_ticket(item.ticket_id, summary, f"human: {who}")
    audit.record_action(f"human:{who}", "human_approved",
                        {"approval_id": approval_id, "summary": summary, "result": result},
                        ticket_id=item.ticket_id)
    return {"approval": decided.model_dump(), "summary": summary, "ticket_status": ticket_status}


@app.post("/api/approvals/{approval_id}/reject")
async def reject(approval_id: str, body: Decision) -> dict:
    item = approvals.get(approval_id)
    if item is None or item.status != "pending":
        raise HTTPException(404, f"No pending approval '{approval_id}'")
    who = body.decided_by.strip()
    summary = f"{who} rejected {item.kind} {item.ref_id}" + (f": {body.note}" if body.note else ".")
    decided = approvals.decide(approval_id, "rejected", who, {"note": body.note})
    ticket_status = None
    if item.ticket_id is not None:
        ticket_status = await settle_ticket(item.ticket_id, summary, f"human: {who}")
    audit.record_action(f"human:{who}", "human_rejected",
                        {"approval_id": approval_id, "summary": summary}, ticket_id=item.ticket_id)
    return {"approval": decided.model_dump(), "summary": summary, "ticket_status": ticket_status}


# ---------- cash ----------


@app.get("/api/cash")
async def cash() -> dict:
    """Current checking balance from cash_accounts (via the MCP server)."""
    pos = await mcp("get_cash_position")
    checking = next((a for a in pos["accounts"] if a["name"] == "checking"), None)
    if checking is None:
        raise HTTPException(404, "No checking account in cash_accounts")
    return {"account": "checking", "balance": checking["balance"], "as_of": checking["as_of"],
            "date_today": pos["date_today"]}


# ---------- reset ----------


@app.post("/api/reset")
async def reset() -> dict:
    """Restore data/campus_customs_new.db from the untouched original and clear the
    approvals queue. The audit trail is kept (a db_reset entry is added)."""
    if running_tickets:
        raise HTTPException(409, f"Agents are still running on {sorted(running_tickets)}")
    src = sqlite3.connect(f"file:{ORIGINAL_DB}?mode=ro", uri=True)
    dst = sqlite3.connect(WORKING_DB)
    try:
        src.backup(dst)          # copies every page, safe even if another connection is open
    finally:
        src.close()
        dst.close()
    approvals.clear()
    audit.record_action("api", "db_reset", {"summary": f"{WORKING_DB.name} restored from {ORIGINAL_DB.name}"})
    data = await mcp("list_tickets")
    return {"ok": True, "restored_from": ORIGINAL_DB.name,
            "tickets": [{"id": t["id"], "status": t["status"]} for t in data["tickets"]],
            "checking": (await cash())["balance"]}
