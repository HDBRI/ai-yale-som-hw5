"""The approvals queue: agents prepare, a human decides.

Every agent run that ends with `approvals_needed` adds those items here
(output/pending_approvals.json). Nothing in this file moves money; the dashboard's
approve route in main.py does that, through the MCP server's record_payment tool.
"""

import json
import threading
from datetime import datetime, timezone

from . import audit
from .config import HW5_DIR
from .models import AgentReport, PendingApproval, TeamDeps

APPROVALS_PATH = HW5_DIR / "output" / "pending_approvals.json"
_lock = threading.Lock()


def load() -> list[PendingApproval]:
    if not APPROVALS_PATH.exists() or not APPROVALS_PATH.stat().st_size:
        return []
    return [PendingApproval(**a) for a in json.loads(APPROVALS_PATH.read_text(encoding="utf-8"))]


def save(items: list[PendingApproval]) -> None:
    APPROVALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    APPROVALS_PATH.write_text(json.dumps([a.model_dump() for a in items], indent=2), encoding="utf-8")


def prepare(report: AgentReport, deps: TeamDeps) -> None:
    """Queue each approval an agent asked for. One pending item per bill: if the same
    bill is already pending, the newer request replaces it."""
    if not report.approvals_needed:
        return
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _lock:
        items = load()
        for req in report.approvals_needed:
            item_id = f"{req.kind}-{req.ref_id if req.ref_id is not None else deps.ticket_id}"
            items = [a for a in items if not (a.id == item_id and a.status == "pending")]
            items.append(PendingApproval(
                id=item_id, kind=req.kind, ref_id=req.ref_id, amount=req.amount,
                reason=req.reason, ticket_id=deps.ticket_id, prepared_by=deps.role,
                run_id=deps.shared.run_id, created_at=now,
            ))
            audit.record(deps, "approval_prepared", req.model_dump())
        save(items)


def attach_to_owning_tickets(tickets: list[dict]) -> None:
    """A bill belongs to the ticket that references it: rent for lease N goes to the ticket
    with lease_id N, invoice N to the ticket with invoice_id N. Agents working one ticket
    often prepare a competing bill too (both draw on the same cash), so this keeps each
    payment, and its cash change, on the right ticket."""
    by_lease = {t["lease_id"]: t["id"] for t in tickets if t.get("lease_id") is not None}
    by_invoice = {t["invoice_id"]: t["id"] for t in tickets if t.get("invoice_id") is not None}
    with _lock:
        items = load()
        changed = False
        for a in items:
            owner = (by_lease.get(a.ref_id) if a.kind == "rent_payment"
                     else by_invoice.get(a.ref_id) if a.kind == "invoice_payment" else None)
            if a.status == "pending" and owner is not None and owner != a.ticket_id:
                a.ticket_id, changed = owner, True
        if changed:
            save(items)


def get(item_id: str) -> PendingApproval | None:
    """The pending item with this id if there is one (the same bill can be raised again
    after an earlier decision), otherwise the most recent one."""
    matches = [a for a in load() if a.id == item_id]
    return next((a for a in matches if a.status == "pending"), matches[-1] if matches else None)


def decide(item_id: str, status: str, decided_by: str, result: dict | None) -> PendingApproval:
    with _lock:
        items = load()
        for a in items:
            if a.id == item_id and a.status == "pending":
                a.status = status
                a.decided_by = decided_by
                a.decided_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
                a.result = result
                save(items)
                return a
    raise KeyError(item_id)


def clear() -> None:
    with _lock:
        save([])
