"""Facilities agent: owns the shop space and lease. Verifies landlord notices against the
lease on file and hands the rent payment to Accounting.

Prompt: backend/prompts/facilities.md. MCP tools allowed: ROLE_TOOLS["facilities"] in backend/mcp_client.py.
"""

from .base import build_agent

ROLE = "facilities"
agent = build_agent(ROLE)
