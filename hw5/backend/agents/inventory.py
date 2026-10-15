"""Inventory agent: owns stock by SKU and size. Answers whether an order can ship today,
finds shortfalls, checks reprint and restock status with vendors, and records stock changes.

Prompt: backend/prompts/inventory.md. MCP tools allowed: ROLE_TOOLS["inventory"] in backend/mcp_client.py.
"""

from .base import build_agent

ROLE = "inventory"
agent = build_agent(ROLE)
