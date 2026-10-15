"""Entry point for one team run on one ticket, shared by the CLI (run.py) and the API (main.py)."""

import uuid

from . import audit
from .agents.base import run_agent
from .models import AgentReport, SharedRunState, TeamDeps


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


async def run_ticket(ticket_id: int, *, dry_run: bool = False, entry: str = "api",
                     run_id: str | None = None) -> tuple[str, AgentReport]:
    """Start a Boss run on one ticket. The MCP connection (SHOP_MCP) must already be open."""
    shared = SharedRunState(run_id=run_id or new_run_id(), dry_run=dry_run)
    deps = TeamDeps(shared=shared, role="boss", ticket_id=ticket_id)
    audit.record(deps, "ticket_run_start", {"entry": entry, "ticket_id": ticket_id, "dry_run": dry_run})
    report = await run_agent(
        "boss",
        f"Work ticket {ticket_id}. Read it, get every fact you need from the right teammates, "
        "take the actions policy allows, prepare any payment for human approval, and report back.",
        deps,
    )
    return shared.run_id, report
