# Campus Customs Agent Harness

**Contents:** database tables → open tickets → MCP tools → the five agents → API routes → dashboard → safety → Task 9 results. Everything here describes the code as submitted. (One design change along the way: in Task 5 an agent could pay a pre-approved bill; from Task 7 on, agents only *prepare* payments and the human's Approve route is the only thing that pays.)

Source data: `data/campus_customs.db` (original, read-only)
Working copy: `data/campus_customs_new.db` (later problems update this one)

---

## Database tables

### `desk`
Fields: `date_today`, `notes`
Why it matters: It sets the store's "today" (2026-08-31), so agents use it for every due-date and overdue check.

### `tickets`
Fields: `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id` → `leases.id`, `invoice_id` → `invoices.id`, `status`, `notes`, `created_at`
Why it matters: It holds the work queue. Each ticket says what was asked and points to the rows an agent has to check before acting.

### `inventory`
Fields: `sku`, `name`, `size`, `qty`, `location` (primary key: `sku` + `size`)
Why it matters: It shows stock by SKU and size, so agents can tell whether an order can be filled now and which aisle to pick from.

### `pricing`
Fields: `sku`, `unit_cost`, `list_price`
Why it matters: It gives the cost floor and the normal price. Agents need both to judge whether a discount request still makes money.

### `vendors`
Fields: `id`, `name`, `specialty`, `lead_days`
Why it matters: It lists who can restock or ship what, and how fast. Agents use it to decide whether a reorder will arrive in time.

### `invoices`
Fields: `id`, `vendor_id` → `vendors.id`, `amount`, `due_date`, `status`, `description`
Why it matters: It tracks bills the shop owes vendors, including whether each one is open or overdue.

### `leases`
Fields: `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`
Why it matters: It holds the shop's rent obligation. This is a large fixed payment that agents must plan cash around.

### `cash_accounts`
Fields: `name`, `balance`, `date`
Why it matters: It shows how much cash the shop can spend. Agents check it before preparing any payment.

### `payments`
Fields: `id`, `kind`, `ref_id`, `amount`, `account` → `cash_accounts.name`, `paid_at`, `approved_by`
Why it matters: It is the audit log for money going out. It starts empty. Every payment is written here by the approve route, with the name of the human who approved it.

---

## Open tickets and how they link to other tables

| Ticket | Type | Ask | Linked rows | What the data shows |
|---|---|---|---|---|
| **101** | customer_order | Tauhid Zaman wants 1 Classic Bulldog Tee, size S | `inventory` (CC-TEE-WHITE, S) · `invoices` 501 → `vendors` 1 (Bulldog Print Co, 5-day lead) | Size S is **out of stock (0)**. Invoice 501 ($840, rush reprint of this tee) is still `open` and was **due 2026-08-28, so it is 3 days overdue**. |
| **102** | rent_notice | Elm City Properties says rent is due | `leases` 1 · `cash_accounts` (checking) | Rent is **$2,400, due 2026-09-02**. Checking has **$3,400**. Paying both the rent and invoice 501 ($3,240 total) would leave only **$160**. |
| **103** | price_override | Yale AI Club wants 20 navy hoodies, size M, at a bulk discount | `inventory` (CC-HOOD-NAVY, M) · `pricing` (CC-HOOD-NAVY) | Only **8 are in stock in size M**, so 12 are missing. The list price is $58 and the unit cost is $22, so any discount has to stay above $22. |

Notes:
- `tickets.sku` / `tickets.size` link to `inventory` and `pricing` only by matching values. There is no foreign key enforcing that link.
- The three tickets are tied together through cash. All three compete for the same $3,400 in checking, so the agents have to look at the whole cash position, not one bill at a time.

---

## MCP tools: the first three (Task 3, `mcp_server/server.py`, FastMCP → `data/campus_customs_new.db`)

### 1. `check_stock(sku, size, qty_needed)`
- **Reads:** `inventory`
- **Unlocks:** Ticket **101**
- **Why:** Ticket 101 asks for 1 Classic Bulldog Tee (`CC-TEE-WHITE`) in size S. This tool returns `qty_on_hand = 0` and `shortfall = 1` for that exact SKU and size, which shows the order can't come off the shelf and has to wait for the overdue Bulldog Print reprint (invoice 501).

### 2. `get_rent_due(lease_id)`
- **Reads:** `leases`, `desk`, `cash_accounts`
- **Unlocks:** Ticket **102**
- **Why:** Ticket 102 points to `lease_id = 1`. This tool returns the $2,400 Chapel Street rent due 2026-09-02, which is 2 days after the desk date of 2026-08-31. It also shows checking falling from $3,400 to $1,000 after rent, so the agent can confirm the email's "due in 2 days" claim and see whether cash covers rent before preparing the payment.

### 3. `get_sku_pricing(sku)`
- **Reads:** `pricing`
- **Unlocks:** Ticket **103**
- **Why:** Ticket 103 asks for a bulk discount on 20 `CC-HOOD-NAVY` hoodies. This tool returns the $58 list price, the $22 unit cost, a $22 break-even price, and a maximum discount of 62.1% before a loss, so the agent can make a counter-offer that still makes money.

---

## All MCP tools (14, after Tasks 5 and 7)

| Tool | Reads / writes | Table(s) | Main ticket |
|---|---|---|---|
| `check_stock` | read | inventory | 101, 103 |
| `get_sku_stock_all_sizes` | read | inventory | 101 (other sizes), 103 (how much of 20 can ship) |
| `get_rent_due` | read | leases, desk, cash_accounts | 102 |
| `get_sku_pricing` | read | pricing | 103 |
| `list_open_tickets` | read | tickets, desk | all (Boss triage) |
| `list_tickets` | read | tickets, desk | all (dashboard: open and resolved, added in Task 7) |
| `get_ticket` | read | tickets | all |
| `get_invoice` | read | invoices, vendors, desk | 101 (reprint invoice 501, overdue) |
| `get_cash_position` | read | cash_accounts, invoices, leases, desk | 101 + 102 (both bills compete for $3,400) |
| `list_vendors` | read | vendors | 101 (who reprints the tee, lead time) |
| `list_payments` | read | payments | 101, 102 (no double payment) |
| `record_payment` | **write**, human only | payments, cash_accounts, invoices / leases, desk | 101 (invoice 501), 102 (rent). Called only by the approve route, never by an agent |
| `adjust_inventory` | **write** | inventory | 101, 103 (only once an order is confirmed) |
| `update_ticket` | **write** | tickets, desk | all |

---

## Agent team (Task 5, PydanticAI, `backend/`)

Every agent uses **`gpt-5.6-luna` through Portkey** (`backend/config.py`), returns the same structured `AgentReport` (`backend/models.py`), and reaches shop data **only** through the MCP server above. A gate in `backend/mcp_client.py` sits in front of the MCP calls; it does not replace them. Any agent can delegate to any other agent with the `delegate` tool, so the team is fully connected. Delegation stops if it would loop back up the chain, go deeper than 3 levels, or exceed 8 hand-offs per run.

| Agent | File / prompt | Owns | MCP tools it may call |
|---|---|---|---|
| **Boss** | `agents/boss.py` · `prompts/boss.md` | Triage, routing, cross-team conflicts (e.g. bills competing for cash), what goes to the human | `list_open_tickets`, `get_ticket`, `get_cash_position`, `list_payments`, `update_ticket` |
| **Inventory** | `agents/inventory.py` · `prompts/inventory.md` | Stock by SKU and size, shortfalls, alternative sizes, reprint and restock path, stock changes | `get_ticket`, `check_stock`, `get_sku_stock_all_sizes`, `list_vendors`, `get_invoice`, `adjust_inventory`, `update_ticket` |
| **Accounting** | `agents/accounting.py` · `prompts/accounting.md` | Cash position, invoices, rent, payment order, **prepares** payments for human approval, discount floor | `get_ticket`, `get_invoice`, `get_cash_position`, `get_rent_due`, `list_payments`, `list_vendors`, `get_sku_pricing`, `update_ticket` |
| **Facilities** | `agents/facilities.py` · `prompts/facilities.md` | Lease, landlord notices (checks them against the lease), rent timing | `get_ticket`, `get_rent_due`, `get_cash_position`, `list_payments`, `update_ticket` |
| **Customer Service** | `agents/customer_service.py` · `prompts/customer_service.md` | Customer replies, options, quotes within discount policy | `get_ticket`, `check_stock`, `get_sku_stock_all_sizes`, `get_sku_pricing`, `update_ticket` |

**Agent loop:** `agents/base.py → run_agent` steps through each run with `agent.iter()`. Every step (prompt, model turn with its tool calls, tool results, final report), every MCP call, every blocked call and every delegation is **appended** to `output/audit_trail.json`. Each entry records the run id, agent, delegation chain, depth, ticket, step, details and running token usage. The file is never wiped. **Run:** `python -m backend.run [--ticket 101] [--dry-run]`, or through the API below. Payments agents prepare are queued in `output/pending_approvals.json`.

---

## Backend routes (Task 7, FastAPI, `backend/main.py`)

Start the server from `backend/` with `uvicorn main:app --reload --port 8000`, using the HW5 venv. It runs at http://localhost:8000, and interactive docs are at `/docs`.

- `GET /api/health` → server is up, which model is used, and which tickets are running now.
- `GET /api/tickets` → all three tickets with every field, plus `state` = **open** or **resolved** (and the detailed status the agents set).
- `POST /api/tickets/{ticket_id}/run` → runs the agent team (Boss first) on that ticket and returns the Boss's report. Add `?wait=false` to start it in the background.
- `GET /api/runs/{run_id}` → status and final report of a run started with `?wait=false`.
- `GET /api/events?limit=50&ticket_id=&run_id=&after=` → recent agent events, newest first: which agent, what it said, which tools it called, the arguments and results (read from `output/audit_trail.json`).
- `GET /api/approvals?status=pending` → payments, purchases and discounts the agents prepared and are waiting for a human.
- `POST /api/approvals/{approval_id}/approve` (body `{"decided_by": "Name"}`) → the human's Approve click. For a payment this is the **only** code that changes cash: it calls MCP `record_payment`, which re-checks the amount, the balance and double payment, then notes the ticket and settles it.
- `POST /api/approvals/{approval_id}/reject` (body `{"decided_by": "Name", "note": "..."}`) → the human declines; no cash moves, and the ticket gets a note.
- `GET /api/tickets/{ticket_id}/summary` → what each agent did on that ticket's latest run: status, summary, MCP tools used, who it delegated to, plus the Boss's full report (customer message, facts). Feeds the board's shift report.
- `GET /api/cash` → the current checking balance from `cash_accounts`.
- `POST /api/reset` → restores `campus_customs_new.db` from the untouched original and clears the approvals queue, for a fresh run. The audit trail is kept, with a `db_reset` entry added.

**When a ticket counts as resolved:** after a run finishes (and isn't blocked or a dry run), the backend sets the ticket to `resolved` if no approvals for it are still pending. Otherwise it stays `waiting` until the human decides the last cheque. Prepared payments are attached to the ticket that owns the bill (rent → the ticket with that lease_id, invoice → the ticket with that invoice_id), so each cash change lands on the right ticket.

---

## Dashboard (Task 8, React + Vite + TypeScript, `frontend/`)

Start it with `cd frontend && npm run dev`. It opens at http://localhost:5173 and calls the backend at http://localhost:8000 (the default in `src/api.ts`; override with `VITE_API_URL` in `frontend/.env`). The full design rationale is in `output/design.md`.

- **Left, the ticket spike:** tickets as paper order stubs showing status, a "✍️ N to sign" badge, and a **RESOLVED** rubber stamp when done.
- **Centre, the floor:** the ticket hero with **Wake the team** (or a *practice run* with all writes blocked); **five Labubu-style agent desks** (own colour, accessory and voice, a lamp that glows while working, greyed out when not needed); **the live wire** feed (speech bubbles, tool receipts with real results, ✈ baton passes for delegations, sign-offs), polled every 1.2 s while running; and the **shift report** after the run (per-agent cards with tools and hand-offs, the Boss's call, a postcard draft to the customer, and a table of the facts used).
- **Right, the till:** a **cash register** showing checking, which rolls down with a ▼ amount after an approved payment and turns red below the $500 reserve; and the **sign-off tray**, where each prepared payment, purchase or discount is a cheque with Approve / Decline, disabled until a signer name is entered, plus a ledger of recent decisions.
- **↺ Fresh shift** calls the reset route.

---

## Safety

**Guardrails for real customers and real money**
- **Agents only prepare payments; a human approves.** No agent can call `record_payment`, and the gate blocks it even if a model tries (tested). Agents list payments under `approvals_needed`, which queues them in `output/pending_approvals.json`. Cash only changes when a human clicks Approve, through `POST /api/approvals/{id}/approve`, which records the human's name as `approved_by`.
- **Payment rules enforced inside the tool:** exact amount owed (no partial or extra payments), the account must cover it, no paying a closed bill twice, rent at most 7 days early, and everything in one database transaction.
- **Cash reserve and payment order** (in the prompts): keep $500 or more in checking; rent first, then overdue invoices that block an order. Anything that breaks this goes to the human.
- **Least privilege:** each agent sees only its own MCP tools. No agent can pay, only Inventory can change stock, and only Customer Service drafts customer messages.
- **Approval is checked twice:** the approve route doesn't trust the agent's amount. MCP `record_payment` re-checks the exact amount owed, the balance and double payment, and refuses on any mismatch (tested: an $800 attempt on the $840 invoice was refused and no cash moved).
- **Signed decisions:** the dashboard's Approve and Decline stay disabled until a signer name is entered, and every decision is written to the ticket notes, the approvals file and the audit trail with that name.
- **No silent closes:** a ticket can't show resolved while any approval for it is still pending.
- **Browser access is local only:** CORS allows the Vite page (`http://localhost:5173`) and other localhost ports, nothing else.
- **Verify before paying:** Facilities checks a landlord notice against the lease (sender, amount, date) and escalates any mismatch or change of payee, which is a guard against payment-redirect scams.
- **Customer protection:** no prices below cost, and discounts limited to 10% (Customer Service alone) / 10–25% (bulk of 10+ units, with Accounting's floor check and Boss sign-off) / anything higher goes to the human. No internal costs or cash in customer messages, and no promised dates the data can't back.
- **Stock integrity:** stock can't go below zero, changes are capped at 50 units, each change needs a reason, and nothing is "reserved" before an order is confirmed.
- **Dry-run mode** (`--dry-run`) blocks every write, for testing on real data.
- **Full audit trail**, append-only, including blocked attempts. Agents work on the working copy; the original `.db` is never touched.

**Limits that keep token use in check**
- **Team-wide budget per ticket:** 30 model requests, 60 tool calls and 250,000 tokens, shared across every delegated agent through one usage counter. Hitting it stops the run cleanly and reports `blocked`.
- **Per call:** at most 4,000 output tokens, a 60-second timeout, and 2 retries.
- **Delegation caps:** depth 3, 8 hand-offs per run, no self-delegation and no sending work back up the chain.
- **One Boss run per ticket**, so each ticket starts with a small context instead of one growing conversation.
- **Audit text is capped at 2,000 characters per field** so the log stays readable.

---

## Task 9 results (full run on the board after a reset)

| Ticket | Boss called first | Delegations | Human decision | Cash change |
|---|---|---|---|---|
| 101 | Inventory ✓ | Boss → Inventory, Boss → Accounting, Accounting → Inventory, Boss → Customer Service | Declined invoice 501 ($840, "hold" for the reserve) and the reprint purchase | $0.00 |
| 102 | Facilities ✓ | Boss → Facilities, Facilities → Accounting, Boss → Accounting | **Approved rent $2,400** | **−$2,400.00** |
| 103 | Inventory ✓ | Boss → Inventory, Boss → Accounting, Accounting → Inventory, Boss → Customer Service, Customer Service → Inventory | Approved 25% bulk discount ($43.50/unit) | $0.00 |

Checking went **$3,400.00 → $1,000.00**, which matches `cash_accounts` (one `payments` row). Facilities was skipped on 101 and 103, and Inventory and Customer Service were skipped on 102, so not every specialist was sent on every ticket. **Waste we saw:** repeated delegations to the same specialist (Inventory 3× on 103, Accounting 2× on 102), which made 103 the most expensive run (26 requests, about 95k tokens). The next fix would be a prompt rule to pass facts you already have down the chain instead of asking again. Details: `output/desk_tickets.html` (Actual and Cash tabs), `output/resolved_tickets.json`, `output/resolved_board.html`, `output/audit_trail.json`.
