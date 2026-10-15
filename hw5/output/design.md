# Campus Customs Night Desk: dashboard design

**Run it:** start the backend (`cd backend && uvicorn main:app --reload --port 8000`), then the board (`cd frontend && npm run dev`). It opens at http://localhost:5173 and talks to the backend at http://localhost:8000 (`frontend/.env` → `VITE_API_URL`). The backend allows the Vite origin through CORS (`FRONTEND_ORIGINS` in `backend/main.py`).

## The idea: a shop counter after closing time
Campus Customs is a small shop on Chapel Street, so the dashboard is designed as its **back-office desk at night**: black lacquer, neon pink signage, warm desk lamps that switch on when someone is working. It follows our black-and-pink style and has the Yale SOM logo in the header, Evans Hall behind the title bar, and an Evans Hall photo under the till. The goal was a screen that feels like a place, not a spreadsheet, so a person enjoys sitting at it while five agents work.

## Layout: three zones, read left to right like a real counter

| Zone | What it is | Why |
|---|---|---|
| **Left: the ticket spike** | Each ticket is a paper order stub pinned to a kitchen spike, with a torn edge, a pin hole and a slight tilt. It shows #id, type icon, subject, requester, SKU/size/qty, status, and a "✍️ N to sign" badge. | You see the whole queue at a glance, and picking a ticket feels physical: the stub straightens and slides out, and wiggles while the team works it. |
| **Centre: the floor** | (1) The **ticket hero** with a big pink **"Wake the team ✦"** button. (2) **Five agent desks** in a row. (3) **The live wire**, a feed of what the agents say and do. (4) The **shift report** once the run ends. | The centre is where the action is, so the eye goes from *what's asked* → *who's on it* → *what they're saying* → *what they concluded*. |
| **Right: the till** | A **cash register** with the checking balance on a glowing pink display, and under it the **sign-off tray** where cheques the agents prepared wait for a human signature. | Money and approvals are the two things a human must own, so they stay pinned on screen and never scroll away. |

## How the five agents read differently
Each agent is a **Labubu-style desk creature**: the same toothy, bunny-eared body, so they read as one team, but each has its own **colour, accessory and voice**:

| Agent | Colour | Accessory | Voice tag | Working line |
|---|---|---|---|---|
| Boss | hot pink | gold crown | *decides* | triaging |
| Inventory | lilac | cardboard box | *counts* | checking the shelf, scanning every size |
| Accounting | gold | monocle + $ coin | *tallies* | counting the cash drawer |
| Facilities | sky blue | key | *checks* | reading the lease |
| Customer Service | pink | heart | *writes* | drafting a reply |

- **Desks come alive.** Each desk shows a one-line status built from the event stream ("opening the invoice…", "Waiting on Accounting…"). The **lamp glows in the agent's colour** while it works. When it *talks*, the creature bobs and its toothy mouth chatters. When it signs off it smiles. Creatures also blink every few seconds, which makes the floor feel alive even when idle.
- **Unneeded agents dim.** If an agent isn't called on a ticket, its desk greys out as "Not needed on this ticket" ("Standing by" while the run is still going). That way you can *see* that the Boss didn't send every specialist on every ticket.
- **The live wire uses a different shape for each kind of event**, so you can scan it:
  - **Speech bubbles** (agent colour on the left edge, voice tag, timestamp) for what an agent says, with small chips for the tools it is reaching for, in plain words ("counting the cash drawer", not `get_cash_position`).
  - **Tool receipts**: dashed monospace rows with the exact MCP tool, its arguments and the key result values (e.g. `qty on hand: 0 · shortfall: 1`). These are the facts, so they look like receipts.
  - **Baton passes** for delegation: two mini creatures with a little ✈ flying between them and the task in quotes, so hand-offs between agents are obvious.
  - **Sign-offs** with a coloured border and status pill when an agent finishes, **cheque notes** when it leaves something in the tray, and green **human** rows when a person signs.
  - An **ON AIR** light glows red while the team is running.

## How resolved tickets show up
- The stub gets a pink **RESOLVED rubber stamp** that slams in at an angle, and the paper turns grey like a finished order.
- A toast confirms it ("Ticket #102 resolved. The team signed off.").
- **When a ticket counts as resolved:** the team has finished *and* nothing is waiting on a human. If agents prepared a payment, the ticket says **waiting** with a "✍️ to sign" badge until the human decides every cheque, and only then does the stamp land. Agents can't quietly close a ticket that still needs money moved.
- The **shift report** appears under the feed:
  - the Boss's call;
  - one card per agent that worked, with its status, summary, the MCP tools it used (with counts) and who it passed work to;
  - the Boss's **draft reply to the customer as a lined postcard** with a Yale SOM stamp;
  - a fold-out **"receipts"** table of every fact used and the tool it came from.

## How cash shows up
- **Cash register display.** A big seven-segment-style pink number on a black screen.
- **It visibly drains.** After an approved payment, the number **rolls down** from the old balance to the new one, with a red **▼ $2,400.00** under it, so the human feels the money leave. If it ever drops below the $500 reserve, the display turns red with "Below the $500 reserve".
- **Cheques, not rows.** Each pending approval is drawn as a **cheque**: the kind ("Pay rent #1", "Pay vendor invoice #501", "Approve purchase"), a big amount, the agent's reason, *prepared by* with that agent's creature, and a handwritten-style signature line that fills in with your name. **Approve** (pink) and **Decline** are disabled until you type who is signing, so every approval has a name. The name is saved in the browser.
- A small **ledger of recent sign-offs** (✔ approved, ✕ declined) sits under the tray.
- **Approve is the only thing that moves money.** It calls `POST /api/approvals/{id}/approve`, which runs the MCP `record_payment` tool. If the tool refuses (wrong amount, not enough cash, already paid), the error shows in a red toast and no money moves.

## Small touches that make it pleasant
- **"↺ Fresh shift"** resets the database for a new try (with a confirmation), and **"practice run"** runs the agents with every write blocked.
- A **backend-live** light in the header turns red with the URL if the API is unreachable.
- **Sticky** ticket spike and till, so the queue and the money never leave the screen while the feed scrolls.
- The layout adapts down to tablet and phone, and **`prefers-reduced-motion`** turns all animation off for people who need that.
- **One colour language:** pink = the shop and its actions, gold = money and hand-offs, mint = done or approved, red = blocked or below reserve. Every element uses the same colours for the same meaning.
