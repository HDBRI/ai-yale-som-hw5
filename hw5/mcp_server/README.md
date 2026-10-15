# Campus Customs MCP Server

A FastMCP server ([server.py](server.py)) that is the **only** way the HW5 agents (and Claude Code) read or change shop data. The tools return values stored in the database, plus simple arithmetic on them. If a row doesn't exist, a tool returns `"found": false` (or `"ok": false`) and does not guess.

**Database:** `data/campus_customs_new.db`, the working copy. The original `data/campus_customs.db` is never touched. Set `CAMPUS_DB` to point a test at a scratch copy.

## Tools (14)

### Read tools (never change data)
| Tool | Reads | What it returns |
|---|---|---|
| `check_stock(sku, size, qty_needed=1)` | inventory | On-hand units, aisle, whether `qty_needed` can be filled, and the shortfall |
| `get_sku_stock_all_sizes(sku)` | inventory | Every size of a SKU and the total on hand |
| `get_rent_due(lease_id)` | leases, desk, cash_accounts | Rent, due date, days until due, cash before and after rent |
| `get_sku_pricing(sku)` | pricing | Unit cost, list price, margin, break-even price, max discount % before a loss |
| `list_open_tickets()` | tickets, desk | Every unresolved ticket, plus `date_today` |
| `list_tickets()` | tickets, desk | Every ticket, open or resolved, plus `date_today` (for the dashboard) |
| `get_ticket(ticket_id)` | tickets | One ticket with all fields |
| `get_invoice(invoice_id)` | invoices, vendors, desk | Amount, due date, status, days past due, vendor and lead time |
| `get_cash_position()` | cash_accounts, invoices, leases, desk | All balances, open invoices, upcoming rent, and the cash left if everything is paid |
| `list_vendors()` | vendors | Vendor specialty and lead time |
| `list_payments()` | payments | Payments already recorded |

### Write tools (enforce shop rules themselves)
| Tool | Writes | Rules |
|---|---|---|
| `record_payment(kind, ref_id, amount, account, approved_by)` | payments, cash_accounts, invoices / leases | `kind` is invoice or rent; exact amount only; balance must cover it; no double payment; rent at most 7 days early; needs a named approver; one transaction |
| `adjust_inventory(sku, size, delta, reason)` | inventory | Reason required; never below zero; at most 50 units per change |
| `update_ticket(ticket_id, status, note, author)` | tickets | Status must be open / in_progress / waiting / resolved / escalated; notes are appended with the date and author, never overwritten |

The agent backend adds one more check in front of these tools (`backend/mcp_client.py`): each agent role sees only its own tools, no agent may call `record_payment` (only the dashboard's approve route does, after a human clicks Approve), and every call is written to `output/audit_trail.json`.

## Run

```bash
pip install -r mcp_server/requirements.txt
python mcp_server/server.py
```

It is registered for Claude Code in `.mcp.json`, and the agents start it over stdio with the same command.
