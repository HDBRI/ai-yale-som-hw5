"""Boss agent: runs the desk. Reads every open ticket, decides which teammates handle which part,
settles conflicts (e.g. two bills competing for the same cash) and decides what a human must approve.

Prompt: backend/prompts/boss.md. MCP tools allowed: ROLE_TOOLS["boss"] in backend/mcp_client.py.
"""

from .base import build_agent

ROLE = "boss"
agent = build_agent(ROLE)
