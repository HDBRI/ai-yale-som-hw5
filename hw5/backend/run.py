"""Run the Campus Customs team on open tickets from the command line.

    python -m backend.run                 # every open ticket
    python -m backend.run --ticket 101    # one ticket
    python -m backend.run --dry-run       # no writes at all

Each ticket gets its own Boss run (and its own token budget). The Boss delegates to the
other agents, which can also delegate to each other. Agents never pay: payments they
prepare are queued in output/pending_approvals.json for a human to approve on the
dashboard (POST /api/approvals/{id}/approve in backend/main.py).
"""

import argparse
import asyncio
import json

from .mcp_client import SHOP_MCP
from .team import run_ticket


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ticket", type=int, action="append", help="ticket id (repeatable); default: all open")
    p.add_argument("--dry-run", action="store_true", help="block every write tool")
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    async with SHOP_MCP:
        ticket_ids = args.ticket
        if not ticket_ids:
            listing = await SHOP_MCP.direct_call_tool("list_open_tickets", {})
            ticket_ids = [t["id"] for t in listing["tickets"]]
        for ticket_id in ticket_ids:
            run_id, report = await run_ticket(ticket_id, dry_run=args.dry_run, entry="backend.run")
            print(json.dumps({"run_id": run_id, **report.model_dump()}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
