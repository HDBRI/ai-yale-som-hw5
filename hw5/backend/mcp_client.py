"""The one connection to the Campus Customs MCP server, shared by all five agents.

Agents never touch SQLite. Every shop fact and every write goes through the MCP
server (mcp_server/server.py over data/campus_customs_new.db). This module only
adds a gate in front of the MCP calls:

* each agent sees only the MCP tools its role allows (ROLE_TOOLS);
* write tools are blocked in --dry-run mode;
* no agent can call record_payment. Agents only PREPARE payments (approvals_needed in
  their report, queued in output/pending_approvals.json). The dashboard's approve route
  in backend/main.py is the only code that pays, after a human clicks Approve;
* every call (allowed or blocked) is written to the audit trail.
"""

import os
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic_ai import RunContext
from pydantic_ai.mcp import CallToolFunc, MCPToolset
from pydantic_ai.tools import ToolDefinition

from . import audit
from .config import MCP_PYTHON, MCP_SCRIPT
from .models import Role, TeamDeps

READ_TOOLS = {
    "check_stock", "get_sku_stock_all_sizes", "get_rent_due", "get_sku_pricing",
    "list_open_tickets", "get_ticket", "get_invoice", "get_cash_position",
    "list_vendors", "list_payments",
}
WRITE_TOOLS = {"record_payment", "adjust_inventory", "update_ticket"}
HUMAN_ONLY_TOOLS = {"record_payment"}  # called only by the approve route, never by an agent

# Least privilege: which MCP tools each role may call.
ROLE_TOOLS: dict[Role, set[str]] = {
    "boss": {"list_open_tickets", "get_ticket", "get_cash_position", "list_payments",
             "update_ticket"},
    "inventory": {"get_ticket", "check_stock", "get_sku_stock_all_sizes", "list_vendors",
                  "get_invoice", "adjust_inventory", "update_ticket"},
    "accounting": {"get_ticket", "get_invoice", "get_cash_position", "get_rent_due",
                   "list_payments", "list_vendors", "get_sku_pricing", "update_ticket"},
    "facilities": {"get_ticket", "get_rent_due", "get_cash_position", "list_payments",
                   "update_ticket"},
    "customer_service": {"get_ticket", "check_stock", "get_sku_stock_all_sizes",
                         "get_sku_pricing", "update_ticket"},
}


async def _gate(ctx: RunContext[TeamDeps], call_tool: CallToolFunc, name: str,
                args: dict[str, Any]) -> Any:
    deps = ctx.deps
    shared = deps.shared

    def blocked(reason: str) -> dict:
        audit.record(deps, "mcp_tool_blocked", {"tool": name, "args": args, "reason": reason},
                     usage=ctx.usage)
        return {"ok": False, "blocked_by_policy": True, "error": reason}

    if name in HUMAN_ONLY_TOOLS:
        return blocked("Agents cannot pay. Put the payment under approvals_needed with the exact "
                       "amount; a human approves it on the dashboard.")
    if name not in ROLE_TOOLS[deps.role]:
        return blocked(f"The {deps.role} agent is not allowed to call {name}.")
    if name in WRITE_TOOLS and shared.dry_run:
        return blocked("Dry run: no changes may be written. Report what you would do instead.")

    if name == "update_ticket":
        args = {**args, "author": f"{deps.role} agent"}

    result = await call_tool(name, args)
    audit.record(deps, "mcp_tool_call", {"tool": name, "args": args, "result": result,
                                         "write": name in WRITE_TOOLS}, usage=ctx.usage)
    return result


def build_toolset() -> MCPToolset:
    """One stdio connection to the MCP server, opened once per team run.

    The server gets only the environment it needs to start (no API keys).
    CAMPUS_DB lets a test point it at a scratch copy of the database.
    """
    env = {k: os.environ[k] for k in ("SYSTEMROOT", "PATH", "TEMP", "TMP", "HOME", "CAMPUS_DB")
           if k in os.environ}
    transport = StdioTransport(command=str(MCP_PYTHON), args=[str(MCP_SCRIPT)], env=env)
    return MCPToolset(Client(transport), process_tool_call=_gate, max_retries=2)


SHOP_MCP = build_toolset()


def toolset_for(role: Role, toolset: MCPToolset):
    """The same MCP connection, filtered down to the tools this role may see."""
    allowed = ROLE_TOOLS[role]

    def visible(ctx: RunContext[TeamDeps], tool_def: ToolDefinition) -> bool:
        return tool_def.name in allowed

    return toolset.filtered(visible)
