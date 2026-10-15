"""Campus Customs MCP server.

Every agent in HW5 gets its store data through these tools. All tools work
on data/campus_customs_new.db (the working copy) and only return values
that exist in the database, or simple arithmetic on those values. If a row
is missing, the tool says so instead of guessing.

Read tools never change the database. The three write tools
(record_payment, adjust_inventory, update_ticket) check the shop's rules
themselves and refuse anything that breaks them, so a confused agent
cannot overdraw cash, push stock below zero or pay the same bill twice.
"""

import os
import sqlite3
from calendar import monthrange
from datetime import date
from pathlib import Path

from fastmcp import FastMCP

DB_PATH = Path(
    os.getenv("CAMPUS_DB")
    or Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"
)

# Shop rules enforced inside the write tools.
RENT_PAY_WINDOW_DAYS = 7      # rent may be paid at most this many days early
MAX_STOCK_ADJUSTMENT = 50     # largest single inventory change in units
TICKET_STATUSES = {"open", "in_progress", "waiting", "resolved", "escalated"}

mcp = FastMCP("campus-customs")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _today(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT date_today FROM desk").fetchone()
    return row["date_today"] if row else None


def _add_month(iso_day: str) -> str:
    d = date.fromisoformat(iso_day)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(year, month, min(d.day, monthrange(year, month)[1])).isoformat()


@mcp.tool()
def check_stock(sku: str, size: str, qty_needed: int = 1) -> dict:
    """Look up how many units of a SKU/size are on the shelf and whether
    a request for qty_needed units can be filled from stock.

    Reads: inventory
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory "
            "WHERE sku = ? AND size = ?",
            (sku, size),
        ).fetchone()
        if row is None:
            sizes = [
                r["size"]
                for r in conn.execute(
                    "SELECT size FROM inventory WHERE sku = ?", (sku,)
                )
            ]
            return {
                "found": False,
                "sku": sku,
                "size": size,
                "error": "No inventory row for this SKU and size.",
                "sizes_on_record_for_sku": sizes,
            }

    on_hand = row["qty"]
    return {
        "found": True,
        "sku": row["sku"],
        "name": row["name"],
        "size": row["size"],
        "location": row["location"],
        "qty_on_hand": on_hand,
        "qty_needed": qty_needed,
        "can_fill_from_stock": on_hand >= qty_needed,
        "shortfall": max(qty_needed - on_hand, 0),
    }


@mcp.tool()
def get_rent_due(lease_id: int) -> dict:
    """Return the rent owed on a lease, how many days until it is due
    (measured from the desk's date_today), and the cash balances
    available to pay it.

    Reads: leases, desk, cash_accounts
    """
    with _connect() as conn:
        lease = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes "
            "FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        if lease is None:
            return {"found": False, "lease_id": lease_id,
                    "error": "No lease with this id."}
        desk = conn.execute("SELECT date_today FROM desk").fetchone()
        accounts = conn.execute(
            "SELECT name, balance, date FROM cash_accounts"
        ).fetchall()

    today = desk["date_today"] if desk else None
    days_until_due = (
        (date.fromisoformat(lease["next_due"]) - date.fromisoformat(today)).days
        if today else None
    )
    rent = lease["monthly_rent"]
    return {
        "found": True,
        "lease_id": lease["id"],
        "space_name": lease["space_name"],
        "landlord": lease["landlord"],
        "monthly_rent": rent,
        "next_due": lease["next_due"],
        "date_today": today,
        "days_until_due": days_until_due,
        "notes": lease["notes"],
        "cash_accounts": [
            {
                "name": a["name"],
                "balance": a["balance"],
                "as_of": a["date"],
                "balance_after_rent": a["balance"] - rent,
            }
            for a in accounts
        ],
    }


@mcp.tool()
def get_sku_pricing(sku: str) -> dict:
    """Return the unit cost and list price for a SKU, plus the per-unit
    margin and the lowest price that still covers cost.

    Reads: pricing
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?",
            (sku,),
        ).fetchone()
    if row is None:
        return {"found": False, "sku": sku,
                "error": "No pricing row for this SKU."}

    cost, price = row["unit_cost"], row["list_price"]
    return {
        "found": True,
        "sku": row["sku"],
        "unit_cost": cost,
        "list_price": price,
        "margin_per_unit": price - cost,
        "break_even_price": cost,
        "max_discount_pct_before_loss": round((price - cost) / price * 100, 1),
    }


# ---------- read tools added in Task 5 ----------


@mcp.tool()
def list_open_tickets() -> dict:
    """List every ticket that is not resolved, with all of its fields,
    plus the desk's date_today.

    Reads: tickets, desk
    """
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE status != 'resolved' ORDER BY id"
        ).fetchall()
        today = _today(conn)
    return {"date_today": today, "count": len(rows),
            "tickets": [dict(r) for r in rows]}


