"""Shared pieces for all five agents: how an agent is built, how it delegates,
and the agent loop that writes every step to the audit trail."""

from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import (
    RetryPromptPart, TextPart, ThinkingPart, ToolCallPart, ToolReturnPart, UserPromptPart,
)
from pydantic_ai.usage import RunUsage

from .. import approvals, audit
from ..config import (
    AGENT_RETRIES, MAX_DELEGATION_DEPTH, MAX_DELEGATIONS_PER_RUN, MODEL_SETTINGS,
    PROMPTS_DIR, TEAM_LIMITS, build_model,
)
from ..mcp_client import SHOP_MCP, toolset_for
from ..models import ROLES, AgentReport, Role, TeamDeps

ROLE_DESCRIPTIONS: dict[Role, str] = {
    "boss": "triages tickets, splits work, resolves conflicts between teams, decides what goes to a human",
    "inventory": "stock levels by SKU/size, shortfalls, reprints and restocks, vendor lead times, stock adjustments",
    "accounting": "cash, invoices, rent, preparing payments for human approval, price floors and discount math",
    "facilities": "the shop lease, rent notices from the landlord, the physical space",
    "customer_service": "replies to customers and student groups, order options, quotes within discount policy",
}


# ---------- delegation: any agent can hand work to any other agent ----------


async def delegate(ctx: RunContext[TeamDeps], to: Role, task: str,
                   ticket_id: int | None = None) -> dict[str, Any]:
    """Hand a sub-task to a teammate and get their AgentReport back.

    to: boss | inventory | accounting | facilities | customer_service
    task: a specific, self-contained request including the SKU, size, qty, invoice id or
          lease id they need, and what you want back. They cannot see your conversation.
    ticket_id: the ticket this is for, if any.
    """
    deps = ctx.deps
    shared = deps.shared
    reason = None
    if to not in ROLES:
        reason = f"Unknown teammate '{to}'."
    elif to == deps.role:
        reason = "You cannot delegate to yourself."
    elif to in deps.chain:
        reason = (f"{to} is already above you in this chain ({' -> '.join(deps.chain)}); "
                  "answer with what you have instead of sending it back.")
    elif deps.depth + 1 > MAX_DELEGATION_DEPTH:
        reason = f"Delegation depth limit ({MAX_DELEGATION_DEPTH}) reached; finish the task yourself."
    elif shared.delegations >= MAX_DELEGATIONS_PER_RUN:
        reason = f"This run has used all {MAX_DELEGATIONS_PER_RUN} delegations; finish with what you have."
    if reason:
        audit.record(deps, "delegation_refused", {"to": to, "task": task, "reason": reason},
                     usage=ctx.usage)
        return {"delegated": False, "error": reason}

    shared.delegations += 1
    child = deps.for_agent(to, ticket_id)
    audit.record(deps, "delegation", {"to": to, "task": task, "ticket_id": child.ticket_id,
                                      "delegations_used": shared.delegations}, usage=ctx.usage)
    report = await run_agent(to, task, child, usage=ctx.usage)
    return {"delegated": True, "report": report.model_dump()}


# ---------- building an agent ----------


def build_agent(role: Role) -> Agent[TeamDeps, AgentReport]:
    agent = Agent(
        build_model(),
        name=role,
        deps_type=TeamDeps,
        output_type=AgentReport,
        instructions=(PROMPTS_DIR / f"{role}.md").read_text(encoding="utf-8"),
        toolsets=[toolset_for(role, SHOP_MCP)],
        tools=[delegate],
        retries=AGENT_RETRIES,
        model_settings=MODEL_SETTINGS,
    )

    @agent.instructions
    def run_context(ctx: RunContext[TeamDeps]) -> str:
        d = ctx.deps
        s = d.shared
        caller = d.chain[-1] if d.chain else "the human shop owner"
        others = [r for r in ROLES if r != d.role and r not in d.chain]
        team = "\n".join(f"- {r}: {desc}" for r, desc in ROLE_DESCRIPTIONS.items() if r != d.role)
        return (
            "## This run\n"
            f"- You are the **{d.role}** agent. Requested by: {caller}.\n"
            f"- Ticket in focus: {d.ticket_id if d.ticket_id is not None else 'none given'}\n"
            f"- Chain so far: {' -> '.join((*d.chain, d.role))}\n"
            f"- You may delegate to: {', '.join(others) or 'nobody (answer yourself)'}; "
            f"{MAX_DELEGATIONS_PER_RUN - s.delegations} delegations left in this run, "
            f"depth {d.depth}/{MAX_DELEGATION_DEPTH}.\n"
            f"- Dry run (no writes allowed): {'YES' if s.dry_run else 'no'}\n"
            "- Payments: no agent can pay. Prepare each payment under `approvals_needed` with "
            "the exact amount; a human approves it on the dashboard.\n\n"
            f"## Your teammates\n{team}\n\n"
            "Set `agent` in your report to your own role."
        )

    return agent


