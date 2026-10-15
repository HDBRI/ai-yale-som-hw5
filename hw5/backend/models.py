"""Data types shared by the Campus Customs agent team."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
ROLES: tuple[Role, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")


# ---------- structured output every agent returns ----------


class Fact(BaseModel):
    """One shop fact the agent relied on, traced to the MCP tool that returned it."""

    tool: str = Field(description="MCP tool that returned this value, e.g. check_stock")
    field: str = Field(description="Field name in the tool output, e.g. qty_on_hand")
    value: str = Field(description="The value exactly as the tool returned it")


class ApprovalRequest(BaseModel):
    """Something only a human may approve. Agents prepare these; the dashboard's
    approve route (backend/main.py) is the only thing that acts on them."""

    kind: Literal["invoice_payment", "rent_payment", "purchase", "discount", "other"]
    ref_id: int | None = Field(None, description="invoices.id, leases.id or tickets.id")
    amount: float | None = Field(None, description="Dollar amount or discount % being requested")
    reason: str = Field(description="Why this is needed and what happens if it is not approved")


class AgentReport(BaseModel):
    """What an agent hands back to whoever called it (the human or another agent)."""

    agent: Role
    ticket_ids: list[int] = Field(default_factory=list)
    status: Literal["done", "needs_approval", "waiting", "blocked", "escalated"] = Field(
        description="done = handled; needs_approval = waiting on a human sign-off; "
        "waiting = waiting on a customer, vendor or another agent; "
        "blocked = cannot proceed (missing data or a rule stops it); escalated = sent to a human"
    )
    summary: str = Field(description="Two to four plain sentences on what was found and done")
    facts: list[Fact] = Field(default_factory=list, description="Every number used, with its MCP source")
    actions_taken: list[str] = Field(default_factory=list, description="Writes made through MCP tools, if any")
    approvals_needed: list[ApprovalRequest] = Field(default_factory=list)
    customer_message: str | None = Field(None, description="Draft message to the requester, if one is due")
    next_steps: list[str] = Field(default_factory=list)


# ---------- run-time state passed to every agent as deps ----------


@dataclass
class SharedRunState:
    """One object per team run. Every agent in the run holds the same instance."""

    run_id: str
    dry_run: bool = False                             # True blocks every write tool
    delegations: int = 0                              # delegations used so far in this run


@dataclass
class TeamDeps:
    """Per-agent view of the run: who is acting, who asked, and the shared state."""

    shared: SharedRunState
    role: Role = "boss"
    chain: tuple[Role, ...] = ()                      # callers above this agent, e.g. ("boss", "inventory")
    ticket_id: int | None = None

    @property
    def depth(self) -> int:
        return len(self.chain)

    def for_agent(self, role: Role, ticket_id: int | None) -> "TeamDeps":
        return replace(self, role=role, chain=(*self.chain, self.role),
                       ticket_id=ticket_id if ticket_id is not None else self.ticket_id)


# ---------- audit trail ----------


class AuditEntry(BaseModel):
    """One line in output/audit_trail.json. One entry per agent-loop step, tool call,
    or human/API action. `agent` is a role, or "human" / "api" for dashboard actions."""

    ts: str
    run_id: str
    agent: str
    chain: list[str]
    depth: int
    ticket_id: int | None
    step: int | None = None
    event: str  # run_start, user_prompt, model_request, model_response, tool_results,
    #             mcp_tool_call, mcp_tool_blocked, delegation, delegation_refused,
    #             final_output, error, run_end, approval_prepared, human_approved,
    #             human_rejected, human_approval_failed, db_reset
    model: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, int] | None = None


# ---------- approvals queue (agents prepare, a human decides) ----------


class PendingApproval(BaseModel):
    """One item in output/pending_approvals.json, shown on the dashboard with an Approve button."""

    id: str                      # e.g. "rent_payment-1", "invoice_payment-501"
    kind: Literal["invoice_payment", "rent_payment", "purchase", "discount", "other"]
    ref_id: int | None
    amount: float | None
    reason: str
    ticket_id: int | None
    prepared_by: str             # agent role that prepared it
    run_id: str
    created_at: str
    status: Literal["pending", "approved", "rejected", "failed"] = "pending"
    decided_by: str | None = None
    decided_at: str | None = None
    result: dict[str, Any] | None = None