@mcp.tool()
def list_tickets() -> dict:
    """List every ticket, resolved or not, with all of its fields,
    plus the desk's date_today.

    Reads: tickets, desk
    """
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
        today = _today(conn)
    return {"date_today": today, "count": len(rows),
            "tickets": [dict(r) for r in rows]}


@mcp.tool()
def get_ticket(ticket_id: int) -> dict:
    """Return one ticket with all of its fields.

    Reads: tickets
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
    if row is None:
        return {"found": False, "ticket_id": ticket_id,
                "error": "No ticket with this id."}
    return {"found": True, **dict(row)}


@mcp.tool()
def get_sku_stock_all_sizes(sku: str) -> dict:
    """Return stock for every size of a SKU, plus the total on hand.
    Use it to offer a customer another size or to see how much of a
    bulk order could ship today.

    Reads: inventory
    """
    with _connect() as conn:
        rows = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory "
            "WHERE sku = ? ORDER BY rowid",
            (sku,),
        ).fetchall()
    if not rows:
        return {"found": False, "sku": sku,
                "error": "No inventory rows for this SKU."}
    return {
        "found": True,
        "sku": sku,
        "name": rows[0]["name"],
        "sizes": [{"size": r["size"], "qty": r["qty"],
                   "location": r["location"]} for r in rows],
        "total_on_hand": sum(r["qty"] for r in rows),
    }


@mcp.tool()
def get_invoice(invoice_id: int) -> dict:
    """Return an invoice with its vendor, and how many days it is
    overdue (or until due) measured from the desk's date_today.

    Reads: invoices, vendors, desk
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT i.id, i.vendor_id, i.amount, i.due_date, i.status, "
            "i.description, v.name AS vendor_name, v.specialty, v.lead_days "
            "FROM invoices i LEFT JOIN vendors v ON v.id = i.vendor_id "
            "WHERE i.id = ?",
            (invoice_id,),
        ).fetchone()
        today = _today(conn)
    if row is None:
        return {"found": False, "invoice_id": invoice_id,
                "error": "No invoice with this id."}
    days_past_due = (
        (date.fromisoformat(today) - date.fromisoformat(row["due_date"])).days
        if today else None
    )
    return {
        "found": True,
        "invoice_id": row["id"],
        "amount": row["amount"],
        "due_date": row["due_date"],
        "status": row["status"],
        "description": row["description"],
        "date_today": today,
        "days_past_due": days_past_due,
        "is_overdue": row["status"] == "open" and (days_past_due or 0) > 0,
        "vendor": {"id": row["vendor_id"], "name": row["vendor_name"],
                   "specialty": row["specialty"],
                   "lead_days": row["lead_days"]},
    }


