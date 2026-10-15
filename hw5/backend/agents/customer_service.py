"""Customer Service agent: owns every message to customers and student groups. Gets the
facts from teammates, offers options within policy and drafts the reply.

Prompt: backend/prompts/customer_service.md. MCP tools allowed: ROLE_TOOLS["customer_service"] in backend/mcp_client.py.
"""

from .base import build_agent

ROLE = "customer_service"
agent = build_agent(ROLE)