# ---------- the agent loop, with one audit entry per step ----------


def _describe_node(node: Any) -> tuple[str, dict[str, Any]] | None:
    if Agent.is_user_prompt_node(node):
        return "user_prompt", {"prompt": node.user_prompt}
    if Agent.is_model_request_node(node):
        parts = []
        for p in node.request.parts:
            if isinstance(p, ToolReturnPart):
                parts.append({"tool_return": p.tool_name, "call_id": p.tool_call_id,
                              "content": p.content})
            elif isinstance(p, RetryPromptPart):
                parts.append({"retry": p.tool_name, "content": p.content})
            elif isinstance(p, UserPromptPart):
                parts.append({"user_prompt": p.content})
        has_results = any("tool_return" in p or "retry" in p for p in parts)
        return ("tool_results" if has_results else "model_request"), {"parts": parts}
    if Agent.is_call_tools_node(node):
        parts = []
        for p in node.model_response.parts:
            if isinstance(p, ToolCallPart):
                parts.append({"tool_call": p.tool_name, "call_id": p.tool_call_id,
                              "args": p.args_as_dict()})
            elif isinstance(p, TextPart):
                parts.append({"text": p.content})
            elif isinstance(p, ThinkingPart):
                parts.append({"thinking_chars": len(p.content or "")})
        return "model_response", {"parts": parts,
                                  "finish_reason": node.model_response.finish_reason}
    if Agent.is_end_node(node):
        return "final_output", {"output": node.data.output.model_dump()}
    return None


async def run_agent(role: Role, prompt: str, deps: TeamDeps,
                    usage: RunUsage | None = None) -> AgentReport:
    """Run one agent to completion. Each loop step (prompt, model turn, tool results,
    final answer) is appended to output/audit_trail.json as it happens."""
    from . import get_agent

    agent = get_agent(role)
    usage = usage if usage is not None else RunUsage()
    audit.record(deps, "run_start", {"prompt": prompt}, usage=usage)
    step = 0
    try:
        async with agent.iter(prompt, deps=deps, usage=usage, usage_limits=TEAM_LIMITS) as run:
            async for node in run:
                step += 1
                described = _describe_node(node)
                if described:
                    audit.record(deps, described[0], described[1], step=step, usage=usage)
        report = run.result.output
    except UsageLimitExceeded as exc:
        audit.record(deps, "error", {"type": "UsageLimitExceeded", "message": str(exc)},
                     step=step, usage=usage)
        report = AgentReport(agent=role, ticket_ids=[deps.ticket_id] if deps.ticket_id else [],
                             status="blocked",
                             summary=f"Stopped by the team token/loop limit: {exc}",
                             next_steps=["A human should review this ticket."])
    except Exception as exc:  # noqa: BLE001 - any failure is reported, never hidden
        audit.record(deps, "error", {"type": type(exc).__name__, "message": str(exc)},
                     step=step, usage=usage)
        report = AgentReport(agent=role, ticket_ids=[deps.ticket_id] if deps.ticket_id else [],
                             status="blocked", summary=f"Agent failed: {type(exc).__name__}: {exc}",
                             next_steps=["A human should review this ticket."])
    approvals.prepare(report, deps)
    audit.record(deps, "run_end", {"status": report.status, "summary": report.summary,
                                   "steps": step}, usage=usage)
    return report