@mcp.tool()
def get_cash_position() -> dict:
    """Return every cash account balance, every open invoice and every
    lease's next rent, so Accounting can see whether all current bills
    fit in the cash on hand before paying any one of them.

    Reads: cash_accounts, invoices, leases, desk
    """
    with _connect() as conn:
        accounts = conn.execute(
            "SELECT name, balance, date FROM cash_accounts"
        ).fetchall()
        invoices = conn.execute(
            "SELECT id, vendor_id, amount, due_date, description FROM invoices "
            "WHERE status = 'open' ORDER BY due_date"
        ).fetchall()
        leases = conn.execute(
            "SELECT id, space_name, monthly_rent, next_due FROM leases "
            "ORDER BY next_due"
        ).fetchall()
        today = _today(conn)
    total_cash = sum(a["balance"] for a in accounts)
    open_bills = (sum(i["amount"] for i in invoices)
                  + sum(l["monthly_rent"] for l in leases))
    return {
        "date_today": today,
        "accounts": [{"name": a["name"], "balance": a["balance"],
                      "as_of": a["date"]} for a in accounts],
        "total_cash": total_cash,
        "open_invoices": [dict(i) for i in invoices],
        "upcoming_rent": [dict(l) for l in leases],
        "total_open_bills": open_bills,
        "cash_after_all_bills": total_cash - open_bills,
    }


@mcp.tool()
def list_vendors() -> dict:
    """List every vendor with its specialty and lead time in days.

    Reads: vendors
    """
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors ORDER BY id"
        ).fetchall()
    return {"vendors": [dict(r) for r in rows]}


@mcp.tool()
def list_payments() -> dict:
    """List every payment already recorded, newest first. Check this
    before paying anything so nothing is paid twice.

    Reads: payments
    """
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM payments ORDER BY id DESC"
        ).fetchall()
    return {"count": len(rows), "payments": [dict(r) for r in rows]}


# ---------- write tools added in Task 5 ----------


@mcp.tool()
def record_payment(kind: str, ref_id: int, amount: float, account: str,
                   approved_by: str) -> dict:
    """Pay an open invoice (kind='invoice', ref_id=invoices.id) or a
    lease's rent (kind='rent', ref_id=leases.id) from a cash account.

    The amount must equal the bill exactly, the account must cover it,
    approved_by must name the human who approved it, and the same bill
    cannot be paid twice. On success it writes one payments row,
    lowers the account balance, and marks the invoice paid or moves the
    lease's next_due forward one month, all in one transaction.

    Reads/writes: payments, cash_accounts, invoices or leases, desk
    """
    if not approved_by or not approved_by.strip():
        return {"ok": False, "error": "approved_by is required: a named "
                "human must approve every payment."}
    if kind not in ("invoice", "rent"):
        return {"ok": False, "error": "kind must be 'invoice' or 'rent'."}

    with _connect() as conn:
        today = _today(conn)
        acct = conn.execute(
            "SELECT name, balance FROM cash_accounts WHERE name = ?",
            (account,),
        ).fetchone()
        if acct is None:
            return {"ok": False, "error": f"No cash account named '{account}'."}

        if kind == "invoice":
            bill = conn.execute(
                "SELECT id, amount, status FROM invoices WHERE id = ?",
                (ref_id,),
            ).fetchone()
            if bill is None:
                return {"ok": False, "error": "No invoice with this id."}
            if bill["status"] != "open":
                return {"ok": False, "error": f"Invoice is already "
                        f"'{bill['status']}', so it cannot be paid again."}
            owed = bill["amount"]
        else:
            bill = conn.execute(
                "SELECT id, monthly_rent, next_due FROM leases WHERE id = ?",
                (ref_id,),
            ).fetchone()
            if bill is None:
                return {"ok": False, "error": "No lease with this id."}
            days_early = (date.fromisoformat(bill["next_due"])
                          - date.fromisoformat(today)).days
            if days_early > RENT_PAY_WINDOW_DAYS:
                return {"ok": False, "error": f"Rent is due {bill['next_due']}, "
                        f"{days_early} days away; rent can be paid at most "
                        f"{RENT_PAY_WINDOW_DAYS} days early."}
            owed = bill["monthly_rent"]

        if round(amount, 2) != round(owed, 2):
            return {"ok": False, "error": f"Amount {amount} does not match the "
                    f"{owed} owed. Partial or extra payments are not allowed."}
        if acct["balance"] < owed:
            return {"ok": False, "error": f"Account '{account}' has "
                    f"{acct['balance']}, less than the {owed} owed."}

        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, "
            "approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (kind, ref_id, owed, account, today, approved_by.strip()),
        )
        conn.execute(
            "UPDATE cash_accounts SET balance = balance - ?, date = ? "
            "WHERE name = ?",
            (owed, today, account),
        )
        if kind == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?",
                         (ref_id,))
            new_state = {"invoice_status": "paid"}
        else:
            next_due = _add_month(bill["next_due"])
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?",
                         (next_due, ref_id))
            new_state = {"lease_next_due": next_due}
        balance_after = conn.execute(
            "SELECT balance FROM cash_accounts WHERE name = ?", (account,)
        ).fetchone()["balance"]

    return {"ok": True, "payment_id": cur.lastrowid, "kind": kind,
            "ref_id": ref_id, "amount": owed, "account": account,
            "paid_at": today, "approved_by": approved_by.strip(),
            "balance_after": balance_after, **new_state}


