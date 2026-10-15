"""Accounting agent: owns cash and bills. Checks invoices, rent and the cash position,
pays only what a human approved, and sets the price floor for any discount.

Prompt: backend/prompts/accounting.md. MCP tools allowed: ROLE_TOOLS["accounting"] in backend/mcp_client.py.
"""

from .base import build_agent

ROLE = "accounting"
agent = build_agent(ROLE)