@mcp.tool()
def adjust_inventory(sku: str, size: str, delta: int, reason: str) -> dict:
    """Change the on-hand quantity of one SKU/size by delta (negative
    to ship or pull stock, positive to receive a delivery). A reason is
    required, stock can never go below zero, and one change is capped
    at MAX_STOCK_ADJUSTMENT units.

    Reads/writes: inventory
    """
    if not reason or not reason.strip():
        return {"ok": False, "error": "A reason is required."}
    if delta == 0 or abs(delta) > MAX_STOCK_ADJUSTMENT:
        return {"ok": False, "error": f"delta must be non-zero and at most "
                f"{MAX_STOCK_ADJUSTMENT} units either way."}
    with _connect() as conn:
        row = conn.execute(
            "SELECT qty FROM inventory WHERE sku = ? AND size = ?",
            (sku, size),
        ).fetchone()
        if row is None:
            return {"ok": False, "error": "No inventory row for this SKU and size."}
        new_qty = row["qty"] + delta
        if new_qty < 0:
            return {"ok": False, "error": f"Only {row['qty']} on hand; cannot "
                    f"remove {-delta}."}
        conn.execute(
            "UPDATE inventory SET qty = ? WHERE sku = ? AND size = ?",
            (new_qty, sku, size),
        )
    return {"ok": True, "sku": sku, "size": size, "qty_before": row["qty"],
            "qty_after": new_qty, "reason": reason.strip()}


@mcp.tool()
def update_ticket(ticket_id: int, status: str, note: str, author: str) -> dict:
    """Set a ticket's status and append a dated note signed by author.
    Earlier notes are kept, never overwritten.
    Status must be one of: open, in_progress, waiting, resolved, escalated.

    Reads/writes: tickets, desk
    """
    if status not in TICKET_STATUSES:
        return {"ok": False, "error": f"status must be one of "
                f"{sorted(TICKET_STATUSES)}."}
    if not note or not note.strip():
        return {"ok": False, "error": "A note is required."}
    with _connect() as conn:
        row = conn.execute(
            "SELECT status, notes FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        if row is None:
            return {"ok": False, "error": "No ticket with this id."}
        entry = f"[{_today(conn)} {author.strip() or 'agent'}] {note.strip()}"
        notes = f"{row['notes']}\n{entry}" if row["notes"] else entry
        conn.execute(
            "UPDATE tickets SET status = ?, notes = ? WHERE id = ?",
            (status, notes, ticket_id),
        )
    return {"ok": True, "ticket_id": ticket_id, "status_before": row["status"],
            "status_after": status, "notes": notes}


if __name__ == "__main__":
    mcp.run()
